from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from evaluation.metrics.system_metrics import latency_summary


@dataclass(slots=True)
class OperationSample:
    operation: str
    latency_ms: float
    success: bool
    status_code: int | None = None
    error: str = ""


def run_api_performance_suite(
    *,
    api_base_url: str,
    workspace: str,
    agent: str | None,
    iterations: int,
    include_qa: bool,
    request: Callable[..., httpx.Response] | None = None,
) -> list[OperationSample]:
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    base_url = api_base_url.rstrip("/")
    if request is None:
        client = httpx.Client(trust_env=not _is_loopback_url(base_url))
        request = client.request
    else:
        client = None
    try:
        workspace_id, agent_id = _resolve_targets(
            request=request,
            base_url=base_url,
            workspace=workspace,
            agent=agent,
        )
        samples: list[OperationSample] = []
        for index in range(iterations):
            text = f"Performance probe {uuid4()} iteration {index}."
            created = _sample_request(
                samples,
                "write",
                lambda: request(
                    "POST",
                    f"{base_url}/api/memories",
                    timeout=60.0,
                    headers={
                        "X-Actor-Type": "system",
                        "X-Revision-Reason": "evaluation performance",
                    },
                    json={
                        "workspace_id": workspace_id,
                        "memory_type": "semantic",
                        "canonical_text": text,
                        "summary": "Evaluation performance probe",
                        "owner_agent_id": agent_id,
                        "evidence": [],
                    },
                ),
            )
            memory_id = _json_object(created).get("memory_id") if created is not None else None
            _sample_request(
                samples,
                "recall",
                lambda: request(
                    "POST",
                    f"{base_url}/api/recall",
                    timeout=60.0,
                    json={
                        "workspace_id": workspace_id,
                        "agent_id": agent_id,
                        "query_text": text,
                        "retrieval_mode": "hybrid",
                        "limit": 5,
                    },
                ),
            )
            _sample_request(
                samples,
                "context",
                lambda: request(
                    "POST",
                    f"{base_url}/api/recall/context-pack",
                    timeout=60.0,
                    json={
                        "workspace_id": workspace_id,
                        "agent_id": agent_id,
                        "query_text": text,
                        "retrieval_mode": "hybrid",
                        "limit": 5,
                        "max_tokens": 1000,
                    },
                ),
            )
            if include_qa:
                _sample_request(
                    samples,
                    "qa",
                    lambda: request(
                        "POST",
                        f"{base_url}/api/qa/answer",
                        timeout=120.0,
                        json={
                            "workspace_id": workspace_id,
                            "agent_id": agent_id,
                            "query_text": text,
                            "retrieval_mode": "hybrid",
                            "limit": 5,
                            "max_answer_tokens": 100,
                        },
                    ),
                )
            if memory_id:
                _sample_request(
                    samples,
                    "update",
                    lambda: request(
                        "PATCH",
                        f"{base_url}/api/memories/{memory_id}",
                        timeout=60.0,
                        params={"workspace_id": workspace_id},
                        headers={
                            "X-Actor-Type": "system",
                            "X-Revision-Reason": "evaluation performance update",
                        },
                        json={"summary": "Updated evaluation performance probe"},
                    ),
                )
                _sample_request(
                    samples,
                    "delete",
                    lambda: request(
                        "DELETE",
                        f"{base_url}/api/memories/{memory_id}",
                        timeout=60.0,
                        params={"workspace_id": workspace_id},
                        headers={
                            "X-Actor-Type": "system",
                            "X-Revision-Reason": "evaluation performance cleanup",
                        },
                    ),
                )
        return samples
    finally:
        if client is not None:
            client.close()


def write_performance_outputs(
    *,
    output_csv: Path,
    samples: list[OperationSample],
) -> tuple[Path, Path]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["operation", "latency_ms", "success", "status_code", "error"],
        )
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    "operation": sample.operation,
                    "latency_ms": f"{sample.latency_ms:.3f}",
                    "success": str(sample.success).lower(),
                    "status_code": sample.status_code or "",
                    "error": sample.error,
                }
            )
    summary_path = output_csv.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summarize_operations(samples), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_csv, summary_path


def summarize_operations(samples: list[OperationSample]) -> dict[str, dict[str, float | int]]:
    operations = sorted({sample.operation for sample in samples})
    result: dict[str, dict[str, float | int]] = {}
    for operation in operations:
        rows = [sample for sample in samples if sample.operation == operation]
        successful = [sample.latency_ms for sample in rows if sample.success]
        errors = sum(1 for sample in rows if not sample.success)
        result[operation] = {
            "samples": len(rows),
            "successes": len(successful),
            "errors": errors,
            **latency_summary(successful, error_count=errors),
        }
    return result


def _sample_request(
    samples: list[OperationSample],
    operation: str,
    call: Callable[[], httpx.Response],
) -> httpx.Response | None:
    started = time.perf_counter()
    try:
        response = call()
        latency_ms = (time.perf_counter() - started) * 1000
        success = response.status_code < 400
        samples.append(
            OperationSample(
                operation=operation,
                latency_ms=latency_ms,
                success=success,
                status_code=response.status_code,
                error="" if success else response.text[:500],
            )
        )
        return response if success else None
    except Exception as exc:
        samples.append(
            OperationSample(
                operation=operation,
                latency_ms=(time.perf_counter() - started) * 1000,
                success=False,
                error=str(exc),
            )
        )
        return None


def _resolve_targets(
    *,
    request: Callable[..., httpx.Response],
    base_url: str,
    workspace: str,
    agent: str | None,
) -> tuple[str, str | None]:
    params = {"workspace": workspace}
    if agent:
        params["agent"] = agent
    response = request("GET", f"{base_url}/api/health/detail", params=params, timeout=30.0)
    response.raise_for_status()
    payload = _json_object(response)
    workspace_data = payload.get("workspace")
    if not isinstance(workspace_data, dict) or not workspace_data.get("found"):
        raise ValueError(f"workspace {workspace!r} was not found")
    agent_data = payload.get("agent")
    agent_id = (
        str(agent_data["agent_id"])
        if agent and isinstance(agent_data, dict) and agent_data.get("found")
        else None
    )
    if agent and agent_id is None:
        raise ValueError(f"agent {agent!r} was not found")
    return str(workspace_data["workspace_id"]), agent_id


def _json_object(response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _is_loopback_url(value: str) -> bool:
    return (urlparse(value).hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}
