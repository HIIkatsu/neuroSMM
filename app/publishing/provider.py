"""Publisher protocol and concrete implementations.

Defines the abstract interface that any publishing backend must satisfy,
plus a stub implementation for testing and development.

Publisher-specific objects (e.g. Telegram Bot API responses) never leak
beyond the concrete implementation — only domain-friendly
:class:`PublishResult` objects are returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublishPayload:
    """Platform-agnostic payload sent to a publisher.

    Contains only the content and metadata needed for publishing.
    No publisher-specific objects should appear here.
    """

    text: str
    image_url: str | None = None
    channel_id: str | None = None


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publish attempt.

    Attributes
    ----------
    success : bool
        Whether the publish completed successfully.
    platform_post_id : str | None
        Platform-assigned ID for the published post (if available).
    error_message : str | None
        Reason for failure (only set when ``success`` is False).
    """

    success: bool
    platform_post_id: str | None = None
    error_message: str | None = None


class Publisher(Protocol):
    """Abstract interface for platform publishers.

    Implementations must accept a :class:`PublishPayload` and return a
    :class:`PublishResult`.  No platform-specific types should appear in
    the signature.
    """

    async def publish(self, payload: PublishPayload) -> PublishResult:
        """Publish content and return the result."""
        ...  # pragma: no cover


class StubPublisher:
    """In-memory stub publisher for testing and development.

    Always returns a predictable successful result without calling any
    external API.  Can be configured to simulate failures.
    """

    def __init__(
        self,
        *,
        succeed: bool = True,
        platform_post_id: str = "stub-post-123",
        error_message: str = "Stub publish failure",
    ) -> None:
        self._succeed = succeed
        self._platform_post_id = platform_post_id
        self._error_message = error_message

    async def publish(self, payload: PublishPayload) -> PublishResult:
        """Return a canned result based on configuration."""
        if self._succeed:
            return PublishResult(
                success=True,
                platform_post_id=self._platform_post_id,
            )
        return PublishResult(
            success=False,
            error_message=self._error_message,
        )
