from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from evaluation.cases import EvaluationCase

SUPPORTED_MODES = {
    "no_memory",
    "recency_only",
    "naive_vector_rag",
    "summary_memory",
    "db_memory",
    "db_extraction",
}


@dataclass(slots=True)
class EvaluationResult:
    case_id: str
    source: str
    category: str
    query: str
    expected_answer: str | None
    generated_answer: str
    retrieved_memory_ids: list[str] = field(default_factory=list)
    retrieved_memory_texts: list[str] = field(default_factory=list)
    retrieved_scores: list[float] = field(default_factory=list)
    latency_ms: float = 0.0
    token_usage: int | None = None
    score: float = 0.0
    passed: bool = False
    error: str = ""
    mode: str = "no_memory"
    run_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaselineRunner(Protocol):
    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        ...


class NoMemoryBaseline:
    def __init__(self, *, mode: str, run_id: str, dry_run: bool = False) -> None:
        self._mode = mode
        self._run_id = run_id
        self._dry_run = dry_run

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        started = time.perf_counter()
        if self._dry_run:
            answer = "[dry-run] case validated; no model or memory system was called"
        elif case.expected_answer is None:
            answer = "I do not know."
        else:
            answer = ""
        return EvaluationResult(
            case_id=case.case_id,
            source=case.source,
            category=case.category,
            query=case.query,
            expected_answer=case.expected_answer,
            generated_answer=answer,
            latency_ms=(time.perf_counter() - started) * 1000,
            mode=self._mode,
            run_id=self._run_id,
            metadata={
                "injection_mode": "none",
                "limitation": "No MemoryBase backend was called by this baseline.",
                "dry_run": self._dry_run,
            },
        )


class UnsupportedBaseline:
    def __init__(self, *, mode: str, run_id: str) -> None:
        self._mode = mode
        self._run_id = run_id

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        return EvaluationResult(
            case_id=case.case_id,
            source=case.source,
            category=case.category,
            query=case.query,
            expected_answer=case.expected_answer,
            generated_answer="",
            mode=self._mode,
            run_id=self._run_id,
            error=(
                f"Mode {self._mode!r} is reserved but not implemented yet. "
                "Use --mode no_memory or --dry-run for the current framework."
            ),
            metadata={"injection_mode": "not_supported"},
        )


class LiveMemoryBaselineConfig:
    def __init__(
        self,
        *,
        mode: str,
        run_id: str,
        api_base_url: str,
        workspace: str | None,
        agent: str | None,
        backfill_embeddings: bool,
        use_extraction: bool,
    ) -> None:
        self.mode = mode
        self.run_id = run_id
        self.api_base_url = api_base_url.rstrip("/")
        self.workspace = workspace or os.getenv("MEMORYBASE_WORKSPACE")
        self.agent = agent or os.getenv("MEMORYBASE_AGENT")
        self.backfill_embeddings = backfill_embeddings
        self.use_extraction = use_extraction


class LocalMemoryBaseline:
    def __init__(self, *, mode: str, run_id: str) -> None:
        self._mode = mode
        self._run_id = run_id

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        started = time.perf_counter()
        memories = _local_case_memories(case)
        if self._mode == "recency_only":
            selected = list(reversed(memories))[:3]
        else:
            selected = [_summarize_memory(memory) for memory in memories[:8]]
        generated_answer = "\n".join(selected)
        return EvaluationResult(
            case_id=case.case_id,
            source=case.source,
            category=case.category,
            query=case.query,
            expected_answer=case.expected_answer,
            generated_answer=generated_answer,
            retrieved_memory_ids=[
                f"{self._mode}:{case.case_id}:{index}"
                for index, _memory in enumerate(selected, start=1)
            ],
            retrieved_memory_texts=selected,
            retrieved_scores=[1 / index for index, _memory in enumerate(selected, start=1)],
            latency_ms=(time.perf_counter() - started) * 1000,
            mode=self._mode,
            run_id=self._run_id,
            metadata={
                "injection_mode": "local_case_memory",
                "limitation": (
                    "Uses EvaluationCase sessions directly; does not call MemoryBase APIs."
                ),
            },
        )


def build_baseline(*, mode: str, run_id: str, dry_run: bool = False) -> BaselineRunner:
    return build_baseline_with_config(mode=mode, run_id=run_id, dry_run=dry_run)


def build_baseline_with_config(
    *,
    mode: str,
    run_id: str,
    dry_run: bool = False,
    api_base_url: str | None = None,
    workspace: str | None = None,
    agent: str | None = None,
) -> BaselineRunner:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode {mode!r}; expected one of {sorted(SUPPORTED_MODES)}")
    if mode == "no_memory" or dry_run:
        return NoMemoryBaseline(mode=mode, run_id=run_id, dry_run=dry_run)
    if mode in {"recency_only", "summary_memory"}:
        return LocalMemoryBaseline(mode=mode, run_id=run_id)
    if mode in {"db_memory", "naive_vector_rag", "db_extraction"}:
        return LiveMemoryBaseline(
            config=LiveMemoryBaselineConfig(
                mode=mode,
                run_id=run_id,
                api_base_url=api_base_url or "http://localhost:8000",
                workspace=workspace,
                agent=agent,
                backfill_embeddings=mode == "naive_vector_rag",
                use_extraction=mode == "db_extraction",
            )
        )
    return UnsupportedBaseline(mode=mode, run_id=run_id)


class LiveMemoryBaseline:
    def __init__(self, *, config: LiveMemoryBaselineConfig) -> None:
        self._config = config

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        started = time.perf_counter()
        created_memory_ids: list[str] = []
        embedding_backfill: dict[str, Any] | None = None
        try:
            workspace_id, agent_id = self._resolve_workspace_and_agent()
            for session in case.sessions:
                session_id = self._create_session(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    title=f"{self._config.run_id}:{case.case_id}:{session.session_id}",
                )
                for turn in session.turns:
                    self._observe_message(
                        session_id=session_id,
                        role=turn.role,
                        content=turn.content,
                        agent_id=agent_id,
                    )
                    if turn.role != "user":
                        continue
                    if _is_query_turn(turn.content, case.query):
                        continue
                    if _is_forget_turn(turn.content):
                        self._delete_created_memories(workspace_id, created_memory_ids)
                        created_memory_ids.clear()
                        continue
                    if self._config.use_extraction:
                        created_memory_ids.extend(
                            self._extract_and_approve_memory(
                                workspace_id=workspace_id,
                                content=turn.content,
                                case=case,
                            )
                        )
                    else:
                        created_memory_ids.append(
                            self._create_memory(
                                workspace_id=workspace_id,
                                agent_id=agent_id,
                                content=turn.content,
                                case=case,
                            )
                        )

            if self._config.backfill_embeddings:
                embedding_backfill = self._backfill_embeddings(workspace_id)
            recall = self._recall(
                workspace_id=workspace_id,
                agent_id=agent_id,
                query=case.query,
            )
            memories = [item for item in recall.get("memories", []) if isinstance(item, dict)]
            generated_answer = "\n".join(str(item.get("canonical_text", "")) for item in memories)
            return EvaluationResult(
                case_id=case.case_id,
                source=case.source,
                category=case.category,
                query=case.query,
                expected_answer=case.expected_answer,
                generated_answer=generated_answer,
                retrieved_memory_ids=[str(item.get("memory_id", "")) for item in memories],
                retrieved_memory_texts=[str(item.get("canonical_text", "")) for item in memories],
                retrieved_scores=[_float(item.get("score")) for item in memories],
                latency_ms=(time.perf_counter() - started) * 1000,
                mode=self._config.mode,
                run_id=self._config.run_id,
                metadata={
                    "injection_mode": "memory_api",
                    "write_mode": "extraction_candidates"
                    if self._config.use_extraction
                    else "direct_memory_create",
                    "retrieval_mode": (
                        "vector_backfilled"
                        if self._config.backfill_embeddings
                        else "backend_hybrid_recall"
                    ),
                    "workspace_id": workspace_id,
                    "agent_id": agent_id,
                    "created_memory_ids": created_memory_ids,
                    "embedding_backfill": embedding_backfill,
                    "rank_reasons": [str(item.get("rank_reason", "")) for item in memories],
                    "vector_scores": [_float(item.get("vector_score")) for item in memories],
                    "limitation": (
                        "Uses existing live APIs. Full agent answer generation is "
                        "not implemented yet."
                    ),
                },
            )
        except Exception as exc:
            return EvaluationResult(
                case_id=case.case_id,
                source=case.source,
                category=case.category,
                query=case.query,
                expected_answer=case.expected_answer,
                generated_answer="",
                latency_ms=(time.perf_counter() - started) * 1000,
                mode=self._config.mode,
                run_id=self._config.run_id,
                error=str(exc),
                metadata={"injection_mode": "memory_api"},
            )

    def _resolve_workspace_and_agent(self) -> tuple[str, str | None]:
        if not self._config.workspace:
            raise ValueError(
                f"{self._config.mode} mode requires --workspace or MEMORYBASE_WORKSPACE."
            )
        params = {"workspace": self._config.workspace}
        if self._config.agent:
            params["agent"] = self._config.agent
        payload = self._request("GET", "/api/health/detail", params=params)
        workspace = _checked_target(payload, "workspace")
        agent = _checked_target(payload, "agent") if self._config.agent else None
        return str(workspace["workspace_id"]), str(agent["agent_id"]) if agent else None

    def _create_session(
        self,
        *,
        workspace_id: str,
        agent_id: str | None,
        title: str,
    ) -> str:
        payload = {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "title": title[:200],
            "channel": "cli",
        }
        response = self._request("POST", "/api/sessions", json=payload)
        return str(response["session_id"])

    def _observe_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        agent_id: str | None,
    ) -> None:
        sender_type = "agent" if role == "assistant" else "user" if role == "user" else "system"
        payload = {
            "session_id": session_id,
            "sender_type": sender_type,
            "sender_id": agent_id if sender_type == "agent" else None,
            "role": role,
            "content": content,
        }
        self._request("POST", "/api/observe", json=payload)

    def _create_memory(
        self,
        *,
        workspace_id: str,
        agent_id: str | None,
        content: str,
        case: EvaluationCase,
    ) -> str:
        payload = {
            "workspace_id": workspace_id,
            "memory_type": _memory_type_for_case(case, content),
            "canonical_text": content,
            "summary": f"Evaluation case {case.case_id}",
            "confidence": 0.7,
            "importance": 3,
            "access_level": "project",
            "owner_agent_id": agent_id,
            "evidence": [],
        }
        headers = {
            "X-Actor-Type": "agent",
            "X-Revision-Reason": f"evaluation injection {self._config.run_id}",
        }
        if agent_id:
            headers["X-Actor-Id"] = agent_id
        response = self._request("POST", "/api/memories", json=payload, headers=headers)
        return str(response["memory_id"])

    def _extract_and_approve_memory(
        self,
        *,
        workspace_id: str,
        content: str,
        case: EvaluationCase,
    ) -> list[str]:
        source = self._request(
            "POST",
            "/api/sources",
            json={
                "workspace_id": workspace_id,
                "title": f"Evaluation extraction {self._config.run_id} {case.case_id}"[:240],
                "doc_type": "note",
                "raw_text": content,
                "source_path": (
                    f"eval://{self._config.run_id}/{case.case_id}/{abs(hash(content))}"
                ),
            },
        )
        detail = self._request(
            "GET",
            f"/api/sources/{source['doc_id']}",
            params={"workspace_id": workspace_id},
        )
        chunk_ids = [
            str(chunk["chunk_id"])
            for chunk in detail.get("chunks", [])
            if isinstance(chunk, dict) and chunk.get("chunk_id")
        ]
        if not chunk_ids:
            return []
        extraction = self._request(
            "POST",
            "/api/memory-extraction/from-chunks",
            json={
                "workspace_id": workspace_id,
                "chunk_ids": chunk_ids,
                "max_candidates": 3,
            },
        )
        approved_ids: list[str] = []
        for candidate in extraction.get("candidates", []):
            if not isinstance(candidate, dict) or not candidate.get("memory_id"):
                continue
            approved = self._request(
                "POST",
                f"/api/memory-candidates/{candidate['memory_id']}/approve",
                params={"workspace_id": workspace_id},
            )
            memory = approved.get("memory", {})
            if isinstance(memory, dict) and memory.get("memory_id"):
                approved_ids.append(str(memory["memory_id"]))
        return approved_ids

    def _delete_created_memories(self, workspace_id: str, memory_ids: list[str]) -> None:
        for memory_id in list(memory_ids):
            self._request(
                "DELETE",
                f"/api/memories/{memory_id}",
                params={"workspace_id": workspace_id},
                headers={
                    "X-Actor-Type": "system",
                    "X-Revision-Reason": f"evaluation forgetting {self._config.run_id}",
                },
            )

    def _backfill_embeddings(self, workspace_id: str) -> dict[str, Any]:
        payload = {
            "workspace_id": workspace_id,
            "target": "all",
            "provider": "local",
            "model": "hashing-v1",
            "dimension": 128,
            "limit": 500,
        }
        return self._request("POST", "/api/embeddings/backfill", json=payload)

    def _recall(self, *, workspace_id: str, agent_id: str | None, query: str) -> dict[str, Any]:
        payload = {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "query_text": query,
            "status": "active",
            "retrieval_mode": "vector" if self._config.backfill_embeddings else "hybrid",
            "limit": 10,
        }
        return self._request("POST", "/api/recall", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self._config.api_base_url}{path}",
                timeout=10.0,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise RuntimeError(f"MemoryBase API request failed: {exc}") from exc
        if response.status_code >= 400:
            raise RuntimeError(f"MemoryBase API {response.status_code}: {response.text}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("MemoryBase API returned a non-object response.")
        return payload


def _checked_target(payload: dict[str, Any], key: str) -> dict[str, Any]:
    target = payload.get(key)
    if not isinstance(target, dict) or not target.get("found", False):
        reason = target.get("error") if isinstance(target, dict) else f"{key} not found"
        raise ValueError(str(reason))
    return target


def _is_query_turn(content: str, query: str) -> bool:
    return content.strip() == query.strip()


def _is_forget_turn(content: str) -> bool:
    lowered = content.lower()
    return any(term in lowered for term in ("忘记", "删除", "forget", "delete", "remove"))


def _memory_type_for_case(case: EvaluationCase, content: str) -> str:
    if case.category == "preference_following" or "以后" in content:
        return "preference"
    if case.category in {"temporal_update", "single_fact", "long_context_retention"}:
        return "semantic"
    if "风险" in content:
        return "risk"
    if "任务" in content:
        return "task"
    return "episodic"


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _local_case_memories(case: EvaluationCase) -> list[str]:
    memories: list[str] = []
    for session in case.sessions:
        for turn in session.turns:
            if turn.role != "user":
                continue
            if _is_query_turn(turn.content, case.query):
                continue
            if _is_forget_turn(turn.content):
                memories.clear()
                continue
            memories.append(turn.content)
    return memories


def _summarize_memory(memory: str) -> str:
    compact = " ".join(memory.strip().split())
    if len(compact) <= 120:
        return compact
    return compact[:117] + "..."
