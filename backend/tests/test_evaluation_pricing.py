from evaluation.pricing import estimate_model_cost


def test_estimate_deepseek_chat_cost_uses_cache_miss_snapshot() -> None:
    estimate = estimate_model_cost(
        provider="deepseek",
        model="deepseek-chat",
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
    )

    assert estimate["estimated_cost"] == 2.0
    assert estimate["cost_currency"] == "CNY"
    assert estimate["pricing_as_of"] == "2026-06-07"
    assert estimate["pricing_assumption"] == "cache_miss"


def test_estimate_model_cost_returns_empty_for_unknown_model() -> None:
    estimate = estimate_model_cost(
        provider="unknown",
        model="unknown",
        prompt_tokens=100,
        completion_tokens=20,
    )

    assert estimate["estimated_cost"] is None
