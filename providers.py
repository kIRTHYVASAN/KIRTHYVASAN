"""Data providers: GrowwProvider (live) and DemoProvider (synthetic), same interface.

controller/strategies/backtest code must only depend on this interface, never
on growwapi or Groww-specific fields, so the engine stays broker-agnostic.
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config
from analysis.optionpricing import bs_delta


class Provider(ABC):
    @abstractmethod
    def get_spot_candles(self, instrument: str, interval: str, lookback: int) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_future_candles(self, instrument: str, interval: str, lookback: int) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        ...

    @abstractmethod
    def get_expiries(self, instrument: str) -> list[str]:
        ...

    @abstractmethod
    def get_option_chain(self, instrument: str, expiry: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_near_month_future_symbol(self, instrument: str) -> str:
        ...

    @abstractmethod
    def get_vix(self) -> float:
        ...


class DemoProvider(Provider):
    """Synthetic, deterministic (seeded) market data for offline dev, tests and demo mode."""

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)
        self._spot_base = {"NIFTY": 24650.0, "BANKNIFTY": 51200.0}

    def _walk(self, base: float, n: int, vol: float) -> np.ndarray:
        steps = self._np_rng.normal(0, vol, n)
        return base + np.cumsum(steps)

    def _candles(self, instrument: str, interval: str, lookback: int, vol_mult: float = 1.0) -> pd.DataFrame:
        base = self._spot_base.get(instrument, 20000.0)
        minutes = {"5m": 5, "15m": 15, "1d": 375}[interval]
        vol = base * 0.0006 * vol_mult
        closes = self._walk(base, lookback, vol)
        now = datetime.now().replace(second=0, microsecond=0)
        rows = []
        for i, c in enumerate(closes):
            ts = now - timedelta(minutes=minutes * (lookback - i))
            o = c + self._np_rng.normal(0, vol * 0.3)
            h = max(o, c) + abs(self._np_rng.normal(0, vol * 0.4))
            l = min(o, c) - abs(self._np_rng.normal(0, vol * 0.4))
            v = int(abs(self._np_rng.normal(500000, 150000)))
            rows.append({"timestamp": ts, "open": o, "high": h, "low": l, "close": c, "volume": v})
        return pd.DataFrame(rows)

    def get_spot_candles(self, instrument: str, interval: str, lookback: int) -> pd.DataFrame:
        df = self._candles(instrument, interval, lookback)
        df["volume"] = 0  # index has no real volume, per Groww facts
        return df

    def get_future_candles(self, instrument: str, interval: str, lookback: int) -> pd.DataFrame:
        df = self._candles(instrument, interval, lookback, vol_mult=1.05)
        price_change = df["close"].diff().fillna(0)
        oi_walk = 100_000 + np.cumsum(np.sign(price_change) * self._np_rng.integers(0, 500, len(df)))
        df["oi"] = oi_walk.clip(lower=10_000).astype(int)
        return df

    def get_ltp(self, symbol: str) -> float:
        for name, base in self._spot_base.items():
            if name in symbol:
                return base + self._np_rng.normal(0, base * 0.001)
        return 100.0

    def get_expiries(self, instrument: str) -> list[str]:
        today = datetime.now()
        days_ahead = (1 - today.weekday()) % 7  # next Tuesday-ish weekly expiry
        days_ahead = days_ahead or 7
        expiry = today + timedelta(days=days_ahead)
        return [expiry.strftime("%d%b%y")]

    def get_near_month_future_symbol(self, instrument: str) -> str:
        cfg = config.INSTRUMENTS[instrument]
        return f"{cfg['future_prefix']}-FUT"

    def get_vix(self) -> float:
        return float(self._np_rng.normal(14.0, 2.0))

    def get_option_chain(self, instrument: str, expiry: str) -> pd.DataFrame:
        cfg = config.INSTRUMENTS[instrument]
        spot = self._spot_base.get(instrument, 20000.0)
        step = cfg["strike_step"]
        atm = round(spot / step) * step
        rows = []
        for offset in range(-10, 11):
            strike = atm + offset * step
            for is_call in (True, False):
                delta = bs_delta(spot, strike, is_call)
                intrinsic = max(0.0, (spot - strike) if is_call else (strike - spot))
                time_value = max(2.0, 60 - abs(offset) * 5) + self._np_rng.normal(0, 2)
                ltp = max(0.5, intrinsic + time_value)
                spread = max(0.05, ltp * 0.01)
                oi = max(1000, int(200_000 * math.exp(-0.15 * abs(offset)) + self._np_rng.normal(0, 5000)))
                rows.append({
                    "strike": strike,
                    "option_type": "CE" if is_call else "PE",
                    "groww_symbol": f"{cfg['exchange']}-{instrument}-{expiry}-{int(strike)}-{'CE' if is_call else 'PE'}",
                    "ltp": round(ltp, 2),
                    "bid": round(ltp - spread / 2, 2),
                    "ask": round(ltp + spread / 2, 2),
                    "oi": oi,
                    "volume": int(oi * 0.3),
                    "delta": round(delta, 3),
                    "iv": round(16 + self._rng.uniform(-3, 3), 2),
                })
        return pd.DataFrame(rows)


class GrowwProvider(Provider):
    """Thin wrapper over growwapi. Imported lazily so DemoProvider/tests work
    without the growwapi package or credentials installed."""

    def __init__(self, session):
        self._session = session
        try:
            from growwapi import GrowwAPI  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "growwapi is required for live/paper-with-real-data mode; "
                "pip install growwapi or use --demo"
            ) from exc
        from growwapi import GrowwAPI

        self._api = GrowwAPI(session)

    def get_spot_candles(self, instrument: str, interval: str, lookback: int) -> pd.DataFrame:
        cfg = config.INSTRUMENTS[instrument]
        return self._fetch_candles(cfg["spot_symbol"], interval, lookback)

    def get_future_candles(self, instrument: str, interval: str, lookback: int) -> pd.DataFrame:
        symbol = self.get_near_month_future_symbol(instrument)
        return self._fetch_candles(symbol, interval, lookback)

    def _fetch_candles(self, symbol: str, interval: str, lookback: int) -> pd.DataFrame:
        raw = self._api.get_historical_candles(trading_symbol=symbol, interval=interval, limit=lookback)
        return pd.DataFrame(raw)

    def get_ltp(self, symbol: str) -> float:
        return float(self._api.get_ltp(trading_symbol=symbol))

    def get_expiries(self, instrument: str) -> list[str]:
        return list(self._api.get_expiry_dates(instrument))

    def get_option_chain(self, instrument: str, expiry: str) -> pd.DataFrame:
        raw = self._api.get_option_chain(instrument=instrument, expiry=expiry)
        return pd.DataFrame(raw)

    def get_near_month_future_symbol(self, instrument: str) -> str:
        cfg = config.INSTRUMENTS[instrument]
        futures = self._api.get_future_contracts(instrument=instrument)
        nearest = sorted(futures, key=lambda f: f["expiry"])[0]
        return nearest.get("trading_symbol", f"{cfg['future_prefix']}-FUT")

    def get_vix(self) -> float:
        return float(self._api.get_ltp(trading_symbol="NSE-INDIA VIX"))
