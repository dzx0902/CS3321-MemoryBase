# LoCoMo Integration

MemoryBase supports the official `data/locomo10.json` release from the
`snap-research/locomo` repository.

## Official Sources

- Repository: https://github.com/snap-research/locomo
- Dataset file: https://github.com/snap-research/locomo/blob/main/data/locomo10.json
- Paper: https://arxiv.org/abs/2402.17753
- License: CC BY-NC 4.0

LoCoMo is licensed for attribution and non-commercial use. Do not use the raw
dataset or derived benchmark results for commercial purposes without separate
permission.

## Supported Official Fields

```text
sample_id
conversation.speaker_a / conversation.speaker_b
conversation.session_N / conversation.session_N_date_time
turn.speaker / turn.dia_id / turn.text
turn.img_url / turn.blip_caption
qa.question / qa.answer / qa.evidence / qa.category
qa.adversarial_answer
```

Both speakers are persisted as benchmark memories. Dialog IDs such as `D1:3`
are retained as source IDs so Recall@K, MRR, and nDCG can be calculated against
the official evidence annotations.

The paper defines the QA categories as:

| Value | Category |
| ---: | --- |
| 1 | single-hop |
| 2 | multi-hop |
| 3 | temporal reasoning |
| 4 | open-domain knowledge |
| 5 | adversarial |

Adversarial examples without a gold `answer` require an explicit unknown or
insufficient-information response. The supplied `adversarial_answer` is treated
as forbidden output. Two official examples include both a correct answer and an
adversarial answer; those are scored as normal answer cases with the misleading
answer forbidden.

## Download

```powershell
$url = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
Invoke-WebRequest -Uri $url -OutFile evaluation/external/locomo/raw/locomo10.json
```

Raw and processed files are ignored by Git.

## Convert

```bash
python evaluation/runners/run_external_eval.py --benchmark locomo
```

Output:

```text
evaluation/external/locomo/processed/locomo_cases.jsonl
```

The current `EvaluationCase` format stores the full conversation in every QA
case. The 2.8 MB official source therefore expands to roughly 654 MB for 1,986
QA cases. Convert once and reuse the processed file.

## Local Smoke Test

```bash
python -m evaluation.runners.run_qa_eval \
  --dataset evaluation/external/locomo/processed/locomo_cases.jsonl \
  --mode summary_memory \
  --limit 10 \
  --output evaluation/outputs/external/locomo/summary_memory_results.csv
```

This verifies conversion and deterministic retrieval scoring without paid API
calls. It is not expected to produce a competitive answer score.

## Live MemoryBase Test

Start with a small paid subset:

```bash
python -m evaluation.runners.run_qa_eval \
  --dataset evaluation/external/locomo/processed/locomo_cases.jsonl \
  --mode db_qa \
  --limit 10 \
  --api-base http://127.0.0.1:8000 \
  --workspace cs3321-demo \
  --agent demo-retriever \
  --output evaluation/outputs/external/locomo/db_qa_results.csv
```

The default live runner creates and removes one isolated workspace per case.

## Known Dataset Anomalies

The adapter normalizes combined and zero-padded evidence IDs. Two official QA
items still reference dialog IDs that do not exist in their conversations.
Those IDs remain visible in `metadata.missing_evidence` and are not guessed.
