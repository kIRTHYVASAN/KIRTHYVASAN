"""VWAP pullback: 15m trend, future touches+rejects VWAP, RSI side, 5m vs EMA20."""
from __future__ import annotations

import config
from analysis.indicators import ema, rsi, swing_high_low, vwap
from strategies.common import Signal

NAME = "vwap_pullback"


def _touched_and_rejected(future_5m, vwap_series, direction: str) -> bool:
    tol = config.VWAP_PULLBACK["touch_tolerance_pct"] / 100
    prev, last = future_5m.iloc[-2], future_5m.iloc[-1]
    v_prev, v_last = vwap_series.iloc[-2], vwap_series.iloc[-1]
    touched = prev["low"] <= v_prev * (1 + tol) and prev["high"] >= v_prev * (1 - tol)
    if direction == "bullish":
        return touched and last["close"] > v_last
    return touched and last["close"] < v_last


def generate(context: dict) -> Signal:
    spot_15m = context["spot_15m"]
    spot_5m = context["spot_5m"]
    future_5m = context["future_5m"]

    if len(future_5m) < 2:
        return Signal("no-trade", NAME, 0, "insufficient future data")

    trend_fast = ema(spot_15m["close"], config.SIGNAL["ema_fast"]).iloc[-1]
    trend_slow = ema(spot_15m["close"], config.SIGNAL["ema_slow"]).iloc[-1]
    direction = "bullish" if trend_fast > trend_slow else "bearish"

    v = vwap(future_5m)
    if not _touched_and_rejected(future_5m, v, direction):
        return Signal("no-trade", NAME, 0, "no VWAP touch+reject")

    r = rsi(spot_5m["close"], config.SIGNAL["rsi_period"]).iloc[-1]
    lo, hi = config.SIGNAL["rsi_bull_range"] if direction == "bullish" else config.SIGNAL["rsi_bear_range"]
    if not (lo <= r <= hi):
        return Signal("no-trade", NAME, 0, f"RSI {r:.1f} not in {direction} band")

    ema20 = ema(spot_5m["close"], config.SIGNAL["ema_fast"]).iloc[-1]
    close = spot_5m["close"].iloc[-1]
    price_ok = close > ema20 if direction == "bullish" else close < ema20
    if not price_ok:
        return Signal("no-trade", NAME, 0, "5m price not confirming EMA20 side")

    swing = swing_high_low(spot_5m, config.SIGNAL["swing_lookback"])
    return Signal(direction, NAME, 4, "VWAP pullback+reject with trend, RSI, EMA20 confirm", swing)
