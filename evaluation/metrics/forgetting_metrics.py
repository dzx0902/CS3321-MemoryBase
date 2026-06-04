from __future__ import annotations


def retention_rate(short_accuracy: float, long_accuracy: float) -> float:
    if short_accuracy <= 0:
        return 0.0
    return long_accuracy / short_accuracy


def forgetting_rate(short_accuracy: float, long_accuracy: float) -> float:
    if short_accuracy <= 0:
        return 0.0
    return (short_accuracy - long_accuracy) / short_accuracy
