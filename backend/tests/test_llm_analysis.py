from __future__ import annotations

import json
from uuid import uuid4

import pytest
from app.services.llm_analysis import (
    LlmAnalysisDefaults,
    LlmAnalysisError,
    OpenAICompatibleAnalysisClient,
    SourceChunkForAnalysis,
    parse_llm_candidates,
    resolve_llm_options,
)


def test_parse_llm_candidates_clamps_fields_and_preserves_chunk_id() -> None:
    chunk_id = uuid4()
    drafts = parse_llm_candidates(
        json.dumps(
            {
                "candidates": [
                    {
                        "chunk_id": str(chunk_id),
                        "canonical_text": "MemoryBase should keep PostgreSQL as source of truth.",
                        "memory_type": "constraint",
                        "summary": "PostgreSQL source of truth",
                        "confidence": 1.2,
                        "importance": 9,
                    }
                ]
            }
        ),
        chunks=[
            SourceChunkForAnalysis(
                chunk_id=chunk_id,
                chunk_no=1,
                text="MemoryBase should keep PostgreSQL as source of truth.",
            )
        ],
        max_candidates=5,
    )

    assert len(drafts) == 1
    assert drafts[0].chunk_id == chunk_id
    assert drafts[0].memory_type == "constraint"
    assert drafts[0].confidence == 1
    assert drafts[0].importance == 5


def test_resolve_llm_options_requires_api_key() -> None:
    with pytest.raises(LlmAnalysisError, match="requires an API key"):
        resolve_llm_options(None, LlmAnalysisDefaults(api_key=""))


def test_openai_compatible_analysis_client_maps_chat_completion(monkeypatch) -> None:
    captured = {}
    chunk_id = uuid4()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "candidates": [
                                        {
                                            "chunk_id": str(chunk_id),
                                            "canonical_text": "Private notes must stay hidden.",
                                            "memory_type": "policy",
                                            "summary": "Private notes visibility",
                                            "confidence": 0.86,
                                            "importance": 4,
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }

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

    monkeypatch.setattr("app.services.llm_analysis.httpx.Client", FakeClient)

    client = OpenAICompatibleAnalysisClient()
    drafts = client.analyze(
        chunks=[
            SourceChunkForAnalysis(
                chunk_id=chunk_id,
                chunk_no=3,
                text="Private notes must stay hidden.",
            )
        ],
        max_candidates=2,
        options=resolve_llm_options(
            None,
            LlmAnalysisDefaults(
                api_key="test-key",
                base_url="https://api.example.com/v1/",
                model="analysis-model",
            ),
        ),
    )

    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "analysis-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert drafts[0].memory_type == "policy"
    assert drafts[0].confidence == 0.86
