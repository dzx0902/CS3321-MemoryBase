from __future__ import annotations

from app.api.deps import get_app_settings, get_database
from app.core.config import Settings
from app.core.database import Database
from app.models.source import HealthDatabaseStatus, HealthResponse
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

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
