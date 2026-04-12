"""Text generation provider protocol and implementations.

Defines the abstract interface that any text-generation backend must satisfy,
plus a concrete OpenAI-based implementation.

Provider-specific response objects are never leaked — only domain
:class:`GenerationResult` objects are returned.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.enums import GenerationType
from app.domain.generation import GenerationResult


class TextGenerationProvider(Protocol):
    """Abstract interface for text generation backends."""

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Generate text from the given prompt.

        Returns a :class:`GenerationResult` — never a provider-specific object.
        """
        ...  # pragma: no cover


class StubTextProvider:
    """In-memory stub provider for testing and development.

    Always returns a predictable result without calling any external API.
    """

    def __init__(self, *, response_text: str = "Generated stub text content.") -> None:
        self._response_text = response_text

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Return a canned successful result."""
        return GenerationResult.success(
            generation_type=GenerationType.TEXT,
            content=self._response_text,
            prompt_used=prompt,
            model_name="stub",
            tokens_used=0,
        )


class OpenAITextProvider:
    """OpenAI-backed text generation provider.

    Wraps the ``openai`` async client and translates responses into
    domain :class:`GenerationResult` objects. Provider-specific types
    never escape this boundary.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        default_max_tokens: int = 2048,
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._default_max_tokens = default_max_tokens

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Call the OpenAI Chat Completions API and return a domain result."""
        effective_max_tokens = max_tokens or self._default_max_tokens

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=effective_max_tokens,
            )
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None

            return GenerationResult.success(
                generation_type=GenerationType.TEXT,
                content=content,
                prompt_used=prompt,
                model_name=self._model,
                tokens_used=tokens_used,
            )
        except Exception as exc:
            return GenerationResult.failure(
                generation_type=GenerationType.TEXT,
                error_message=str(exc),
                prompt_used=prompt,
                model_name=self._model,
            )
