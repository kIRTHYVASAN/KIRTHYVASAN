"""Opening Range Breakout: first 15-min range breakout, entries until 11:30.

Range width must be 0.15-0.9% of the range low; confirmed by 15m trend and
future VWAP side.
"""
from __future__ import annotations

from datetime import datetime, time

import config
from analysis.indicators import ema, vwap
from strategies.common import NO_TRADE, Signal

NAME = "orb"


def _opening_range(spot_5m):
    cfg = config.ORB
    start = time.fromisoformat(cfg["range_start_time"])
    end = time.fromisoformat(cfg["range_end_time"])
    ts = spot_5m["timestamp"]
    mask = (ts.dt.time >= start) & (ts.dt.time <= end)
    return spot_5m[mask]


def generate(context: dict) -> Signal:
    spot_5m = context["spot_5m"]
    spot_15m = context["spot_15m"]
    future_5m = context["future_5m"]
    now: datetime = context["now"]
    cfg = config.ORB

    cutoff = time.fromisoformat(cfg["entry_cutoff_time"])
    if now.time() > cutoff:
        return Signal("no-trade", NAME, 0, "past ORB entry cutoff")

    orb_range = _opening_range(spot_5m)
    if orb_range.empty:
        return Signal("no-trade", NAME, 0, "no opening-range data yet")

    range_high = float(orb_range["high"].max())
    range_low = float(orb_range["low"].min())
    if range_low <= 0:
        return Signal("no-trade", NAME, 0, "invalid range")

    range_pct = (range_high - range_low) / range_low * 100
    if not (cfg["min_range_pct"] <= range_pct <= cfg["max_range_pct"]):
        return Signal("no-trade", NAME, 0, f"range width {range_pct:.2f}% out of bounds")

    last_close = float(spot_5m["close"].iloc[-1])
    trend_fast = ema(spot_15m["close"], config.SIGNAL["ema_fast"]).iloc[-1]
    trend_slow = ema(spot_15m["close"], config.SIGNAL["ema_slow"]).iloc[-1]
    future_vwap = vwap(future_5m).iloc[-1]
    future_close = float(future_5m["close"].iloc[-1])

    swing = {"swing_high": range_high, "swing_low": range_low}

    if last_close > range_high and trend_fast > trend_slow and future_close > future_vwap:
        return Signal("bullish", NAME, 3, "ORB breakout above range, trend+VWAP confirm", swing)
    if last_close < range_low and trend_fast < trend_slow and future_close < future_vwap:
        return Signal("bearish", NAME, 3, "ORB breakdown below range, trend+VWAP confirm", swing)
    return Signal("no-trade", NAME, 0, "no confirmed breakout", swing)
