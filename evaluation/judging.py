from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Callable

import httpx

from evaluation.cases import EvaluationCase, parse_case
from evaluation.pricing import estimate_model_cost

JUDGE_FIELDS = [
    "judge_pass",
    "judge_score",
    "judge_reason",
    "judge_provider",
    "judge_model",
    "judge_prompt_tokens",
    "judge_completion_tokens",
    "judge_cost",
    "judge_same_model",
]


def judge_results_csv(
    *,
    input_csv: Path,
    dataset: Path,
    output_csv: Path,
    api_key: str,
    base_url: str,
    model: str,
    provider: str = "deepseek",
    request: Callable[..., httpx.Response] | None = None,
) -> Path:
    with input_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    case_ids = {row.get("case_id", "") for row in rows}
    cases = _load_selected_cases(dataset, case_ids)
    requester = request or httpx.request
    for row in rows:
        case = cases.get(row.get("case_id", ""))
        if case is None:
            raise ValueError(f"case {row.get('case_id')!r} was not found in {dataset}")
        judgement = judge_answer(
            case=case,
            generated_answer=row.get("generated_answer", ""),
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider=provider,
            request=requester,
        )
        row.update(judgement)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields + [field for field in JUDGE_FIELDS if field not in fields],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_csv


def _load_selected_cases(
    dataset: Path,
    case_ids: set[str],
) -> dict[str, EvaluationCase]:
    cases: dict[str, EvaluationCase] = {}
    with dataset.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = json.loads(line)
            if raw.get("case_id") not in case_ids:
                continue
            case = parse_case(raw, path=dataset, line_no=line_no)
            cases[case.case_id] = case
            if len(cases) == len(case_ids):
                break
    return cases


def judge_answer(
    *,
    case: EvaluationCase,
    generated_answer: str,
    api_key: str,
    base_url: str,
    model: str,
    provider: str,
    request: Callable[..., httpx.Response],
) -> dict[str, str]:
    response = request(
        "POST",
        f"{base_url.rstrip('/')}/chat/completions",
        timeout=120.0,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0,
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict benchmark answer judge. Evaluate the overall "
                        "meaning, not substring overlap. A response that mentions the gold "
                        "answer but ultimately denies it or says it cannot determine the "
                        "answer is incorrect. For refuse_or_unknown cases, require an "
                        "explicit unanswerable or insufficient-information conclusion. "
                        "Return JSON with pass (boolean), score (0 to 1), and reason."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": case.query,
                            "gold_answer": case.expected_answer,
                            "accepted_answers": case.metadata.get("accepted_answers", []),
                            "expected_behavior": case.expected_behavior,
                            "forbidden_answers": case.forbidden_answers,
                            "candidate_answer": generated_answer,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        },
    )
    response.raise_for_status()
    payload = response.json()
    content = str(payload.get("choices", [{}])[0].get("message", {}).get("content", ""))
    parsed = _parse_judgement(content)
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    cost = estimate_model_cost(
        provider=provider,
        model=model,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )
    return {
        "judge_pass": str(bool(parsed["pass"])).lower(),
        "judge_score": f"{float(parsed['score']):.6f}",
        "judge_reason": str(parsed["reason"]),
        "judge_provider": provider,
        "judge_model": model,
        "judge_prompt_tokens": str(usage.get("prompt_tokens") or ""),
        "judge_completion_tokens": str(usage.get("completion_tokens") or ""),
        "judge_cost": (
            f"{float(cost['estimated_cost']):.8f}"
            if isinstance(cost["estimated_cost"], float)
            else ""
        ),
        "judge_same_model": "true",
    }


def _parse_judgement(content: str) -> dict[str, object]:
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match is None:
            raise ValueError(f"judge response was not JSON: {content[:200]}")
        raw = json.loads(match.group(0))
    if not isinstance(raw, dict) or not isinstance(raw.get("pass"), bool):
        raise ValueError(f"judge response has invalid schema: {raw!r}")
    score = raw.get("score", 1.0 if raw["pass"] else 0.0)
    return {
        "pass": raw["pass"],
        "score": min(max(float(score), 0.0), 1.0),
        "reason": str(raw.get("reason") or ""),
    }
