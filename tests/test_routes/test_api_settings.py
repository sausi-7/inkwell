import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from inkwell.app import create_app
import pytest_asyncio


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
# Tests for POST /api/settings/test-llm
# ------------------------------------------------------------------
@pytest.mark.asyncio
@patch("inkwell.routes.api_settings.litellm.completion")
async def test_llm_probe_success(mock_completion, client):
    mock_completion.return_value = {"choices": [{"message": {"content": "pong"}}]}

    payload = {"model": "gpt-4o"}
    headers = {"X-LLM-Key": "sk-valid-key"}

    response = await client.post("/api/settings/test-llm", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "gpt-4o responded" in data["detail"]

    args, kwargs = mock_completion.call_args
    assert kwargs["model"] == "gpt-4o"
    assert kwargs["api_key"] == "sk-valid-key"
    assert kwargs["max_tokens"] == 1


@pytest.mark.asyncio
@patch("inkwell.routes.api_settings.litellm.completion")
async def test_llm_probe_handles_auth_failure_and_redacts_key(mock_completion, client):
    secret_key = "sk-very-secret-123"
    mock_completion.side_effect = Exception(f"Invalid Request: Unauthorized for key {secret_key}")

    payload = {"model": "claude-3-opus"}
    headers = {"X-LLM-Key": secret_key}

    response = await client.post("/api/settings/test-llm", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert secret_key not in data["detail"]
    assert "[redacted]" in data["detail"]


@pytest.mark.asyncio
async def test_llm_probe_fails_if_model_missing(client):
    response = await client.post("/api/settings/test-llm", json={"model": "  "})

    assert response.status_code == 200  # App logic returns ok: False instead of 422
    assert response.json()["ok"] is False
    assert "Model is required" in response.json()["detail"]


@pytest.mark.asyncio
@patch("inkwell.routes.api_settings.litellm.completion")
async def test_llm_probe_works_without_header(mock_completion, client):
    mock_completion.return_value = {"ok": True}

    response = await client.post("/api/settings/test-llm", json={"model": "gpt-3.5-turbo"})

    assert response.status_code == 200
    # Ensure api_key was NOT passed to litellm if header was missing
    _, kwargs = mock_completion.call_args
    assert "api_key" not in kwargs
