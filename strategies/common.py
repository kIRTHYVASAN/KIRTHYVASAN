"""Shared strategy types and helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time


@dataclass
class Signal:
    direction: str  # "bullish" | "bearish" | "no-trade"
    strategy: str
    score: float
    reason: str
    swing: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


NO_TRADE = Signal(direction="no-trade", strategy="", score=0, reason="no setup")


def in_time_window(now: datetime, start: str, end: str) -> bool:
    start_t = time.fromisoformat(start)
    end_t = time.fromisoformat(end)
    return start_t <= now.time() <= end_t
