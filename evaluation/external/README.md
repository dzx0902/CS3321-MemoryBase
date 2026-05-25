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
| LongMemEval | Partially supported | Converts common JSON/JSONL records with question, answer, and session/message fields. |
| LoCoMo | Partially supported | Converts common conversation + qa records into one case per QA item. |
| MemoryAgentBench | Partially supported | Converts common interaction/message records into EvaluationCase JSONL. |
| BEIR | TODO | Retriever-only supplemental benchmark. |
| BEAM | TODO | Optional ultra-long context retention benchmark. |

Add download URLs, license notes, and exact raw file names before integrating each dataset.
