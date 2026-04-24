"""Tests for inkwell.personas.prompt_builder."""

from inkwell.personas.prompt_builder import build_ai_prefs_block, build_personality_block


def test_empty_personality_returns_default_guidance():
    block = build_personality_block({})
    assert "conversational" in block.lower()
    assert "helpful" in block.lower()


def test_personality_block_includes_name_and_bio():
    block = build_personality_block({"name": "Saurabh", "bio": "Indie developer."})
    assert "Saurabh" in block
    assert "Indie developer" in block


def test_personality_block_formats_dos_and_donts_as_bullets():
    block = build_personality_block({
        "name": "Test",
        "dos": ["Ask follow-up questions"],
        "donts": ["Never mention products unless asked"],
    })
    assert "DO:" in block
    assert "- Ask follow-up questions" in block
    assert "DON'T:" in block
    assert "- Never mention products unless asked" in block


def test_personality_block_omits_missing_optional_fields():
    """Missing interests/tone/examples shouldn't produce empty stub sections."""
    block = build_personality_block({"name": "Minimal"})
    assert "Interests:" not in block
    assert "Tone:" not in block
    assert "Example comments" not in block


def test_personality_block_includes_example_comments_when_provided():
    block = build_personality_block({
        "name": "Test",
        "example_comments": ["I ran into the same issue last month..."],
    })
    assert "Example comments" in block
    assert "I ran into the same issue" in block


def test_ai_prefs_block_is_empty_when_no_filters():
    assert build_ai_prefs_block({}) == ""
    assert build_ai_prefs_block({"keywords": {"include": ["x"]}}) == ""


def test_ai_prefs_block_renders_prefer_avoid_and_notes():
    block = build_ai_prefs_block({
        "ai_preferences": {
            "prefer_topics": ["founders asking for feedback"],
            "avoid_topics": ["link drops"],
            "engagement_notes": "Be strict with Yes.",
        }
    })
    assert "PREFER" in block
    assert "founders asking for feedback" in block
    assert "AVOID" in block
    assert "link drops" in block
    assert "Be strict with Yes." in block
