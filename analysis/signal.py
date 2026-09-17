"""trend_vwap signal: 7 checks -> bullish / bearish / no-trade.

Checks: 15m trend, 5m trend, future VWAP side, volume surge, RSI band,
breakout-or-retest with room to S/R, and PCR bias. Both trend checks must
agree with the candidate direction (hard gate); the overall score across all
7 checks must clear config.SIGNAL["min_score"].
"""
from __future__ import annotations

import config
from analysis.indicators import ema, rsi, swing_high_low, vwap


def _trend(df, direction: str) -> bool:
    fast = ema(df["close"], config.SIGNAL["ema_fast"]).iloc[-1]
    slow = ema(df["close"], config.SIGNAL["ema_slow"]).iloc[-1]
    return fast > slow if direction == "bullish" else fast < slow


def _volume_surge(df) -> bool:
    lookback = config.SIGNAL["volume_lookback"]
    avg_vol = df["volume"].tail(lookback).mean()
    if not avg_vol:
        return False
    return df["volume"].iloc[-1] > config.SIGNAL["volume_multiplier"] * avg_vol


def _rsi_ok(df, direction: str) -> bool:
    r = rsi(df["close"], config.SIGNAL["rsi_period"]).iloc[-1]
    lo, hi = config.SIGNAL["rsi_bull_range"] if direction == "bullish" else config.SIGNAL["rsi_bear_range"]
    return lo <= r <= hi


def _vwap_side(future_df, direction: str) -> bool:
    v = vwap(future_df).iloc[-1]
    close = future_df["close"].iloc[-1]
    return close > v if direction == "bullish" else close < v


def _breakout_or_retest(spot_5m, direction: str) -> bool:
    # Prior swing (excluding the live bar) is what a breakout needs to clear.
    swing = swing_high_low(spot_5m.iloc[:-1], config.SIGNAL["swing_lookback"])
    close = spot_5m["close"].iloc[-1]
    fast = ema(spot_5m["close"], config.SIGNAL["ema_fast"]).iloc[-1]
    if direction == "bullish":
        breakout = close >= swing["swing_high"]
        retest_with_room = close <= fast * 1.002 and swing["swing_high"] > close
        return bool(breakout or retest_with_room)
    breakout = close <= swing["swing_low"]
    retest_with_room = close >= fast * 0.998 and swing["swing_low"] < close
    return bool(breakout or retest_with_room)


def _pcr_bias(pcr: float | None, direction: str) -> bool:
    if pcr is None:
        return False
    if direction == "bullish":
        return pcr >= 1.0
    return pcr <= 1.0


def _score_direction(spot_15m, spot_5m, future_5m, pcr, direction: str) -> tuple[int, dict]:
    checks = {
        "trend_15m": _trend(spot_15m, direction),
        "trend_5m": _trend(spot_5m, direction),
        "future_vwap": _vwap_side(future_5m, direction),
        "volume_surge": _volume_surge(future_5m),
        "rsi": _rsi_ok(spot_5m, direction),
        "breakout_or_retest": _breakout_or_retest(spot_5m, direction),
        "pcr": _pcr_bias(pcr, direction),
    }
    return sum(checks.values()), checks


def trend_vwap(spot_15m, spot_5m, future_5m, pcr: float | None = None) -> dict:
    min_score = config.SIGNAL["min_score"]
    swing = swing_high_low(spot_5m, config.SIGNAL["swing_lookback"])

    bull_score, bull_checks = _score_direction(spot_15m, spot_5m, future_5m, pcr, "bullish")
    bear_score, bear_checks = _score_direction(spot_15m, spot_5m, future_5m, pcr, "bearish")

    def _gate_ok(checks: dict) -> bool:
        return checks["trend_15m"] and checks["trend_5m"]

    candidate = None
    if _gate_ok(bull_checks) and bull_score >= min_score and bull_score >= bear_score:
        candidate = ("bullish", bull_score, bull_checks)
    elif _gate_ok(bear_checks) and bear_score >= min_score:
        candidate = ("bearish", bear_score, bear_checks)

    if candidate is None:
        return {"direction": "no-trade", "score": max(bull_score, bear_score), "checks": {}, "swing": swing}

    direction, score, checks = candidate
    return {"direction": direction, "score": score, "checks": checks, "swing": swing}
