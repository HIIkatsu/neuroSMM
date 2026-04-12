"""Tests for app.core.logging — structured logging setup."""

from __future__ import annotations

import json
import logging

from app.core.logging import _JsonFormatter, get_logger, setup_logging


class TestSetupLogging:
    """setup_logging() must configure the root logger correctly."""

    def test_sets_root_level(self) -> None:
        setup_logging(level="DEBUG", json_output=False)
        assert logging.getLogger().level == logging.DEBUG

    def test_sets_info_level(self) -> None:
        setup_logging(level="INFO", json_output=False)
        assert logging.getLogger().level == logging.INFO

    def test_case_insensitive_level(self) -> None:
        setup_logging(level="warning", json_output=False)
        assert logging.getLogger().level == logging.WARNING

    def test_replaces_existing_handlers(self) -> None:
        setup_logging(level="INFO", json_output=False)
        setup_logging(level="INFO", json_output=False)
        # Should only have one handler, not two
        assert len(logging.getLogger().handlers) == 1

    def test_json_formatter_attached_when_json(self) -> None:
        setup_logging(level="INFO", json_output=True)
        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, _JsonFormatter)

    def test_human_formatter_attached_when_not_json(self) -> None:
        setup_logging(level="INFO", json_output=False)
        handler = logging.getLogger().handlers[0]
        assert not isinstance(handler.formatter, _JsonFormatter)


class TestGetLogger:
    """get_logger() must return a standard logger."""

    def test_returns_named_logger(self) -> None:
        logger = get_logger("test.module")
        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)

    def test_same_name_returns_same_logger(self) -> None:
        a = get_logger("same.name")
        b = get_logger("same.name")
        assert a is b


class TestJsonFormatter:
    """The JSON formatter must emit valid, parseable JSON lines."""

    def test_basic_message_is_valid_json(self) -> None:
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "hello world"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_extra_fields_included(self) -> None:
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="event", args=(), exc_info=None,
        )
        record.user_id = 42  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["user_id"] == 42

    def test_exception_info_included(self) -> None:
        formatter = _JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="failed", args=(), exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "boom" in data["exception"]

    def test_internal_attrs_excluded(self) -> None:
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="msg", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        # Internal attributes like 'pathname', 'lineno' should NOT appear
        assert "pathname" not in data
        assert "lineno" not in data
        assert "funcName" not in data
