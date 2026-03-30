"""Analysis pipeline — builds prompt and calls LLM."""

import logging

from outreachpilot.analyzers.base import Analysis
from outreachpilot.analyzers.llm_client import chat_completion
from outreachpilot.personas.prompt_builder import build_personality_block, build_ai_prefs_block
from outreachpilot.scanners.base import RawSignal

logger = logging.getLogger(__name__)


def analyze_signal(
    signal: RawSignal,
    personality: dict | None = None,
    filters: dict | None = None,
) -> Analysis:
    """Analyze a signal using AI and return structured analysis."""
    # Build comments text
    comments_text = ""
    if signal.replies:
        for i, c in enumerate(signal.replies[:10], 1):
            comments_text += f"\n{i}. [score: {c.score}] u/{c.author}: {c.body}"
    else:
        comments_text = "\n(No comments yet)"

    personality_block = build_personality_block(personality or {})
    ai_prefs_block = build_ai_prefs_block(filters or {})

    subreddit = signal.metadata.get("subreddit", signal.platform)

    prompt = f"""You are analyzing a Reddit post for outreach potential.

{personality_block}

Subreddit: r/{subreddit}
Post title: {signal.title}
Post body: {signal.body or '(no body text)'}
Score: {signal.score} | Comments: {signal.reply_count}

Top comments:{comments_text}
{ai_prefs_block}

Return a JSON object (no markdown fencing) with these exact keys:
- "summary": 1-2 sentence summary of what the post is about
- "coolest_comment": Copy the most interesting/insightful/funny comment verbatim. If no comments are interesting, write "no cool comments"
- "suggested_reply": A suggested reply to that cool comment, written in the voice described above. If no cool comment, write "\u2014"
- "suggested_post_comment": A useful comment you'd leave on this post, written in the voice described above. Be genuinely helpful and specific to this post.
- "engage": "Yes", "No", or "Maybe". Be strict with "Yes" \u2014 only use it for exceptional posts that are a perfect engagement opportunity based on the criteria above. Most posts should be "Maybe" or "No".
- "why": 1 sentence explaining the engagement recommendation"""

    result = chat_completion(prompt)
    if result is None:
        return Analysis.error_fallback()

    return Analysis(
        summary=result.get("summary", ""),
        coolest_comment=result.get("coolest_comment", "no cool comments"),
        suggested_reply=result.get("suggested_reply", "\u2014"),
        suggested_post_comment=result.get("suggested_post_comment", "\u2014"),
        engage=result.get("engage", "Maybe"),
        why=result.get("why", ""),
    )
