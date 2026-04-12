"""
Shared constants for NeuroSMM V2.

Only truly cross-cutting values belong here.  Domain-specific enums or limits
should live in their own domain modules (introduced in PR 03).
"""

from __future__ import annotations

# ── application metadata ───────────────────────────────────────────
APP_NAME: str = "NeuroSMM"
APP_VERSION: str = "2.0.0.dev0"

# ── api defaults ───────────────────────────────────────────────────
DEFAULT_API_PREFIX: str = "/api/v1"
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
