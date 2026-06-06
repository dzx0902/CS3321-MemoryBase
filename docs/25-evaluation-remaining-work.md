# Evaluation Remaining Work

## Purpose

This document records evaluation-route items that are intentionally not complete yet. They require backend features, external datasets, a running API, or model/judge configuration.

## Backend-Dependent Items

```text
- embedding similarity scoring beyond backend recall scores
- keyword-only vs vector vs hybrid baseline comparison report
- concurrent saturation and load testing
- hard cleanup APIs for evaluation sessions and source documents
```

Required backend support:

```text
- source chunk vector retrieval path
- independent judge model configuration
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
- independent LLM-as-judge
- semantic groundedness beyond citation validation
- hallucination rate
- embedding similarity judge
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
Retrieval-only modes use direct memory API injection. `db_qa`, `vector_qa`, and
`db_extraction_qa` call the real answer endpoint. The extraction QA mode exercises source
import, candidate extraction, approval, recall, context packaging, and answer generation.
```

Current extraction support:

```text
- rule-based chunk -> candidate memory extraction exists
- candidate approve/reject workflow exists
- evaluation db_extraction mode can exercise source import -> extraction -> approve -> recall
- extraction from full documents and sessions is not implemented yet
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

## Newly Completed

```text
- provider-backed QA modes with prompt/completion/total token usage
- deterministic citation validity and citation-groundedness
- retrieval leakage and answer leakage split
- generated measured long-context retention curves
- sequential write/recall/context/QA/update/delete performance sampling
- external benchmark convert-and-run entry point
- default soft cleanup for evaluation-created memories
```
