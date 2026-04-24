"""LLM client wrapper.

Uses LiteLLM so the same code path works across OpenAI, Anthropic Claude, Ollama,
and anything else LiteLLM supports. Provider is chosen by the LLM_MODEL env var:

    gpt-4o-mini            → OpenAI        (needs OPENAI_API_KEY)
    claude-sonnet-4-6      → Anthropic     (needs ANTHROPIC_API_KEY)
    ollama/llama3          → local Ollama  (needs OLLAMA_API_BASE, defaults to
                                            http://localhost:11434)
"""

import json
import logging
import time

import litellm

from inkwell.config import LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def _supports_native_json_mode(model: str) -> bool:
    """Return True only for providers we trust with response_format='json_object'.

    OpenAI's JSON mode is rock-solid. Claude and Ollama support is newer / uneven,
    so we fall back to instruction-based JSON (the prompt already asks for it) plus
    fence stripping. Keeps the swap low-risk; we can widen this as providers mature.
    """
    return model.startswith(("gpt-", "openai/"))


def _strip_code_fences(text: str) -> str:
    """Strip a leading ```json ... ``` fence that some models add around JSON."""
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def chat_completion(prompt: str, retries: int = 3) -> dict | None:
    """Send a prompt, parse JSON response, retry on transient failures."""
    kwargs: dict = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }
    if _supports_native_json_mode(LLM_MODEL):
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(retries):
        try:
            response = litellm.completion(**kwargs)
            text = _strip_code_fences(response.choices[0].message.content.strip())
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt < retries - 1:
                logger.warning("LLM returned non-JSON (%s), retrying...", e)
                time.sleep(2)
            else:
                logger.error("LLM returned non-JSON after %d attempts", retries)
                return None
        except Exception as e:
            if attempt < retries - 1:
                logger.warning("LLM call failed (%s), retrying...", e)
                time.sleep(2)
            else:
                logger.error("LLM call failed after %d attempts: %s", retries, e)
                return None
    return None
