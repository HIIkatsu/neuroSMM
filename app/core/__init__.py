"""
NeuroSMM V2 — Core Layer.

Public re-exports so downstream code can write::

    from app.core import get_settings, get_logger, NeuroSMMError
"""

from app.core.config import Settings, get_settings
from app.core.constants import APP_NAME, APP_VERSION
from app.core.exceptions import NeuroSMMError
from app.core.logging import get_logger, setup_logging

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "NeuroSMMError",
    "Settings",
    "get_logger",
    "get_settings",
    "setup_logging",
]
