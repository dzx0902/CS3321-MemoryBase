from __future__ import annotations

from uuid import uuid4

from app.api.deps import get_answer_service
from app.main import create_app
from app.models.qa import AnswerResponse
from app.services.llm_service import ChatCompletionRequest, OpenAICompatibleChatProvider
from fastapi.testclient import TestClient


def test_openai_compatible_chat_provider_maps_response(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "Answer with [M1]."}}]}

    class FakeClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def post(self, url, *, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.services.llm_service.httpx.Client", FakeClient)
    provider = OpenAICompatibleChatProvider(
        provider_name="deepseek",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1/",
        model="deepseek-chat",
    )

    result = provider.complete(
        ChatCompletionRequest(
            system_prompt="system",
            user_prompt="user",
            temperature=0.2,
            max_tokens=100,
        )
    )

    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "deepseek-chat"
    assert captured["json"]["messages"][0]["role"] == "system"
    assert result.content == "Answer with [M1]."
    assert result.provider == "deepseek"
    assert result.model == "deepseek-chat"


def test_qa_answer_api_returns_generated_answer() -> None:
    workspace_id = uuid4()

    class FakeAnswerService:
        def answer(self, payload):
            return AnswerResponse(
                answer="Rust [M1]",
                provider="deepseek",
                model="deepseek-chat",
                recall_id=None,
                result_count=1,
                citation_map={"memories": {}, "evidence": {}},
                token_count=42,
                token_budget=3000,
                selected_memories=[],
                supporting_evidence=[],
            )

    app = create_app()
    app.dependency_overrides[get_answer_service] = lambda: FakeAnswerService()
    client = TestClient(app)

    response = client.post(
        "/api/qa/answer",
        json={
            "workspace_id": str(workspace_id),
            "query_text": "我最喜欢的编程语言是什么？",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Rust [M1]"
    assert payload["provider"] == "deepseek"
    assert payload["model"] == "deepseek-chat"
