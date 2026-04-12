"""
Shared exception hierarchy for NeuroSMM V2.

Every domain- or service-level error inherits from :class:`NeuroSMMError` so
callers (API routers, bot handlers) can catch all application errors in one
place and convert them to user-facing responses.

HTTP-status hints are attached to each class so the API layer can derive the
correct status code without ``isinstance`` chains.
"""

from __future__ import annotations


class NeuroSMMError(Exception):
    """Base class for all application exceptions.

    Attributes
    ----------
    message : str
        Human-readable error description (safe to show to users).
    status_code : int
        Suggested HTTP status code for API responses.
    """

    status_code: int = 500

    def __init__(self, message: str = "Internal application error") -> None:
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.message!r})"


# ── client errors ──────────────────────────────────────────────────


class ValidationError(NeuroSMMError):
    """Input failed domain/business validation."""

    status_code: int = 422


class NotFoundError(NeuroSMMError):
    """Requested entity does not exist."""

    status_code: int = 404


class ConflictError(NeuroSMMError):
    """Operation conflicts with current state (duplicate, wrong status, etc.)."""

    status_code: int = 409


class AuthenticationError(NeuroSMMError):
    """Caller could not be authenticated."""

    status_code: int = 401


class AuthorizationError(NeuroSMMError):
    """Caller lacks permission to perform the action."""

    status_code: int = 403


# ── infrastructure / integration errors ────────────────────────────


class ExternalServiceError(NeuroSMMError):
    """An external dependency (OpenAI, Telegram API, …) returned an error."""

    status_code: int = 502


class ConfigurationError(NeuroSMMError):
    """Application configuration is missing or invalid."""

    status_code: int = 500
