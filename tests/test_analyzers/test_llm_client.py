"""Tests for inkwell.analyzers.llm_client pure helpers.

Network-hitting paths aren't tested here — the helpers below are the parts that
have actually broken in practice (model-prefix detection, fence stripping from
models that ignore 'no markdown' instructions)."""

from inkwell.analyzers.llm_client import _strip_code_fences, _supports_native_json_mode


def test_strip_code_fences_no_op_on_plain_json():
    assert _strip_code_fences('{"engage": "Yes"}') == '{"engage": "Yes"}'


def test_strip_code_fences_removes_json_fence():
    text = '```json\n{"engage": "Yes"}\n```'
    assert _strip_code_fences(text) == '{"engage": "Yes"}'


def test_strip_code_fences_removes_bare_fence():
    text = '```\n{"engage": "No"}\n```'
    assert _strip_code_fences(text) == '{"engage": "No"}'


def test_strip_code_fences_handles_single_line_fence():
    """Some models return ```{"k": "v"}``` with no newline."""
    assert _strip_code_fences('```{"k": "v"}```') == '{"k": "v"}'


def test_json_mode_enabled_for_openai_gpt_models():
    assert _supports_native_json_mode("gpt-4o-mini") is True
    assert _supports_native_json_mode("gpt-4o") is True
    assert _supports_native_json_mode("openai/gpt-4o-mini") is True


def test_json_mode_disabled_for_claude():
    """Claude support via LiteLLM's response_format is newer and uneven —
    we rely on prompt-based JSON instead. Flip this when we trust it."""
    assert _supports_native_json_mode("claude-sonnet-4-6") is False
    assert _supports_native_json_mode("claude-opus-4-6") is False


def test_json_mode_disabled_for_ollama():
    assert _supports_native_json_mode("ollama/llama3") is False
    assert _supports_native_json_mode("ollama_chat/mistral") is False
