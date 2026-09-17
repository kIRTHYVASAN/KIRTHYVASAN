"""Minimal Black-Scholes pricing, used only to make synthetic/demo option data
plausible (delta-banded selection, backtest premium paths) — not for real
options Greeks or live pricing decisions."""
from __future__ import annotations

import math


def bs_delta(spot: float, strike: float, is_call: bool, iv: float = 0.16, t_years: float = 0.02) -> float:
    if spot <= 0 or strike <= 0 or t_years <= 0:
        return 0.5 if is_call else -0.5
    d1 = (math.log(spot / strike) + 0.5 * iv * iv * t_years) / (iv * math.sqrt(t_years))
    n_d1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
    return n_d1 if is_call else n_d1 - 1


def bs_price(spot: float, strike: float, is_call: bool, iv: float = 0.16, t_years: float = 0.02, r: float = 0.07) -> float:
    if t_years <= 0:
        return max(0.0, (spot - strike) if is_call else (strike - spot))
    if spot <= 0 or strike <= 0:
        return 0.0
    sqrt_t = math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / (iv * sqrt_t)
    d2 = d1 - iv * sqrt_t

    def _n(x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    if is_call:
        price = spot * _n(d1) - strike * math.exp(-r * t_years) * _n(d2)
    else:
        price = strike * math.exp(-r * t_years) * _n(-d2) - spot * _n(-d1)
    return max(0.05, price)
