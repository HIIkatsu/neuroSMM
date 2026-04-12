"""Image prompt builder — constructs AI prompts from draft context.

Responsible for assembling clean, explicit image-generation prompts from
draft metadata (title, topic, tone, content type) and optional project
context plus current draft text.

No I/O, no provider coupling — pure function.
"""

from __future__ import annotations

from app.domain.draft import Draft
from app.domain.enums import ContentType, Tone
from app.domain.project import Project

# ── tone modifiers for visual style ──────────────────────────────────

_TONE_VISUAL: dict[Tone, str] = {
    Tone.NEUTRAL: "Clean, balanced composition with a professional look.",
    Tone.FORMAL: "Polished, corporate-style imagery with a professional aesthetic.",
    Tone.CASUAL: "Relaxed, approachable visual style with warm tones.",
    Tone.HUMOROUS: "Playful, lighthearted visual style with bright colors.",
    Tone.PROMOTIONAL: "Eye-catching, vibrant promotional visual that grabs attention.",
}

# ── content type hints ───────────────────────────────────────────────

_CONTENT_TYPE_IMAGE_HINTS: dict[ContentType, str] = {
    ContentType.TEXT: "Create a simple illustrative image for a text post.",
    ContentType.IMAGE: "Create the main image for an image-focused social media post.",
    ContentType.TEXT_AND_IMAGE: "Create a complementary image for a post that also includes text.",
}


def build_image_prompt(
    draft: Draft,
    project: Project | None = None,
) -> str:
    """Build an image-generation prompt from draft and optional project context.

    Parameters
    ----------
    draft:
        The draft whose context drives the prompt.
    project:
        Optional project for additional channel context.

    Returns
    -------
    str
        The assembled prompt string ready to send to an image AI provider.
    """
    parts: list[str] = []

    # Content type hint
    content_hint = _CONTENT_TYPE_IMAGE_HINTS.get(
        draft.content_type,
        "Create a social media image.",
    )
    parts.append(content_hint)

    # Tone / visual style
    tone_visual = _TONE_VISUAL.get(draft.tone, _TONE_VISUAL[Tone.NEUTRAL])
    parts.append(tone_visual)

    # Project context
    if project is not None:
        project_ctx = f'For the channel "{project.title}".'
        if project.description:
            project_ctx += f" Channel theme: {project.description}"
        parts.append(project_ctx)

    # Topic
    if draft.topic:
        parts.append(f"Subject: {draft.topic}")

    # Title context
    if draft.title:
        parts.append(f"Title/headline: {draft.title}")

    # Existing text context — helps the image match the written content
    if draft.text_content:
        parts.append(f"Post text for context: {draft.text_content}")

    return "\n\n".join(parts)
