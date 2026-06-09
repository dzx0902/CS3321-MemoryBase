# MemoryAgentBench Dataset Notes

## Official Source

- Repository: `https://github.com/HUST-AI-HYZ/MemoryAgentBench`
- Dataset: `https://huggingface.co/datasets/ai-hyz/MemoryAgentBench`
- Repository license: MIT

The official dataset contains parquet shards for Accurate Retrieval, Conflict
Resolution, Long Range Understanding, and Test-Time Learning.

## Supported Format

The adapter supports the official Conflict Resolution parquet shard. Each row
contains one shared context plus parallel question, answer, and QA identifier
arrays. Conversion expands every question into an `EvaluationCase` while
retaining a shared `context_group_id`.

Context is split into memory blocks below the 600-character context-pack
compaction boundary. Every block carries an explicit sequence label because the
official Conflict Resolution answer is determined by the later conflicting
fact.

## Commands

```bash
python evaluation/runners/run_external_eval.py --benchmark memoryagentbench
python evaluation/runners/run_grouped_benchmark_eval.py \
  --dataset evaluation/external/memoryagentbench/processed/memoryagentbench_cases.jsonl \
  --group factconsolidation_sh_6k \
  --limit 3 \
  --output evaluation/outputs/memoryagentbench/db_qa_results.csv
```

Grouped execution injects the shared context once and then evaluates multiple
questions in the same isolated workspace.
