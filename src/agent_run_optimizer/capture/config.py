"""Configuration for what data is captured and how costs are estimated."""
from __future__ import annotations

from pydantic import BaseModel, Field

_DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # model_id -> (input_usd_per_1k_tokens, output_usd_per_1k_tokens)
    "claude-opus-4-7": (0.015, 0.075),
    "claude-sonnet-4-6": (0.003, 0.015),
    "claude-haiku-4-5-20251001": (0.00025, 0.00125),
}


class RunCaptureConfig(BaseModel):
    store_messages: bool = True
    store_tool_results: bool = True
    cost_per_1k_tokens: dict[str, tuple[float, float]] = Field(
        default_factory=lambda: dict(_DEFAULT_PRICING)
    )

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """Return estimated cost in USD, or None if model is not in the pricing table."""
        pricing = self.cost_per_1k_tokens.get(model)
        if pricing is None:
            return None
        i_cost, o_cost = pricing
        return round((input_tokens / 1000) * i_cost + (output_tokens / 1000) * o_cost, 8)