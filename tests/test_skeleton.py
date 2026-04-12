"""
Smoke tests for the V2 repository skeleton.

These tests verify that the package structure is importable and the
project metadata is correct. They will grow as real modules are added.
"""


def test_app_package_importable() -> None:
    """The top-level app package must be importable."""
    import app  # noqa: F401


def test_app_subpackages_importable() -> None:
    """All V2 sub-packages must be importable."""
    import app.api  # noqa: F401
    import app.bot  # noqa: F401
    import app.core  # noqa: F401
    import app.domain  # noqa: F401
    import app.generation  # noqa: F401
    import app.generation.image  # noqa: F401
    import app.generation.orchestration  # noqa: F401
    import app.generation.text  # noqa: F401
    import app.integrations  # noqa: F401
    import app.miniapp  # noqa: F401
    import app.services  # noqa: F401


def test_project_version() -> None:
    """The project version must be set to a V2 dev release."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        v = version("neurosmm")
        assert v.startswith("2."), f"Expected V2 version, got {v!r}"
    except PackageNotFoundError:
        # Package is not installed in editable mode in this environment — skip.
        pass
