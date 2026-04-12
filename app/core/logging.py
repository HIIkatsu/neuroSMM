"""
Structured logging configuration for NeuroSMM V2.

Call :func:`setup_logging` once during application startup.  All application
code should use the standard :mod:`logging` module — this module only
*configures* it (formatter, level, handlers).

Usage::

    from app.core.logging import setup_logging, get_logger

    setup_logging(level="DEBUG", json_output=True)
    logger = get_logger(__name__)
    logger.info("hello", extra={"user_id": 42})
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        # Merge caller-supplied *extra* keys (skip internal LogRecord attrs)
        for key, value in record.__dict__.items():
            if key not in _BUILTIN_LOG_ATTRS and key not in payload:
                payload[key] = value
        return json.dumps(payload, default=str)


# Attributes that belong to LogRecord internals and should never leak into
# the JSON payload.
_BUILTIN_LOG_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class _HumanFormatter(logging.Formatter):
    """Simple human-readable formatter for local development."""

    FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    def __init__(self) -> None:
        super().__init__(fmt=self.FMT, datefmt="%Y-%m-%d %H:%M:%S")


def setup_logging(
    *,
    level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure the root logger for the whole application.

    Parameters
    ----------
    level:
        Log level name (``DEBUG``, ``INFO``, …).
    json_output:
        If *True* (the default for production), use JSON lines.
        If *False*, use a human-friendly format.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove any previously attached handlers (avoids double-logging when
    # called more than once, e.g. in tests).
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level.upper())
    handler.setFormatter(_JsonFormatter() if json_output else _HumanFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    This is a thin wrapper around :func:`logging.getLogger` to keep imports
    consistent across the codebase.
    """
    return logging.getLogger(name)
