"""Exception-to-HTTP error translation for NeuroSMM API.

Registers global exception handlers that convert domain/service exceptions
to clean JSON HTTP error responses using the ``status_code`` hint on each
exception class.

**Security rule**: internal details (tracebacks, provider error messages,
API keys) are *never* exposed to the client.  Only human-readable,
user-safe messages leave this boundary; raw details go to server logs.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ExternalServiceError, NeuroSMMError
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── User-safe messages for external service errors ─────────────────────
_SAFE_EXTERNAL_ERROR = (
    "Внешний сервис временно недоступен. Попробуйте позже."
)


def _safe_message(exc: NeuroSMMError) -> str:
    """Return a user-safe error message.

    For :class:`ExternalServiceError` the raw provider message is
    replaced with a generic one so that API keys, model names,
    rate-limit details etc. never leak to the client.
    """
    if isinstance(exc, ExternalServiceError):
        return _SAFE_EXTERNAL_ERROR
    return exc.message


def register_exception_handlers(app: FastAPI) -> None:
    """Attach application exception handlers to the FastAPI app."""

    @app.exception_handler(NeuroSMMError)
    async def neurosmm_error_handler(
        request: Request,
        exc: NeuroSMMError,
    ) -> JSONResponse:
        # Full detail goes to server logs only
        logger.warning(
            "Application error: %s",
            exc.message,
            extra={"status_code": exc.status_code, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": _safe_message(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all for truly unexpected errors.

        Logs the full traceback server-side but returns only a generic
        message to the client so no internals leak.
        """
        logger.exception(
            "Unhandled error on %s: %s",
            request.url.path,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера. Попробуйте позже."},
        )
