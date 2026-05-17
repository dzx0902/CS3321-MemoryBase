# Discussion 04: Policy and Recall

Date: 2026-03-15
Participants: Alice, Bob, Demo Agent

## Notes

Recall should return memory items with supporting evidence and source chunks. The first version can use keyword search and PostgreSQL full text search.

AccessPolicy is needed because AI agents should not read every memory. Project level memory can be visible to a retriever agent, but private memory must stay hidden unless explicitly allowed.

The permissions demo should compare public, project, and private memories. A project-only retriever agent must not see private budget or personal coordination notes.

RecallLog records query text, filters, result count, top memory IDs, and context pack JSON.

## Decisions

- Build a view for agent visible memory.
- Seed one private memory for the permission demo.
- Record recall activity in RecallLog for audit and reporting.
