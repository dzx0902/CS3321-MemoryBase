from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPrice:
    currency: str
    input_per_million: float
    output_per_million: float
    pricing_as_of: str
    source: str
    assumption: str


DEEPSEEK_PRICING_SOURCE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing"

MODEL_PRICES: dict[tuple[str, str], ModelPrice] = {
    ("deepseek", "deepseek-chat"): ModelPrice(
        currency="CNY",
        input_per_million=1.0,
        output_per_million=2.0,
        pricing_as_of="2026-06-07",
        source=DEEPSEEK_PRICING_SOURCE,
        assumption="cache_miss",
    ),
    ("deepseek", "deepseek-v4-flash"): ModelPrice(
        currency="CNY",
        input_per_million=1.0,
        output_per_million=2.0,
        pricing_as_of="2026-06-07",
        source=DEEPSEEK_PRICING_SOURCE,
        assumption="cache_miss",
    ),
}


def estimate_model_cost(
    *,
    provider: object,
    model: object,
    prompt_tokens: object,
    completion_tokens: object,
) -> dict[str, object]:
    price = MODEL_PRICES.get((str(provider or "").lower(), str(model or "").lower()))
    input_tokens = _optional_int(prompt_tokens)
    output_tokens = _optional_int(completion_tokens)
    if price is None or input_tokens is None or output_tokens is None:
        return {
            "estimated_cost": None,
            "cost_currency": None,
            "pricing_as_of": None,
            "pricing_source": None,
            "pricing_assumption": None,
        }
    estimated_cost = (
        input_tokens * price.input_per_million + output_tokens * price.output_per_million
    ) / 1_000_000
    return {
        "estimated_cost": estimated_cost,
        "cost_currency": price.currency,
        "pricing_as_of": price.pricing_as_of,
        "pricing_source": price.source,
        "pricing_assumption": price.assumption,
    }


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
