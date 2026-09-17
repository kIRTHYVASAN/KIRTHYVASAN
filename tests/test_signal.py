import numpy as np
import pandas as pd

from analysis.signal import trend_vwap


def _trending_df(seed: int, direction: str = "up") -> pd.DataFrame:
    """A realistic uptrend: steady climb, a consolidation, then a breakout leg
    (mirrored for downtrends). Built to actually clear all 7 trend_vwap checks
    -- a pure monotonic ramp fails the RSI (overbought) and breakout (a bar's
    own high always exceeds its own close) checks."""
    seg1 = np.linspace(100, 112, 30)
    rng = np.random.default_rng(seed)
    seg2 = 112 + np.cumsum(rng.normal(0, 0.8, 25))
    seg3 = seg2[-1] + np.cumsum([1.0, 1.5, 2.0])
    close = np.concatenate([seg1, seg2, seg3])
    if direction == "down":
        close = 212 - close  # mirror to invert the trend, same move sizes
    volume = np.full(len(close), 1000.0)
    volume[-1] = 5000.0
    return pd.DataFrame({
        "open": close, "high": close + 0.3, "low": close - 0.3, "close": close, "volume": volume,
    })


def test_trend_vwap_detects_uptrend_breakout_as_bullish():
    spot_15m = _trending_df(0, "up")
    spot_5m = _trending_df(0, "up")
    future_5m = _trending_df(0, "up")
    future_5m[["open", "high", "low", "close"]] += 0.5  # future trades above spot -> above VWAP

    result = trend_vwap(spot_15m, spot_5m, future_5m, pcr=1.3)
    assert result["direction"] == "bullish"
    assert result["score"] >= 6


def test_trend_vwap_detects_downtrend_breakdown_as_bearish():
    spot_15m = _trending_df(0, "down")
    spot_5m = _trending_df(0, "down")
    future_5m = _trending_df(0, "down")
    future_5m[["open", "high", "low", "close"]] -= 0.5

    result = trend_vwap(spot_15m, spot_5m, future_5m, pcr=0.7)
    assert result["direction"] == "bearish"
    assert result["score"] >= 6


def test_trend_vwap_returns_no_trade_when_choppy():
    n = 60
    rng = np.random.default_rng(1)
    close = 100 + rng.normal(0, 0.2, n)
    df = pd.DataFrame({
        "open": close, "high": close + 0.3, "low": close - 0.3, "close": close,
        "volume": np.full(n, 1000.0),
    })
    result = trend_vwap(df, df, df, pcr=1.0)
    assert result["direction"] == "no-trade"
