"""Risk gate (hard trading limits) and position sizing.

config.RISK values are hard limits: this module enforces them and must never
be bypassed by strategy/analysis code.
"""
from __future__ import annotations

from datetime import datetime, time

import config


def gate(state: dict, now: datetime | None = None) -> tuple[bool, str]:
    """state: {trades_today, daily_pnl_pct, open_lots}. Returns (allowed, reason)."""
    now = now or datetime.now()
    risk = config.RISK

    start_t = time.fromisoformat(risk["entry_window"][0])
    end_t = time.fromisoformat(risk["entry_window"][1])
    if not (start_t <= now.time() <= end_t):
        return False, f"outside entry window {risk['entry_window']}"

    if state.get("trades_today", 0) >= risk["max_trades_per_day"]:
        return False, f"max trades/day ({risk['max_trades_per_day']}) reached"

    if state.get("daily_pnl_pct", 0.0) <= -risk["max_daily_loss_pct"]:
        return False, f"daily loss stop ({risk['max_daily_loss_pct']}%) hit"

    if state.get("open_lots", 0) >= risk["max_lots"]:
        return False, f"max lots ({risk['max_lots']}) already open"

    return True, ""


def build_plan(direction: str, spot: float, swing: dict, option: dict, capital: float, lot_size: int) -> dict:
    """Entry at ask; SL from underlying swing distance x |delta|, clamped to
    10-30% of premium; 2R target; qty sized to 1% risk/trade, capped at max_lots."""
    risk = config.RISK
    entry = float(option["ask"])
    delta = abs(float(option.get("delta", 0.5))) or 0.5

    underlying_stop = swing["swing_low"] if direction == "bullish" else swing["swing_high"]
    underlying_distance = abs(spot - underlying_stop)
    raw_premium_distance = underlying_distance * delta

    lo_pct, hi_pct = risk["sl_pct_of_premium"]
    premium_distance = max(entry * lo_pct, min(entry * hi_pct, raw_premium_distance))
    if premium_distance <= 0:
        premium_distance = entry * lo_pct

    sl = round(entry - premium_distance, 2)
    target = round(entry + risk["reward_multiple"] * premium_distance, 2)

    risk_amount = capital * risk["risk_per_trade_pct"] / 100
    per_lot_risk = premium_distance * lot_size
    lots = int(risk_amount // per_lot_risk) if per_lot_risk > 0 else 0
    lots = max(0, min(lots, risk["max_lots"]))
    qty = lots * lot_size

    return {
        "entry": entry,
        "sl": sl,
        "target": target,
        "premium_risk_per_unit": round(premium_distance, 2),
        "lots": lots,
        "qty": qty,
        "risk_amount": round(risk_amount, 2),
        "reward_multiple": risk["reward_multiple"],
    }
