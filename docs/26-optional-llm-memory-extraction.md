# Optional LLM Memory Extraction

## 1. Background

MemoryBase now supports two candidate extraction paths from selected `source_chunk`
records:

- `rule_based`: deterministic local heuristics, no external model required.
- `llm`: optional OpenAI-compatible analysis path, still writing reviewed
  candidates into the existing memory lifecycle.

This is an extension of the existing candidate workflow, not a replacement for
it. The product default remains `rule_based`, so the demo can still run without
network access or API keys.

## 2. Current lifecycle

The current end-to-end flow is:

```text
SourceDocument
  -> SourceChunk
  -> /api/memory-extraction/from-chunks
  -> MemoryItem(status='candidate')
  -> MemoryEvidence
  -> approve / reject
  -> active memory enters Memories / Recall / Graph / Wiki
```

Important points:

- Both extraction methods create `status='candidate'` memories first.
- New candidates do not enter default recall until a human approves them.
- Evidence still points back to exactly one selected chunk.
- The run is still recorded in `audit_log`.

## 3. Frontend usage

On `Sources -> Source Detail`:

1. Select one or more chunks.
2. Keep the default `Use LLM` unchecked to run `rule_based`.
3. Check `Use LLM` to reveal `API Key`, `Base URL`, `Model`, and `Provider`.
4. Click `Extract Candidates`.
5. Review generated candidates in place.
6. Click `Approve` or `Reject`.

The candidate cards still show the same review-oriented fields:

- `canonical_text`
- `memory_type`
- `importance`
- `confidence`
- source chunk title and line range

## 4. API contract

`POST /api/memory-extraction/from-chunks` now accepts an optional method switch:

```json
{
  "workspace_id": "uuid",
  "chunk_ids": ["uuid"],
  "max_candidates": 10,
  "method": "llm",
  "llm": {
    "api_key": "sk-...",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen-plus",
    "provider": "dashscope"
  }
}
```

Notes:

- `method` defaults to `rule_based`.
- `llm` is only needed when `method = "llm"`.
- `provider` is currently a metadata label for audit/debug visibility; the real
  request routing depends on `api_key`, `base_url`, and `model`.
- The backend expects an OpenAI-compatible `POST {base_url}/chat/completions`
  endpoint and requests JSON output.

Response shape:

```json
{
  "workspace_id": "uuid",
  "method": "llm",
  "created_count": 3,
  "candidates": []
}
```

## 5. CLI usage

The CLI now exposes `mb extract`:

```bash
mb extract \
  --workspace 00000000-0000-0000-0000-000000000201 \
  --chunk 11111111-1111-1111-1111-111111111111 \
  --chunk 22222222-2222-2222-2222-222222222222 \
  --max-candidates 10 \
  --method llm \
  --llm-api-key "$LLM_ANALYSIS_API_KEY" \
  --llm-base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --llm-model qwen-plus \
  --llm-provider dashscope
```

If you omit `--method`, the CLI falls back to `rule_based`.

## 6. LLM behavior

The new LLM path lives in an independent backend module:

- `backend/app/services/llm_analysis.py`

Its job is intentionally narrow:

- receive selected chunks
- ask an OpenAI-compatible model for JSON candidate drafts
- normalize `memory_type`, `confidence`, `importance`, and summary
- clamp outputs into the existing MemoryBase schema
- hand the results back to the existing extraction service

This keeps the main lifecycle unchanged:

- no new approval rules
- no direct write into `active`
- no schema expansion required for the first LLM pass

## 7. Qwen example

For Qwen through DashScope compatible mode, the frontend fields can be filled as:

- `Base URL`: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `Model`: `qwen-plus`
- `Provider`: `dashscope`

If using the international endpoint:

- `Base URL`: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

Use a non-thinking model for this flow, because the backend expects JSON output
compatible with `response_format = {"type": "json_object"}`.

## 8. What is still not implemented

This change does **not** yet implement the richer draft-table workflow discussed
in design notes:

- no `analysis_run`
- no `analysis_memory_draft`
- no `analysis_draft_evidence`

So the current architecture is:

- optional LLM-assisted candidate extraction: implemented
- analysis staging tables and richer review workspace: future work

## 9. Verification

The implementation was validated with:

- backend tests for LLM parsing, API, service, and CLI paths
- frontend `npm run lint`
- frontend `npm run build`

