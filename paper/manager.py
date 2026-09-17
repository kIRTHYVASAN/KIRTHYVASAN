"""Auto-manage open paper positions: fetch each position's current option
price and run it through risk/exits (partial/trail/time-stop/target/stop/
square-off), applying the result to paper state. This never places a live
order -- it only advances the paper broker's own state -- and it enforces
exactly the same exit rules a human approving trades would be expected to
follow.
"""
from __future__ import annotations

import re
from datetime import datetime

import config
from paper import broker as paper_broker
from risk import exits as risk_exits

_SYMBOL_RE = re.compile(r"^[A-Z]+-([A-Z]+)-(\d{2}[A-Za-z]{3}\d{2})-(\d+)-(CE|PE)$")


def _parse_symbol(symbol: str) -> tuple[str, str, float, str] | None:
    match = _SYMBOL_RE.match(symbol)
    if not match:
        return None
    instrument, expiry, strike, opt_type = match.groups()
    return instrument, expiry, float(strike), opt_type


def _current_option_price(provider, symbol: str) -> float | None:
    parsed = _parse_symbol(symbol)
    if not parsed:
        return None
    instrument, expiry, strike, opt_type = parsed
    if instrument not in config.INSTRUMENTS:
        return None
    chain = provider.get_option_chain(instrument, expiry)
    row = chain[(chain["strike"] == strike) & (chain["option_type"] == opt_type)]
    if row.empty:
        return None
    return float(row.iloc[0]["ltp"])


def refresh_positions(provider, state: dict, now: datetime | None = None) -> list[dict]:
    """Check every open position and apply any triggered exit.

    Returns a list of {symbol, action, price} for anything actioned this tick.
    """
    now = now or datetime.now()
    actions: list[dict] = []

    for pos in list(state.get("positions", [])):
        price = _current_option_price(provider, pos["symbol"])
        if price is None:
            continue

        position_for_eval = {
            "entry": pos["entry"],
            "sl": pos["sl"],
            "original_sl": pos["original_sl"],
            "target": pos["target"],
            "entered_at": datetime.fromisoformat(pos["entered_at"]),
            "partial_done": pos["partial_done"],
        }
        result = risk_exits.evaluate_exit(position_for_eval, price, now)
        action = result["action"]
        if action == "hold":
            continue

        if action == "partial_exit":
            exit_qty = int(pos["remaining_qty"] * result["exit_fraction"])
            if exit_qty > 0:
                paper_broker.apply_exit(state, pos["id"], price, exit_qty, action, result.get("new_sl"))
                actions.append({"symbol": pos["symbol"], "action": action, "price": price})
        elif action == "trail_sl":
            pos["sl"] = result["new_sl"]
            paper_broker.save_state(state)
            actions.append({"symbol": pos["symbol"], "action": action, "price": price})
        else:  # stop_loss, target_hit, time_stop, square_off -> full close
            paper_broker.apply_exit(state, pos["id"], price, pos["remaining_qty"], action)
            actions.append({"symbol": pos["symbol"], "action": action, "price": price})

    return actions
