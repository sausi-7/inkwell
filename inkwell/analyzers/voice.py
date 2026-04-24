"""On-demand voice drafting — the only code path that spends LLM tokens.

Key + model are passed in per-call (not read from env) so the web UI can BYOK
from browser localStorage without the server ever persisting them. The CLI
`inkwell draft` subcommand reads them from env for parity.
"""

from __future__ import annotations

import json
import logging
import time

import litellm

from inkwell.analyzers.llm_client import _strip_code_fences, _supports_native_json_mode
from inkwell.personas.prompt_builder import build_personality_block
from inkwell.scanners.base import RawSignal

logger = logging.getLogger(__name__)

DRAFT_MAX_TOKENS = 512
DRAFT_TEMPERATURE = 0.7
NO_COMMENT_SENTINEL = "no cool comments"


def _build_draft_prompt(signal: RawSignal, personality: dict, coolest: str) -> str:
    personality_block = build_personality_block(personality or {})
    subreddit = signal.metadata.get("subreddit", signal.platform)

    comment_section = ""
    if coolest and coolest != NO_COMMENT_SENTINEL:
        comment_section = f"\nMost interesting existing comment:\n{coolest}\n"

    return f"""You are writing Reddit comments in the voice described below.

{personality_block}

Subreddit: r/{subreddit}
Post title: {signal.title}
Post body: {signal.body or '(no body text)'}
{comment_section}
Return a JSON object (no markdown fencing) with exactly these two keys:
- "reply_to_comment": A reply to the most interesting existing comment above, in the voice described. If there is no cool comment, return "—".
- "post_comment": A top-level comment on this post, in the voice described. Be genuinely helpful and specific."""


def draft_voice(
    signal: RawSignal,
    personality: dict,
    coolest_comment: str,
    *,
    model: str,
    api_key: str | None = None,
    temperature: float = DRAFT_TEMPERATURE,
    max_tokens: int = DRAFT_MAX_TOKENS,
    retries: int = 3,
) -> dict | None:
    """Generate {'reply_to_comment', 'post_comment'} in the user's voice.

    `api_key` can be None for providers that don't need one (e.g. ollama/*).
    Returns None on failure.
    """
    prompt = _build_draft_prompt(signal, personality, coolest_comment)

    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if _supports_native_json_mode(model):
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(retries):
        try:
            response = litellm.completion(**kwargs)
            text = _strip_code_fences(response.choices[0].message.content.strip())
            parsed = json.loads(text)
            return {
                "reply_to_comment": parsed.get("reply_to_comment", "—"),
                "post_comment": parsed.get("post_comment", "—"),
            }
        except json.JSONDecodeError as e:
            if attempt < retries - 1:
                logger.warning("voice: non-JSON response (%s), retrying...", e)
                time.sleep(1.5)
            else:
                logger.error("voice: non-JSON after %d attempts", retries)
                return None
        except Exception as e:
            if attempt < retries - 1:
                logger.warning("voice: call failed (%s), retrying...", e)
                time.sleep(1.5)
            else:
                logger.error("voice: call failed after %d attempts: %s", retries, e)
                return None
    return None
