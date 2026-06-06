from __future__ import annotations

from typing import Any

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


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


def test_naive_vector_rag_backfills_embeddings_before_recall(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append((method, url))
        if url.endswith("/api/health/detail"):
            return FakeResponse(
                {
                    "workspace": {
                        "found": True,
                        "workspace_id": "00000000-0000-0000-0000-000000000201",
                    }
                }
            )
        if url.endswith("/api/sessions"):
            return FakeResponse({"session_id": "session-1"})
        if url.endswith("/api/observe"):
            return FakeResponse({"message_id": "message-1"})
        if url.endswith("/api/memories"):
            return FakeResponse({"memory_id": "memory-1"})
        if url.endswith("/api/embeddings/backfill"):
            return FakeResponse({"memory_count": 1, "chunk_count": 1})
        if url.endswith("/api/recall"):
            assert kwargs["json"]["retrieval_mode"] == "vector"
            return FakeResponse(
                {
                    "memories": [
                        {
                            "memory_id": "memory-1",
                            "canonical_text": "Please remember that Rust is my favorite language.",
                            "score": 0.9,
                            "vector_score": 0.7,
                            "rank_reason": "semantic match",
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    case = EvaluationCase(
        case_id="single_fact_001",
        source="synthetic",
        category="single_fact",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="Please remember that Rust is my favorite language.",
                    )
                ],
            )
        ],
        query="What is my favorite language?",
        expected_answer="Rust",
    )

    result = build_baseline_with_config(
        mode="naive_vector_rag",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
        cleanup=False,
    ).run_case(case)

    assert result.error == ""
    assert result.mode == "naive_vector_rag"
    assert result.retrieved_memory_ids == ["memory-1"]
    assert result.metadata["retrieval_mode"] == "vector_backfilled"
    assert result.metadata["vector_scores"] == [0.7]
    assert ("POST", "http://testserver/api/embeddings/backfill") in calls
    assert calls.index(("POST", "http://testserver/api/embeddings/backfill")) < calls.index(
        ("POST", "http://testserver/api/recall")
    )


def test_db_extraction_uses_candidate_workflow_before_recall(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append((method, url))
        if url.endswith("/api/health/detail"):
            return FakeResponse(
                {
                    "workspace": {
                        "found": True,
                        "workspace_id": "00000000-0000-0000-0000-000000000201",
                    }
                }
            )
        if url.endswith("/api/sessions"):
            return FakeResponse({"session_id": "session-1"})
        if url.endswith("/api/observe"):
            return FakeResponse({"message_id": "message-1"})
        if url.endswith("/api/sources") and method == "POST":
            return FakeResponse({"doc_id": "doc-1", "chunk_count": 1})
        if url.endswith("/api/sources/doc-1"):
            return FakeResponse({"chunks": [{"chunk_id": "chunk-1"}]})
        if url.endswith("/api/memory-extraction/from-chunks"):
            return FakeResponse({"candidates": [{"memory_id": "candidate-1"}]})
        if url.endswith("/api/memory-candidates/candidate-1/approve"):
            return FakeResponse({"memory": {"memory_id": "memory-1", "status": "active"}})
        if url.endswith("/api/recall"):
            return FakeResponse(
                {
                    "memories": [
                        {
                            "memory_id": "memory-1",
                            "canonical_text": "Please remember that Rust is my favorite language.",
                            "score": 0.8,
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    case = EvaluationCase(
        case_id="single_fact_001",
        source="synthetic",
        category="single_fact",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="Please remember that Rust is my favorite language.",
                    )
                ],
            )
        ],
        query="What is my favorite language?",
        expected_answer="Rust",
    )

    result = build_baseline_with_config(
        mode="db_extraction",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
        cleanup=False,
    ).run_case(case)

    assert result.error == ""
    assert result.mode == "db_extraction"
    assert result.metadata["write_mode"] == "extraction_candidates"
    assert result.retrieved_memory_ids == ["memory-1"]
    assert ("POST", "http://testserver/api/memory-extraction/from-chunks") in calls
    assert ("POST", "http://testserver/api/memory-candidates/candidate-1/approve") in calls


def test_db_qa_calls_answer_endpoint_and_cleans_up(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append((method, url))
        if url.endswith("/api/health/detail"):
            return FakeResponse(
                {
                    "workspace": {
                        "found": True,
                        "workspace_id": "00000000-0000-0000-0000-000000000201",
                    }
                }
            )
        if url.endswith("/api/sessions"):
            return FakeResponse({"session_id": "session-1"})
        if url.endswith("/api/observe"):
            return FakeResponse({"message_id": "message-1"})
        if url.endswith("/api/memories") and method == "POST":
            return FakeResponse({"memory_id": "memory-1"})
        if url.endswith("/api/qa/answer"):
            return FakeResponse(
                {
                    "answer": "Rust [M1].",
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "prompt_tokens": 100,
                    "completion_tokens": 5,
                    "total_tokens": 105,
                    "token_count": 30,
                    "token_budget": 3000,
                    "citation_map": {"memories": {"M1": {"memory_id": "memory-1"}}},
                    "supporting_evidence": [],
                    "selected_memories": [
                        {"memory_id": "memory-1", "score": 0.9, "selection_reason": "match"}
                    ],
                }
            )
        if "/api/memories/memory-1" in url and method == "DELETE":
            return FakeResponse({"memory_id": "memory-1", "status": "forgotten"})
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    case = EvaluationCase(
        case_id="single_fact_qa",
        source="synthetic",
        category="single_fact",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="Please remember that Rust is my favorite language.",
                    )
                ],
            )
        ],
        query="What is my favorite language?",
        expected_answer="Rust",
    )

    result = build_baseline_with_config(
        mode="db_qa",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
    ).run_case(case)

    assert result.error == ""
    assert result.generated_answer == "Rust [M1]."
    assert result.token_usage == 105
    assert result.metadata["provider"] == "deepseek"
    assert result.retrieved_memory_ids == ["memory-1"]
    assert ("POST", "http://testserver/api/qa/answer") in calls
    assert ("DELETE", "http://testserver/api/memories/memory-1") in calls
