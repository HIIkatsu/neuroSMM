"""Tests for app.core.exceptions — shared exception hierarchy."""

from __future__ import annotations

import pytest

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    NeuroSMMError,
    NotFoundError,
    ValidationError,
)


class TestNeuroSMMError:
    """Base exception must carry message and status_code."""

    def test_default_message(self) -> None:
        err = NeuroSMMError()
        assert err.message == "Internal application error"

    def test_custom_message(self) -> None:
        err = NeuroSMMError("something broke")
        assert err.message == "something broke"
        assert str(err) == "something broke"

    def test_default_status_code(self) -> None:
        assert NeuroSMMError.status_code == 500

    def test_repr(self) -> None:
        err = NeuroSMMError("oops")
        assert "NeuroSMMError" in repr(err)
        assert "oops" in repr(err)

    def test_is_exception(self) -> None:
        with pytest.raises(NeuroSMMError):
            raise NeuroSMMError("test")


class TestClientErrors:
    """Client-facing exceptions must have correct status codes."""

    def test_validation_error(self) -> None:
        err = ValidationError("bad input")
        assert err.status_code == 422
        assert isinstance(err, NeuroSMMError)

    def test_not_found_error(self) -> None:
        err = NotFoundError("user not found")
        assert err.status_code == 404
        assert isinstance(err, NeuroSMMError)

    def test_conflict_error(self) -> None:
        err = ConflictError("duplicate")
        assert err.status_code == 409
        assert isinstance(err, NeuroSMMError)

    def test_authentication_error(self) -> None:
        err = AuthenticationError("invalid token")
        assert err.status_code == 401
        assert isinstance(err, NeuroSMMError)

    def test_authorization_error(self) -> None:
        err = AuthorizationError("forbidden")
        assert err.status_code == 403
        assert isinstance(err, NeuroSMMError)


class TestInfraErrors:
    """Infrastructure exceptions must have correct status codes."""

    def test_external_service_error(self) -> None:
        err = ExternalServiceError("OpenAI timeout")
        assert err.status_code == 502
        assert isinstance(err, NeuroSMMError)

    def test_configuration_error(self) -> None:
        err = ConfigurationError("missing key")
        assert err.status_code == 500
        assert isinstance(err, NeuroSMMError)


class TestExceptionHierarchy:
    """All custom exceptions must be catchable via the base class."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ValidationError,
            NotFoundError,
            ConflictError,
            AuthenticationError,
            AuthorizationError,
            ExternalServiceError,
            ConfigurationError,
        ],
    )
    def test_all_catchable_as_base(self, exc_cls: type[NeuroSMMError]) -> None:
        with pytest.raises(NeuroSMMError):
            raise exc_cls("test")
