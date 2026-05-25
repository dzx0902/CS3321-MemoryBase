from __future__ import annotations

import math


def recall_at_k(gold_ids: list[str], retrieved_ids: list[str], k: int) -> float:
    if not gold_ids:
        return 0.0
    return len(set(gold_ids) & set(retrieved_ids[:k])) / len(set(gold_ids))


def precision_at_k(gold_ids: list[str], retrieved_ids: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(gold_ids) & set(retrieved_ids[:k])) / k


def mrr(gold_ids: list[str], retrieved_ids: list[str]) -> float:
    gold = set(gold_ids)
    for index, memory_id in enumerate(retrieved_ids, start=1):
        if memory_id in gold:
            return 1 / index
    return 0.0


def ndcg_at_k(gold_ids: list[str], retrieved_ids: list[str], k: int) -> float:
    gold = set(gold_ids)
    if not gold:
        return 0.0
    dcg = 0.0
    for index, memory_id in enumerate(retrieved_ids[:k], start=1):
        if memory_id in gold:
            dcg += 1 / math.log2(index + 1)
    ideal_hits = min(len(gold), k)
    ideal_dcg = sum(1 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def score_retrieval(gold_ids: list[str], retrieved_ids: list[str]) -> dict[str, float]:
    return {
        "recall_at_1": recall_at_k(gold_ids, retrieved_ids, 1),
        "recall_at_3": recall_at_k(gold_ids, retrieved_ids, 3),
        "recall_at_5": recall_at_k(gold_ids, retrieved_ids, 5),
        "recall_at_10": recall_at_k(gold_ids, retrieved_ids, 10),
        "precision_at_1": precision_at_k(gold_ids, retrieved_ids, 1),
        "precision_at_3": precision_at_k(gold_ids, retrieved_ids, 3),
        "precision_at_5": precision_at_k(gold_ids, retrieved_ids, 5),
        "precision_at_10": precision_at_k(gold_ids, retrieved_ids, 10),
        "mrr": mrr(gold_ids, retrieved_ids),
        "ndcg_at_10": ndcg_at_k(gold_ids, retrieved_ids, 10),
    }
