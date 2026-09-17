"""Pick a CE/PE strike from the option chain: delta band + liquidity filters."""
from __future__ import annotations

import pandas as pd

import config


def _spread_pct(row) -> float:
    mid = (row["bid"] + row["ask"]) / 2
    if not mid:
        return float("inf")
    return (row["ask"] - row["bid"]) / mid * 100


def select_option(chain: pd.DataFrame, direction: str) -> dict | None:
    """direction: 'bullish' -> CE, 'bearish' -> PE. Returns the chosen row as a dict, or None."""
    opt_type = "CE" if direction == "bullish" else "PE"
    candidates = chain[chain["option_type"] == opt_type].copy()
    if candidates.empty:
        return None

    dmin, dmax = config.SELECT["delta_min"], config.SELECT["delta_max"]
    candidates["abs_delta"] = candidates["delta"].abs()
    candidates = candidates[(candidates["abs_delta"] >= dmin) & (candidates["abs_delta"] <= dmax)]
    candidates = candidates[candidates["oi"] >= config.SELECT["min_oi"]]
    candidates["spread_pct"] = candidates.apply(_spread_pct, axis=1)
    candidates = candidates[candidates["spread_pct"] <= config.SELECT["max_spread_pct"]]
    if candidates.empty:
        return None

    # Prefer delta closest to the midpoint of the band, then tightest spread.
    mid_delta = (dmin + dmax) / 2
    candidates["delta_dist"] = (candidates["abs_delta"] - mid_delta).abs()
    best = candidates.sort_values(["delta_dist", "spread_pct"]).iloc[0]
    return best.to_dict()
