from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.semantic import EntityListResponse, EntityResponse, SceneListResponse, SceneResponse


class SemanticRepository(Protocol):
    def list_entities(
        self,
        *,
        workspace_id: UUID | None,
        entity_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> EntityListResponse:
        ...

    def list_scenes(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> SceneListResponse:
        ...


@dataclass(slots=True)
class SemanticService:
    repository: SemanticRepository

    def list_entities(
        self,
        *,
        workspace_id: UUID | None,
        entity_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> EntityListResponse:
        return self.repository.list_entities(
            workspace_id=workspace_id,
            entity_type=entity_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def list_scenes(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> SceneListResponse:
        return self.repository.list_scenes(
            workspace_id=workspace_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )


class PostgresSemanticRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_entities(
        self,
        *,
        workspace_id: UUID | None,
        entity_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> EntityListResponse:
        filters: list[str] = []
        params: dict[str, object] = {"limit": page_size, "offset": (page - 1) * page_size}
        if workspace_id is not None:
            filters.append("e.workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if entity_type is not None:
            filters.append("e.entity_type = %(entity_type)s")
            params["entity_type"] = entity_type
        if status is not None and status != "all":
            filters.append("e.status = %(status)s")
            params["status"] = status
        if keyword:
            filters.append(
                "(e.canonical_name ILIKE %(keyword)s OR e.description ILIKE %(keyword)s)"
            )
            params["keyword"] = f"%{keyword}%"
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM entity e {where_clause}", params)
                total = cur.fetchone()["total"]
                cur.execute(
                    f"""
                    SELECT
                        e.entity_id,
                        e.workspace_id,
                        e.canonical_name,
                        e.entity_type,
                        e.description,
                        e.status,
                        e.created_at,
                        e.updated_at,
                        COUNT(DISTINCT me.memory_id) AS memory_count
                    FROM entity e
                    LEFT JOIN memory_entity me ON me.entity_id = e.entity_id
                    {where_clause}
                    GROUP BY e.entity_id
                    ORDER BY e.updated_at DESC, e.canonical_name ASC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = cur.fetchall()

        return EntityListResponse(
            items=[EntityResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def list_scenes(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> SceneListResponse:
        filters: list[str] = []
        params: dict[str, object] = {"limit": page_size, "offset": (page - 1) * page_size}
        if workspace_id is not None:
            filters.append("ms.workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if keyword:
            filters.append("(ms.scene_slug ILIKE %(keyword)s OR ms.title ILIKE %(keyword)s)")
            params["keyword"] = f"%{keyword}%"
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM memory_scene ms {where_clause}", params)
                total = cur.fetchone()["total"]
                cur.execute(
                    f"""
                    SELECT
                        ms.scene_id,
                        ms.workspace_id,
                        ms.scene_slug,
                        ms.title,
                        ms.summary,
                        ms.created_at,
                        ms.updated_at,
                        COUNT(DISTINCT msc.memory_id) AS memory_count
                    FROM memory_scene ms
                    LEFT JOIN memory_scene_cell msc ON msc.scene_id = ms.scene_id
                    {where_clause}
                    GROUP BY ms.scene_id
                    ORDER BY ms.updated_at DESC, ms.scene_slug ASC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = cur.fetchall()

        return SceneListResponse(
            items=[SceneResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )
