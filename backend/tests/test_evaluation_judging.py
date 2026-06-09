import csv
import json
from pathlib import Path

from evaluation.cases import EvaluationCase
from evaluation.judging import judge_answer, judge_results_csv


class FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"pass": false, "score": 0.1, '
                            '"reason": "The answer is ultimately uncertain."}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }


def test_judge_answer_rejects_uncertain_semantic_answer() -> None:
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return FakeResponse()

    case = EvaluationCase(
        case_id="case-1",
        source="longmemeval",
        category="temporal_reasoning",
        sessions=[],
        query="Which vehicle was first?",
        expected_answer="bike",
    )

    result = judge_answer(
        case=case,
        generated_answer="The bike was mentioned, but I cannot determine which was first.",
        api_key="test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        provider="deepseek",
        request=fake_request,
    )

    assert result["judge_pass"] == "false"
    assert result["judge_score"] == "0.100000"
    assert result["judge_cost"] == "0.00014000"
    assert captured["method"] == "POST"


def test_judge_results_loads_only_requested_cases(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "case-1",
                        "category": "qa",
                        "query": "Question?",
                        "expected_answer": "Answer",
                    }
                ),
                '{"case_id": "unused", "large_unsupported_field": true}',
            ]
        ),
        encoding="utf-8",
    )
    input_csv = tmp_path / "results.csv"
    with input_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "generated_answer"],
        )
        writer.writeheader()
        writer.writerow({"case_id": "case-1", "generated_answer": "Answer"})

    output_csv = tmp_path / "judged.csv"
    judge_results_csv(
        input_csv=input_csv,
        dataset=dataset,
        output_csv=output_csv,
        api_key="test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        request=lambda *args, **kwargs: FakeResponse(),
    )

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["case_id"] == "case-1"
    assert row["judge_pass"] == "false"


def test_judge_results_retries_and_resumes_checkpoint(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        "\n".join(
            json.dumps(
                {
                    "case_id": f"case-{index}",
                    "category": "qa",
                    "query": "Question?",
                    "expected_answer": "Answer",
                }
            )
            for index in range(1, 3)
        ),
        encoding="utf-8",
    )
    input_csv = tmp_path / "results.csv"
    with input_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "generated_answer"])
        writer.writeheader()
        writer.writerows(
            [
                {"case_id": "case-1", "generated_answer": "Answer"},
                {"case_id": "case-2", "generated_answer": "Answer"},
            ]
        )

    calls = 0

    class TruncatedResponse(FakeResponse):
        def json(self) -> dict:
            return {
                "choices": [{"message": {"content": '{"pass": false, "reason": "cut'}}],
                "usage": {},
            }

    def flaky_request(*args, **kwargs):
        nonlocal calls
        calls += 1
        return TruncatedResponse() if calls == 1 else FakeResponse()

    output_csv = tmp_path / "judged.csv"
    judge_results_csv(
        input_csv=input_csv,
        dataset=dataset,
        output_csv=output_csv,
        api_key="test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        request=flaky_request,
    )
    assert calls == 3

    judge_results_csv(
        input_csv=input_csv,
        dataset=dataset,
        output_csv=output_csv,
        api_key="test",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        request=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("completed rows should be skipped")
        ),
    )
