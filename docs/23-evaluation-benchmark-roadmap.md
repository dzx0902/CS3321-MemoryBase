# Evaluation And Benchmark Roadmap

Document order:

```text
1/2 Backend implementation roadmap: docs/22-backend-memory-roadmap.md
2/2 Evaluation and benchmark roadmap
```

## Purpose

This document tracks evaluation and benchmark implementation for MemoryBase. It is separate from backend capability implementation so the project can first measure behavior, then improve the backend based on evidence.

Backend implementation roadmap is tracked separately in:

```text
docs/22-backend-memory-roadmap.md
```

## Evaluation Goal

Build a repeatable local framework for measuring:

```text
- memory retrieval quality
- long-term memory QA
- long-context retention and forgetting rate
- temporal update and conflict handling
- selective forgetting and deletion leakage
- long-term preference following
- database and system performance
- external benchmark compatibility
```

## Branch And Workflow

- Do not use the `jflin` branch for this work.
- Use a dedicated evaluation branch, such as:

```text
feat/evaluation-memory-benchmark-plan
```

- Keep evaluation-only changes separate from backend behavior changes where possible.
- Do not commit, push, create PRs, or mutate GitHub issues unless explicitly requested.
- Do not store API keys, real database URLs, or real user data in benchmark files.

## Preferred Technology

Use Python for the evaluation framework because the backend and CLI are Python-first:

```text
pyproject.toml
backend/app
backend/app/cli
backend/app/services
```

Do not force TypeScript unless project direction changes.

## Directory Plan

Minimum local framework:

```text
evaluation/
  README.md
  datasets/
    synthetic_memory_cases.jsonl
    conflict_cases.jsonl
    deletion_cases.jsonl
    preference_cases.jsonl
  metrics/
    retrieval_metrics.py
    qa_metrics.py
    forgetting_metrics.py
    system_metrics.py
  runners/
    run_retrieval_eval.py
    run_qa_eval.py
    run_forgetting_eval.py
    run_conflict_eval.py
    run_deletion_eval.py
    run_preference_eval.py
    run_performance_eval.py
    run_all.py
  reports/
    generate_report.py
  outputs/
    retrieval_results.csv
    qa_results.csv
    forgetting_results.csv
    conflict_results.csv
    deletion_results.csv
    preference_results.csv
    performance_results.csv
    benchmark_report.md
```

External benchmark extension:

```text
evaluation/
  adapters/
    longmemeval_adapter.py
    locomo_adapter.py
    memoryagentbench_adapter.py
    beam_adapter.py
    beir_adapter.py
  external/
    README.md
    longmemeval/
      raw/
      processed/
    locomo/
      raw/
      processed/
    memoryagentbench/
      raw/
      processed/
    beam/
      raw/
      processed/
    beir/
      raw/
      processed/
  runners/
    run_external_eval.py
    run_longmemeval_eval.py
    run_locomo_eval.py
    run_memoryagentbench_eval.py
  outputs/
    external/
      longmemeval_results.csv
      locomo_results.csv
      memoryagentbench_results.csv
      external_benchmark_report.md
```

## Unified EvaluationCase

All synthetic and external cases should convert to this internal shape:

```json
{
  "case_id": "string",
  "source": "synthetic | longmemeval | locomo | memoryagentbench | beam | beir",
  "category": "single_fact | multi_session | temporal_update | conflict | deletion | preference | abstention | summarization | retrieval | performance",
  "sessions": [
    {
      "session_id": "string",
      "turns": [
        {
          "role": "user | assistant | system",
          "content": "string",
          "metadata": {}
        }
      ]
    }
  ],
  "query": "string",
  "expected_answer": "string | null",
  "expected_answer_contains": [],
  "forbidden_answers": [],
  "forbidden_patterns": [],
  "gold_memory_ids": [],
  "expected_behavior": "answer | answer_latest | refuse_or_unknown | follow_preference | retrieve",
  "metadata": {}
}
```

## First Implementation Scope

Implement this document before large backend behavior changes. The evaluation framework is the measuring layer for the backend roadmap.

Phase E1 should be a minimal, reviewable framework:

```text
- JSONL loader
- category filter
- --limit support
- --dry-run support
- EvaluationCase validation
- baseline interface stubs
- QA metrics
- retrieval metrics
- CSV writer
- markdown report generator
- small synthetic datasets
- README with usage and metric explanations
```

Do not include backend behavior rewrites in Phase E1.

## Dataset Loader Requirements

The loader must support:

```text
- JSONL input
- category filtering
- case count limit
- dry-run mode
- clear validation errors with case_id when possible
```

Example CLI:

```bash
python evaluation/runners/run_all.py --dataset evaluation/datasets/synthetic_memory_cases.jsonl --mode db_memory --limit 20
python evaluation/runners/run_retrieval_eval.py --category single_fact
python evaluation/runners/run_conflict_eval.py --category temporal_update
python evaluation/runners/run_deletion_eval.py --category deletion
python evaluation/reports/generate_report.py
```

## Test Isolation

Every evaluation run should use isolated test data:

```text
- unique test namespace
- evaluation-specific user id or workspace slug
- safe cleanup option
- option to preserve failed cases for inspection
```

Recommended run metadata:

```text
run_id = eval_<timestamp>_<short_random_id>
namespace = run_id
mode = no_memory | recency_only | naive_vector_rag | summary_memory | db_memory
dataset = path
limit = number
```

## Memory Injection Rules

Preferred:

```text
case sessions -> real conversation or memory write flow -> query real recall/search/agent flow
```

Only directly write database rows if no real API exists. If direct DB writes are used, report it:

```text
injection_mode = direct_db
limitation = "Bypassed real memory write flow because no API exists yet."
```

## Query Result Fields

Each result CSV should include as many of these fields as applicable:

```text
case_id
source
category
query
expected_answer
generated_answer
retrieved_memory_ids
retrieved_memory_texts
retrieved_scores
latency_ms
token_usage
score
pass
error
mode
run_id
```

## Metrics

Retrieval:

```text
Recall@1
Recall@3
Recall@5
Recall@10
Precision@k
MRR
nDCG@10
```

QA:

```text
exact_match
contains_match
simple_f1
forbidden_answer_violation
```

Long-context forgetting:

```text
accuracy_by_history_length
retention_rate
forgetting_rate
```

Formulas:

```text
Forgetting Rate(L) = (Acc_short - Acc_L) / Acc_short
Retention Rate(L) = Acc_L / Acc_short
```

Conflict:

```text
temporal_accuracy
conflict_resolution_accuracy
stale_memory_error_rate
```

Deletion / forgetting:

```text
deletion_success_rate
privacy_leakage_rate
retrieval_leakage_rate
context_leakage_rate
answer_leakage_rate
```

Preference:

```text
preference_following_rate
preference_retrieval_rate
violation_rate
```

Performance:

```text
write_latency
query_latency_p50
query_latency_p95
query_latency_p99
update_latency
delete_latency
context_package_latency
qps
throughput
storage_cost
index_build_time
token_cost_per_answer
error_rate
```

## Synthetic Benchmarks

Use synthetic cases to cover database-specific behavior that external benchmarks do not cover well:

```text
- single fact memory
- multi-session QA
- temporal update
- conflict resolution
- deletion / selective forgetting
- long-term preference following
- soft delete exclusion
- superseded memory suppression
- permission and workspace isolation
- audit and revision expectations
```

Example categories:

```text
single_fact
temporal_update
deletion
preference_following
long_context_retention
permission_isolation
audit_coverage
```

## External Benchmarks

Priority:

```text
1. LongMemEval
2. LoCoMo
3. MemoryAgentBench
4. BEIR or MS MARCO
5. BEAM
6. GAIA / WorkBench / ToolBench as optional agent-task benchmarks
```

### LongMemEval

Purpose:

```text
long-term dialogue memory, cross-session reasoning, temporal reasoning, knowledge update, abstention
```

Status target:

```text
adapter skeleton first, then small subset runner
```

### LoCoMo

Purpose:

```text
long multi-session dialogue memory, personal information, event order, cross-session QA, event summarization
```

Important rule:

```text
Do not paste the whole dialogue into one prompt. Simulate session-by-session memory writes.
```

### MemoryAgentBench

Purpose:

```text
accurate retrieval, test-time learning, long-range understanding, conflict resolution
```

Status target:

```text
adapter skeleton; integrate closest subtasks first
```

### BEIR / MS MARCO / Natural Questions / HotpotQA

Purpose:

```text
retriever / embedding / reranker / generic RAG evaluation only
```

Warning:

```text
Do not treat these as primary evidence for long-term agent memory.
```

### BEAM

Purpose:

```text
ultra-long context retention stress testing
```

Status target:

```text
optional adapter design and small sample runner
```

### GAIA / WorkBench / ToolBench

Purpose:

```text
optional agent task-level evaluation after memory integration
```

Warning:

```text
Not a primary memory benchmark.
```

## Report Requirements

`benchmark_report.md` should include:

```text
- experiment settings
- model setting
- database setting
- dataset scale
- synthetic benchmark results
- external benchmark results
- retrieval-only benchmark results
- full agent QA benchmark results
- performance benchmark results
- failed case analysis
- baseline comparison placeholders
```

Tables to include:

```text
- overall score by benchmark
- accuracy / F1 / Recall@k by category
- retention rate by history length
- stale memory error rate for conflict/update tasks
- privacy leakage rate for deletion tasks
- P50 / P95 / P99 latency
- token cost by baseline
```

## Baselines

At minimum, reserve interfaces for:

```text
no_memory
recency_only
naive_vector_rag
summary_memory
db_memory
```

If only `db_memory` is functional at first, keep the structure ready for later baselines.

## Duplicate Work Checks

Before implementing:

```bash
git status --short --branch
git fetch origin
git log --oneline --decorate --graph --all --max-count=40
git log --oneline origin/dev..HEAD
git diff --name-status origin/dev...HEAD
git log --all --grep "evaluation"
git log --all --grep "benchmark"
git log --all -- evaluation
rg -n "EvaluationCase|LongMemEval|LoCoMo|MemoryAgentBench|benchmark_report|Recall@|nDCG|MRR"
```

Check duplicate patches:

```bash
git cherry -v origin/dev HEAD
git show <commit-a> --patch | git patch-id --stable
git show <commit-b> --patch | git patch-id --stable
```

## Validation Plan

Minimum validation for the first evaluation PR:

```bash
python evaluation/runners/run_all.py --dataset evaluation/datasets/synthetic_memory_cases.jsonl --mode no_memory --limit 5 --dry-run
python evaluation/reports/generate_report.py
ruff check backend scripts evaluation
python -m pytest backend/tests -q
```

If validation cannot run, report:

```text
- command
- failure reason
- whether environmental or code-related
- remaining risk
```

## Handoff Template

At the end of evaluation work, record:

```text
Date:
Branch:
Evaluation phase:
Files changed:
Datasets changed:
Commands run:
Validation evidence:
Metrics currently supported:
Unsupported metrics:
Known limitations:
Next evaluation step:
Do not touch:
```
