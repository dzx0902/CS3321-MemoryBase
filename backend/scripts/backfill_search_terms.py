from __future__ import annotations

import argparse
from dataclasses import dataclass

from app.core.database import Database
from app.services.tokenizer import build_search_text


@dataclass(frozen=True)
class BackfillCounts:
    source_chunks: int
    memories: int


def backfill_search_terms(
    database_url: str,
    *,
    full: bool,
    missing_only: bool,
    workspace_slug: str | None,
) -> BackfillCounts:
    if full == missing_only:
        raise ValueError("Choose exactly one of --full or --missing-only.")

    database = Database(database_url)
    source_count = 0
    memory_count = 0
    with database.connection() as conn:
        with conn.cursor() as cur:
            source_rows = _fetch_source_chunks(
                cur,
                missing_only=missing_only,
                workspace_slug=workspace_slug,
            )
            for row in source_rows:
                cur.execute(
                    """
                    UPDATE source_chunk
                    SET search_text_zh = %(search_text_zh)s
                    WHERE chunk_id = %(chunk_id)s
                    """,
                    {
                        "chunk_id": row["chunk_id"],
                        "search_text_zh": build_search_text(row["chunk_text"]),
                    },
                )
                source_count += 1

            memory_rows = _fetch_memories(
                cur,
                missing_only=missing_only,
                workspace_slug=workspace_slug,
            )
            if memory_rows:
                cur.execute("ALTER TABLE memory_item DISABLE TRIGGER USER")
                try:
                    for row in memory_rows:
                        cur.execute(
                            """
                            UPDATE memory_item
                            SET search_text_zh = %(search_text_zh)s
                            WHERE memory_id = %(memory_id)s
                            """,
                            {
                                "memory_id": row["memory_id"],
                                "search_text_zh": build_search_text(
                                    row["canonical_text"],
                                    row["summary"],
                                ),
                            },
                        )
                        memory_count += 1
                    cur.execute("ALTER TABLE memory_item ENABLE TRIGGER USER")
                except Exception:
                    conn.rollback()
                    raise
        conn.commit()
    return BackfillCounts(source_chunks=source_count, memories=memory_count)


def _fetch_source_chunks(cur, *, missing_only: bool, workspace_slug: str | None):
    filters = _workspace_filters("sd", workspace_slug)
    if missing_only:
        filters.append("sc.search_text_zh IS NULL")
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    cur.execute(
        f"""
        SELECT sc.chunk_id, sc.chunk_text
        FROM source_chunk sc
        JOIN source_document sd ON sd.doc_id = sc.doc_id
        {'JOIN workspace w ON w.workspace_id = sd.workspace_id' if workspace_slug else ''}
        {where_clause}
        ORDER BY sc.chunk_id
        """,
        {"workspace_slug": workspace_slug},
    )
    return cur.fetchall()


def _fetch_memories(cur, *, missing_only: bool, workspace_slug: str | None):
    filters = _workspace_filters("mi", workspace_slug)
    if missing_only:
        filters.append("mi.search_text_zh IS NULL")
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    cur.execute(
        f"""
        SELECT mi.memory_id, mi.canonical_text, mi.summary
        FROM memory_item mi
        {'JOIN workspace w ON w.workspace_id = mi.workspace_id' if workspace_slug else ''}
        {where_clause}
        ORDER BY mi.memory_id
        """,
        {"workspace_slug": workspace_slug},
    )
    return cur.fetchall()


def _workspace_filters(table_alias: str, workspace_slug: str | None) -> list[str]:
    if workspace_slug is None:
        return []
    return [f"{table_alias}.workspace_id = w.workspace_id", "w.slug = %(workspace_slug)s"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill MemoryBase lexical search fields.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true", help="Recompute every supported row.")
    mode.add_argument(
        "--missing-only",
        action="store_true",
        help="Only fill rows where search_text_zh is NULL.",
    )
    parser.add_argument("--workspace-slug", help="Limit backfill to one workspace slug.")
    parser.add_argument("--database-url", help="Override configured DATABASE_URL.")
    args = parser.parse_args()

    database_url = args.database_url
    if database_url is None:
        from app.core.config import get_settings

        database_url = get_settings().database_url

    counts = backfill_search_terms(
        database_url,
        full=args.full,
        missing_only=args.missing_only,
        workspace_slug=args.workspace_slug,
    )
    print(f"source_chunks={counts.source_chunks}")
    print(f"memories={counts.memories}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
