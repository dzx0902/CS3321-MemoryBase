from __future__ import annotations


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile_value
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def latency_summary(latencies_ms: list[float], error_count: int = 0) -> dict[str, float]:
    total = len(latencies_ms)
    return {
        "p50_latency_ms": percentile(latencies_ms, 0.50),
        "p95_latency_ms": percentile(latencies_ms, 0.95),
        "p99_latency_ms": percentile(latencies_ms, 0.99),
        "average_latency_ms": sum(latencies_ms) / total if total else 0.0,
        "error_rate": error_count / (total + error_count) if total + error_count else 0.0,
    }
