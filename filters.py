"""Market/event filters: expiry day, VIX band, event days, bid-ask spread."""
from __future__ import annotations

from datetime import date, datetime

import config


def is_expiry_day(expiry: str, today: date | None = None) -> bool:
    today = today or datetime.now().date()
    try:
        expiry_date = datetime.strptime(expiry, "%d%b%y").date()
    except ValueError:
        return False
    return expiry_date == today


def vix_in_band(vix: float) -> bool:
    lo, hi = config.FILTERS["vix_band"]
    return lo <= vix <= hi


def is_event_day(today: date | None = None) -> bool:
    today = today or datetime.now().date()
    return today.strftime("%Y-%m-%d") in config.FILTERS["event_days"]


def spread_ok(bid: float, ask: float) -> bool:
    mid = (bid + ask) / 2
    if not mid:
        return False
    spread_pct = (ask - bid) / mid * 100
    return spread_pct <= config.FILTERS["max_bid_ask_spread_pct"]


def market_ok(expiry: str, vix: float, today: date | None = None) -> tuple[bool, str]:
    """Aggregate gate. Returns (allowed, reason-if-blocked)."""
    if config.FILTERS["avoid_expiry_day"] and is_expiry_day(expiry, today):
        return False, "expiry day"
    if not vix_in_band(vix):
        return False, f"VIX {vix:.1f} outside band {config.FILTERS['vix_band']}"
    if is_event_day(today):
        return False, "event day"
    return True, ""
