from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.metrics.system_metrics import latency_summary  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUTS = PROJECT_ROOT / "evaluation" / "outputs"


def generate_report(*, outputs_dir: Path = DEFAULT_OUTPUTS) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    report_path = outputs_dir / "benchmark_report.md"
    csv_paths = sorted(path for path in outputs_dir.rglob("*_results.csv") if path.is_file())
    lines = [
        "# MemoryBase Benchmark Report",
        "",
        "## Experiment Settings",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| framework | local evaluation runner |",
        "| model | not configured in Phase E1 |",
        "| database | not called by no_memory/dry-run baseline |",
        "| outputs_dir | `%s` |" % outputs_dir.as_posix(),
        "",
        "## Result Files",
        "",
    ]
    if not csv_paths:
        lines.append("No result CSV files were found.")
    else:
        lines.extend(
            [
                "| File | Cases | Pass Rate | Error Count | P95 Latency (ms) |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for path in csv_paths:
            rows = _read_rows(path)
            pass_count = sum(1 for row in rows if row.get("pass") == "true")
            error_count = sum(1 for row in rows if row.get("error"))
            latencies = [_float(row.get("latency_ms")) for row in rows]
            summary = latency_summary(latencies, error_count=error_count)
            pass_rate = pass_count / len(rows) if rows else 0.0
            label = path.relative_to(outputs_dir).as_posix()
            lines.append(
                f"| `{label}` | {len(rows)} | {pass_rate:.2%} | {error_count} | "
                f"{summary['p95_latency_ms']:.3f} |"
            )

    lines.extend(["", "## Category Metrics", ""])
    category_rows = _category_rows(csv_paths)
    if category_rows:
        lines.extend(["| Category | Cases | Pass Rate |", "| --- | ---: | ---: |"])
        for category, values in sorted(category_rows.items()):
            total = values["total"]
            pass_rate = values["passed"] / total if total else 0.0
            lines.append(f"| {category} | {total} | {pass_rate:.2%} |")
    else:
        lines.append("No category metrics are available yet.")

    lines.extend(["", "## Baseline Metrics", ""])
    baseline_rows = _group_rows(csv_paths, "mode")
    if baseline_rows:
        lines.extend(
            [
                "| Baseline | Cases | Pass Rate | Avg F1 | Privacy Leakage | "
                "Stale Error | P95 Latency (ms) |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for mode, rows in sorted(baseline_rows.items()):
            lines.append(_metric_summary_row(mode, rows))
    else:
        lines.append("No baseline metrics are available yet.")

    lines.extend(["", "## Category Detail Metrics", ""])
    grouped_category_rows = _group_rows(csv_paths, "category")
    if grouped_category_rows:
        lines.extend(
            [
                "| Category | Cases | Pass Rate | Avg F1 | Privacy Leakage | Stale Error |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for category, rows in sorted(grouped_category_rows.items()):
            lines.append(_category_metric_summary_row(category, rows))
    else:
        lines.append("No detailed category metrics are available yet.")

    lines.extend(
        [
            "",
            "## Baseline Comparison",
            "",
            "`no_memory`, `recency_only`, `summary_memory`, `db_memory`, "
            "`db_extraction`, and `naive_vector_rag` execute. `db_extraction` "
            "uses rule-based candidate extraction before recall. `naive_vector_rag` "
            "runs local embedding backfill and then calls vector-mode recall.",
            "",
            "Run multiple baselines with `run_all.py --modes "
            "summary_memory,db_memory,naive_vector_rag` to create per-mode result "
            "subdirectories and this combined report.",
            "",
            "## Failed Cases",
            "",
        ]
    )
    failed = _failed_rows(csv_paths)
    if failed:
        lines.extend(["| Case | Category | Mode | Error |", "| --- | --- | --- | --- |"])
        for row in failed[:20]:
            lines.append(
                f"| {row.get('case_id', '')} | {row.get('category', '')} | "
                f"{row.get('mode', '')} | {row.get('error', '')} |"
            )
    else:
        lines.append("No failed cases were recorded.")

    lines.extend(
        [
            "",
            "## Current Limitations",
            "",
            "- `recency_only` and `summary_memory` use case sessions directly.",
            "- `db_memory` uses memory create and recall APIs.",
            "- `db_extraction` uses source import, chunk extraction, candidate approve, "
            "and recall.",
            "- `naive_vector_rag` depends on backend embedding tables and "
            "the local hashing provider.",
            "- External benchmark adapters support common JSON/JSONL shapes only.",
            "- LLM-as-judge, groundedness, and token cost are not implemented yet.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MemoryBase benchmark report.")
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS)
    args = parser.parse_args()
    path = generate_report(outputs_dir=args.outputs_dir)
    print(f"wrote benchmark report to {path}")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _category_rows(csv_paths: list[Path]) -> dict[str, Counter]:
    categories: dict[str, Counter] = defaultdict(Counter)
    for path in csv_paths:
        for row in _read_rows(path):
            category = row.get("category") or "uncategorized"
            categories[category]["total"] += 1
            if row.get("pass") == "true":
                categories[category]["passed"] += 1
    return categories


def _failed_rows(csv_paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in csv_paths:
        for row in _read_rows(path):
            if row.get("pass") != "true" or row.get("error"):
                rows.append(row)
    return rows


def _group_rows(csv_paths: list[Path], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in csv_paths:
        for row in _read_rows(path):
            grouped[row.get(key) or "unknown"].append(row)
    return grouped


def _metric_summary_row(label: str, rows: list[dict[str, str]]) -> str:
    pass_rate = _bool_rate(rows, "pass")
    avg_f1 = _average(rows, "simple_f1")
    privacy = _bool_rate(rows, "privacy_leakage")
    stale = _bool_rate(rows, "stale_memory_error")
    latencies = [_float(row.get("latency_ms")) for row in rows]
    p95 = latency_summary(latencies)["p95_latency_ms"]
    return (
        f"| {label} | {len(rows)} | {pass_rate:.2%} | {avg_f1:.3f} | "
        f"{privacy:.2%} | {stale:.2%} | {p95:.3f} |"
    )


def _category_metric_summary_row(label: str, rows: list[dict[str, str]]) -> str:
    return (
        f"| {label} | {len(rows)} | {_bool_rate(rows, 'pass'):.2%} | "
        f"{_average(rows, 'simple_f1'):.3f} | "
        f"{_bool_rate(rows, 'privacy_leakage'):.2%} | "
        f"{_bool_rate(rows, 'stale_memory_error'):.2%} |"
    )


def _bool_rate(rows: list[dict[str, str]], key: str) -> float:
    values = [row.get(key) for row in rows if row.get(key) in {"true", "false"}]
    if not values:
        return 0.0
    return sum(1 for value in values if value == "true") / len(values)


def _average(rows: list[dict[str, str]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows if row.get(key)]
    return sum(values) / len(values) if values else 0.0


def _float(value: str | None) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


if __name__ == "__main__":
    main()
