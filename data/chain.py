"""Expiries, option chain, ATM strike, and PCR summary."""
from __future__ import annotations

import pandas as pd

import config
from providers import Provider


def expiries(provider: Provider, instrument: str) -> list[str]:
    return provider.get_expiries(instrument)


def nearest_expiry(provider: Provider, instrument: str) -> str:
    exp = expiries(provider, instrument)
    if not exp:
        raise RuntimeError(f"No expiries available for {instrument}")
    return exp[0]


def option_chain(provider: Provider, instrument: str, expiry: str | None = None) -> pd.DataFrame:
    expiry = expiry or nearest_expiry(provider, instrument)
    return provider.get_option_chain(instrument, expiry)


def atm_strike(spot: float, instrument: str) -> float:
    step = config.INSTRUMENTS[instrument]["strike_step"]
    return round(spot / step) * step


def pcr_summary(chain: pd.DataFrame) -> dict:
    ce_oi = chain.loc[chain["option_type"] == "CE", "oi"].sum()
    pe_oi = chain.loc[chain["option_type"] == "PE", "oi"].sum()
    pcr = (pe_oi / ce_oi) if ce_oi else float("nan")
    return {"ce_oi": int(ce_oi), "pe_oi": int(pe_oi), "pcr": round(pcr, 3) if ce_oi else None}
