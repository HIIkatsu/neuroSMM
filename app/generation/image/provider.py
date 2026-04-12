"""Image generation provider protocol and implementations.

Defines the abstract interface that any image-generation backend must satisfy,
plus a concrete OpenAI DALL-E-based implementation and a stub for tests/dev.

Provider-specific response objects are never leaked — only domain
:class:`GenerationResult` objects are returned.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.enums import GenerationType
from app.domain.generation import GenerationResult


class ImageGenerationProvider(Protocol):
    """Abstract interface for image generation backends."""

    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
    ) -> GenerationResult:
        """Generate an image from the given prompt.

        Returns a :class:`GenerationResult` whose ``content`` field holds
        the image URL — never a provider-specific object.
        """
        ...  # pragma: no cover


class StubImageProvider:
    """In-memory stub provider for testing and development.

    Always returns a predictable result without calling any external API.
    """

    def __init__(
        self,
        *,
        image_url: str = "https://stub.example.com/generated-image.png",
    ) -> None:
        self._image_url = image_url

    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
    ) -> GenerationResult:
        """Return a canned successful result."""
        return GenerationResult.success(
            generation_type=GenerationType.IMAGE,
            content=self._image_url,
            prompt_used=prompt,
            model_name="stub",
            tokens_used=0,
        )


class OpenAIImageProvider:
    """OpenAI DALL-E-backed image generation provider.

    Wraps the ``openai`` async client and translates responses into
    domain :class:`GenerationResult` objects.  Provider-specific types
    never escape this boundary.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "dall-e-3",
        default_size: str = "1024x1024",
        timeout: float = 60.0,
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model
        self._default_size = default_size

    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
    ) -> GenerationResult:
        """Call the OpenAI Images API and return a domain result."""
        effective_size = size or self._default_size

        try:
            response = await self._client.images.generate(
                model=self._model,
                prompt=prompt,
                n=1,
                size=effective_size,  # type: ignore[call-overload]
            )

            if not response.data or not response.data[0].url:
                return GenerationResult.failure(
                    generation_type=GenerationType.IMAGE,
                    error_message="Provider returned empty image data",
                    prompt_used=prompt,
                    model_name=self._model,
                )

            image_url = response.data[0].url

            return GenerationResult.success(
                generation_type=GenerationType.IMAGE,
                content=image_url,
                prompt_used=prompt,
                model_name=self._model,
                tokens_used=None,
            )
        except Exception as exc:
            return GenerationResult.failure(
                generation_type=GenerationType.IMAGE,
                error_message=str(exc),
                prompt_used=prompt,
                model_name=self._model,
            )
