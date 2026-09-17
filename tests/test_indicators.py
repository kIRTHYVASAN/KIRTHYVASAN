import numpy as np
import pandas as pd

from analysis.indicators import ema, rsi, swing_high_low, vwap


def _uptrend_df(n=60):
    close = np.linspace(100, 160, n)
    return pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1, "close": close,
        "volume": np.full(n, 1000),
    })


def test_ema_tracks_uptrend_below_price():
    df = _uptrend_df()
    fast = ema(df["close"], 20)
    assert fast.iloc[-1] < df["close"].iloc[-1]
    assert fast.iloc[-1] > fast.iloc[0]


def test_rsi_high_in_strong_uptrend():
    df = _uptrend_df()
    r = rsi(df["close"], 14)
    assert r.iloc[-1] > 70


def test_vwap_between_low_and_high_of_session():
    df = _uptrend_df()
    v = vwap(df)
    assert (v.iloc[10:] >= df["low"].min()).all()
    assert (v.iloc[10:] <= df["high"].max()).all()


def test_swing_high_low_matches_window_extremes():
    df = _uptrend_df()
    result = swing_high_low(df, window=10)
    tail = df.tail(10)
    assert result["swing_high"] == tail["high"].max()
    assert result["swing_low"] == tail["low"].min()
