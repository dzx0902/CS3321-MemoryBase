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
| LongMemEval | TODO | Primary long-term memory benchmark target. |
| LoCoMo | TODO | Multi-session dialogue memory target. |
| MemoryAgentBench | TODO | Memory-agent task benchmark target. |
| BEIR | TODO | Retriever-only supplemental benchmark. |
| BEAM | TODO | Optional ultra-long context retention benchmark. |

Add download URLs, license notes, and exact raw file names before integrating each dataset.
