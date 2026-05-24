from __future__ import annotations

import psycopg
import pytest


def test_workspace_slug_is_unique_and_required(integration_db: str) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspace(workspace_id, slug, name, scope_type)
                VALUES
                  ('10000000-0000-0000-0000-000000000001', 'runtime-a', 'Runtime A', 'project')
                """
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    """
                    INSERT INTO workspace(workspace_id, slug, name, scope_type)
                    VALUES
                      ('10000000-0000-0000-0000-000000000002', 'runtime-a', 'Runtime B', 'project')
                    """
                )
