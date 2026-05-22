from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
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


@router.get("/health/detail")
def health_detail(
    workspace: str | None = None,
    agent: str | None = None,
    settings: Settings = Depends(get_app_settings),
    database: Database = Depends(get_database),
) -> JSONResponse:
    ok, error = database.ping()
    detail: dict[str, object] = {"schema": None, "workspace": None, "agent": None}
    if ok:
        detail = database.health_detail(workspace=workspace, agent=agent)

    payload: dict[str, object] = {
        "status": "ok" if ok else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": HealthDatabaseStatus(status="up" if ok else "down", error=error).model_dump(
            mode="json"
        ),
        **detail,
    }
    return JSONResponse(status_code=200 if ok else 503, content=jsonable_encoder(payload))
