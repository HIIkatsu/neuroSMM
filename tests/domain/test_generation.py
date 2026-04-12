"""Tests for GenerationRequest and GenerationResult domain value objects."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.domain.enums import GenerationStatus, GenerationType, Tone
from app.domain.generation import GenerationRequest, GenerationResult


class TestGenerationRequestCreation:
    """GenerationRequest construction and defaults."""

    def test_minimal_request(self) -> None:
        req = GenerationRequest(
            generation_type=GenerationType.TEXT,
            prompt="Write about AI",
        )
        assert req.generation_type == GenerationType.TEXT
        assert req.prompt == "Write about AI"
        assert req.draft_id is None
        assert req.tone == Tone.NEUTRAL
        assert req.max_tokens is None

    def test_full_request(self) -> None:
        req = GenerationRequest(
            draft_id=5,
            generation_type=GenerationType.IMAGE,
            prompt="A futuristic city",
            tone=Tone.CASUAL,
            max_tokens=2000,
        )
        assert req.draft_id == 5
        assert req.generation_type == GenerationType.IMAGE
        assert req.max_tokens == 2000


class TestGenerationRequestValidation:
    """GenerationRequest invariants."""

    def test_prompt_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            GenerationRequest(generation_type=GenerationType.TEXT, prompt="")

    def test_prompt_stripped(self) -> None:
        req = GenerationRequest(
            generation_type=GenerationType.TEXT,
            prompt="  hello  ",
        )
        assert req.prompt == "hello"

    def test_prompt_max_length(self) -> None:
        with pytest.raises(PydanticValidationError):
            GenerationRequest(
                generation_type=GenerationType.TEXT,
                prompt="x" * 5001,
            )

    def test_draft_id_must_be_positive_when_provided(self) -> None:
        with pytest.raises(PydanticValidationError):
            GenerationRequest(
                draft_id=0,
                generation_type=GenerationType.TEXT,
                prompt="test",
            )

    def test_max_tokens_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            GenerationRequest(
                generation_type=GenerationType.TEXT,
                prompt="test",
                max_tokens=0,
            )

    def test_max_tokens_upper_bound(self) -> None:
        with pytest.raises(PydanticValidationError):
            GenerationRequest(
                generation_type=GenerationType.TEXT,
                prompt="test",
                max_tokens=20_000,
            )


class TestGenerationRequestImmutability:
    """GenerationRequest is frozen."""

    def test_cannot_mutate(self) -> None:
        req = GenerationRequest(
            generation_type=GenerationType.TEXT, prompt="test"
        )
        with pytest.raises(PydanticValidationError):
            req.prompt = "new"  # type: ignore[misc]


class TestGenerationResultCreation:
    """GenerationResult construction and defaults."""

    def test_defaults(self) -> None:
        result = GenerationResult(generation_type=GenerationType.TEXT)
        assert result.status == GenerationStatus.PENDING
        assert result.content is None
        assert result.error_message is None
        assert result.prompt_used == ""
        assert result.model_name is None
        assert result.tokens_used is None

    def test_success_factory(self) -> None:
        result = GenerationResult.success(
            generation_type=GenerationType.TEXT,
            content="Generated text",
            prompt_used="Write about AI",
            model_name="gpt-4o",
            tokens_used=150,
        )
        assert result.status == GenerationStatus.COMPLETED
        assert result.content == "Generated text"
        assert result.is_success is True
        assert result.is_failure is False
        assert result.model_name == "gpt-4o"
        assert result.tokens_used == 150

    def test_failure_factory(self) -> None:
        result = GenerationResult.failure(
            generation_type=GenerationType.IMAGE,
            error_message="Rate limited",
            prompt_used="A cat",
            model_name="dall-e-3",
        )
        assert result.status == GenerationStatus.FAILED
        assert result.content is None
        assert result.error_message == "Rate limited"
        assert result.is_success is False
        assert result.is_failure is True


class TestGenerationResultProperties:
    """is_success and is_failure property logic."""

    def test_pending_is_not_success(self) -> None:
        result = GenerationResult(generation_type=GenerationType.TEXT)
        assert result.is_success is False
        assert result.is_failure is False

    def test_completed_without_content_is_not_success(self) -> None:
        result = GenerationResult(
            generation_type=GenerationType.TEXT,
            status=GenerationStatus.COMPLETED,
            content=None,
        )
        assert result.is_success is False

    def test_in_progress_is_not_failure(self) -> None:
        result = GenerationResult(
            generation_type=GenerationType.TEXT,
            status=GenerationStatus.IN_PROGRESS,
        )
        assert result.is_failure is False


class TestGenerationResultValidation:
    """GenerationResult validation rules."""

    def test_tokens_used_must_be_non_negative(self) -> None:
        with pytest.raises(PydanticValidationError):
            GenerationResult(
                generation_type=GenerationType.TEXT,
                tokens_used=-1,
            )

    def test_immutable(self) -> None:
        result = GenerationResult(generation_type=GenerationType.TEXT)
        with pytest.raises(PydanticValidationError):
            result.status = GenerationStatus.COMPLETED  # type: ignore[misc]
