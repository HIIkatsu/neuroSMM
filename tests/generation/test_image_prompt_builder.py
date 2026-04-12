"""Tests for the image prompt builder."""

from __future__ import annotations

from app.domain.draft import Draft
from app.domain.enums import ContentType, Tone
from app.domain.project import Project
from app.generation.image.prompt_builder import build_image_prompt


class TestBuildImagePrompt:
    """Tests for build_image_prompt function."""

    def _make_draft(
        self,
        *,
        title: str = "",
        topic: str = "",
        tone: Tone = Tone.NEUTRAL,
        content_type: ContentType = ContentType.IMAGE,
        text_content: str = "",
    ) -> Draft:
        return Draft(
            project_id=1,
            author_id=1,
            title=title,
            topic=topic,
            tone=tone,
            content_type=content_type,
            text_content=text_content,
        )

    def _make_project(
        self,
        *,
        title: str = "My Channel",
        description: str = "",
    ) -> Project:
        return Project(
            id=1,
            owner_id=1,
            title=title,
            description=description,
        )

    def test_minimal_draft_produces_prompt(self) -> None:
        draft = self._make_draft()
        prompt = build_image_prompt(draft)

        assert prompt  # non-empty
        assert "image" in prompt.lower()

    def test_topic_included(self) -> None:
        draft = self._make_draft(topic="AI trends in 2025")
        prompt = build_image_prompt(draft)

        assert "AI trends in 2025" in prompt

    def test_title_included(self) -> None:
        draft = self._make_draft(title="Breaking News")
        prompt = build_image_prompt(draft)

        assert "Breaking News" in prompt

    def test_tone_neutral(self) -> None:
        draft = self._make_draft(tone=Tone.NEUTRAL)
        prompt = build_image_prompt(draft)

        assert "clean" in prompt.lower() or "balanced" in prompt.lower()

    def test_tone_formal(self) -> None:
        draft = self._make_draft(tone=Tone.FORMAL)
        prompt = build_image_prompt(draft)

        assert "professional" in prompt.lower()

    def test_tone_casual(self) -> None:
        draft = self._make_draft(tone=Tone.CASUAL)
        prompt = build_image_prompt(draft)

        assert "relaxed" in prompt.lower() or "warm" in prompt.lower()

    def test_tone_humorous(self) -> None:
        draft = self._make_draft(tone=Tone.HUMOROUS)
        prompt = build_image_prompt(draft)

        assert "playful" in prompt.lower() or "lighthearted" in prompt.lower()

    def test_tone_promotional(self) -> None:
        draft = self._make_draft(tone=Tone.PROMOTIONAL)
        prompt = build_image_prompt(draft)

        assert "eye-catching" in prompt.lower() or "promotional" in prompt.lower()

    def test_content_type_image(self) -> None:
        draft = self._make_draft(content_type=ContentType.IMAGE)
        prompt = build_image_prompt(draft)

        assert "image" in prompt.lower()

    def test_content_type_text(self) -> None:
        draft = self._make_draft(content_type=ContentType.TEXT)
        prompt = build_image_prompt(draft)

        assert "illustrative" in prompt.lower() or "text post" in prompt.lower()

    def test_content_type_text_and_image(self) -> None:
        draft = self._make_draft(content_type=ContentType.TEXT_AND_IMAGE)
        prompt = build_image_prompt(draft)

        assert "complementary" in prompt.lower() or "text" in prompt.lower()

    def test_existing_text_content_included(self) -> None:
        draft = self._make_draft(
            content_type=ContentType.TEXT_AND_IMAGE,
            text_content="Here is the start of my post...",
        )
        prompt = build_image_prompt(draft)

        assert "Here is the start of my post..." in prompt

    def test_project_context_included(self) -> None:
        draft = self._make_draft(topic="Tech news")
        project = self._make_project(
            title="TechDaily", description="Daily tech updates"
        )
        prompt = build_image_prompt(draft, project=project)

        assert "TechDaily" in prompt
        assert "Daily tech updates" in prompt

    def test_project_without_description(self) -> None:
        draft = self._make_draft()
        project = self._make_project(title="SimpleChannel", description="")
        prompt = build_image_prompt(draft, project=project)

        assert "SimpleChannel" in prompt

    def test_no_project_context_when_none(self) -> None:
        draft = self._make_draft()
        prompt = build_image_prompt(draft, project=None)

        assert "channel" not in prompt.lower()

    def test_all_fields_combined(self) -> None:
        draft = self._make_draft(
            title="Big Announcement",
            topic="Product launch",
            tone=Tone.PROMOTIONAL,
            content_type=ContentType.TEXT_AND_IMAGE,
            text_content="We are excited to announce...",
        )
        project = self._make_project(
            title="BrandChannel", description="Our official brand page"
        )
        prompt = build_image_prompt(draft, project=project)

        assert "Big Announcement" in prompt
        assert "Product launch" in prompt
        assert "We are excited to announce..." in prompt
        assert "BrandChannel" in prompt
        assert "Our official brand page" in prompt
