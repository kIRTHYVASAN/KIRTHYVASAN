"""Indicator building blocks: EMA, VWAP, RSI, swing highs/lows."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    """Rolling session VWAP from a candle DataFrame with high/low/close/volume."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum().replace(0, np.nan)
    return (typical * df["volume"]).cumsum() / cum_vol


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.finfo(float).eps)
    return 100 - (100 / (1 + rs))


def swing_high_low(df: pd.DataFrame, window: int = 20) -> dict:
    """Most recent swing high/low over the trailing `window` candles."""
    recent = df.tail(window)
    return {
        "swing_high": float(recent["high"].max()),
        "swing_low": float(recent["low"].min()),
    }
