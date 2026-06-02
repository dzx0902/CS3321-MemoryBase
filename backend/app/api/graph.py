from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.graph import GraphHealthResponse, GraphResponse, GraphSyncResponse
from ..services.graph_service import GraphService, GraphUnavailableError
from .deps import get_graph_service

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/health", response_model=GraphHealthResponse)
def get_graph_health(service: GraphService = Depends(get_graph_service)) -> GraphHealthResponse:
    return service.health()


@router.get("/workspace", response_model=GraphResponse)
def get_workspace_graph(
    workspace_id: UUID = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
    fallback: bool = Query(default=True),
    service: GraphService = Depends(get_graph_service),
) -> GraphResponse:
    try:
        return service.load_workspace_graph(
            workspace_id=workspace_id,
            limit=limit,
            fallback=fallback,
        )
    except GraphUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/workspace/preview", response_model=GraphResponse)
def preview_workspace_graph(
    workspace_id: UUID = Query(...),
    limit: int = Query(default=30, ge=1, le=100),
    service: GraphService = Depends(get_graph_service),
) -> GraphResponse:
    return service.preview_workspace(workspace_id=workspace_id, limit=limit)


@router.post("/workspace/sync", response_model=GraphSyncResponse)
def sync_workspace_graph(
    workspace_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    service: GraphService = Depends(get_graph_service),
) -> GraphSyncResponse:
    try:
        return service.sync_workspace(workspace_id=workspace_id, limit=limit)
    except GraphUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
