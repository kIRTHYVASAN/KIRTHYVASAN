"""Strategy registry: name -> generate(context) -> Signal."""
from __future__ import annotations

from analysis.signal import trend_vwap as _trend_vwap
from strategies import oi_buildup, orb, vwap_pullback
from strategies.common import Signal


def _trend_vwap_generate(context: dict) -> Signal:
    result = _trend_vwap(
        context["spot_15m"], context["spot_5m"], context["future_5m"], context.get("pcr")
    )
    reason = f"score {result['score']}, checks={result['checks']}"
    return Signal(result["direction"], "trend_vwap", result["score"], reason, result["swing"])


REGISTRY = {
    "trend_vwap": _trend_vwap_generate,
    "orb": orb.generate,
    "vwap_pullback": vwap_pullback.generate,
    "oi_buildup": oi_buildup.generate,
}


def generate(strategy_name: str, context: dict) -> Signal:
    if strategy_name not in REGISTRY:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    return REGISTRY[strategy_name](context)
