# Discussion 05: Wiki and Timeline

Date: 2026-03-20
Participants: Alice, Carol, Demo Agent

## Notes

The exported Wiki should make database memory readable by humans. Each WikiPage needs revisions so repeated export can be audited.

Wiki pages should include source provenance. A reader should be able to trace a wiki statement back to MemoryItem, MemoryEvidence, SourceChunk, and SourceDocument.

TimelineEntry is useful for showing how the project evolved from topic selection to schema design, recall, governance, and final demo.

## Decisions

- Export at least three wiki pages for the demo.
- Keep current_revision_no on WikiPage synchronized with WikiPageRevision.
- Mark wiki pages for rebuild when generated memory changes.
