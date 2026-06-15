# LongMemEval Full Evaluation - 2026-06-09

## Scope

This run evaluated all 500 official LongMemEval oracle cases with the live
MemoryBase `db_qa` path and DeepSeek `deepseek-chat`.

The evaluator included:

- session dates mapped to memory `valid_from`
- batched memory injection
- isolated evaluation workspaces
- per-case CSV checkpoints and resume support
- semantic LLM judgement with retry and resume support

## Results

| Metric | Result |
| --- | ---: |
| Cases | 500 |
| API errors | 0 |
| Deterministic pass | 176 / 500 (35.2%) |
| Semantic judge pass | 292 / 500 (58.4%) |
| Semantic judge fail | 208 / 500 (41.6%) |
| Deterministic failures upgraded by judge | 139 |
| Deterministic passes rejected by judge | 23 |
| Judge prompt tokens | 124,430 |
| Judge completion tokens | 27,327 |
| Estimated judge cost | 0.1791 CNY |

## Semantic Results By Category

| Category | Cases | Pass | Pass Rate |
| --- | ---: | ---: | ---: |
| abstention | 30 | 28 | 93.3% |
| temporal_update | 72 | 58 | 80.6% |
| single_fact | 120 | 95 | 79.2% |
| temporal_reasoning | 127 | 67 | 52.8% |
| preference_following | 30 | 11 | 36.7% |
| multi_session | 121 | 33 | 27.3% |

## Interpretation

The deterministic 35.2% score substantially underestimates semantic answer
quality because it relies on strict answer matching. The semantic judge accepts
paraphrases and equivalent calculations while rejecting answers that mention
the expected value but ultimately refuse or reach the wrong conclusion.

The strongest current capabilities are abstention, temporal updates, and
single-fact recall. Multi-session reasoning and preference following remain the
main quality bottlenecks.

The answer model and judge both used `deepseek-chat`. The 58.4% result is useful
engineering evidence, but publication-grade evaluation should use an
independent judge model or the official evaluator.

## Artifacts

The reviewable per-case score artifact is stored at:

```text
evaluation/results/longmemeval_full_20260609.csv
```

It contains case ID, category, deterministic pass, semantic pass, and judge
score for all 500 cases.

The complete generated-answer and judge-reason CSV remains a local generated
artifact under `evaluation/outputs/`. It exceeds the repository's large-file
limit and is not required to reproduce the aggregate results.

## Validation

```text
python -m pytest backend/tests/test_evaluation_judging.py -q
python -m pytest backend/tests/test_evaluation_baselines.py backend/tests/test_evaluation_adapters.py -q
python -m pytest backend/tests/test_memories.py -q
python -m pytest backend/tests/test_postgres_integration.py -k "batch_memory_create or atomically_supersede" -q
ruff check evaluation/judging.py backend/tests/test_evaluation_judging.py
```
