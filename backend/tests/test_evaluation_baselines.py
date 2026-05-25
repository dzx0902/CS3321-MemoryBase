from __future__ import annotations

from evaluation.baselines import build_baseline_with_config
from evaluation.cases import EvaluationCase, EvaluationSession, EvaluationTurn


def test_recency_only_uses_latest_memory_first() -> None:
    case = EvaluationCase(
        case_id="temporal_update_001",
        source="synthetic",
        category="temporal_update",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[EvaluationTurn(role="user", content="我现在住在上海。")],
            ),
            EvaluationSession(
                session_id="s2",
                turns=[EvaluationTurn(role="user", content="我现在住在北京。")],
            ),
            EvaluationSession(
                session_id="s3",
                turns=[EvaluationTurn(role="user", content="我现在住在哪里？")],
            ),
        ],
        query="我现在住在哪里？",
        expected_answer="北京",
    )

    result = build_baseline_with_config(mode="recency_only", run_id="test").run_case(case)

    assert result.retrieved_memory_texts[0] == "我现在住在北京。"
    assert "北京" in result.generated_answer


def test_summary_memory_clears_local_memory_after_forget_turn() -> None:
    case = EvaluationCase(
        case_id="deletion_001",
        source="synthetic",
        category="deletion",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[EvaluationTurn(role="user", content="我的临时验证码是 123456。")],
            ),
            EvaluationSession(
                session_id="s2",
                turns=[EvaluationTurn(role="user", content="请忘记我的临时验证码。")],
            ),
            EvaluationSession(
                session_id="s3",
                turns=[EvaluationTurn(role="user", content="我的临时验证码是多少？")],
            ),
        ],
        query="我的临时验证码是多少？",
        expected_answer=None,
        forbidden_answers=["123456"],
        expected_behavior="refuse_or_unknown",
    )

    result = build_baseline_with_config(mode="summary_memory", run_id="test").run_case(case)

    assert "123456" not in result.generated_answer
    assert result.retrieved_memory_texts == []
