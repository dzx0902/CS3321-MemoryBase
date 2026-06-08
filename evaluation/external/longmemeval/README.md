# LongMemEval Integration

MemoryBase supports the official LongMemEval record shape published by the
LongMemEval authors:

```text
question_id
question / question_date / question_type
answer / answer_session_ids
haystack_sessions / haystack_session_ids / haystack_dates
```

The adapter preserves session IDs, answer-session IDs, dates, and per-turn
`has_answer` metadata. Session dates are also prefixed to turn text because the
current MemoryBase write APIs do not expose a separate event-time field.
LongMemEval assistant turns are persisted as benchmark memories as well as user
turns, which is required for its assistant-memory question type. Other datasets
retain the default user-turn-only injection behavior.

## Official Sources

- Repository: https://github.com/xiaowu0162/LongMemEval
- Dataset: https://huggingface.co/datasets/xiaowu0162/LongMemEval
- Paper: https://arxiv.org/abs/2410.10813

As of June 7, 2026, the Hugging Face repository exposes extensionless files:

| File | Approximate Size | Intended Use |
| --- | ---: | --- |
| `longmemeval_oracle` | 15 MB | Adapter validation and oracle-session experiments |
| `longmemeval_s` | 278 MB | Small-context benchmark |
| `longmemeval_m` | 2.7 GB | Medium-context benchmark |

The official code repository is MIT licensed. The dataset repository does not
currently declare a dataset license in its card metadata. Do not redistribute
the raw dataset until its data license and usage terms have been confirmed.

## Download

Download one variant at a time. Keeping a single variant in `raw/` avoids
duplicate question IDs across variants.

PowerShell example:

```powershell
$url = "https://huggingface.co/datasets/xiaowu0162/LongMemEval/resolve/main/longmemeval_oracle"
Invoke-WebRequest -Uri $url -OutFile evaluation/external/longmemeval/raw/longmemeval_oracle
```

The raw and processed files are ignored by Git. Only `.gitkeep` and this guide
should be committed.

## Convert

```bash
python evaluation/runners/run_external_eval.py --benchmark longmemeval
```

Output:

```text
evaluation/external/longmemeval/processed/longmemeval_cases.jsonl
```

## Local Smoke Test

This path does not call a paid provider:

```bash
python -m evaluation.runners.run_benchmark_eval \
  --benchmark longmemeval \
  --mode summary_memory \
  --limit 10 \
  --output evaluation/outputs/external/longmemeval/summary_memory_results.csv
```

## Live MemoryBase Test

Start the API and then run a small paid subset first:

```bash
python -m evaluation.runners.run_benchmark_eval \
  --benchmark longmemeval \
  --mode db_qa \
  --limit 10 \
  --api-base http://127.0.0.1:8000 \
  --workspace cs3321-demo \
  --agent demo-retriever \
  --output evaluation/outputs/external/longmemeval/db_qa_results.csv
```

The default live runner creates one isolated workspace per case and removes it
afterward. Use `--shared-workspace` only for deliberate persistence tests.

## Current Scoring Boundary

The adapter is format-complete for the official JSON records. Exact/contains
answer scoring is still weaker than the official LongMemEval LLM judge for
open-ended answers. Treat deterministic pass rates as smoke-test evidence until
an independent judge is configured.
