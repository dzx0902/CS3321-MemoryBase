# MemoryBase Evaluation Framework

## Purpose

This framework measures MemoryBase as a database-backed agent memory system, not as a
generic RAG demo. It is designed to evaluate retrieval, long-term QA, conflict handling,
forgetting, preference following, performance, and external benchmark compatibility.

The framework supports local baselines and live end-to-end MemoryBase runs. Live QA modes
write session turns and memories, recall context, call the configured LLM provider, record
token usage and citations, then soft-delete memories created by the case.

## Data Format

Synthetic and external benchmarks are converted to one internal `EvaluationCase` JSONL shape:

```json
{
  "case_id": "single_fact_001",
  "source": "synthetic",
  "category": "single_fact",
  "sessions": [
    {
      "session_id": "s1",
      "turns": [
        {
          "role": "user",
          "content": "请记住，我最喜欢的编程语言是 Rust。"
        }
      ]
    }
  ],
  "query": "我最喜欢的编程语言是什么？",
  "expected_answer": "Rust",
  "expected_answer_contains": ["Rust"],
  "forbidden_answers": [],
  "forbidden_patterns": [],
  "gold_memory_ids": [],
  "expected_behavior": "answer",
  "metadata": {}
}
```

## Running

Validate cases without calling a backend:

```bash
python evaluation/runners/run_all.py --dry-run --limit 5
```

Run the current executable baseline:

```bash
python evaluation/runners/run_all.py --mode no_memory --limit 5
```

Run against a live MemoryBase API:

```bash
python evaluation/runners/run_all.py \
  --mode db_memory \
  --api-base http://localhost:8000 \
  --workspace cs3321-demo \
  --agent codex \
  --limit 5
```

`db_memory` can also read `MEMORYBASE_WORKSPACE` and `MEMORYBASE_AGENT`.

Run several baselines into one combined report:

```bash
python evaluation/runners/run_all.py \
  --modes summary_memory,db_qa,vector_qa,db_extraction_qa \
  --api-base http://localhost:8000 \
  --workspace cs3321-demo \
  --agent codex \
  --limit 5
```

When `--modes` is used, results are written under `evaluation/outputs/<mode>/`
and `benchmark_report.md` summarizes all modes together.

Live retrieval modes use the current memory API directly:

```text
case sessions -> /api/sessions + /api/observe
memory-bearing user turns -> /api/memories
query -> /api/recall
```

Live QA modes call `/api/qa/answer` after writing the case:

```text
db_qa             direct memory write + hybrid recall + LLM answer
vector_qa         embedding backfill + vector recall + LLM answer
db_extraction_qa  source extraction + approval + hybrid recall + LLM answer
```

Live CLI runs create an isolated workspace per case by default and delete it with all
dependent rows after scoring. Use `--shared-workspace` to reuse the requested workspace, or
`--preserve-eval-data` to keep isolated failure data. Shared-workspace cleanup can only
soft-delete created memories because session and source delete APIs do not exist yet.

Run individual suites:

```bash
python evaluation/runners/run_qa_eval.py --category single_fact
python evaluation/runners/run_retrieval_eval.py --category single_fact
python evaluation/runners/run_conflict_eval.py --category temporal_update
python evaluation/runners/run_deletion_eval.py --dataset evaluation/datasets/deletion_cases.jsonl
python evaluation/runners/run_preference_eval.py --dataset evaluation/datasets/preference_cases.jsonl
python evaluation/reports/generate_report.py
```

Outputs are written to:

```text
evaluation/outputs/
```

## Metrics

Implemented in Phase E1:

```text
- exact_match
- contains_match
- simple_f1
- forbidden_answer_violation
- Recall@1 / Recall@3 / Recall@5 / Recall@10
- Precision@1 / Precision@3 / Precision@5 / Precision@10
- MRR
- nDCG@10
- p50 / p95 / p99 latency helpers
- provider/model and prompt/completion/total token usage
- citation validity and deterministic citation-groundedness
- retrieval leakage and answer leakage
- retention/forgetting by measured history token length
```

Still model- or dataset-dependent:

```text
- hallucination rate
- LLM-as-judge score
- embedding cost per answer
```

LLM token cost per answer is estimated from a dated model-price snapshot when
the provider/model is known. The current DeepSeek snapshot assumes cache-miss
input pricing; update `evaluation/pricing.py` when provider prices change.

## Baselines

The framework reserves these modes:

```text
no_memory
recency_only
naive_vector_rag
summary_memory
db_memory
db_extraction
db_qa
vector_qa
db_extraction_qa
```

`no_memory`, `recency_only`, `summary_memory`, `--dry-run`, `db_memory`, `db_extraction`, and `naive_vector_rag` execute.
`recency_only` and `summary_memory` use only the case sessions and do not call the
backend. `db_memory` requires a running API, workspace, and optionally an agent.
`db_extraction` imports each memory-bearing turn as a source, extracts candidate
memories from chunks, approves them, and then recalls active memory.
`naive_vector_rag` also requires a running API. It writes evaluation memories through
the memory API, calls `/api/embeddings/backfill` with the local hashing provider, and
then calls `/api/recall` with `retrieval_mode=vector` so the result records backend
vector scoring fields.

## Long-Context Retention

```bash
python -m evaluation.runners.run_long_context_eval \
  --token-lengths 1000,10000,50000,100000 \
  --mode db_qa \
  --workspace cs3321-demo \
  --agent demo-retriever
```

The generator materializes filler history and records actual `cl100k_base` token counts.

## API Performance

```bash
python -m evaluation.runners.run_api_performance \
  --workspace cs3321-demo \
  --agent demo-retriever \
  --iterations 20
```

Add `--include-qa` only when real model latency and provider cost are intended.

## Adding Cases

Add one JSON object per line to a dataset under `evaluation/datasets/`. Prefer small,
focused cases with explicit `category`, `expected_answer`, `expected_answer_contains`,
`forbidden_answers`, and `expected_behavior`.

Use synthetic cases for database-specific behaviors:

```text
- deletion and soft delete exclusion
- forgotten status exclusion
- superseded memory suppression
- conflict resolution
- workspace isolation
- audit and revision coverage
```

## External Benchmarks

External data should not be modified in place.

```text
evaluation/external/<benchmark>/raw/
evaluation/external/<benchmark>/processed/
```

Adapters convert raw benchmark data into `EvaluationCase` JSONL.

Convert and execute supplied benchmark data in one command:

```bash
python -m evaluation.runners.run_benchmark_eval \
  --benchmark longmemeval \
  --mode db_qa \
  --workspace cs3321-demo \
  --agent demo-retriever
```

| Benchmark | Purpose | Current Status |
| --- | --- | --- |
| LongMemEval | Long-term dialogue memory, temporal reasoning, abstention | Official JSON format supported; independent judge pending |
| LoCoMo | Multi-session dialogue memory and event QA | Official QA format supported; event summarization pending |
| MemoryAgentBench | Memory-agent retrieval, learning, conflict tasks | TODO adapter skeleton |
| BEIR / MS MARCO | Retriever/RAG only, not primary memory evidence | TODO adapter skeleton |
| BEAM | Ultra-long context retention stress test | TODO adapter skeleton |

LongMemEval and LoCoMo source, license, and execution instructions are in their
respective directories under `evaluation/external/`. Equivalent notes are still
required before using other official benchmark files.

## Current Limitations

- `recency_only` and `summary_memory` are local baselines and do not call the backend.
- Retrieval-only modes do not generate an LLM answer; use the QA modes for that path.
- External adapters support common JSON/JSONL shapes but still need official dataset download and license documentation.
- Citation-groundedness validates references against the returned citation map; it is not an LLM judge.
- Shared-workspace runs cannot delete evaluation sessions or imported source documents.
- No API keys, database URLs, or real user data should be stored in benchmark files.
