"""Exception-to-HTTP error translation for NeuroSMM API.

Registers a global exception handler that converts domain/service exceptions
to clean JSON HTTP error responses using the ``status_code`` hint on each
exception class.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import NeuroSMMError
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach application exception handlers to the FastAPI app."""

    @app.exception_handler(NeuroSMMError)
    async def neurosmm_error_handler(
        request: Request,
        exc: NeuroSMMError,
    ) -> JSONResponse:
        logger.warning(
            "Application error: %s",
            exc.message,
            extra={"status_code": exc.status_code, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )
