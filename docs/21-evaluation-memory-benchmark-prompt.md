# Evaluation Memory Benchmark Execution Prompt

## Purpose

Use this prompt as the long-context handoff record for building the MemoryBase evaluation and benchmark system. The goal is to make future agent runs preserve context, avoid duplicated work, and keep implementation aligned with the repository workflow.

MemoryBase is not a generic RAG demo. It is a database-backed agent memory management system. Evaluation must measure memory write, retrieval, update, conflict handling, forgetting, cross-session retention, preference following, auditability, and database performance.

## Repository Rules

- Reply to the project owner in Chinese.
- Keep code, comments, CLI output labels, and commit messages in English.
- Do not use the `jflin` branch for this work.
- Use a dedicated feature branch for this plan. Current suggested branch:

```text
feat/evaluation-memory-benchmark-plan
```

- Do not run `git commit`, `git push`, `gh pr create`, `gh issue edit`, `gh issue comment`, or issue-closing commands unless the owner explicitly asks for that exact action.
- Treat existing uncommitted changes as intentional owner work. Do not revert unrelated files.
- Before implementation, check current branch and worktree status.
- Before remote or issue decisions, check live GitHub issue state when tooling/network is available.

## Current Context Snapshot

Observed on 2026-05-25:

```text
Base branch before planning: dev
Dedicated planning branch: feat/evaluation-memory-benchmark-plan
Existing dirty files before this prompt:
  M docs/08-api-design.md
  ?? prompt3.md
  ?? prompt4.md
```

Do not assume `docs/08-api-design.md`, `prompt3.md`, or `prompt4.md` were authored by the current agent unless a later handoff says so.

Existing relevant code:

```text
backend/app/cli/commands/eval.py
backend/app/services/memory_service.py
backend/app/services/recall_service.py
backend/app/services/search_service.py
backend/app/services/context_pack_service.py
data/eval/recall_gold.json
data/eval/search_adversarial_gold.json
```

Open issue state checked through GitHub API because `gh` was unavailable in the local Windows shell. No open issue was found that directly owns the full unified evaluation framework. Closest related issues were:

```text
#38 Establish P0 API, SQL, permission, retrieval, and UI regression tests
#43 Future roadmap for pgvector, LLM, agent collaboration, and sync ecosystem
```

## Implementation Strategy

Build evaluation first, then improve retrieval and memory behavior. The first implementation phase should not start with embedding, hybrid retrieval, automatic extraction, or lifecycle refactors.

Recommended phase order:

```text
Phase 1: Unified evaluation framework skeleton
Phase 2: Synthetic benchmark cases and metrics
Phase 3: Real MemoryBase adapter using current APIs/CLI
Phase 4: External benchmark adapter skeletons
Phase 5: LongMemEval or LoCoMo small subset integration
Phase 6: Hybrid retrieval and memory-system improvements measured by the framework
```

## Phase 1 Task List

Create a minimal local framework under `evaluation/`:

```text
evaluation/
  README.md
  datasets/
  metrics/
  runners/
  reports/
  outputs/
```

Required capabilities:

```text
- JSONL case loader
- category filtering
- --limit support
- --dry-run support
- unified EvaluationCase schema
- CSV output
- benchmark_report.md generation
- baseline interface stubs:
  - no_memory
  - recency_only
  - naive_vector_rag
  - summary_memory
  - db_memory
```

Preferred language: Python, because the backend and existing CLI are Python-first.

Do not force TypeScript for evaluation unless the repository direction changes.

## Unified EvaluationCase

Use one internal schema for synthetic and external benchmarks:

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

## Metrics To Implement First

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
forbidden_answer_violation
simple_f1
```

Governance:

```text
latest_answer_accuracy
stale_memory_error_rate
deletion_success_rate
privacy_leakage_rate
preference_following_rate
```

Performance:

```text
p50_latency_ms
p95_latency_ms
p99_latency_ms
average_latency_ms
throughput_qps
error_rate
```

## Synthetic Case Coverage

Add small JSONL datasets first:

```text
single_fact: remember and answer one stable user fact
temporal_update: old city Shanghai, new city Beijing, answer latest city
deletion: remember code 123456, forget it, then do not leak it
preference: remember formula style preference, later obey it
forgetting: compare accuracy across longer synthetic histories
```

Synthetic cases should cover database-specific behavior that external benchmarks often miss:

```text
- soft delete exclusion
- forgotten status exclusion
- conflict resolution
- superseded memory suppression
- audit and revision expectations
- workspace or namespace isolation
```

## Real System Adapter Rules

The evaluation runner should eventually call real MemoryBase flows:

```text
memory write: current memory creation or conversation/session write path
retrieval: recall/search API or CLI client
context package: context pack service/API when available
agent answer: real agent endpoint if implemented; otherwise record as not supported
```

If a runner must directly write database rows because no API exists, it must mark this in the output report:

```text
injection_mode = direct_db
limitation = "Bypassed real memory write flow because no API exists yet."
```

Each run must isolate test data:

```text
test_namespace = eval_<timestamp>_<short_random_id>
test_user_id or workspace slug must be evaluation-specific
cleanup default should be safe and explicit
```

## External Benchmarks

External benchmark priority:

```text
1. LongMemEval
2. LoCoMo
3. MemoryAgentBench
4. BEIR or MS MARCO
5. BEAM
```

Do not modify raw benchmark formats. Use this structure:

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
```

If a dataset cannot be downloaded automatically:

```text
- keep an adapter skeleton
- document manual download path
- mark status as TODO or partially supported
- explain blocker in README
```

## Duplicate Work And Commit Check

Before starting implementation:

```bash
git status --short --branch
git fetch origin
git log --oneline --decorate --graph --all --max-count=40
git log --oneline origin/dev..HEAD
git diff --name-status origin/dev...HEAD
```

Check whether similar evaluation work already exists:

```bash
git log --all --grep "evaluation"
git log --all --grep "benchmark"
git log --all -- evaluation
rg -n "EvaluationCase|LongMemEval|LoCoMo|MemoryAgentBench|benchmark_report|Recall@|nDCG|MRR"
```

Check whether local commits duplicate target branch patches:

```bash
git cherry -v origin/dev HEAD
```

For two suspicious commits:

```bash
git show <commit-a> --patch | git patch-id --stable
git show <commit-b> --patch | git patch-id --stable
```

Before asking for commit approval:

```bash
git status --short
git diff --cached --name-status
git diff --cached
git log --oneline origin/dev..HEAD
```

## Long-Context Handoff Template

At the end of every substantial work session, append or update a concise handoff note in the active planning/report location:

```text
Date:
Branch:
Goal:
Files changed:
Commands run:
Validation evidence:
Current limitations:
Open questions:
Next exact step:
Do not touch:
```

Keep handoffs factual. Do not record secrets, API keys, database URLs, or real user data.

## Validation Plan

Minimum validation for the first evaluation framework PR:

```bash
python -m pytest backend/tests -q
python evaluation/runners/run_all.py --dataset evaluation/datasets/synthetic_memory_cases.jsonl --mode no_memory --limit 5 --dry-run
python evaluation/reports/generate_report.py
ruff check backend scripts evaluation
```

If some commands cannot run because dependencies or database services are unavailable, report:

```text
- command
- failure reason
- whether failure is environmental or code-related
- remaining risk
```

## Suggested First PR Scope

Keep the first PR reviewable:

```text
- evaluation README
- EvaluationCase schema and loader
- basic metrics modules
- synthetic cases
- dry-run runners
- CSV writer
- markdown report generator
- external benchmark README plus adapter skeletons only
```

Do not include:

```text
- pgvector schema changes
- embedding generation
- hybrid retrieval implementation
- lifecycle state machine changes
- conflict resolution behavior changes
- forgetting execution behavior changes
```

Those should be measured and implemented in later PRs.

## Suggested Commit Message

Use this only after the owner explicitly approves a commit:

```text
docs(evaluation): plan benchmark framework and handoff workflow
```
