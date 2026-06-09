from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
import psycopg
from dotenv import load_dotenv

from evaluation.cases import EvaluationCase, EvaluationTurn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

SUPPORTED_MODES = {
    "db_extraction_qa",
    "no_memory",
    "recency_only",
    "naive_vector_rag",
    "summary_memory",
    "db_memory",
    "db_extraction",
    "db_qa",
    "vector_qa",
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
        generate_answer: bool,
        cleanup: bool,
        isolate: bool,
    ) -> None:
        self.mode = mode
        self.run_id = run_id
        self.api_base_url = api_base_url.rstrip("/")
        self.workspace = workspace or os.getenv("MEMORYBASE_WORKSPACE")
        self.agent = agent or os.getenv("MEMORYBASE_AGENT")
        self.backfill_embeddings = backfill_embeddings
        self.use_extraction = use_extraction
        self.generate_answer = generate_answer
        self.cleanup = cleanup
        self.isolate = isolate


class LocalMemoryBaseline:
    def __init__(self, *, mode: str, run_id: str) -> None:
        self._mode = mode
        self._run_id = run_id

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        started = time.perf_counter()
        memory_entries = _local_case_memory_entries(case)
        if self._mode == "recency_only":
            selected_entries = list(reversed(memory_entries))[:3]
        else:
            selected_entries = [
                (memory_id, _summarize_memory(memory)) for memory_id, memory in memory_entries[:8]
            ]
        selected = [memory for _memory_id, memory in selected_entries]
        generated_answer = "\n".join(selected)
        return EvaluationResult(
            case_id=case.case_id,
            source=case.source,
            category=case.category,
            query=case.query,
            expected_answer=case.expected_answer,
            generated_answer=generated_answer,
            retrieved_memory_ids=[memory_id for memory_id, _memory in selected_entries],
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
    cleanup: bool = True,
    isolate: bool = False,
) -> BaselineRunner:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode {mode!r}; expected one of {sorted(SUPPORTED_MODES)}")
    if mode == "no_memory" or dry_run:
        return NoMemoryBaseline(mode=mode, run_id=run_id, dry_run=dry_run)
    if mode in {"recency_only", "summary_memory"}:
        return LocalMemoryBaseline(mode=mode, run_id=run_id)
    if mode in {
        "db_memory",
        "naive_vector_rag",
        "db_extraction",
        "db_qa",
        "vector_qa",
        "db_extraction_qa",
    }:
        return LiveMemoryBaseline(
            config=LiveMemoryBaselineConfig(
                mode=mode,
                run_id=run_id,
                api_base_url=api_base_url or "http://localhost:8000",
                workspace=workspace,
                agent=agent,
                backfill_embeddings=mode in {"naive_vector_rag", "vector_qa"},
                use_extraction=mode in {"db_extraction", "db_extraction_qa"},
                generate_answer=mode in {"db_qa", "vector_qa", "db_extraction_qa"},
                cleanup=cleanup,
                isolate=isolate,
            )
        )
    return UnsupportedBaseline(mode=mode, run_id=run_id)


class LiveMemoryBaseline:
    def __init__(self, *, config: LiveMemoryBaselineConfig) -> None:
        self._config = config
        self._client = (
            httpx.Client(timeout=120.0, trust_env=False)
            if _is_loopback_url(config.api_base_url)
            else None
        )

    def run_case(self, case: EvaluationCase) -> EvaluationResult:
        started = time.perf_counter()
        created_memory_ids: list[str] = []
        memory_source_ids: dict[str, str] = {}
        embedding_backfill: dict[str, Any] | None = None
        workspace_id: str | None = None
        isolated_workspace = False
        pending_memories: list[tuple[str, EvaluationTurn]] = []
        try:
            if self._config.isolate:
                workspace_id, agent_id = self._create_isolated_workspace(case)
                isolated_workspace = True
            else:
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
                    if not _is_memory_turn(case, turn):
                        continue
                    if _is_query_turn(turn.content, case.query):
                        continue
                    if _should_apply_forget_turn(case, turn):
                        created = self._create_memories(
                            workspace_id=workspace_id,
                            agent_id=agent_id,
                            entries=pending_memories,
                            case=case,
                        )
                        for memory_id, pending_turn in created:
                            source_id = _turn_source_id(pending_turn)
                            if source_id:
                                memory_source_ids[memory_id] = source_id
                        created_memory_ids.extend(memory_id for memory_id, _turn in created)
                        pending_memories.clear()
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
                        pending_memories.append((turn.content, turn))

            created = self._create_memories(
                workspace_id=workspace_id,
                agent_id=agent_id,
                entries=pending_memories,
                case=case,
            )
            for memory_id, pending_turn in created:
                created_memory_ids.append(memory_id)
                source_id = _turn_source_id(pending_turn)
                if source_id:
                    memory_source_ids[memory_id] = source_id

            if self._config.backfill_embeddings:
                embedding_backfill = self._backfill_embeddings(workspace_id)
            if self._config.generate_answer:
                answer = self._answer(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    query=case.query,
                )
                memories = [
                    item for item in answer.get("selected_memories", []) if isinstance(item, dict)
                ]
                generated_answer = str(answer.get("answer", ""))
                token_usage = _optional_int(answer.get("total_tokens"))
                response_metadata = {
                    "provider": answer.get("provider"),
                    "model": answer.get("model"),
                    "prompt_tokens": answer.get("prompt_tokens"),
                    "completion_tokens": answer.get("completion_tokens"),
                    "total_tokens": answer.get("total_tokens"),
                    "context_tokens": answer.get("token_count"),
                    "token_budget": answer.get("token_budget"),
                    "citation_map": answer.get("citation_map", {}),
                    "supporting_evidence": answer.get("supporting_evidence", []),
                }
            else:
                recall = self._recall(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    query=case.query,
                )
                memories = [item for item in recall.get("memories", []) if isinstance(item, dict)]
                generated_answer = "\n".join(
                    str(item.get("canonical_text", "")) for item in memories
                )
                token_usage = None
                response_metadata = {}
            return EvaluationResult(
                case_id=case.case_id,
                source=case.source,
                category=case.category,
                query=case.query,
                expected_answer=case.expected_answer,
                generated_answer=generated_answer,
                retrieved_memory_ids=[
                    memory_source_ids.get(
                        str(item.get("memory_id", "")),
                        str(item.get("memory_id", "")),
                    )
                    for item in memories
                ],
                retrieved_memory_texts=[str(item.get("canonical_text", "")) for item in memories],
                retrieved_scores=[_float(item.get("score")) for item in memories],
                latency_ms=(time.perf_counter() - started) * 1000,
                token_usage=token_usage,
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
                    "memory_source_ids": memory_source_ids,
                    "embedding_backfill": embedding_backfill,
                    "rank_reasons": [str(item.get("rank_reason", "")) for item in memories],
                    "vector_scores": [_float(item.get("vector_score")) for item in memories],
                    "answer_generation": self._config.generate_answer,
                    "cleanup_requested": self._config.cleanup,
                    "isolated_workspace": isolated_workspace,
                    **response_metadata,
                    "limitation": (
                        "Evaluation-created sessions and extraction source documents cannot "
                        "be deleted through the current public API."
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
        finally:
            if isolated_workspace and workspace_id and self._config.cleanup:
                try:
                    self._delete_isolated_workspace(workspace_id)
                except Exception:
                    pass
            elif self._config.cleanup and workspace_id and created_memory_ids:
                try:
                    self._delete_created_memories(workspace_id, created_memory_ids)
                except Exception:
                    # Cleanup must not replace the benchmark result or original failure.
                    pass

    def run_group(self, cases: list[EvaluationCase]) -> list[EvaluationResult]:
        if not cases:
            return []
        if not self._config.generate_answer or self._config.use_extraction:
            raise ValueError("grouped live evaluation currently requires direct-memory QA mode")
        if any(case.sessions != cases[0].sessions for case in cases[1:]):
            raise ValueError("grouped evaluation cases must share identical sessions")

        workspace_id: str | None = None
        created_memory_ids: list[str] = []
        results: list[EvaluationResult] = []
        pending_memories: list[tuple[str, EvaluationTurn]] = []
        try:
            if self._config.isolate:
                workspace_id, agent_id = self._create_isolated_workspace(cases[0])
            else:
                workspace_id, agent_id = self._resolve_workspace_and_agent()
            for session in cases[0].sessions:
                session_id = self._create_session(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    title=f"{self._config.run_id}:{cases[0].metadata.get('context_group_id')}",
                )
                for turn in session.turns:
                    self._observe_message(
                        session_id=session_id,
                        role=turn.role,
                        content=turn.content,
                        agent_id=agent_id,
                    )
                    if not _is_memory_turn(cases[0], turn):
                        continue
                    pending_memories.append((turn.content, turn))
            created_memory_ids.extend(
                memory_id
                for memory_id, _turn in self._create_memories(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    entries=pending_memories,
                    case=cases[0],
                )
            )

            for case in cases:
                started = time.perf_counter()
                try:
                    answer = self._answer(
                        workspace_id=workspace_id,
                        agent_id=agent_id,
                        query=case.query,
                    )
                    memories = [
                        item
                        for item in answer.get("selected_memories", [])
                        if isinstance(item, dict)
                    ]
                    results.append(
                        EvaluationResult(
                            case_id=case.case_id,
                            source=case.source,
                            category=case.category,
                            query=case.query,
                            expected_answer=case.expected_answer,
                            generated_answer=str(answer.get("answer", "")),
                            retrieved_memory_ids=[
                                str(item.get("memory_id", "")) for item in memories
                            ],
                            retrieved_memory_texts=[
                                str(item.get("canonical_text", "")) for item in memories
                            ],
                            retrieved_scores=[_float(item.get("score")) for item in memories],
                            latency_ms=(time.perf_counter() - started) * 1000,
                            token_usage=_optional_int(answer.get("total_tokens")),
                            mode=self._config.mode,
                            run_id=self._config.run_id,
                            metadata={
                                "injection_mode": "grouped_memory_api",
                                "write_mode": "direct_memory_create",
                                "retrieval_mode": "backend_hybrid_recall",
                                "workspace_id": workspace_id,
                                "agent_id": agent_id,
                                "created_memory_ids": created_memory_ids,
                                "answer_generation": True,
                                "provider": answer.get("provider"),
                                "model": answer.get("model"),
                                "prompt_tokens": answer.get("prompt_tokens"),
                                "completion_tokens": answer.get("completion_tokens"),
                                "total_tokens": answer.get("total_tokens"),
                                "context_tokens": answer.get("token_count"),
                                "token_budget": answer.get("token_budget"),
                                "citation_map": answer.get("citation_map", {}),
                                "supporting_evidence": answer.get(
                                    "supporting_evidence",
                                    [],
                                ),
                                "context_group_id": case.metadata.get("context_group_id"),
                            },
                        )
                    )
                except Exception as exc:
                    results.append(
                        EvaluationResult(
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
                            metadata={
                                "injection_mode": "grouped_memory_api",
                                "context_group_id": case.metadata.get("context_group_id"),
                            },
                        )
                    )
            return results
        finally:
            if self._config.isolate and workspace_id and self._config.cleanup:
                self._delete_isolated_workspace(workspace_id)
            elif self._config.cleanup and workspace_id and created_memory_ids:
                self._delete_created_memories(workspace_id, created_memory_ids)

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

    def _create_isolated_workspace(self, case: EvaluationCase) -> tuple[str, str]:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("isolated live evaluation requires DATABASE_URL")
        slug = _evaluation_slug(self._config.run_id, case.case_id)
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workspace (slug, name, description, scope_type)
                    VALUES (%s, %s, %s, 'project')
                    RETURNING workspace_id
                    """,
                    (
                        slug,
                        f"Evaluation {case.case_id}"[:120],
                        f"Isolated evaluation workspace for {self._config.run_id}",
                    ),
                )
                workspace_id = str(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO agent (workspace_id, name, agent_type, status)
                    VALUES (%s, %s, 'retriever', 'active')
                    RETURNING agent_id
                    """,
                    (workspace_id, "evaluation-agent"),
                )
                agent_id = str(cur.fetchone()[0])
            conn.commit()
        return workspace_id, agent_id

    def _delete_isolated_workspace(self, workspace_id: str) -> None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM workspace WHERE workspace_id = %s", (workspace_id,))
            conn.commit()

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

    def _create_memories(
        self,
        *,
        workspace_id: str,
        agent_id: str | None,
        entries: list[tuple[str, EvaluationTurn]],
        case: EvaluationCase,
    ) -> list[tuple[str, EvaluationTurn]]:
        created: list[tuple[str, EvaluationTurn]] = []
        supersession_ids: dict[str, str] = {}
        pending: list[tuple[str, EvaluationTurn, str | None, str | None]] = []
        pending_keys: set[str] = set()

        def flush() -> None:
            if not pending:
                return
            payload = {
                "items": [
                    {
                        "workspace_id": workspace_id,
                        "memory_type": _memory_type_for_case(case, content),
                        "canonical_text": content,
                        "summary": f"Evaluation case {case.case_id}",
                        "confidence": 0.7,
                        "importance": 3,
                        "access_level": "project",
                        "owner_agent_id": agent_id,
                        **({"valid_from": valid_from} if valid_from else {}),
                        **(
                            {"supersedes_memory_id": supersession_ids[supersession_key]}
                            if supersession_key and supersession_key in supersession_ids
                            else {}
                        ),
                        "evidence": [],
                    }
                    for content, _turn, valid_from, supersession_key in pending
                ]
            }
            headers = {
                "X-Actor-Type": "agent",
                "X-Revision-Reason": f"evaluation batch injection {self._config.run_id}",
            }
            if agent_id:
                headers["X-Actor-Id"] = agent_id
            response = self._request(
                "POST",
                "/api/memories/batch",
                json=payload,
                headers=headers,
            )
            items = response.get("items", [])
            if not isinstance(items, list) or len(items) != len(pending):
                raise RuntimeError("MemoryBase batch memory response size did not match request")
            for item, (_content, turn, _valid_from, supersession_key) in zip(
                items,
                pending,
                strict=True,
            ):
                if not isinstance(item, dict) or not item.get("memory_id"):
                    continue
                memory_id = str(item["memory_id"])
                created.append((memory_id, turn))
                if supersession_key:
                    supersession_ids[supersession_key] = memory_id
            pending.clear()
            pending_keys.clear()

        for content, turn in entries:
            supersession_key = _turn_supersession_key(turn)
            if supersession_key and supersession_key in pending_keys:
                flush()
            pending.append(
                (
                    content,
                    turn,
                    _turn_valid_from(turn),
                    supersession_key,
                )
            )
            if supersession_key:
                pending_keys.add(supersession_key)
            if len(pending) == 500:
                flush()
        flush()
        return created

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

    def _answer(self, *, workspace_id: str, agent_id: str | None, query: str) -> dict[str, Any]:
        payload = {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "query_text": query,
            "status": "active",
            "retrieval_mode": "vector" if self._config.backfill_embeddings else "hybrid",
            "limit": 10,
        }
        return self._request("POST", "/api/qa/answer", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            if self._client is not None:
                response = self._client.request(
                    method,
                    f"{self._config.api_base_url}{path}",
                    **kwargs,
                )
            else:
                response = httpx.request(
                    method,
                    f"{self._config.api_base_url}{path}",
                    timeout=120.0,
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


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _is_loopback_url(value: str) -> bool:
    return (urlparse(value).hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}


def _evaluation_slug(run_id: str, case_id: str) -> str:
    raw = f"{run_id}-{case_id}".lower()
    normalized = "".join(char if char.isalnum() else "-" for char in raw)
    return normalized.strip("-")[:55] + "-" + str(time.time_ns())[-8:]


def _local_case_memories(case: EvaluationCase) -> list[str]:
    return [memory for _memory_id, memory in _local_case_memory_entries(case)]


def _local_case_memory_entries(case: EvaluationCase) -> list[tuple[str, str]]:
    memories: list[tuple[str, str]] = []
    fallback_index = 0
    for session in case.sessions:
        for turn in session.turns:
            if not _is_memory_turn(case, turn):
                continue
            if _is_query_turn(turn.content, case.query):
                continue
            if _should_apply_forget_turn(case, turn):
                memories.clear()
                continue
            fallback_index += 1
            memory_id = _turn_source_id(turn) or f"local:{case.case_id}:{fallback_index}"
            memories.append((memory_id, turn.content))
    return memories


def _is_memory_turn(case: EvaluationCase, turn: EvaluationTurn) -> bool:
    if turn.role == "user":
        return True
    return case.source in {"locomo", "longmemeval"} and turn.role == "assistant"


def _should_apply_forget_turn(case: EvaluationCase, turn: EvaluationTurn) -> bool:
    return case.category == "deletion" and _is_forget_turn(turn.content)


def _turn_source_id(turn: EvaluationTurn) -> str:
    for key in ("dia_id", "longmemeval_session_id"):
        value = turn.metadata.get(key)
        if value is not None and str(value):
            return str(value)
    return ""


def _turn_supersession_key(turn: EvaluationTurn) -> str | None:
    value = turn.metadata.get("supersession_key")
    return str(value) if value else None


def _turn_valid_from(turn: EvaluationTurn) -> str | None:
    explicit = turn.metadata.get("valid_from")
    if explicit:
        return str(explicit)
    session_date = turn.metadata.get("session_date")
    if not session_date:
        return None
    value = str(session_date).strip()
    for date_format in (
        "%Y/%m/%d (%a) %H:%M",
        "%I:%M %p on %d %B, %Y",
    ):
        try:
            return datetime.strptime(value, date_format).replace(tzinfo=UTC).isoformat()
        except ValueError:
            continue
    return None


def _summarize_memory(memory: str) -> str:
    compact = " ".join(memory.strip().split())
    if len(compact) <= 120:
        return compact
    return compact[:117] + "..."
