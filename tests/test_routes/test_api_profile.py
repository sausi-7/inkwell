import pytest
import httpx
from unittest.mock import patch

from inkwell.app import create_app
from inkwell.routes.api_profile import _is_meaningfully_configured

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
async def client():
    """Create a fresh Async httpx Client for each test."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ------------------------------------------------------------------
# Logic Tests
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "personality_dict, expected",
    [
        ({"bio": "I am a dev", "example_comments": ["Comment 1"]}, True),
        ({"bio": "", "example_comments": ["Comment 1"]}, False),
        ({"bio": "I am a dev", "example_comments": []}, False),
        ({"bio": "    ", "example_comments": ["Comment 1"]}, False),
        ({}, False),
    ],
    ids=[
        "fully_configured_profile",
        "missing_bio_content",
        "missing_example_comments",
        "bio_with_only_whitespace",
        "totally_empty_dictionary",
    ],
)
def test_is_meaningfully_configured(personality_dict, expected):
    assert _is_meaningfully_configured(personality_dict) is expected


# ------------------------------------------------------------------
# Tests for GET /api/profile
# ------------------------------------------------------------------


@pytest.mark.asyncio
@patch("inkwell.routes.api_profile.load_personality")
async def test_get_profile_success(mock_load, client):
    mock_load.return_value = {
        "name": "Name",
        "bio": "A multi-line bio string\nthat represents a persona.\n",
        "example_comments": ["Example 1"],
    }

    response = await client.get("/api/profile")
    assert response.status_code == 200

    data = response.json()
    assert data["profile"]["name"] == "Name"
    assert data["configured"] is True


@pytest.mark.asyncio
@patch("inkwell.routes.api_profile.load_personality")
async def test_get_profile_not_configured(mock_load, client):
    mock_load.return_value = {}

    response = await client.get("/api/profile")
    assert response.status_code == 200
    assert response.json()["configured"] is False


# ------------------------------------------------------------------
# Tests for POST /api/profile
# ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected_tone_structure",
    [
        (
            {"name": "Name", "tone": {"style": "witty", "humor": "dry", "formality": "casual"}},
            {"style": "witty", "humor": "dry", "formality": "casual"},
        ),
        ({"name": "Name1", "tone": {"style": "", "humor": "", "formality": ""}}, {}),
    ],
    ids=["save_full", "save_empty_tone"],
)
@patch("inkwell.routes.api_profile.write_yaml")
async def test_save_profile_scenarios(mock_write, client, payload, expected_tone_structure):
    mock_write.return_value = "personality.yml"

    # Await the post call
    response = await client.post("/api/profile", json=payload)

    assert response.status_code == 200
    actual_data_saved = mock_write.call_args[0][1]
    assert actual_data_saved["tone"] == expected_tone_structure


@pytest.mark.asyncio
@patch("inkwell.routes.api_profile.write_yaml")
async def test_save_profile_internal_error_handling(mock_write, client):
    mock_write.side_effect = Exception("Disk Full")

    response = await client.post("/api/profile", json={"name": "User"})

    assert response.status_code == 500
    assert "Write failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_save_profile_validation_error(client):
    bad_payload = {"name": "User", "interests": "not-a-list"}

    response = await client.post("/api/profile", json=bad_payload)
    assert response.status_code == 422
