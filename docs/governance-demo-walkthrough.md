# Governance Demo Walkthrough

This walkthrough pairs with `database/10_governance_demo_fixture.sql` and is intended
for final-report screenshots and the live demo.

## 1. Prepare the demo database

```bash
npm run db:setup
```

The setup command loads:

1. Core schema files `00_init.sql` through `06_triggers.sql`.
2. Seed workspace data from `07_seed.sql`.
3. Search backfill.
4. Governance fixture data from `10_governance_demo_fixture.sql`.
5. Demo SQL queries from `08_demo_queries.sql`.

## 2. Verify governance counts

```sql
SELECT status, count(*)
FROM memory_item
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
GROUP BY status
ORDER BY status;

SELECT status, count(*)
FROM conflict_record
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
GROUP BY status
ORDER BY status;

SELECT target_type, status, count(*)
FROM forget_request
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
GROUP BY target_type, status
ORDER BY target_type, status;
```

Expected demo signals:

- at least one `forgotten` memory;
- at least one `archived` memory;
- at least one `superseded` memory;
- at least one `resolved` conflict;
- at least one forgotten source document;
- at least two completed forget requests.

## 3. UI screenshot checklist

Capture these pages after backend and frontend are running:

1. Governance / Forget Requests: show completed requests for memory and source targets.
2. Governance / Conflicts: show one open conflict and one resolved conflict.
3. Governance / Audit: filter for `memory.forget`, `memory.soft_delete`, or
   `source.forget`. If the live demo also runs candidate extraction, additionally
   filter for `memory_extraction.run.complete`.
4. Memory Detail: show evidence and revision history for a governed memory.
5. Source Detail: show the forgotten source only from a governance/admin view if exposed.

## 4. SQL screenshot checklist

Use `database/08_demo_queries.sql` for broad demo results, then add these focused
queries if the report needs governance-specific evidence:

```sql
SELECT memory_id, status, canonical_text, superseded_by_memory_id
FROM memory_item
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
  AND status IN ('forgotten', 'archived', 'superseded')
ORDER BY status, memory_id;

SELECT conflict_id, conflict_type, status, resolution_note
FROM conflict_record
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
ORDER BY status, created_at DESC;

SELECT action_type, target_type, target_id, created_at
FROM audit_log
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
  AND action_type IN ('memory.forget', 'memory.soft_delete', 'source.forget')
ORDER BY created_at DESC;
```

## 5. Interpretation for the report

The fixture is intentionally small. Its goal is not to simulate a production
governance dataset, but to make the lifecycle visible:

- memory records are not physically deleted;
- old decisions can be archived or superseded;
- forgotten targets remain auditable;
- conflict records preserve both sides and the resolution;
- audit rows provide traceable operation history.
