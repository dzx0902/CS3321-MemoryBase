from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from psycopg.errors import UniqueViolation

from ..core.database import Database
from ..models.source import (
    SourceCreateRequest,
    SourceDetailResponse,
    SourceImportResponse,
    SourceListResponse,
    SourceSummaryResponse,
)
from .chunking import build_chunks


class SourceConflictError(Exception):
    pass


class SourceNotFoundError(Exception):
    pass


class SourceRepository(Protocol):
    def create_source(
        self,
        payload: SourceCreateRequest,
        *,
        chunk_max_chars: int,
        chunk_overlap_lines: int,
    ) -> SourceImportResponse:
        ...

    def list_sources(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SourceListResponse:
        ...

    def get_source(
        self, doc_id: UUID, workspace_id: UUID, *, include_forgotten: bool = False
    ) -> SourceDetailResponse | None:
        ...


@dataclass(slots=True)
class SourceService:
    repository: SourceRepository
    chunk_max_chars: int
    chunk_overlap_lines: int

    def import_source(self, payload: SourceCreateRequest) -> SourceImportResponse:
        return self.repository.create_source(
            payload,
            chunk_max_chars=self.chunk_max_chars,
            chunk_overlap_lines=self.chunk_overlap_lines,
        )

    def list_sources(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SourceListResponse:
        return self.repository.list_sources(
            workspace_id=workspace_id,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size,
        )

    def get_source(
        self, doc_id: UUID, workspace_id: UUID, *, include_forgotten: bool = False
    ) -> SourceDetailResponse:
        source = self.repository.get_source(
            doc_id,
            workspace_id,
            include_forgotten=include_forgotten,
        )
        if source is None:
            raise SourceNotFoundError(f"source {doc_id} not found")
        return source


class PostgresSourceRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create_source(
        self,
        payload: SourceCreateRequest,
        *,
        chunk_max_chars: int,
        chunk_overlap_lines: int,
    ) -> SourceImportResponse:
        checksum = hashlib.sha256(payload.raw_text.encode("utf-8")).hexdigest()
        chunks = build_chunks(
            payload.raw_text,
            max_chars=chunk_max_chars,
            overlap_lines=chunk_overlap_lines,
        )

        try:
            with self._database.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO source_document (
                            workspace_id,
                            session_id,
                            doc_type,
                            title,
                            source_path,
                            raw_text,
                            checksum,
                            imported_by_user_id
                        )
                        VALUES (
                            %(workspace_id)s,
                            %(session_id)s,
                            %(doc_type)s,
                            %(title)s,
                            %(source_path)s,
                            %(raw_text)s,
                            %(checksum)s,
                            %(imported_by_user_id)s
                        )
                        RETURNING doc_id
                        """,
                        {
                            "workspace_id": payload.workspace_id,
                            "session_id": payload.session_id,
                            "doc_type": payload.doc_type,
                            "title": payload.title,
                            "source_path": payload.source_path,
                            "raw_text": payload.raw_text,
                            "checksum": checksum,
                            "imported_by_user_id": payload.imported_by_user_id,
                        },
                    )
                    row = cur.fetchone()
                    if row is None:
                        raise RuntimeError("failed to create source document")
                    doc_id = row["doc_id"]

                    for chunk in chunks:
                        cur.execute(
                            """
                            INSERT INTO source_chunk (
                                doc_id,
                                chunk_no,
                                chunk_text,
                                start_line,
                                end_line,
                                token_count
                            )
                            VALUES (
                                %(doc_id)s,
                                %(chunk_no)s,
                                %(chunk_text)s,
                                %(start_line)s,
                                %(end_line)s,
                                %(token_count)s
                            )
                            """,
                            {
                                "doc_id": doc_id,
                                "chunk_no": chunk.chunk_no,
                                "chunk_text": chunk.chunk_text,
                                "start_line": chunk.start_line,
                                "end_line": chunk.end_line,
                                "token_count": chunk.token_count,
                            },
                        )

                conn.commit()
                return SourceImportResponse(doc_id=doc_id, chunk_count=len(chunks))
        except UniqueViolation as exc:
            raise SourceConflictError(
                "source document with the same checksum already exists"
            ) from exc

    def list_sources(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SourceListResponse:
        query = """
            SELECT
                sd.doc_id,
                sd.workspace_id,
                sd.title,
                sd.doc_type,
                sd.source_path,
                sd.status,
                sd.imported_at,
                COUNT(sc.chunk_id) AS chunk_count
            FROM source_document sd
            LEFT JOIN source_chunk sc ON sc.doc_id = sd.doc_id
        """
        count_query = "SELECT COUNT(*) AS total FROM source_document sd"
        filters: list[str] = []
        params: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if status is None:
            filters.append("sd.status = 'active'")
        elif status != "all":
            filters.append("sd.status = %(status)s")
            params["status"] = status
        if workspace_id is not None:
            filters.append("sd.workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if keyword is not None:
            filters.append(
                "(sd.title ILIKE %(keyword)s OR COALESCE(sd.source_path, '') ILIKE %(keyword)s)"
            )
            params["keyword"] = f"%{keyword}%"
        if filters:
            where_clause = f" WHERE {' AND '.join(filters)}"
            query += where_clause
            count_query += where_clause
        query += """
            GROUP BY
                sd.doc_id,
                sd.workspace_id,
                sd.title,
                sd.doc_type,
                sd.source_path,
                sd.status,
                sd.imported_at
            ORDER BY sd.imported_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                cur.execute(query, params)
                rows = cur.fetchall()
        return SourceListResponse(
            items=[SourceSummaryResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_source(
        self, doc_id: UUID, workspace_id: UUID, *, include_forgotten: bool = False
    ) -> SourceDetailResponse | None:
        status_filter = "" if include_forgotten else "AND sd.status = 'active'"
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        sd.doc_id,
                        sd.workspace_id,
                        sd.session_id,
                        sd.title,
                        sd.doc_type,
                        sd.source_path,
                        sd.status,
                        sd.checksum,
                        sd.raw_text,
                        sd.imported_at,
                        COUNT(sc.chunk_id) AS chunk_count
                    FROM source_document sd
                    LEFT JOIN source_chunk sc ON sc.doc_id = sd.doc_id
                    WHERE sd.doc_id = %(doc_id)s
                      AND sd.workspace_id = %(workspace_id)s
                      {status_filter}
                    GROUP BY
                        sd.doc_id,
                        sd.workspace_id,
                        sd.session_id,
                        sd.title,
                        sd.doc_type,
                        sd.source_path,
                        sd.status,
                        sd.checksum,
                        sd.raw_text,
                        sd.imported_at
                    """,
                    {"doc_id": doc_id, "workspace_id": workspace_id},
                )
                source_row = cur.fetchone()
                if source_row is None:
                    return None

                cur.execute(
                    """
                    SELECT chunk_id, chunk_no, chunk_text, start_line, end_line, token_count
                    FROM source_chunk
                    WHERE doc_id = %(doc_id)s
                    ORDER BY chunk_no ASC
                    """,
                    {"doc_id": doc_id},
                )
                chunk_rows = cur.fetchall()

        return SourceDetailResponse(**source_row, chunks=chunk_rows)
