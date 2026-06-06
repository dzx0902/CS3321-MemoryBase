from __future__ import annotations

from evaluation.performance import OperationSample, summarize_operations


def test_performance_summary_groups_operations_and_errors() -> None:
    summary = summarize_operations(
        [
            OperationSample("recall", 10.0, True, 200),
            OperationSample("recall", 20.0, True, 200),
            OperationSample("recall", 5.0, False, 500, "failed"),
            OperationSample("write", 8.0, True, 201),
        ]
    )

    assert summary["recall"]["samples"] == 3
    assert summary["recall"]["errors"] == 1
    assert summary["recall"]["p50_latency_ms"] == 15.0
    assert summary["recall"]["error_rate"] == 1 / 3
    assert summary["write"]["throughput_qps"] == 125.0
