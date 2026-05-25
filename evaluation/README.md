# MemoryBase Evaluation Framework

## Purpose

This framework measures MemoryBase as a database-backed agent memory system, not as a
generic RAG demo. It is designed to evaluate retrieval, long-term QA, conflict handling,
forgetting, preference following, performance, and external benchmark compatibility.

Phase E1 is intentionally minimal. It validates data formats, runs local baselines, writes
CSV files, and generates a markdown report. It does not call the real MemoryBase backend yet.

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
Phase E2 uses the current memory API directly:

```text
case sessions -> /api/sessions + /api/observe
memory-bearing user turns -> /api/memories
query -> /api/recall
```

This is not full automatic memory extraction yet. It is marked as `injection_mode=memory_api`.

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
```

Reserved for later backend-connected phases:

```text
- groundedness
- hallucination rate
- LLM-as-judge score
- retention rate by real history length
- stale memory error rate from real conflict resolution
- privacy leakage rate from real forgetting execution
- token cost per answer
```

## Baselines

The framework reserves these modes:

```text
no_memory
recency_only
naive_vector_rag
summary_memory
db_memory
```

`no_memory`, `--dry-run`, and `db_memory` execute. `db_memory` requires a running API,
workspace, and optionally an agent. Other modes return explicit "reserved but not
implemented" errors until their adapters are connected.

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

| Benchmark | Purpose | Current Status |
| --- | --- | --- |
| LongMemEval | Long-term dialogue memory, temporal reasoning, abstention | TODO adapter skeleton |
| LoCoMo | Multi-session dialogue memory and event QA | TODO adapter skeleton |
| MemoryAgentBench | Memory-agent retrieval, learning, conflict tasks | TODO adapter skeleton |
| BEIR / MS MARCO | Retriever/RAG only, not primary memory evidence | TODO adapter skeleton |
| BEAM | Ultra-long context retention stress test | TODO adapter skeleton |

Manual download instructions and license notes should be added in
`evaluation/external/README.md` before storing raw benchmark data.

## Current Limitations

- The real MemoryBase API is not called in Phase E1.
- `db_memory` mode is reserved but not implemented.
- External adapters are skeleton-only in the next phase.
- No API keys, database URLs, or real user data should be stored in benchmark files.
