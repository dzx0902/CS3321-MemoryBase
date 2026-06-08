from __future__ import annotations

import re

from evaluation.cases import EvaluationCase


def score_qa(case: EvaluationCase, generated_answer: str) -> dict[str, float | bool]:
    exact = _normalize(generated_answer) == _normalize(case.expected_answer or "")
    contains = _contains_expected(case, generated_answer)
    refusal = _is_refusal(generated_answer)
    forbidden_mention = _has_forbidden_answer(case, generated_answer) or _has_forbidden_pattern(
        case, generated_answer
    )
    answer_latest = case.expected_behavior == "answer_latest"
    blocking_forbidden = forbidden_mention and not answer_latest
    stale_answer_error = answer_latest and not contains
    expected_refusal = case.expected_behavior == "refuse_or_unknown"
    expected_text = case.expected_answer or " ".join(case.expected_answer_contains)
    f1 = simple_f1(expected_text, generated_answer)
    passed = _passes_case(
        case,
        exact=exact,
        contains=contains,
        forbidden=blocking_forbidden,
        refusal=refusal,
    )
    return {
        "exact_match": exact,
        "contains_match": contains,
        "refusal_match": refusal,
        "forbidden_answer_violation": forbidden_mention,
        "historical_value_mention": answer_latest and forbidden_mention,
        "stale_answer_error": stale_answer_error,
        "simple_f1": f1,
        "pass": passed,
        "score": _score(
            exact=exact,
            contains=contains,
            forbidden=blocking_forbidden,
            refusal=expected_refusal and refusal,
            f1=f1,
        ),
    }


def simple_f1(expected: str, actual: str) -> float:
    expected_tokens = _tokens(expected)
    actual_tokens = _tokens(actual)
    if not expected_tokens and not actual_tokens:
        return 1.0
    if not expected_tokens or not actual_tokens:
        return 0.0
    expected_counts: dict[str, int] = {}
    for token in expected_tokens:
        expected_counts[token] = expected_counts.get(token, 0) + 1
    overlap = 0
    for token in actual_tokens:
        count = expected_counts.get(token, 0)
        if count:
            overlap += 1
            expected_counts[token] = count - 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(actual_tokens)
    recall = overlap / len(expected_tokens)
    return 2 * precision * recall / (precision + recall)


def _passes_case(
    case: EvaluationCase,
    *,
    exact: bool,
    contains: bool,
    forbidden: bool,
    refusal: bool,
) -> bool:
    if forbidden:
        return False
    if case.expected_behavior == "refuse_or_unknown" and case.expected_answer is None:
        return refusal
    if case.expected_answer_contains:
        return contains
    if case.expected_answer is not None:
        return exact or contains
    return not forbidden


def _contains_expected(case: EvaluationCase, generated_answer: str) -> bool:
    if case.expected_answer_contains:
        return all(item in generated_answer for item in case.expected_answer_contains)
    if case.expected_answer:
        return case.expected_answer in generated_answer
    return False


def _has_forbidden_answer(case: EvaluationCase, generated_answer: str) -> bool:
    return any(answer and answer in generated_answer for answer in case.forbidden_answers)


def _has_forbidden_pattern(case: EvaluationCase, generated_answer: str) -> bool:
    for pattern in case.forbidden_patterns:
        try:
            if re.search(pattern, generated_answer):
                return True
        except re.error:
            if pattern in generated_answer:
                return True
    return False


def _score(
    *,
    exact: bool,
    contains: bool,
    forbidden: bool,
    refusal: bool,
    f1: float,
) -> float:
    if forbidden:
        return 0.0
    if refusal:
        return 1.0
    if exact:
        return 1.0
    if contains:
        return max(0.8, f1)
    return f1


def _is_refusal(value: str) -> bool:
    normalized = _normalize(value)
    patterns = (
        r"\bi do not know\b",
        r"\bi don't know\b",
        r"\bnot enough (?:information|context)\b",
        r"\binsufficient (?:information|context)\b",
        r"\bcannot (?:determine|answer|tell)\b",
        r"\bcan't (?:determine|answer|tell)\b",
        r"\bunknown\b",
        r"不知道",
        r"不清楚",
        r"信息不足",
        r"无法(?:确定|判断|回答)",
        r"没有足够(?:的信息|上下文)",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _tokens(value: str) -> list[str]:
    normalized = _normalize(value)
    if not normalized:
        return []
    if " " in normalized:
        return normalized.split()
    return list(normalized)
