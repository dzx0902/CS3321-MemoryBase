from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..core.config import Settings
from ..core.database import Database
from ..models.source import HealthDatabaseStatus, HealthResponse
from .deps import get_app_settings, get_database

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    settings: Settings = Depends(get_app_settings),
    database: Database = Depends(get_database),
) -> JSONResponse:
    ok, error = database.ping()
    payload = HealthResponse(
        status="ok" if ok else "degraded",
        service=settings.app_name,
        database=HealthDatabaseStatus(status="up" if ok else "down", error=error),
    )
    return JSONResponse(
        status_code=200 if ok else 503,
        content=payload.model_dump(mode="json"),
    )
