# Evaluation Remaining Work

## Purpose

This document records evaluation-route items that are intentionally not complete yet. They require backend features, external datasets, a running API, or model/judge configuration.

## Backend-Dependent Items

```text
- embedding similarity scoring beyond backend recall scores
- keyword-only vs vector vs hybrid baseline comparison report
- real write/query/update/delete P50/P95/P99/QPS performance suite
- real context leakage and answer leakage split
- long history 1K / 10K / 50K / 100K / 500K retention curves
```

Required backend support:

```text
- source chunk vector retrieval path
- context package leakage inspection
- agent answer or answer-generation endpoint
```

## External Dataset Items

```text
- official LongMemEval full-format validation
- official LoCoMo full-format validation
- official MemoryAgentBench full-format validation
- BEIR / MS MARCO retriever-only benchmark conversion
- BEAM long-context stress benchmark conversion
```

Current state:

```text
- LongMemEval / LoCoMo / MemoryAgentBench support common JSON/JSONL shapes.
- Raw official datasets are not stored in this repository.
- Download URLs, licenses, and exact file names still need to be documented before use.
```

## Model-Dependent Items

```text
- LLM-as-judge
- groundedness
- hallucination rate
- embedding similarity judge
- token usage
- token cost per answer
```

Required configuration:

```text
- model provider
- judge prompt
- API key through environment/config only
- deterministic evaluation settings
- cost accounting policy
```

## Live API Items

```text
- db_memory synthetic benchmark evidence against a live API
- real deletion retrieval leakage
- real conflict stale memory error rate
- real context-pack leakage
- real wiki/export leakage
```

Current `db_memory` behavior:

```text
/api/health/detail
/api/sessions
/api/observe
/api/memories
/api/memory-extraction/from-chunks
/api/memory-candidates
/api/recall
DELETE /api/memories/{memory_id} for injected deletion cases
```

Limitation:

```text
It uses direct memory API injection. It does not yet test automatic memory extraction or full agent answer generation.
```

Current extraction support:

```text
- rule-based chunk -> candidate memory extraction exists
- candidate approve/reject workflow exists
- extraction from full documents and sessions is not implemented yet
- evaluation does not yet use extraction mode by default
```

## Current Backend Unlocks

```text
- memory and source chunk embedding storage exists
- local hashing embedding provider exists
- /api/embeddings/backfill exists
- recall returns keyword/vector/recency/evidence score fields when embeddings are present
- recall supports explicit keyword, vector, and hybrid retrieval modes
- recall vector mode can use both memory embeddings and source chunk embeddings through evidence
- evaluation naive_vector_rag can now backfill embeddings and call live recall
```

## Next Backend Route

Continue backend B1 by expanding vector coverage and reporting comparisons:

```text
1. Add benchmark report comparison for keyword-only / vector-only / hybrid.
2. Add embedding similarity scoring beyond backend recall scores.
3. Add real context leakage and answer leakage inspection.
4. Keep naive_vector_rag as the live API vector-backed baseline.
```
