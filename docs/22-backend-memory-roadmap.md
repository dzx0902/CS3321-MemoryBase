# Backend Memory Capability Roadmap

Document order:

```text
1/2 Backend implementation roadmap
2/2 Evaluation and benchmark roadmap: docs/23-evaluation-benchmark-roadmap.md
```

## Purpose

This document tracks backend implementation work for upgrading MemoryBase from a traceable memory database into an agent memory backend with semantic retrieval, automatic memory generation, lifecycle governance, conflict handling, forgetting verification, and context package optimization.

Evaluation and benchmark implementation is intentionally tracked separately in:

```text
docs/23-evaluation-benchmark-roadmap.md
```

## Branch And Workflow

- Do not use the `jflin` branch for this work.
- Use a dedicated feature branch per implementation batch.
- Keep backend changes separate from evaluation-only changes when possible.
- Do not commit, push, create PRs, or mutate GitHub issues unless explicitly requested by the owner.
- Before implementation, check existing code, open issues, and local dirty files.

## Current Backend Baseline

Relevant backend modules:

```text
backend/app/services/memory_service.py
backend/app/services/recall_service.py
backend/app/services/search_service.py
backend/app/services/context_pack_service.py
backend/app/services/governance_service.py
backend/app/services/conversation_service.py
backend/app/api/memories.py
backend/app/api/recall.py
backend/app/api/search.py
backend/app/api/governance.py
backend/app/api/sessions.py
database/01_schema_core.sql
database/02_schema_memory.sql
database/03_schema_governance.sql
database/04_indexes.sql
database/06_triggers.sql
```

Existing behavior already includes memory creation, evidence binding, lexical recall/search, context packaging, revisions/audit in parts of the schema, governance entities, and CLI/API access patterns. Verify the exact current state before editing.

## Backend Goal

Upgrade the system from:

```text
store + search + trace + govern
```

to:

```text
generate memory + semantic recall + closed-loop agent use + measurable governance + verified forgetting
```

## Implementation Phases

Read this document before changing backend behavior. Do not start a backend implementation phase until the corresponding evaluation target is either already available or explicitly deferred by the owner.

### Phase B1: Hybrid Memory Retrieval

Goal:

```text
keyword search + vector search + metadata filters + recency weighting + evidence quality weighting + reranking
```

Tasks:

```text
- Add embedding storage for memory and source chunks.
- Decide between embedding columns and memory_embeddings / chunk_embeddings tables.
- Add an embedding generation service boundary.
- Add vector search repository logic.
- Add hybrid scoring function.
- Preserve workspace, agent, memory_type, status, visibility, and created_at filters.
- Default retrieval to active memory only.
- Exclude archived, forgotten, superseded, and rejected memory by default.
- Return ranking explanations.
```

Suggested result shape:

```json
{
  "memory_id": "uuid",
  "score": 0.87,
  "keyword_score": 0.31,
  "vector_score": 0.42,
  "recency_score": 0.08,
  "evidence_score": 0.06,
  "rank_reason": "semantic match + recent + verified evidence"
}
```

Acceptance criteria:

```text
- Synonym or paraphrase queries can recall relevant memories.
- Default retrieval does not return forgotten / archived / superseded memory.
- Results include score, evidence, and ranking explanation.
- Evaluation can compare keyword-only vs hybrid retrieval.
```

### Phase B2: Automatic Memory Extraction Pipeline

Goal:

```text
raw document / chunk / conversation / agent result / wiki page -> candidate memories
```

Candidate memory shape:

```json
{
  "type": "decision",
  "content": "The project uses PostgreSQL as the primary database.",
  "confidence": 0.91,
  "status": "candidate",
  "source_chunk_ids": ["chunk_001"],
  "evidence_ids": ["ev_001"],
  "reason": "document contains explicit architecture decision"
}
```

Memory types:

```text
fact
decision
preference
task
risk
constraint
policy
summary
```

Potential APIs:

```text
POST /memory-extraction/from-document
POST /memory-extraction/from-session
POST /memory-extraction/from-chunks
GET  /memory-candidates
POST /memory-candidates/{id}/approve
POST /memory-candidates/{id}/reject
```

Implementation order:

```text
- Define CandidateMemory schema.
- Implement rule-based extraction first.
- Add LLM extraction later behind a service boundary.
- Bind source chunks and evidence automatically.
- Keep extracted memory in candidate status.
- Move to active only after approve.
```

Acceptance criteria:

```text
- Importing text can generate candidate memories.
- Candidate memories include source chunks or evidence.
- Candidate memories do not enter default retrieval.
- Approved candidates become active and retrievable.
```

### Phase B3: Memory Lifecycle State Machine

Recommended states:

```text
candidate
active
superseded
archived
forgotten
rejected
conflicted
```

Allowed transitions:

```text
candidate -> active
candidate -> rejected
active -> superseded
active -> archived
active -> conflicted
conflicted -> active
conflicted -> superseded
active -> forgotten
archived -> forgotten
```

Tasks:

```text
- Validate state transitions.
- Write memory revision records on state changes.
- Write audit logs on state changes.
- Keep default retrieval active-only.
- Keep default context packages active + verified only.
- Force forgotten memory out of retrieval, context, and exports.
```

Acceptance criteria:

```text
- Illegal transitions are rejected.
- Every state change has version and audit evidence.
- Non-active states are excluded by default.
- Forgotten memory cannot enter context packages.
```

### Phase B4: Conflict Detection And Resolution

Conflict types:

```text
duplicate
semantic_overlap
conflict
temporal_update
permission_risk
evidence_conflict
```

Tasks:

```text
- Search similar existing memories before activating a new memory.
- Detect duplicate / overlap / conflict / temporal update.
- Create conflict records.
- Generate suggested resolution.
- Add resolve API.
- Update memory statuses after resolution.
```

Potential APIs:

```text
POST /memories/{id}/detect-conflicts
GET  /conflicts
POST /conflicts/{id}/resolve
```

Example:

```text
Old memory: The project uses MySQL.
New memory: The project has moved to PostgreSQL.
Detection: temporal_update
Suggested action: mark old as superseded and activate new
```

Acceptance criteria:

```text
- Fact conflicts create conflict records.
- Temporal updates suggest superseding old memory.
- Resolve changes statuses correctly.
- Conflict handling is audited.
```

### Phase B5: Forgetting Execution And Verification

Governance flow:

```text
request -> approve -> execute -> verify -> audit
```

Suggested request states:

```text
submitted
approved
executing
executed
verified
rejected
failed
```

Tasks:

```text
- Implement forgetting approval.
- Locate related memory / evidence / wiki / context cache.
- Execute soft delete or redaction.
- Force retrieval exclusion for forgotten content.
- Run verification queries automatically.
- Generate forgetting audit reports.
```

Verification example:

```text
Forgotten content: temporary code 123456
Queries:
  - keyword search "123456"
  - semantic query "what is my verification code"
  - context generation query
  - agent answer query
Expected:
  - no output leaks 123456
```

Acceptance criteria:

```text
- Forgotten memory no longer appears in retrieval.
- Forgotten memory no longer enters context packages.
- Wiki exports do not contain forgotten content.
- Verification report proves the forgetting request took effect.
```

### Phase B6: Context Package Optimization

Tasks:

```text
- Add token budget control.
- Add memory priority scoring.
- Compress evidence.
- Include conflict and risk warnings.
- Apply permission filters before packaging.
- Standardize citations.
- Support agent-profile-specific context strategies.
```

Suggested context package shape:

```json
{
  "query": "...",
  "selected_memories": [],
  "supporting_evidence": [],
  "conflict_warnings": [],
  "risk_notes": [],
  "excluded_memories": [
    {
      "memory_id": "uuid",
      "reason": "archived / forgotten / permission_denied / low_score"
    }
  ],
  "token_budget": 4000,
  "estimated_tokens": 3250
}
```

Acceptance criteria:

```text
- Context packages stay under token budget.
- Each selected memory has a selection reason.
- Conflicts and risks are explicit.
- Permission-denied or forgotten content never enters context.
```

### Phase B7: Database Reliability Tests

Index and query optimization:

```text
- EXPLAIN ANALYZE export.
- Compare latency before and after indexes.
- Test large dataset retrieval performance.
- Focus queries:
  - workspace_id + status + memory_type
  - workspace_id + agent_id + visibility
  - memory_id -> evidence -> chunk -> raw_document
  - conflict status query
  - forget request status query
  - timeline query
```

Transaction consistency:

```text
- memory create
- memory revision create
- evidence link create
- audit log write
- timeline update
- rollback on partial failure
- concurrent update handling
- continuous revision numbers
```

Permission isolation:

```text
- workspace A cannot access workspace B.
- agent A cannot access agent B private memory.
- normal users cannot access restricted memory.
- forgotten memory is inaccessible even with permission.
```

Audit completeness:

```text
- memory create/update/archive
- conflict resolve
- forget execute
- permission change
```

## Version Targets

### v0.2 Backend Target

```text
- embedding storage
- hybrid retrieval
- retrieval explanation
- keyword-only vs hybrid comparison support
```

### v0.3 Backend Target

```text
- automatic memory extraction
- candidate memory state
- approve / reject workflow
- lifecycle state machine
- evidence auto-binding
```

### v0.4 Backend Target

```text
- conflict detection
- temporal update detection
- conflict resolution API
- forgetting execution
- forgetting verification
```

### v0.5 Backend Target

```text
- stronger external benchmark integration support
- long-context retention support
- baseline comparison hooks
```

## Non-Goals For First Backend PR

Do not bundle all backend roadmap items into one PR. Avoid mixing:

```text
- schema migration
- embedding provider integration
- automatic extraction
- lifecycle state machine
- conflict resolution
- forgetting execution
- context package rewrite
```

The first backend PR after evaluation should be narrow, preferably hybrid retrieval or lifecycle state validation, depending on benchmark evidence.

## Handoff Template

At the end of backend work, record:

```text
Date:
Branch:
Backend phase:
Files changed:
Schema changes:
API changes:
Commands run:
Validation evidence:
Behavior before:
Behavior after:
Known limitations:
Next backend step:
Do not touch:
```
