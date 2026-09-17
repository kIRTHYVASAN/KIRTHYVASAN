"""Spot/future candle and LTP access, and near-month future resolution.

Thin wrappers over a Provider so callers never touch broker-specific fields.
"""
from __future__ import annotations

import pandas as pd

from providers import Provider


def spot_candles(provider: Provider, instrument: str, interval: str = "5m", lookback: int = 100) -> pd.DataFrame:
    return provider.get_spot_candles(instrument, interval, lookback)


def future_candles(provider: Provider, instrument: str, interval: str = "5m", lookback: int = 100) -> pd.DataFrame:
    return provider.get_future_candles(instrument, interval, lookback)


def ltp(provider: Provider, symbol: str) -> float:
    return provider.get_ltp(symbol)


def near_month_future(provider: Provider, instrument: str) -> str:
    return provider.get_near_month_future_symbol(instrument)


def vix(provider: Provider) -> float:
    return provider.get_vix()
