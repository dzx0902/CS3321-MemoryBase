from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from ..core.database import Database
from ..models.wiki import WikiExportRequest, WikiExportResponse


class WikiRepository(Protocol):
    def export_page(self, payload: WikiExportRequest) -> WikiExportResponse:
        ...


@dataclass(slots=True)
class WikiService:
    repository: WikiRepository

    def export_page(self, payload: WikiExportRequest) -> WikiExportResponse:
        return self.repository.export_page(payload)


class PostgresWikiRepository:
    def __init__(self, database: Database) -> None:
        self._database = database
        self._output_dir = Path(__file__).resolve().parents[3] / "data" / "markdown_wiki"

    def export_page(self, payload: WikiExportRequest) -> WikiExportResponse:
        page_data = self._build_markdown(payload)
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT page_id, current_revision_no, created_at
                    FROM wiki_page
                    WHERE workspace_id = %(workspace_id)s AND page_slug = %(page_slug)s
                    """,
                    {"workspace_id": payload.workspace_id, "page_slug": payload.page_slug},
                )
                existing = cur.fetchone()

                if existing is None:
                    generated_from_memory_id = (
                        payload.memory_ids[0]
                        if payload.memory_ids and len(payload.memory_ids) == 1
                        else None
                    )
                    cur.execute(
                        """
                        INSERT INTO wiki_page (
                            workspace_id,
                            page_slug,
                            page_type,
                            title,
                            generated_from_memory_id,
                            current_revision_no,
                            needs_rebuild
                        )
                        VALUES (
                            %(workspace_id)s,
                            %(page_slug)s,
                            %(page_type)s,
                            %(title)s,
                            %(generated_from_memory_id)s,
                            1,
                            FALSE
                        )
                        RETURNING page_id, current_revision_no, created_at
                        """,
                        {
                            **payload.model_dump(),
                            "generated_from_memory_id": generated_from_memory_id,
                        },
                    )
                    page_row = cur.fetchone()
                else:
                    next_revision_no = existing["current_revision_no"] + 1
                    cur.execute(
                        """
                        UPDATE wiki_page
                        SET
                            page_type = %(page_type)s,
                            title = %(title)s,
                            current_revision_no = %(current_revision_no)s,
                            needs_rebuild = FALSE
                        WHERE page_id = %(page_id)s
                        RETURNING page_id, current_revision_no, created_at
                        """,
                        {
                            "page_id": existing["page_id"],
                            "page_type": payload.page_type,
                            "title": payload.title,
                            "current_revision_no": next_revision_no,
                        },
                    )
                    page_row = cur.fetchone()

                if page_row is None:
                    raise RuntimeError("failed to upsert wiki page")

                cur.execute(
                    """
                    INSERT INTO wiki_page_revision (
                        page_id,
                        revision_no,
                        frontmatter_json,
                        body_markdown,
                        generated_by
                    )
                    VALUES (
                        %(page_id)s,
                        %(revision_no)s,
                        %(frontmatter_json)s::jsonb,
                        %(body_markdown)s,
                        'exporter'
                    )
                    """,
                    {
                        "page_id": page_row["page_id"],
                        "revision_no": page_row["current_revision_no"],
                        "frontmatter_json": _json_dumps(page_data["frontmatter_json"]),
                        "body_markdown": page_data["body_markdown"],
                    },
                )
            conn.commit()

        output_path = self._write_markdown_file(
            payload.page_slug,
            page_data["markdown_file_contents"],
            payload.workspace_id,
            payload.write_files,
        )

        return WikiExportResponse(
            page_id=page_row["page_id"],
            workspace_id=payload.workspace_id,
            page_slug=payload.page_slug,
            title=payload.title,
            page_type=payload.page_type,
            revision_no=page_row["current_revision_no"],
            body_markdown=page_data["body_markdown"],
            needs_rebuild=False,
            output_path=str(output_path),
            frontmatter_json=page_data["frontmatter_json"],
            source_doc_ids=page_data["source_doc_ids"],
            created_at=page_row["created_at"],
        )

    def _build_markdown(self, payload: WikiExportRequest) -> dict[str, object]:
        filters = ["mi.workspace_id = %(workspace_id)s", "mi.status = 'active'"]
        params: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "limit": payload.max_memories,
        }
        if payload.memory_ids is not None:
            filters.append("mi.memory_id = ANY(%(memory_ids)s::uuid[])")
            params["memory_ids"] = [str(memory_id) for memory_id in payload.memory_ids]
        where_clause = " AND ".join(filters)
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        mi.memory_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        array_remove(array_agg(DISTINCT sd.doc_id), NULL) AS source_doc_ids,
                        array_remove(array_agg(DISTINCT sd.title), NULL) AS source_titles
                    FROM memory_item mi
                    LEFT JOIN memory_evidence me ON me.memory_id = mi.memory_id
                    LEFT JOIN source_chunk sc ON sc.chunk_id = me.chunk_id
                    LEFT JOIN source_document sd ON sd.doc_id = sc.doc_id
                    WHERE {where_clause}
                    GROUP BY
                        mi.memory_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        mi.updated_at
                    ORDER BY importance DESC, confidence DESC, updated_at DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                memory_rows = cur.fetchall()

        generated_at = datetime.now(timezone.utc).isoformat()
        memory_ids = [row["memory_id"] for row in memory_rows]
        source_doc_ids = sorted(
            {doc_id for row in memory_rows for doc_id in (row["source_doc_ids"] or [])}
        )
        frontmatter_json = {
            "workspace_id": str(payload.workspace_id),
            "page_slug": payload.page_slug,
            "title": payload.title,
            "page_type": payload.page_type,
            "generated_at": generated_at,
            "memory_ids": [str(memory_id) for memory_id in memory_ids],
            "source_doc_ids": [str(doc_id) for doc_id in source_doc_ids],
        }

        lines = [f"# {payload.title}", "", f"- Page Type: {payload.page_type}", ""]
        if not memory_rows:
            lines.extend(["## Overview", "", "No active memories found for this workspace."])
        else:
            lines.extend(["## Active Memories", ""])
            for index, row in enumerate(memory_rows, start=1):
                source_titles = ", ".join(row["source_titles"] or [])
                source_ids = ", ".join(str(doc_id) for doc_id in (row["source_doc_ids"] or []))
                lines.extend(
                    [
                        f"### {index}. {row['summary'] or row['memory_type']}",
                        "",
                        row["canonical_text"],
                        "",
                        f"- Confidence: {row['confidence']}",
                        f"- Importance: {row['importance']}",
                        f"- Source IDs: {source_ids or 'N/A'}",
                        f"- Source Titles: {source_titles or 'N/A'}",
                        "",
                    ]
                )
        body_markdown = "\n".join(lines).strip() + "\n"
        frontmatter_lines = [
            "---",
            f"workspace_id: {payload.workspace_id}",
            f"page_slug: {payload.page_slug}",
            f"title: {payload.title}",
            f"page_type: {payload.page_type}",
            f"generated_at: {generated_at}",
            "memory_ids:",
        ]
        frontmatter_lines.extend(
            [f"  - {memory_id}" for memory_id in frontmatter_json["memory_ids"]] or ["  -"]
        )
        frontmatter_lines.append("source_doc_ids:")
        frontmatter_lines.extend(
            [f"  - {doc_id}" for doc_id in frontmatter_json["source_doc_ids"]] or ["  -"]
        )
        frontmatter_lines.append("---")
        markdown_file_contents = "\n".join(frontmatter_lines) + "\n\n" + body_markdown
        return {
            "body_markdown": body_markdown,
            "frontmatter_json": frontmatter_json,
            "source_doc_ids": source_doc_ids,
            "markdown_file_contents": markdown_file_contents,
        }

    def _write_markdown_file(
        self, page_slug: str, contents: str, workspace_id: object, write_files: bool
    ) -> Path:
        workspace_dir = self._output_dir / str(workspace_id)
        output_path = workspace_dir / f"{page_slug}.md"
        if write_files:
            workspace_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_text(contents, encoding="utf-8")
        return output_path


def _json_dumps(payload: object) -> str:
    import json

    return json.dumps(payload, default=str)
