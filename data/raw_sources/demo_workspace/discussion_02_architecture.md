# Discussion 02: Architecture

Date: 2026-03-06
Participants: Alice, Bob, Carol, Demo Agent

## Notes

MemoryBase uses a file-database dual state model. Human readable Markdown remains useful for review, while PostgreSQL provides query, constraints, views, triggers, and auditability.

The core data flow is SourceDocument to SourceChunk to MemoryItem to MemoryEvidence. Revision and AuditLog record changes after memory creation.

The backend should expose import, source, memory, recall, policy, audit, and wiki export APIs. The frontend should show dashboard, source, memory, recall, wiki, timeline, audit, and conflict pages.

## Decisions

- PostgreSQL is the primary database.
- Markdown files remain the source projection and reporting output.
- The first demo focuses on deterministic SQL behavior, not LLM automation.
