"""
Health check endpoint.

GET /api/health
    — Used by load balancers, Docker health checks, and CI pipelines.
    — Verifies the app is up AND the database connection is alive.
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    summary="Health check",
    response_description="App and DB status",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Returns:
        200  { "status": "ok", "database": "ok" }
        503  { "status": "degraded", "database": "unreachable" }
    """
    db_status = "ok"
    http_status = status.HTTP_200_OK

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database health check failed", exc_info=exc)
        db_status = "unreachable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={"status": "ok" if db_status == "ok" else "degraded", "database": db_status},
    )
