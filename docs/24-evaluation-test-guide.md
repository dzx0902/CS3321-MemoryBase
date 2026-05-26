# Evaluation Test Guide

## Purpose

This guide explains how to run the MemoryBase evaluation framework end to end. It covers local baselines, live `db_memory` evaluation, external benchmark conversion, performance checks, and report interpretation.

## Preconditions

Use Python 3.11+ from the repository root:

```bash
python --version
```

Install project dependencies in the same way used by the backend test workflow. Do not put API keys, database URLs, or real user data in benchmark files.

The runnable evaluation code lives under:

```text
evaluation/
```

Main datasets:

```text
evaluation/datasets/synthetic_memory_cases.jsonl
evaluation/datasets/conflict_cases.jsonl
evaluation/datasets/deletion_cases.jsonl
evaluation/datasets/preference_cases.jsonl
evaluation/datasets/performance_cases.jsonl
```

Outputs are generated under:

```text
evaluation/outputs/
```

Generated CSV and markdown reports are ignored by git.

## Step 1: Static Validation

Run lint first:

```bash
ruff check backend scripts evaluation
```

Expected result:

```text
All checks passed!
```

## Step 2: Unit Tests

Run evaluation-specific tests:

```bash
python -m pytest backend/tests/test_evaluation_baselines.py backend/tests/test_evaluation_adapters.py -q
```

Expected result:

```text
5 passed
```

For broader regression:

```bash
python -m pytest backend/tests -q
```

If `test_repo_context.py` fails in a restricted sandbox because `git init` cannot write `.pytest_tmp/.git/config`, rerun that test or the full suite with normal filesystem permissions.

## Step 3: Dry Run

Dry run validates dataset loading, filtering, CSV writing, and report generation without calling any backend or model:

```bash
python evaluation/runners/run_all.py \
  --dataset evaluation/datasets/synthetic_memory_cases.jsonl \
  --mode no_memory \
  --limit 5 \
  --dry-run
```

Expected outputs:

```text
evaluation/outputs/qa_results.csv
evaluation/outputs/retrieval_results.csv
evaluation/outputs/conflict_results.csv
evaluation/outputs/deletion_results.csv
evaluation/outputs/preference_results.csv
evaluation/outputs/forgetting_results.csv
evaluation/outputs/performance_results.csv
evaluation/outputs/benchmark_report.md
```

## Step 4: Local Baseline Runs

Run `recency_only`:

```bash
python evaluation/runners/run_all.py \
  --dataset evaluation/datasets/synthetic_memory_cases.jsonl \
  --mode recency_only \
  --limit 6
```

Run `summary_memory`:

```bash
python evaluation/runners/run_all.py \
  --dataset evaluation/datasets/synthetic_memory_cases.jsonl \
  --mode summary_memory \
  --limit 6
```

These baselines use only `EvaluationCase.sessions`; they do not call MemoryBase APIs. They are useful as cheap comparisons for temporal update, deletion leakage, and preference cases.

Current baseline status:

```text
no_memory       implemented
recency_only    implemented
summary_memory  implemented
db_memory       implemented against live API
naive_vector_rag implemented against live API with local embedding backfill and vector-mode recall
```

## Step 5: Performance Runner

Run the local performance dataset:

```bash
python evaluation/runners/run_performance_eval.py \
  --dataset evaluation/datasets/performance_cases.jsonl \
  --mode summary_memory
```

This currently measures runner/baseline latency, not database write/query/update/delete latency. Real database performance evaluation should use `db_memory` after the API is running.

## Step 6: Live db_memory Evaluation

Start MemoryBase API in another terminal using the repository's normal backend workflow. Then run:

```bash
python evaluation/runners/run_all.py \
  --dataset evaluation/datasets/synthetic_memory_cases.jsonl \
  --mode db_memory \
  --api-base http://localhost:8000 \
  --workspace cs3321-demo \
  --agent codex \
  --limit 6
```

You can also provide:

```text
MEMORYBASE_WORKSPACE
MEMORYBASE_AGENT
```

`db_memory` currently performs this flow:

```text
/api/health/detail
/api/sessions
/api/observe
/api/memories
/api/recall
```

For deletion cases it soft-deletes memories it injected:

```text
DELETE /api/memories/{memory_id}
```

Known limitation:

```text
db_memory uses explicit memory API injection. It does not yet test automatic memory extraction or full agent answer generation.
```

## Step 7: External Benchmark Conversion

Raw data must stay under:

```text
evaluation/external/<benchmark>/raw/
```

Processed `EvaluationCase` JSONL is written to:

```text
evaluation/external/<benchmark>/processed/
```

Convert LongMemEval-like JSON/JSONL:

```bash
python evaluation/runners/run_external_eval.py --benchmark longmemeval
```

Convert LoCoMo-like JSON/JSONL:

```bash
python evaluation/runners/run_external_eval.py --benchmark locomo
```

Convert MemoryAgentBench-like JSON/JSONL:

```bash
python evaluation/runners/run_external_eval.py --benchmark memoryagentbench
```

Direct wrappers:

```bash
python evaluation/runners/run_longmemeval_eval.py
python evaluation/runners/run_locomo_eval.py
python evaluation/runners/run_memoryagentbench_eval.py
```

Current adapter support is partial. It handles common JSON/JSONL shapes with fields such as:

```text
question / query
answer / expected_answer / target
sessions / haystack_sessions / conversation / messages / turns
qa / qas / questions
task_type / category
```

Official dataset variants must be verified before using results as benchmark evidence.

## Step 8: Report Generation

Generate or refresh the report:

```bash
python evaluation/reports/generate_report.py
```

Open:

```text
evaluation/outputs/benchmark_report.md
```

The report includes:

```text
- result files
- pass rate
- category metrics
- baseline metrics
- average F1
- privacy leakage rate
- stale memory error rate
- P95 latency
- failed cases
- current limitations
```

## Step 9: Interpreting Key Metrics

QA:

```text
exact_match
contains_match
simple_f1
forbidden_answer_violation
```

Retrieval:

```text
Recall@1 / Recall@3 / Recall@5 / Recall@10
Precision@k
MRR
nDCG@10
```

Governance:

```text
deletion_success = no forbidden deleted content leaked
privacy_leakage = forbidden answer appeared
stale_memory_error = stale forbidden answer appeared in temporal/conflict cases
preference_following = preference case passed
```

Performance:

```text
latency_ms
P50 / P95 / P99 helpers
```

## Step 10: Recommended Evidence Bundle

Before asking for review, collect:

```bash
ruff check backend scripts evaluation
python -m pytest backend/tests/test_evaluation_baselines.py backend/tests/test_evaluation_adapters.py -q
python evaluation/runners/run_all.py --dataset evaluation/datasets/synthetic_memory_cases.jsonl --mode recency_only --limit 6
python evaluation/runners/run_all.py --dataset evaluation/datasets/synthetic_memory_cases.jsonl --mode summary_memory --limit 6
python evaluation/runners/run_performance_eval.py --dataset evaluation/datasets/performance_cases.jsonl --mode summary_memory
python evaluation/reports/generate_report.py
```

If a live API is available, add:

```bash
python evaluation/runners/run_all.py \
  --dataset evaluation/datasets/synthetic_memory_cases.jsonl \
  --mode db_memory \
  --api-base http://localhost:8000 \
  --workspace <workspace> \
  --agent <agent> \
  --limit 6
```

## Remaining Work

Still not fully implemented:

```text
- naive_vector_rag baseline
- embedding similarity scoring
- official LongMemEval / LoCoMo / MemoryAgentBench full-format validation
- LLM-as-judge
- groundedness
- hallucination rate
- token usage and token cost
- real write/query/update/delete database performance suite
- real context leakage and answer leakage split
- long history 1K / 10K / 50K / 100K / 500K retention curves
```

These require either a running API with seed data, external benchmark files, or an LLM judge configuration.
