"""Health/readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.database import get_db_session
from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


async def _check_db(session: AsyncSession) -> str:
    """Run a simple query to verify DB connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
async def health(
    session: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """Check API and database health."""
    db_status = await _check_db(session)
    status = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(status=status, database=db_status)
