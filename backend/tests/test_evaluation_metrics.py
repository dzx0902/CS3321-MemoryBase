from evaluation.cases import EvaluationCase
from evaluation.metrics.qa_metrics import score_qa


def _case(**overrides: object) -> EvaluationCase:
    values = {
        "case_id": "temporal-1",
        "source": "synthetic",
        "category": "temporal_update",
        "sessions": [],
        "query": "Where do I live now?",
        "expected_answer": "Beijing",
        "forbidden_answers": ["Shanghai"],
        "expected_behavior": "answer_latest",
    }
    values.update(overrides)
    return EvaluationCase(**values)


def test_answer_latest_allows_historical_value_as_context() -> None:
    metrics = score_qa(_case(), "I previously lived in Shanghai, but now live in Beijing.")

    assert metrics["pass"] is True
    assert metrics["forbidden_answer_violation"] is True
    assert metrics["historical_value_mention"] is True
    assert metrics["stale_answer_error"] is False


def test_answer_latest_fails_when_latest_value_is_missing() -> None:
    metrics = score_qa(_case(), "You live in Shanghai.")

    assert metrics["pass"] is False
    assert metrics["stale_answer_error"] is True


def test_deletion_case_still_blocks_forbidden_content() -> None:
    case = _case(
        case_id="deletion-1",
        category="deletion",
        expected_answer=None,
        forbidden_answers=["secret-code"],
        expected_behavior="refuse_or_unknown",
    )

    metrics = score_qa(case, "The deleted value was secret-code.")

    assert metrics["pass"] is False
    assert metrics["forbidden_answer_violation"] is True
    assert metrics["historical_value_mention"] is False


def test_refusal_case_requires_explicit_unknown_answer() -> None:
    case = _case(
        case_id="adversarial-1",
        category="adversarial",
        expected_answer=None,
        forbidden_answers=["a painting"],
        expected_behavior="refuse_or_unknown",
    )

    hallucinated = score_qa(case, "She bought a sculpture.")
    refused = score_qa(case, "There is not enough information to answer that.")

    assert hallucinated["pass"] is False
    assert hallucinated["refusal_match"] is False
    assert refused["pass"] is True
    assert refused["refusal_match"] is True
    assert refused["score"] == 1.0
