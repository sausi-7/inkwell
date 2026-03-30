"""Build prompt blocks from persona and filter configs."""


def build_personality_block(personality: dict) -> str:
    """Build the personality section of the LLM prompt."""
    if not personality:
        return ("Write comments that are conversational, fun, non-marketing-y, "
                "slightly humorous, and genuinely helpful.")

    name = personality.get("name", "the user")
    bio = personality.get("bio", "").strip()
    interests = ", ".join(personality.get("interests", []))
    expertise = ", ".join(personality.get("expertise", []))
    tone = personality.get("tone", {})
    dos = personality.get("dos", [])
    donts = personality.get("donts", [])
    examples = personality.get("example_comments", [])

    block = f"You are writing comments as {name}."
    if bio:
        block += f"\nBio: {bio}"
    if interests:
        block += f"\nInterests: {interests}"
    if expertise:
        block += f"\nExpertise: {expertise}"
    if tone:
        block += f"\nTone: {tone.get('style', 'conversational')}"
        block += f"\nHumor style: {tone.get('humor', 'light')}"
        block += f"\nFormality: {tone.get('formality', 'casual')}"
    if dos:
        block += "\n\nDO:\n" + "\n".join(f"- {d}" for d in dos)
    if donts:
        block += "\n\nDON'T:\n" + "\n".join(f"- {d}" for d in donts)
    if examples:
        block += "\n\nExample comments that reflect this voice:"
        for i, ex in enumerate(examples, 1):
            block += f'\n{i}. "{ex.strip()}"'

    return block


def build_ai_prefs_block(filters: dict) -> str:
    """Build the AI engagement preferences section of the prompt."""
    if not filters:
        return ""
    ai_prefs = filters.get("ai_preferences", {})
    if not ai_prefs:
        return ""

    block = "\nEngagement criteria:"
    prefer = ai_prefs.get("prefer_topics", [])
    avoid = ai_prefs.get("avoid_topics", [])
    notes = ai_prefs.get("engagement_notes", "")

    if prefer:
        block += "\nPREFER posts that are:"
        for p in prefer:
            block += f"\n- {p}"
    if avoid:
        block += "\nAVOID posts that are:"
        for a in avoid:
            block += f"\n- {a}"
    if notes:
        block += f"\nAdditional guidance: {notes.strip()}"

    return block
