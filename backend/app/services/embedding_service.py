from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

from ..models.embedding import EmbeddingGenerateRequest, EmbeddingGenerateResponse

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


class EmbeddingProvider(Protocol):
    def embed(self, payload: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        ...


@dataclass(slots=True)
class EmbeddingService:
    provider: EmbeddingProvider

    def embed(self, payload: EmbeddingGenerateRequest) -> EmbeddingGenerateResponse:
        return self.provider.embed(payload)


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
