import pytest
import json
import time
from queue import Queue
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
import pytest_asyncio

from inkwell.app import create_app
from inkwell.routes.api_scan import _scan_state

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    _scan_state["running"] = False
    _scan_state["started_at"] = None
    _scan_state["current_subreddit"] = None
    _scan_state["cancel"] = False
    _scan_state["queue"] = None

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ------------------------------------------------------------------
# Tests for GET /api/scan/status
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_scan_status_idle(client):
    response = await client.get("/api/scan/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert data["current_subreddit"] is None


@pytest.mark.asyncio
async def test_get_scan_status_running(client):
    _scan_state["running"] = True
    _scan_state["current_subreddit"] = "r/python"

    response = await client.get("/api/scan/status")
    data = response.json()
    assert data["running"] is True
    assert data["current_subreddit"] == "r/python"


# ------------------------------------------------------------------
# Tests for POST /api/scan
# ------------------------------------------------------------------


@pytest.mark.asyncio
@patch("inkwell.routes.api_scan._run_scan_with_emit")
async def test_start_scan_success(mock_run, client):

    def mock_emit_logic(emit, options):
        emit({"kind": "start", "subreddit_count": 2})
        emit({"kind": "done", "scanned": 2, "new_signals": 0})

    mock_run.side_effect = mock_emit_logic

    response = await client.post("/api/scan", json={"limit_subreddits": 2})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = response.text.strip().split("\n\n")
    assert 'data: {"kind": "start", "subreddit_count": 2}' in events[0]
    assert 'data: {"kind": "done"' in events[1]

    assert _scan_state["running"] is False


@pytest.mark.asyncio
async def test_start_scan_conflict(client):
    _scan_state["running"] = True

    response = await client.post("/api/scan", json={})
    assert response.status_code == 409
    assert "already running" in response.json()["detail"]


@patch("inkwell.routes.api_scan.logger")
@patch("inkwell.routes.api_scan._run_scan_with_emit")
@pytest.mark.asyncio
async def test_start_scan_exception_handling(mock_run, mock_logger, client):
    mock_run.side_effect = Exception("Reddit API Down/Timeout")

    response = await client.post("/api/scan", json={})

    assert 'data: {"kind": "error", "message": "Reddit API Down/Timeout"}' in response.text
    assert _scan_state["running"] is False


@patch("inkwell.routes.api_scan._run_scan_with_emit")
@pytest.mark.asyncio
async def test_scan_heartbeat_precedes_completion_on_stall(mock_run, client):
    def stalling_scan(emit, options):
        # 7s stall > 5s heartbeat interval
        time.sleep(7.0)
        emit({"kind": "done", "scanned": 1})

    mock_run.side_effect = stalling_scan

    response = await client.post("/api/scan", json={"limit_subreddits": 1})

    events = [ev for ev in response.text.strip().split("\n\n") if ev.startswith("data:")]

    heartbeat_index = next((i for i, ev in enumerate(events) if '"kind": "heartbeat"' in ev), -1)
    done_index = next((i for i, ev in enumerate(events) if '"kind": "done"' in ev), -1)

    assert heartbeat_index != -1, "No heartbeat detected"
    assert done_index != -1, "Scan never finished"

    assert heartbeat_index < done_index, (
        f"Heartbeat (pos {heartbeat_index}) should have arrived "
        f"before scan completion (pos {done_index})"
    )

    heartbeat_data = json.loads(events[heartbeat_index].replace("data: ", ""))
    assert heartbeat_data["elapsed_s"] >= 5.0


@patch("inkwell.routes.api_scan._run_scan_with_emit")
@pytest.mark.asyncio
async def test_rapid_restart(mock_run, client):
    await client.post("/api/scan")
    response = await client.post("/api/scan")
    assert response.status_code == 200  # Should NOT be 409


# ------------------------------------------------------------------
# Tests for POST /api/scan/stop
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_scan_not_running(client):
    response = await client.post("/api/scan/stop")
    assert response.json() == {"ok": False, "detail": "No scan is running."}


@pytest.mark.asyncio
async def test_stop_scan_success(client):
    """Verify stop sets cancel flag and injects event into queue."""
    mock_queue = Queue()
    _scan_state["running"] = True
    _scan_state["queue"] = mock_queue

    response = await client.post("/api/scan/stop")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert _scan_state["cancel"] is True

    # Verify the 'cancelled' event was pushed to wake up the SSE stream
    injected_event = mock_queue.get()
    assert injected_event["kind"] == "cancelled"
