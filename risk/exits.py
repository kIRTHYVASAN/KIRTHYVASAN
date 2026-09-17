"""Exit management: partial at 1R -> SL to breakeven, trail after 1.5R,
30-min time stop if the trade hasn't moved, and hard square-off.

position: {entry, sl, original_sl, target, qty, entered_at, partial_done}
`original_sl` anchors the R calculation so moving `sl` to breakeven after the
partial exit doesn't distort later R-multiple math.
"""
from __future__ import annotations

from datetime import datetime, time

import config


def _r_unit(position: dict) -> float:
    return position["entry"] - position.get("original_sl", position["sl"])


def _r_multiple(position: dict, price: float) -> float:
    r_unit = _r_unit(position)
    if r_unit <= 0:
        return 0.0
    return (price - position["entry"]) / r_unit


def evaluate_exit(position: dict, current_price: float, now: datetime) -> dict:
    cfg = config.EXITS
    square_off_t = time.fromisoformat(cfg["square_off_time"])
    if now.time() >= square_off_t:
        return {"action": "square_off", "exit_fraction": 1.0}

    if current_price <= position["sl"]:
        return {"action": "stop_loss", "exit_fraction": 1.0}

    if current_price >= position["target"]:
        return {"action": "target_hit", "exit_fraction": 1.0}

    r_mult = _r_multiple(position, current_price)
    elapsed_minutes = (now - position["entered_at"]).total_seconds() / 60

    if elapsed_minutes >= cfg["time_stop_minutes"] and r_mult < cfg["partial_at_r"]:
        return {"action": "time_stop", "exit_fraction": 1.0}

    if not position.get("partial_done") and r_mult >= cfg["partial_at_r"]:
        return {
            "action": "partial_exit",
            "exit_fraction": cfg["partial_fraction"],
            "new_sl": position["entry"],
        }

    if position.get("partial_done") and r_mult >= cfg["trail_after_r"]:
        r_unit = max(_r_unit(position), 0.01)
        trailing_sl = current_price - r_unit
        if trailing_sl > position["sl"]:
            return {"action": "trail_sl", "exit_fraction": 0.0, "new_sl": round(trailing_sl, 2)}

    return {"action": "hold", "exit_fraction": 0.0}
