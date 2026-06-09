from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx

from ..core.database import Database
from ..models.embedding import (
    ChunkEmbeddingRecord,
    EmbeddingBackfillRequest,
    EmbeddingBackfillResponse,
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    MemoryEmbeddingRecord,
)

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


class EmbeddingProvider(Protocol):
    def embed(self, payload: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        ...


class EmbeddingRepository(Protocol):
    def embed_memory(
        self,
        *,
        memory_id: UUID,
        provider: EmbeddingProvider,
        provider_name: str,
        model: str,
        dimension: int,
    ) -> MemoryEmbeddingRecord:
        ...

    def embed_chunk(
        self,
        *,
        chunk_id: UUID,
        provider: EmbeddingProvider,
        provider_name: str,
        model: str,
        dimension: int,
    ) -> ChunkEmbeddingRecord:
        ...

    def backfill(
        self,
        payload: EmbeddingBackfillRequest,
        provider: EmbeddingProvider,
    ) -> EmbeddingBackfillResponse:
        ...


@dataclass(slots=True)
class EmbeddingService:
    provider: EmbeddingProvider
    repository: EmbeddingRepository | None = None
    default_provider_name: str = "local"
    default_model: str = "hashing-v1"
    default_dimension: int = 128

    def embed(self, payload: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        return self.provider.embed(self._with_configured_defaults(payload))

    def embed_memory(
        self,
        *,
        memory_id: UUID,
        provider_name: str = "local",
        model: str = "hashing-v1",
        dimension: int = 128,
    ) -> MemoryEmbeddingRecord:
        if self.repository is None:
            raise RuntimeError("Embedding repository is not configured.")
        provider_name, model, dimension = self._resolve_embedding_options(
            provider_name=provider_name,
            model=model,
            dimension=dimension,
        )
        return self.repository.embed_memory(
            memory_id=memory_id,
            provider=self.provider,
            provider_name=provider_name,
            model=model,
            dimension=dimension,
        )

    def embed_chunk(
        self,
        *,
        chunk_id: UUID,
        provider_name: str = "local",
        model: str = "hashing-v1",
        dimension: int = 128,
    ) -> ChunkEmbeddingRecord:
        if self.repository is None:
            raise RuntimeError("Embedding repository is not configured.")
        provider_name, model, dimension = self._resolve_embedding_options(
            provider_name=provider_name,
            model=model,
            dimension=dimension,
        )
        return self.repository.embed_chunk(
            chunk_id=chunk_id,
            provider=self.provider,
            provider_name=provider_name,
            model=model,
            dimension=dimension,
        )

    def backfill(self, payload: EmbeddingBackfillRequest) -> EmbeddingBackfillResponse:
        if self.repository is None:
            raise RuntimeError("Embedding repository is not configured.")
        if payload.provider == "local" and payload.model == "hashing-v1":
            payload = payload.model_copy(
                update={
                    "provider": self.default_provider_name,
                    "model": self.default_model,
                    "dimension": (
                        self.default_dimension if payload.dimension == 128 else payload.dimension
                    ),
                }
            )
        return self.repository.backfill(payload, self.provider)

    def _with_configured_defaults(
        self,
        payload: EmbeddingGenerateRequest,
    ) -> EmbeddingGenerateRequest:
        if payload.provider == "local" and payload.model == "hashing-v1":
            return payload.model_copy(
                update={
                    "provider": self.default_provider_name,
                    "model": self.default_model,
                    "dimension": (
                        self.default_dimension if payload.dimension == 128 else payload.dimension
                    ),
                }
            )
        return payload

    def _resolve_embedding_options(
        self,
        *,
        provider_name: str,
        model: str,
        dimension: int,
    ) -> tuple[str, str, int]:
        if provider_name == "local" and model == "hashing-v1":
            resolved_dimension = self.default_dimension if dimension == 128 else dimension
            return self.default_provider_name, self.default_model, resolved_dimension
        return provider_name, model, dimension


class LocalHashingEmbeddingProvider:
    def embed(self, payload: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        vector = [0.0] * payload.dimension
        for token in _tokens(payload.text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % payload.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        normalized = _normalize(vector)
        return EmbeddingGenerateResponse(
            provider=payload.provider,
            model=payload.model,
            dimension=payload.dimension,
            embedding=normalized,
            text_hash=hashlib.sha256(payload.text.encode("utf-8")).hexdigest(),
        )


class SiliconFlowEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        timeout: float = 30.0,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 0.25,
    ) -> None:
        if not api_key:
            raise ValueError("SILICONFLOW_API_KEY is required for SiliconFlow embeddings.")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._retry_backoff_seconds = retry_backoff_seconds

    def embed(self, payload: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        request_body: dict[str, object] = {
            "model": payload.model,
            "input": payload.text,
            "encoding_format": "float",
        }
        if payload.dimension > 0:
            request_body["dimensions"] = payload.dimension

        response = self._post_with_retry(request_body)
        data = response.json()
        embedding = data.get("data", [{}])[0].get("embedding")
        if not isinstance(embedding, list):
            raise ValueError("SiliconFlow embedding response did not contain an embedding vector.")
        vector = [float(value) for value in embedding]
        return EmbeddingGenerateResponse(
            provider=payload.provider,
            model=payload.model,
            dimension=len(vector),
            embedding=vector,
            text_hash=hashlib.sha256(payload.text.encode("utf-8")).hexdigest(),
        )

    def _post_with_retry(self, request_body: dict[str, object]) -> httpx.Response:
        with httpx.Client(timeout=self._timeout) as client:
            for attempt in range(self._max_attempts):
                try:
                    response = client.post(
                        f"{self._base_url}/embeddings",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request_body,
                    )
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    if status_code != 429 and status_code < 500:
                        raise
                    last_error: httpx.HTTPError = exc
                except httpx.TransportError as exc:
                    last_error = exc

                if attempt + 1 == self._max_attempts:
                    raise last_error
                time.sleep(self._retry_backoff_seconds * (2**attempt))

        raise RuntimeError("Embedding request retry loop exited unexpectedly.")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class PostgresEmbeddingRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def embed_memory(
        self,
        *,
        memory_id: UUID,
        provider: EmbeddingProvider,
        provider_name: str,
        model: str,
        dimension: int,
    ) -> MemoryEmbeddingRecord:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                row = self._fetch_memory_text(cur, memory_id)
                embedding = provider.embed(
                    EmbeddingGenerateRequest(
                        text=str(row["canonical_text"]),
                        provider=provider_name,
                        model=model,
                        dimension=dimension,
                    )
                )
                record = self._upsert_memory_embedding(cur, row, embedding)
            conn.commit()
        return MemoryEmbeddingRecord(**record)

    def embed_chunk(
        self,
        *,
        chunk_id: UUID,
        provider: EmbeddingProvider,
        provider_name: str,
        model: str,
        dimension: int,
    ) -> ChunkEmbeddingRecord:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                row = self._fetch_chunk_text(cur, chunk_id)
                embedding = provider.embed(
                    EmbeddingGenerateRequest(
                        text=str(row["chunk_text"]),
                        provider=provider_name,
                        model=model,
                        dimension=dimension,
                    )
                )
                record = self._upsert_chunk_embedding(cur, row, embedding)
            conn.commit()
        return ChunkEmbeddingRecord(**record)

    def backfill(
        self,
        payload: EmbeddingBackfillRequest,
        provider: EmbeddingProvider,
    ) -> EmbeddingBackfillResponse:
        memory_count = 0
        chunk_count = 0
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                if payload.target in {"memories", "all"}:
                    cur.execute(
                        """
                        SELECT memory_id, workspace_id, canonical_text
                        FROM memory_item
                        WHERE workspace_id = %(workspace_id)s
                          AND status = 'active'
                        ORDER BY updated_at DESC
                        LIMIT %(limit)s
                        """,
                        {"workspace_id": payload.workspace_id, "limit": payload.limit},
                    )
                    for row in cur.fetchall():
                        embedding = provider.embed(
                            EmbeddingGenerateRequest(
                                text=str(row["canonical_text"]),
                                provider=payload.provider,
                                model=payload.model,
                                dimension=payload.dimension,
                            )
                        )
                        self._upsert_memory_embedding(cur, row, embedding)
                        memory_count += 1

                if payload.target in {"chunks", "all"}:
                    cur.execute(
                        """
                        SELECT
                            sc.chunk_id,
                            sc.doc_id,
                            sd.workspace_id,
                            sc.chunk_text
                        FROM source_chunk sc
                        JOIN source_document sd ON sd.doc_id = sc.doc_id
                        WHERE sd.workspace_id = %(workspace_id)s
                          AND sd.status = 'active'
                        ORDER BY sd.imported_at DESC, sc.chunk_no ASC
                        LIMIT %(limit)s
                        """,
                        {"workspace_id": payload.workspace_id, "limit": payload.limit},
                    )
                    for row in cur.fetchall():
                        embedding = provider.embed(
                            EmbeddingGenerateRequest(
                                text=str(row["chunk_text"]),
                                provider=payload.provider,
                                model=payload.model,
                                dimension=payload.dimension,
                            )
                        )
                        self._upsert_chunk_embedding(cur, row, embedding)
                        chunk_count += 1
            conn.commit()
        return EmbeddingBackfillResponse(
            workspace_id=payload.workspace_id,
            target=payload.target,
            memory_count=memory_count,
            chunk_count=chunk_count,
        )

    def _fetch_memory_text(self, cur, memory_id: UUID) -> dict[str, object]:
        cur.execute(
            """
            SELECT memory_id, workspace_id, canonical_text
            FROM memory_item
            WHERE memory_id = %(memory_id)s
              AND status = 'active'
            """,
            {"memory_id": memory_id},
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"active memory {memory_id} not found")
        return row

    def _fetch_chunk_text(self, cur, chunk_id: UUID) -> dict[str, object]:
        cur.execute(
            """
            SELECT
                sc.chunk_id,
                sc.doc_id,
                sd.workspace_id,
                sc.chunk_text
            FROM source_chunk sc
            JOIN source_document sd ON sd.doc_id = sc.doc_id
            WHERE sc.chunk_id = %(chunk_id)s
              AND sd.status = 'active'
            """,
            {"chunk_id": chunk_id},
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"active chunk {chunk_id} not found")
        return row

    def _upsert_memory_embedding(
        self,
        cur,
        row: dict[str, object],
        embedding: EmbeddingGenerateResponse,
    ) -> dict[str, object]:
        cur.execute(
            """
            INSERT INTO memory_embedding (
                memory_id,
                workspace_id,
                provider,
                model,
                dimension,
                embedding_json,
                embedding_text_hash
            )
            VALUES (
                %(memory_id)s,
                %(workspace_id)s,
                %(provider)s,
                %(model)s,
                %(dimension)s,
                %(embedding_json)s::jsonb,
                %(embedding_text_hash)s
            )
            ON CONFLICT (memory_id, provider, model, embedding_text_hash)
            DO UPDATE SET
                dimension = EXCLUDED.dimension,
                embedding_json = EXCLUDED.embedding_json
            RETURNING
                embedding_id,
                memory_id,
                workspace_id,
                provider,
                model,
                dimension,
                embedding_text_hash,
                created_at
            """,
            {
                "memory_id": row["memory_id"],
                "workspace_id": row["workspace_id"],
                "provider": embedding.provider,
                "model": embedding.model,
                "dimension": embedding.dimension,
                "embedding_json": json.dumps(embedding.embedding),
                "embedding_text_hash": embedding.text_hash,
            },
        )
        return cur.fetchone()

    def _upsert_chunk_embedding(
        self,
        cur,
        row: dict[str, object],
        embedding: EmbeddingGenerateResponse,
    ) -> dict[str, object]:
        cur.execute(
            """
            INSERT INTO source_chunk_embedding (
                chunk_id,
                doc_id,
                workspace_id,
                provider,
                model,
                dimension,
                embedding_json,
                embedding_text_hash
            )
            VALUES (
                %(chunk_id)s,
                %(doc_id)s,
                %(workspace_id)s,
                %(provider)s,
                %(model)s,
                %(dimension)s,
                %(embedding_json)s::jsonb,
                %(embedding_text_hash)s
            )
            ON CONFLICT (chunk_id, provider, model, embedding_text_hash)
            DO UPDATE SET
                dimension = EXCLUDED.dimension,
                embedding_json = EXCLUDED.embedding_json
            RETURNING
                embedding_id,
                chunk_id,
                doc_id,
                workspace_id,
                provider,
                model,
                dimension,
                embedding_text_hash,
                created_at
            """,
            {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "workspace_id": row["workspace_id"],
                "provider": embedding.provider,
                "model": embedding.model,
                "dimension": embedding.dimension,
                "embedding_json": json.dumps(embedding.embedding),
                "embedding_text_hash": embedding.text_hash,
            },
        )
        return cur.fetchone()
