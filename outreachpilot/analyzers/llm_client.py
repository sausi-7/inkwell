"""LLM client wrapper — supports OpenAI directly, with LiteLLM as optional backend."""

import json
import logging
import time

from openai import OpenAI

from outreachpilot.config import OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def chat_completion(prompt: str, retries: int = 3) -> dict | None:
    """Send a prompt and parse JSON response, with retries."""
    client = get_client()

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            )
            text = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < retries - 1:
                logger.warning("LLM parse error (%s), retrying...", e)
                time.sleep(2)
            else:
                logger.error("LLM analysis failed: %s", e)
                return None
    return None
