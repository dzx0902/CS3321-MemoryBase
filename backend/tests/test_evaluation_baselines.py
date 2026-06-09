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


def test_longmemeval_local_baseline_includes_assistant_turns() -> None:
    case = EvaluationCase(
        case_id="longmemeval_assistant_001",
        source="longmemeval",
        category="single_fact",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[
                    EvaluationTurn(role="user", content="What should I cook?"),
                    EvaluationTurn(role="assistant", content="Try mushroom risotto."),
                ],
            )
        ],
        query="What dish did the assistant suggest?",
        expected_answer="mushroom risotto",
    )

    result = build_baseline_with_config(mode="summary_memory", run_id="test").run_case(case)

    assert "Try mushroom risotto." in result.retrieved_memory_texts


def test_locomo_local_baseline_uses_dialog_ids_for_retrieval() -> None:
    case = EvaluationCase(
        case_id="locomo_conv-1_qa001",
        source="locomo",
        category="single_hop",
        sessions=[
            EvaluationSession(
                session_id="session_1",
                turns=[
                    EvaluationTurn(
                        role="assistant",
                        content="Melanie: The race supported mental health.",
                        metadata={"dia_id": "D1:2"},
                    )
                ],
            )
        ],
        query="What did the race support?",
        expected_answer="mental health",
        gold_memory_ids=["D1:2"],
    )

    result = build_baseline_with_config(mode="summary_memory", run_id="test").run_case(case)

    assert result.retrieved_memory_ids == ["D1:2"]
    assert "mental health" in result.generated_answer


def test_locomo_local_baseline_does_not_apply_deletion_forget_heuristic() -> None:
    case = EvaluationCase(
        case_id="locomo_conv-1_qa002",
        source="locomo",
        category="single_hop",
        sessions=[
            EvaluationSession(
                session_id="session_1",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="Caroline: Do not forget that the race supported mental health.",
                        metadata={"dia_id": "D1:1"},
                    ),
                    EvaluationTurn(
                        role="assistant",
                        content="Melanie: I will remember that.",
                        metadata={"dia_id": "D1:2"},
                    ),
                ],
            )
        ],
        query="What did the race support?",
        expected_answer="mental health",
        gold_memory_ids=["D1:1"],
    )

    result = build_baseline_with_config(mode="summary_memory", run_id="test").run_case(case)

    assert result.retrieved_memory_ids[:2] == ["D1:1", "D1:2"]


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


def test_longmemeval_live_baseline_writes_assistant_turns(monkeypatch) -> None:
    memory_payloads: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
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
        if url.endswith("/api/memories/batch"):
            memory_payloads.extend(kwargs["json"]["items"])
            return FakeResponse({"items": [{"memory_id": "memory-1"}]})
        if url.endswith("/api/recall"):
            return FakeResponse({"memories": []})
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    case = EvaluationCase(
        case_id="longmemeval_assistant_002",
        source="longmemeval",
        category="single_fact",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[EvaluationTurn(role="assistant", content="Try mushroom risotto.")],
            )
        ],
        query="What dish did the assistant suggest?",
        expected_answer="mushroom risotto",
    )

    result = build_baseline_with_config(
        mode="db_memory",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
        cleanup=False,
    ).run_case(case)

    assert result.error == ""
    assert [payload["canonical_text"] for payload in memory_payloads] == ["Try mushroom risotto."]


def test_live_baseline_maps_dates_and_supersession_into_batch_payloads(monkeypatch) -> None:
    batches: list[list[dict[str, Any]]] = []
    next_memory_id = 1

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        nonlocal next_memory_id
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
        if url.endswith("/api/memories/batch"):
            items = kwargs["json"]["items"]
            batches.append(items)
            response_items = []
            for _item in items:
                response_items.append({"memory_id": f"memory-{next_memory_id}"})
                next_memory_id += 1
            return FakeResponse({"items": response_items})
        if url.endswith("/api/recall"):
            return FakeResponse({"memories": []})
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    case = EvaluationCase(
        case_id="memoryagentbench_supersession",
        source="memoryagentbench",
        category="conflict_single_hop_6k",
        sessions=[
            EvaluationSession(
                session_id="s1",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="The chairperson is Alice.",
                        metadata={
                            "valid_from": "2000-01-01T00:00:01+00:00",
                            "supersession_key": "chairperson",
                        },
                    )
                ],
            ),
            EvaluationSession(
                session_id="s2",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="The unrelated fact is stable.",
                        metadata={"session_date": "2023/04/10 (Mon) 17:50"},
                    )
                ],
            ),
            EvaluationSession(
                session_id="s3",
                turns=[
                    EvaluationTurn(
                        role="user",
                        content="The chairperson is Bob.",
                        metadata={
                            "valid_from": "2000-01-01T00:00:03+00:00",
                            "supersession_key": "chairperson",
                        },
                    )
                ],
            ),
        ],
        query="Who is the chairperson?",
        expected_answer="Bob",
        expected_behavior="answer_latest",
    )

    result = build_baseline_with_config(
        mode="db_memory",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
        cleanup=False,
    ).run_case(case)

    assert result.error == ""
    assert [len(batch) for batch in batches] == [2, 1]
    assert batches[0][0]["valid_from"] == "2000-01-01T00:00:01+00:00"
    assert batches[0][1]["valid_from"] == "2023-04-10T17:50:00+00:00"
    assert batches[1][0]["supersedes_memory_id"] == "memory-1"


def test_locomo_live_baseline_maps_memory_uuid_to_dialog_id(monkeypatch) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
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
        if url.endswith("/api/memories/batch"):
            return FakeResponse({"items": [{"memory_id": "memory-uuid-1"}]})
        if url.endswith("/api/recall"):
            return FakeResponse(
                {
                    "memories": [
                        {
                            "memory_id": "memory-uuid-1",
                            "canonical_text": "Melanie: The race supported mental health.",
                            "score": 0.9,
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    case = EvaluationCase(
        case_id="locomo_conv-1_qa001",
        source="locomo",
        category="single_hop",
        sessions=[
            EvaluationSession(
                session_id="session_1",
                turns=[
                    EvaluationTurn(
                        role="assistant",
                        content="Melanie: The race supported mental health.",
                        metadata={"dia_id": "D1:2"},
                    )
                ],
            )
        ],
        query="What did the race support?",
        expected_answer="mental health",
        gold_memory_ids=["D1:2"],
    )

    result = build_baseline_with_config(
        mode="db_memory",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
        cleanup=False,
    ).run_case(case)

    assert result.error == ""
    assert result.retrieved_memory_ids == ["D1:2"]
    assert result.metadata["memory_source_ids"] == {"memory-uuid-1": "D1:2"}


def test_grouped_live_baseline_injects_context_once_for_multiple_questions(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []
    batch_sizes: list[int] = []

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
        if url.endswith("/api/memories/batch"):
            items = kwargs["json"]["items"]
            batch_sizes.append(len(items))
            return FakeResponse(
                {
                    "items": [
                        {"memory_id": f"memory-{index}"}
                        for index, _item in enumerate(items, start=1)
                    ]
                }
            )
        if url.endswith("/api/qa/answer"):
            return FakeResponse(
                {
                    "answer": "Bob [M1].",
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "total_tokens": 20,
                    "selected_memories": [
                        {
                            "memory_id": "memory-1",
                            "canonical_text": "The chairperson is Bob.",
                            "score": 0.9,
                        }
                    ],
                    "citation_map": {"memories": {"M1": {"memory_id": "memory-1"}}},
                }
            )
        raise AssertionError(f"unexpected request {method} {url}")

    monkeypatch.setattr("evaluation.baselines.httpx.request", fake_request)
    sessions = [
        EvaluationSession(
            session_id="context-1",
            turns=[
                EvaluationTurn(role="user", content="The chairperson was Alice."),
                EvaluationTurn(role="user", content="The chairperson is Bob."),
            ],
        )
    ]
    cases = [
        EvaluationCase(
            case_id=f"group-{index}",
            source="memoryagentbench",
            category="conflict_single_hop_6k",
            sessions=sessions,
            query=question,
            expected_answer="Bob",
            expected_behavior="answer_latest",
            metadata={"context_group_id": "factconsolidation_sh_6k"},
        )
        for index, question in enumerate(
            ["Who is the chairperson?", "Who holds the role now?"],
            start=1,
        )
    ]
    baseline = build_baseline_with_config(
        mode="db_qa",
        run_id="test",
        api_base_url="http://testserver",
        workspace="demo",
        cleanup=False,
    )

    results = baseline.run_group(cases)

    assert len(results) == 2
    assert batch_sizes == [2]
    assert calls.count(("POST", "http://testserver/api/memories/batch")) == 1
    assert calls.count(("POST", "http://testserver/api/qa/answer")) == 2
    assert all(result.generated_answer == "Bob [M1]." for result in results)


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
        if url.endswith("/api/memories/batch"):
            return FakeResponse({"items": [{"memory_id": "memory-1"}]})
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
        if url.endswith("/api/memories/batch") and method == "POST":
            return FakeResponse({"items": [{"memory_id": "memory-1"}]})
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
