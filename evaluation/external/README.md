# External Benchmarks

Raw benchmark data belongs in:

```text
evaluation/external/<benchmark>/raw/
```

Converted `EvaluationCase` JSONL files belong in:

```text
evaluation/external/<benchmark>/processed/
```

Do not edit raw benchmark files in place. Adapters under `evaluation/adapters/` are
responsible for conversion.

## Status

| Benchmark | Status | Notes |
| --- | --- | --- |
| LongMemEval | Official format supported | Handles extensionless official files, nested sessions, dates, answer-session IDs, abstention, preferences, and knowledge updates. |
| LoCoMo | Official format supported | Handles session dictionaries, timestamps, speakers, image captions, QA categories, evidence IDs, and adversarial questions. |
| MemoryAgentBench | Partially supported | Converts common interaction/message records into EvaluationCase JSONL. |
| BEIR | TODO | Retriever-only supplemental benchmark. |
| BEAM | TODO | Optional ultra-long context retention benchmark. |

LongMemEval and LoCoMo download, license, and execution details are documented
in their benchmark directories. Add equivalent documentation before promoting
another adapter from partial support.
