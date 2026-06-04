from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from ..models.qa import AnswerRequest, AnswerResponse
from ..models.recall import RecallRequest
from .context_pack_service import format_context_pack
from .recall_service import RecallService


@dataclass(frozen=True, slots=True)
class ChatCompletionRequest:
    system_prompt: str
    user_prompt: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True, slots=True)
class ChatCompletionResponse:
    content: str
    provider: str
    model: str


class ChatProvider(Protocol):
    provider_name: str
    model: str

    def complete(self, payload: ChatCompletionRequest) -> ChatCompletionResponse:
        ...


class OpenAICompatibleChatProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError(f"{provider_name} API key is required for answer generation.")
        if not model:
            raise ValueError(f"{provider_name} chat model is required for answer generation.")
        self.provider_name = provider_name
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def complete(self, payload: ChatCompletionRequest) -> ChatCompletionResponse:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": payload.system_prompt},
                        {"role": "user", "content": payload.user_prompt},
                    ],
                    "temperature": payload.temperature,
                    "max_tokens": payload.max_tokens,
                },
            )
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError(f"{self.provider_name} response did not contain message content.")
        return ChatCompletionResponse(
            content=content.strip(),
            provider=self.provider_name,
            model=self.model,
        )


@dataclass(slots=True)
class AnswerService:
    recall_service: RecallService
    chat_provider: ChatProvider
    default_temperature: float = 0.2
    default_max_tokens: int = 800

    def answer(self, payload: AnswerRequest) -> AnswerResponse:
        recall_payload = RecallRequest(
            workspace_id=payload.workspace_id,
            agent_id=payload.agent_id,
            query_text=payload.query_text,
            memory_type=payload.memory_type,
            access_level=payload.access_level,
            status=payload.status,
            retrieval_mode=payload.retrieval_mode,
            limit=payload.limit,
        )
        recall = self.recall_service.execute(recall_payload)
        context = format_context_pack(recall, max_tokens=payload.max_context_tokens)
        completion = self.chat_provider.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(),
                user_prompt=_user_prompt(query_text=payload.query_text, context=context.markdown),
                temperature=(
                    self.default_temperature if payload.temperature is None else payload.temperature
                ),
                max_tokens=payload.max_answer_tokens or self.default_max_tokens,
            )
        )
        return AnswerResponse(
            answer=completion.content,
            provider=completion.provider,
            model=completion.model,
            recall_id=recall.recall_id,
            result_count=recall.result_count,
            retrieval_info=recall.retrieval_info,
            citation_map=context.citation_map,
            token_count=context.token_count,
            token_budget=context.token_budget,
            selected_memories=context.selected_memories,
            supporting_evidence=context.supporting_evidence,
            created_at=recall.created_at,
        )


def _system_prompt() -> str:
    return (
        "You are MemoryBase's grounded answer generator. Answer in the user's language. "
        "Use only the supplied MemoryBase context as factual support. If the context does "
        "not contain enough evidence, say you do not know. Prefer concise answers. "
        "When using recalled memories or evidence, cite refs like [M1] or [E1]."
    )


def _user_prompt(*, query_text: str, context: str) -> str:
    return "Question:\n" f"{query_text}\n\n" "MemoryBase context:\n" f"{context}\n\n" "Answer:"
