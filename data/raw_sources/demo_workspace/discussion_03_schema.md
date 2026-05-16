# Discussion 03: Schema

Date: 2026-03-10
Participants: Alice, Bob, Carol

## Notes

The schema needs clear primary keys, foreign keys, unique constraints, check constraints, indexes, views, and triggers.

SourceDocument stores imported files and checksum. SourceChunk stores chunk text, line range, and search vector. MemoryItem stores canonical memory, status, confidence, importance, access level, and current revision number.

MemoryEvidence connects MemoryItem and SourceChunk. This relationship is many-to-many because one memory can cite several chunks and one chunk can support several memories.

AuditLog records before and after JSON. MemoryRevision stores immutable memory versions.

## Decisions

- Evidence must always point to a real source chunk.
- Memory update history must be queryable without reading application logs.
- Soft delete uses status changes instead of physical deletion.
