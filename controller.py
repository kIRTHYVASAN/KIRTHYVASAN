"""scan(provider, strategy) -> proposal dict. Never places orders.

The proposal is the single object the dashboard shows the user for
APPROVE/REJECT; execution (even paper) only happens after that approval.
"""
from __future__ import annotations

from datetime import datetime

import config
import filters
import strategies
from analysis.selector import select_option
from data import chain, feed
from paper import broker as paper_broker
from risk import engine as risk_engine


def scan(provider, strategy_name: str, instrument: str = config.DEFAULT_INSTRUMENT) -> dict:
    now = datetime.now()
    spot_5m = feed.spot_candles(provider, instrument, "5m", lookback=150)
    spot_15m = feed.spot_candles(provider, instrument, "15m", lookback=80)
    future_5m = feed.future_candles(provider, instrument, "5m", lookback=150)

    expiry = chain.nearest_expiry(provider, instrument)
    option_chain = chain.option_chain(provider, instrument, expiry)
    pcr = chain.pcr_summary(option_chain)["pcr"]
    vix = feed.vix(provider)

    market_allowed, market_reason = filters.market_ok(expiry, vix, now.date())

    context = {
        "spot_15m": spot_15m, "spot_5m": spot_5m, "future_5m": future_5m,
        "now": now, "pcr": pcr,
    }
    signal = strategies.generate(strategy_name, context)

    proposal = {
        "timestamp": now.isoformat(),
        "instrument": instrument,
        "strategy": strategy_name,
        "direction": signal.direction,
        "score": signal.score,
        "reason": signal.reason,
        "market_ok": market_allowed,
        "market_reason": market_reason,
        "vix": round(vix, 2),
        "pcr": pcr,
        "expiry": expiry,
        "tradeable": False,
    }

    if not market_allowed or signal.direction == "no-trade":
        if not market_allowed:
            proposal["reason"] = market_reason
        return proposal

    option = select_option(option_chain, signal.direction)
    if option is None:
        proposal["reason"] = "no liquid option in delta band"
        return proposal

    lot_size = config.INSTRUMENTS[instrument]["lot_size"]
    paper_state = paper_broker.load_state()
    pnl = paper_broker.pnl_summary(paper_state)
    open_lots = sum(p["remaining_qty"] for p in paper_state["positions"]) // lot_size if lot_size else 0
    day_state = {
        "trades_today": paper_state.get("trades_today", 0),
        "daily_pnl_pct": pnl["daily_pnl_pct"],
        "open_lots": open_lots,
    }
    risk_allowed, risk_reason = risk_engine.gate(day_state, now)
    if not risk_allowed:
        proposal["reason"] = risk_reason
        return proposal

    spot_now = float(spot_5m["close"].iloc[-1])
    plan = risk_engine.build_plan(
        signal.direction, spot_now, signal.swing, option, paper_state["capital"], lot_size,
    )

    proposal.update({
        "option_symbol": option["groww_symbol"],
        "option_type": option["option_type"],
        "strike": option["strike"],
        "delta": option["delta"],
        **plan,
    })
    proposal["tradeable"] = plan["qty"] > 0
    if not proposal["tradeable"]:
        proposal["reason"] = "position size rounds to 0 lots at current risk %"
    return proposal
