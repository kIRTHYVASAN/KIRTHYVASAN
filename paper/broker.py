"""Paper trading broker: JSON position state + CSV fills log under logs/paper/.

No real orders are ever placed here — this only simulates fills for the
approved proposal so the strategies can be tracked before going live.
"""
from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime
from pathlib import Path

STATE_DIR = Path("logs/paper")
STATE_FILE = STATE_DIR / "state.json"
FILLS_FILE = STATE_DIR / "fills.csv"

DEFAULT_CAPITAL = 100_000.0


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_state() -> dict:
    return {
        "date": _today_str(),
        "capital": DEFAULT_CAPITAL,
        "positions": [],
        "closed": [],
        "trades_today": 0,
        "realized_pnl_today": 0.0,
    }


def load_state() -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        state = _default_state()
        save_state(state)
        return state
    state = json.loads(STATE_FILE.read_text())
    if state.get("date") != _today_str():
        state["date"] = _today_str()
        state["trades_today"] = 0
        state["realized_pnl_today"] = 0.0
        save_state(state)
    return state


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _log_fill(row: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not FILLS_FILE.exists()
    with FILLS_FILE.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def place_order(state: dict, symbol: str, direction: str, entry: float, sl: float,
                 target: float, qty: int, strategy: str) -> dict:
    now = datetime.now()
    position = {
        "id": str(uuid.uuid4())[:8],
        "symbol": symbol,
        "direction": direction,
        "strategy": strategy,
        "entry": entry,
        "sl": sl,
        "original_sl": sl,
        "target": target,
        "qty": qty,
        "remaining_qty": qty,
        "entered_at": now.isoformat(),
        "partial_done": False,
    }
    state["positions"].append(position)
    state["trades_today"] = state.get("trades_today", 0) + 1
    _log_fill({
        "time": now.isoformat(), "symbol": symbol, "side": "BUY",
        "qty": qty, "price": entry, "position_id": position["id"], "reason": "entry",
    })
    save_state(state)
    return position


def apply_exit(state: dict, position_id: str, exit_price: float, exit_qty: int,
                reason: str, new_sl: float | None = None) -> float:
    for pos in state["positions"]:
        if pos["id"] != position_id:
            continue
        realized = (exit_price - pos["entry"]) * exit_qty
        state["realized_pnl_today"] = state.get("realized_pnl_today", 0.0) + realized
        pos["remaining_qty"] -= exit_qty
        _log_fill({
            "time": datetime.now().isoformat(), "symbol": pos["symbol"], "side": "SELL",
            "qty": exit_qty, "price": exit_price, "position_id": position_id, "reason": reason,
        })
        if new_sl is not None:
            pos["sl"] = new_sl
        if reason == "partial_exit":
            pos["partial_done"] = True
        if pos["remaining_qty"] <= 0:
            pos["closed_at"] = datetime.now().isoformat()
            pos["exit_reason"] = reason
            state["closed"].append(pos)
            state["positions"] = [p for p in state["positions"] if p["id"] != position_id]
        save_state(state)
        return realized
    return 0.0


def get_positions(state: dict) -> list[dict]:
    return state.get("positions", [])


def pnl_summary(state: dict) -> dict:
    capital = state.get("capital", DEFAULT_CAPITAL)
    realized = state.get("realized_pnl_today", 0.0)
    closed = state.get("closed", [])
    wins = sum(1 for p in closed if p.get("exit_reason") in ("target_hit", "trail_sl", "partial_exit"))
    return {
        "capital": capital,
        "realized_pnl_today": round(realized, 2),
        "daily_pnl_pct": round((realized / capital * 100) if capital else 0.0, 3),
        "trades_today": state.get("trades_today", 0),
        "open_positions": len(state.get("positions", [])),
        "closed_trades": len(closed),
        "win_rate": round(wins / len(closed) * 100, 1) if closed else None,
    }
