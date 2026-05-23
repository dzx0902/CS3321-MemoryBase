from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.stats import MemoryStatisticResponse, StatsCountResponse, StatsOverviewResponse


class StatsRepository(Protocol):
    def overview(self, *, workspace_id: UUID) -> StatsOverviewResponse:
        ...


@dataclass(slots=True)
class StatsService:
    repository: StatsRepository

    def overview(self, *, workspace_id: UUID) -> StatsOverviewResponse:
        return self.repository.overview(workspace_id=workspace_id)


class PostgresStatsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def overview(self, *, workspace_id: UUID) -> StatsOverviewResponse:
        params = {"workspace_id": workspace_id}
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                scalar_counts = {
                    "source_count": self._count(
                        cur, "source_document", "workspace_id = %(workspace_id)s", params
                    ),
                    "chunk_count": self._chunk_count(cur, params),
                    "memory_count": self._count(
                        cur, "memory_item", "workspace_id = %(workspace_id)s", params
                    ),
                    "active_memory_count": self._count(
                        cur,
                        "memory_item",
                        "workspace_id = %(workspace_id)s AND status = 'active'",
                        params,
                    ),
                    "recall_count": self._count(
                        cur, "recall_log", "workspace_id = %(workspace_id)s", params
                    ),
                    "wiki_page_count": self._count(
                        cur, "wiki_page", "workspace_id = %(workspace_id)s", params
                    ),
                    "policy_count": self._count(
                        cur, "access_policy", "workspace_id = %(workspace_id)s", params
                    ),
                    "audit_count": self._count(
                        cur, "audit_log", "workspace_id = %(workspace_id)s", params
                    ),
                    "conflict_count": self._count(
                        cur, "conflict_record", "workspace_id = %(workspace_id)s", params
                    ),
                    "forget_request_count": self._count(
                        cur, "forget_request", "workspace_id = %(workspace_id)s", params
                    ),
                    "entity_count": self._count(
                        cur, "entity", "workspace_id = %(workspace_id)s", params
                    ),
                    "scene_count": self._count(
                        cur, "memory_scene", "workspace_id = %(workspace_id)s", params
                    ),
                }

                cur.execute(
                    """
                    SELECT memory_type, status, access_level, memory_count,
                           avg_confidence, avg_importance
                    FROM v_memory_statistics
                    WHERE workspace_id = %(workspace_id)s
                    ORDER BY memory_count DESC, memory_type ASC
                    """,
                    params,
                )
                memory_statistics = [
                    MemoryStatisticResponse(
                        memory_type=row["memory_type"],
                        status=row["status"],
                        access_level=row["access_level"],
                        memory_count=row["memory_count"],
                        avg_confidence=float(row["avg_confidence"])
                        if row["avg_confidence"] is not None
                        else None,
                        avg_importance=float(row["avg_importance"])
                        if row["avg_importance"] is not None
                        else None,
                    )
                    for row in cur.fetchall()
                ]

                memory_type_counts = self._group_counts(
                    cur,
                    "memory_item",
                    "memory_type",
                    "workspace_id = %(workspace_id)s",
                    params,
                )
                source_status_counts = self._group_counts(
                    cur,
                    "source_document",
                    "status",
                    "workspace_id = %(workspace_id)s",
                    params,
                )
                latest_activity_at = self._latest_activity_at(cur, params)

        return StatsOverviewResponse(
            workspace_id=workspace_id,
            memory_statistics=memory_statistics,
            memory_type_counts=memory_type_counts,
            source_status_counts=source_status_counts,
            latest_activity_at=latest_activity_at,
            **scalar_counts,
        )

    def _count(self, cur: object, table: str, where_clause: str, params: dict[str, object]) -> int:
        cur.execute(f"SELECT COUNT(*) AS total FROM {table} WHERE {where_clause}", params)
        return cur.fetchone()["total"]

    def _chunk_count(self, cur: object, params: dict[str, object]) -> int:
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM source_chunk sc
            JOIN source_document sd ON sd.doc_id = sc.doc_id
            WHERE sd.workspace_id = %(workspace_id)s
            """,
            params,
        )
        return cur.fetchone()["total"]

    def _group_counts(
        self,
        cur: object,
        table: str,
        column: str,
        where_clause: str,
        params: dict[str, object],
    ) -> list[StatsCountResponse]:
        cur.execute(
            f"""
            SELECT {column} AS name, COUNT(*) AS count
            FROM {table}
            WHERE {where_clause}
            GROUP BY {column}
            ORDER BY count DESC, name ASC
            """,
            params,
        )
        return [StatsCountResponse(name=row["name"], count=row["count"]) for row in cur.fetchall()]

    def _latest_activity_at(self, cur: object, params: dict[str, object]) -> object:
        cur.execute(
            """
            SELECT max(activity_at) AS latest_activity_at
            FROM (
                SELECT updated_at AS activity_at
                FROM memory_item
                WHERE workspace_id = %(workspace_id)s
                UNION ALL
                SELECT imported_at AS activity_at
                FROM source_document
                WHERE workspace_id = %(workspace_id)s
                UNION ALL
                SELECT created_at AS activity_at
                FROM audit_log
                WHERE workspace_id = %(workspace_id)s
                UNION ALL
                SELECT created_at AS activity_at
                FROM recall_log
                WHERE workspace_id = %(workspace_id)s
                UNION ALL
                SELECT updated_at AS activity_at
                FROM wiki_page
                WHERE workspace_id = %(workspace_id)s
            ) recent_activity
            """,
            params,
        )
        return cur.fetchone()["latest_activity_at"]
