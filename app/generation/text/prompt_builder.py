"""Text prompt builder — constructs AI prompts from draft context.

Responsible for assembling clean, explicit prompts from draft metadata
(title, topic, tone, content type) and optional project context.

No I/O, no provider coupling — pure function.
"""

from __future__ import annotations

from app.domain.draft import Draft
from app.domain.enums import ContentType, Tone
from app.domain.project import Project

# ── tone instructions ─────────────────────────────────────────────────

_TONE_INSTRUCTIONS: dict[Tone, str] = {
    Tone.NEUTRAL: "Use a balanced, neutral tone.",
    Tone.FORMAL: "Use a formal, professional tone.",
    Tone.CASUAL: "Use a casual, conversational tone.",
    Tone.HUMOROUS: "Use a light, humorous tone.",
    Tone.PROMOTIONAL: "Use an engaging, promotional tone.",
}

# ── content type hints ────────────────────────────────────────────────

_CONTENT_TYPE_HINTS: dict[ContentType, str] = {
    ContentType.TEXT: "Generate a text post.",
    ContentType.IMAGE: "Generate a caption for an image post.",
    ContentType.TEXT_AND_IMAGE: "Generate text for a post that will include an image.",
}

# ── safety preamble ───────────────────────────────────────────────────

_SAFETY_PREAMBLE = (
    "You are a helpful social-media content assistant. "
    "Do not present unverified claims as facts. "
    "Use cautious, hedging language for factual-looking statements "
    "unless grounded source data is provided. "
    "Do not generate harmful, misleading, or offensive content."
)


def build_text_prompt(
    draft: Draft,
    project: Project | None = None,
) -> str:
    """Build a text-generation prompt from draft and optional project context.

    Parameters
    ----------
    draft:
        The draft whose context drives the prompt.
    project:
        Optional project for additional channel context.

    Returns
    -------
    str
        The assembled prompt string ready to send to an AI provider.
    """
    parts: list[str] = [_SAFETY_PREAMBLE]

    # Content type hint
    content_hint = _CONTENT_TYPE_HINTS.get(draft.content_type, "Generate a social media post.")
    parts.append(content_hint)

    # Tone instruction
    tone_instruction = _TONE_INSTRUCTIONS.get(draft.tone, _TONE_INSTRUCTIONS[Tone.NEUTRAL])
    parts.append(tone_instruction)

    # Project context
    if project is not None:
        project_ctx = f"This is for the channel \"{project.title}\"."
        if project.description:
            project_ctx += f" Channel description: {project.description}"
        parts.append(project_ctx)

    # Topic
    if draft.topic:
        parts.append(f"Topic: {draft.topic}")

    # Title context
    if draft.title:
        parts.append(f"Title/headline: {draft.title}")

    # Existing text context (if partially written)
    if draft.text_content:
        parts.append(f"Existing draft text to expand or improve: {draft.text_content}")

    return "\n\n".join(parts)
