"""Historical candle sources for backtesting: GrowwHistory (cached real data)
and DemoHistory (synthetic multi-day data), both exposing the same interface
the backtest engine needs: multi-day 5m spot/future candles."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import config
from providers import Provider

CACHE_DIR = Path("cache")
BARS_PER_DAY = 75  # 09:15-15:30 in 5-minute bars


def _trading_days(end: datetime, days: int) -> list[datetime]:
    out = []
    d = end
    while len(out) < days:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


class DemoHistory:
    """Deterministic synthetic multi-day 5m spot+future series."""

    def __init__(self, instrument: str, days: int = 60, seed: int = 7):
        self.instrument = instrument
        self.days = days
        self._rng = np.random.default_rng(seed)
        base = {"NIFTY": 24650.0, "BANKNIFTY": 51200.0}.get(instrument, 20000.0)
        self.spot_5m = self._generate(base)
        self.future_5m = self._derive_future(self.spot_5m)

    def _generate(self, base: float) -> pd.DataFrame:
        day_list = _trading_days(datetime.now().replace(hour=15, minute=30, second=0, microsecond=0), self.days)
        rows = []
        level = base
        for day in day_list:
            day_start = day.replace(hour=9, minute=15)
            level += self._rng.normal(0, base * 0.001)  # small overnight gap
            vol = base * 0.0005
            for i in range(BARS_PER_DAY):
                ts = day_start + timedelta(minutes=5 * i)
                step = self._rng.normal(0, vol)
                o = level
                c = level + step
                h = max(o, c) + abs(self._rng.normal(0, vol * 0.4))
                l = min(o, c) - abs(self._rng.normal(0, vol * 0.4))
                rows.append({"timestamp": ts, "open": o, "high": h, "low": l, "close": c, "volume": 0})
                level = c
        return pd.DataFrame(rows)

    def _derive_future(self, spot_5m: pd.DataFrame) -> pd.DataFrame:
        df = spot_5m.copy()
        basis = df["close"] * 0.0006
        for col in ("open", "high", "low", "close"):
            df[col] = df[col] + basis
        df["volume"] = np.abs(self._rng.normal(400_000, 120_000, len(df))).astype(int)
        price_change = df["close"].diff().fillna(0)
        oi_walk = 100_000 + np.cumsum(np.sign(price_change) * self._rng.integers(0, 400, len(df)))
        df["oi"] = np.clip(oi_walk, 10_000, None).astype(int)
        return df

    def resample_15m(self, df: pd.DataFrame) -> pd.DataFrame:
        return resample(df, "15min")


class GrowwHistory:
    """Cached wrapper over a GrowwProvider for repeated backtest runs."""

    def __init__(self, provider: Provider, instrument: str, days: int = 60):
        self.provider = provider
        self.instrument = instrument
        self.days = days
        CACHE_DIR.mkdir(exist_ok=True)
        self.spot_5m = self._cached_fetch("spot", provider.get_spot_candles)
        self.future_5m = self._cached_fetch("future", provider.get_future_candles)

    def _cache_key(self, kind: str) -> Path:
        key = hashlib.sha1(f"{self.instrument}-{kind}-{self.days}".encode()).hexdigest()[:16]
        return CACHE_DIR / f"{kind}_{self.instrument}_{self.days}_{key}.json"

    def _cached_fetch(self, kind: str, fetch_fn) -> pd.DataFrame:
        path = self._cache_key(kind)
        if path.exists():
            return pd.read_json(path, convert_dates=["timestamp"])
        lookback = self.days * BARS_PER_DAY
        df = fetch_fn(self.instrument, "5m", lookback)
        df.to_json(path, date_format="iso")
        return df

    def resample_15m(self, df: pd.DataFrame) -> pd.DataFrame:
        return resample(df, "15min")


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    indexed = df.set_index("timestamp")
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    if "oi" in indexed.columns:
        agg["oi"] = "last"
    out = indexed.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["open"])
    return out.reset_index()
