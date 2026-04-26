import pytest
from unittest.mock import patch
from inkwell.app import create_app
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ------------------------------------------------------------------
# Tests for POST /signals/{signal_id}/draft
# ------------------------------------------------------------------


@pytest.mark.asyncio
@patch("inkwell.routes.api_signals._find_signal")
@patch("inkwell.routes.api_signals.load_personality")
@patch("inkwell.routes.api_signals.draft_voice")
async def test_draft_signal_uses_correct_rawsignal_structure(
    mock_draft, mock_personality, mock_find, client
):
    mock_find.return_value = (
        {
            "platform": "reddit",
            "platform_id": "t3_123",
            "url": "https://reddit.com/r/test",
            "title": "Scaling Solr",
            "body": "How do I handle 74M docs?",
            "author": "dev_user",
            "score": 100,
            "reply_count": 5,
            "created_utc": 1714000000.0,
            "subreddit": "solr",
            "analysis": {"coolest_comment": "Try partitioning."},
            "drafts": None,
        },
        "2026-04-25",
    )

    mock_personality.return_value = {"bio": "Expert Engineer", "example_comments": ["Comment 1"]}
    mock_draft.return_value = ["Drafted Reply"]

    payload = {"model": "gpt-4o"}
    headers = {"X-LLM-Key": "sk-test"}
    response = await client.post("/api/signals/t3_123/draft", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"drafts": ["Drafted Reply"], "cached": False, "model": "gpt-4o"}


@pytest.mark.asyncio
@patch("inkwell.routes.api_signals._find_signal")
async def test_draft_signal_not_found(mock_find, client):
    mock_find.return_value = (None, None)
    response = await client.post("/api/signals/t3_123/draft", json={"model": "gpt-4"})
    assert response.status_code == 404


@pytest.mark.asyncio
@patch("inkwell.routes.api_signals._find_signal")
async def test_draft_signal_fails_on_missing_key(mock_find, client):
    mock_find.return_value = ({"platform_id": "t3_123"}, "2026-04-25")

    response = await client.post("/api/signals/t3_123/draft", json={"model": "gpt-4"})
    assert response.status_code == 400
    assert "No API key" in response.json()["detail"]


@pytest.mark.asyncio
@patch("inkwell.routes.api_signals._find_signal")
async def test_draft_signal_fails_on_missing_model(mock_find, client):
    mock_find.return_value = ({"platform_id": "t3_123"}, "2026-04-25")
    response = await client.post("/api/signals/t3_123/draft", json={"model": "   "})
    assert response.status_code == 400
    assert "Model is required" in response.json()["detail"]


@pytest.mark.asyncio
@patch("inkwell.routes.api_signals._find_signal")
@patch("inkwell.routes.api_signals._update_stored_signal")
async def test_draft_signal_persistence_logic(mock_update, mock_find, client):
    mock_find.return_value = ({"platform_id": "t3_123", "drafts": None}, "2026-04-25")

    with patch("inkwell.routes.api_signals.draft_voice", return_value=["New Draft"]):
        await client.post(
            "/api/signals/t3_123/draft", json={"model": "gpt-4o"}, headers={"X-LLM-Key": "key"}
        )

    args, _ = mock_update.call_args
    date_str, sig_id, patch_data = args

    assert date_str == "2026-04-25"
    assert sig_id == "t3_123"
    assert patch_data["drafts"] == ["New Draft"]
    assert patch_data["draft_model"] == "gpt-4o"


@pytest.mark.asyncio
@patch("inkwell.routes.api_signals._find_signal")
@patch("inkwell.routes.api_signals.draft_voice")
async def test_draft_signal_llm_failure_handling(mock_draft, mock_find, client):
    mock_find.return_value = ({"platform_id": "t3_123", "drafts": None}, "2026-04-25")
    mock_draft.return_value = None

    response = await client.post(
        "/api/signals/t3_123/draft", json={"model": "gpt-4o"}, headers={"X-LLM-Key": "key"}
    )

    assert response.status_code == 502
    assert "LLM call failed" in response.json()["detail"]
