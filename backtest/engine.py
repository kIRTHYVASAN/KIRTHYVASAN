"""Backtest engine.

Per backtest assumptions (see CLAUDE.md): signal on a closed 5m candle, entry
at the next option candle's open + Rs 0.10 slippage, ATM option of the
nearest weekly expiry, stop checked before target within a candle, gaps fill
at open, PCR is skipped. Option OHLC is synthesized from the spot/future OHLC
via Black-Scholes (no real historical option chain in demo mode); VIX/event
filters need a live data feed and are not modeled here — only the hard
config.RISK limits (trade count, daily loss stop, entry window, lot cap) are
enforced, exactly as they would be live.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config
import strategies
from analysis.optionpricing import bs_delta, bs_price
from backtest import costs
from backtest.history import DemoHistory, GrowwHistory
from data.chain import atm_strike
from paper.broker import DEFAULT_CAPITAL
from risk import engine as risk_engine
from risk import exits as risk_exits

IV = 0.16


def _next_weekly_expiry_t_years(ts: datetime) -> float:
    days_ahead = (3 - ts.weekday()) % 7  # Thursday
    expiry = ts.replace(hour=15, minute=30, second=0, microsecond=0) + timedelta(days=days_ahead)
    seconds = max((expiry - ts).total_seconds(), 300)
    return seconds / (365 * 24 * 3600)


def _option_ohlc(bar: pd.Series, strike: float, is_call: bool, t_years: float) -> tuple[float, float, float]:
    if is_call:
        high = bs_price(bar["high"], strike, True, IV, t_years)
        low = bs_price(bar["low"], strike, True, IV, t_years)
        close = bs_price(bar["close"], strike, True, IV, t_years)
    else:
        high = bs_price(bar["low"], strike, False, IV, t_years)
        low = bs_price(bar["high"], strike, False, IV, t_years)
        close = bs_price(bar["close"], strike, False, IV, t_years)
    return high, low, close


def run_backtest(instrument: str, strategy_name: str, days: int = 60, demo: bool = True,
                  provider=None, capital: float = DEFAULT_CAPITAL) -> dict:
    if demo or provider is None:
        history = DemoHistory(instrument, days=days)
    else:
        history = GrowwHistory(provider, instrument, days=days)

    spot_5m = history.spot_5m.reset_index(drop=True)
    future_5m = history.future_5m.reset_index(drop=True)
    spot_15m_full = history.resample_15m(spot_5m)
    lot_size = config.INSTRUMENTS[instrument]["lot_size"]

    dates = spot_5m["timestamp"].dt.date
    trades: list[dict] = []

    for day in sorted(dates.unique()):
        day_positions = np.where(dates == day)[0]
        if len(day_positions) < 60:  # need enough bars for a real session
            continue
        day_start, day_end = int(day_positions[0]), int(day_positions[-1])
        day_state = {"trades_today": 0, "daily_pnl_pct": 0.0, "open_lots": 0}

        idx = day_start
        while idx < day_end:
            now = spot_5m["timestamp"].iloc[idx]
            if idx < 100:  # warm up EMA(50)-on-15m etc. across prior days
                idx += 1
                continue

            allowed, _ = risk_engine.gate(day_state, now=now)
            if not allowed:
                idx += 1
                continue

            spot_5m_window = spot_5m.iloc[: idx + 1]
            future_5m_window = future_5m.iloc[: idx + 1]
            spot_15m_window = spot_15m_full[spot_15m_full["timestamp"] <= now]
            if len(spot_15m_window) < 3:
                idx += 1
                continue

            context = {
                "spot_15m": spot_15m_window,
                "spot_5m": spot_5m_window,
                "future_5m": future_5m_window,
                "now": now.to_pydatetime() if hasattr(now, "to_pydatetime") else now,
                "pcr": None,
            }
            signal = strategies.generate(strategy_name, context)

            entry_idx = idx + 1
            if signal.direction not in ("bullish", "bearish") or entry_idx > day_end:
                idx += 1
                continue

            entry_bar = spot_5m.iloc[entry_idx]
            if entry_bar["timestamp"].date() != day:
                idx += 1
                continue

            is_call = signal.direction == "bullish"
            entry_spot = float(entry_bar["open"])
            strike = atm_strike(entry_spot, instrument)
            t_years = _next_weekly_expiry_t_years(entry_bar["timestamp"])
            delta = bs_delta(entry_spot, strike, is_call, IV, t_years)
            raw_entry = bs_price(entry_spot, strike, is_call, IV, t_years)
            entry_price = costs.slippage_adjusted(raw_entry, is_buy=True)

            plan = risk_engine.build_plan(
                signal.direction, entry_spot, signal.swing,
                {"ask": entry_price, "delta": delta}, capital, lot_size,
            )
            if plan["qty"] <= 0:
                idx += 1
                continue

            position = {
                "entry": plan["entry"], "sl": plan["sl"], "original_sl": plan["sl"],
                "target": plan["target"], "entered_at": entry_bar["timestamp"], "partial_done": False,
            }
            qty_total = plan["qty"]
            remaining_qty = qty_total
            realized = 0.0
            exit_price = None
            exit_reason = None
            j = entry_idx

            while j <= day_end:
                bar = spot_5m.iloc[j]
                t_rem = _next_weekly_expiry_t_years(bar["timestamp"])
                opt_high, opt_low, opt_close = _option_ohlc(bar, strike, is_call, t_rem)

                if opt_low <= position["sl"]:
                    exit_price, exit_reason = position["sl"], "stop_loss"
                    realized += (exit_price - position["entry"]) * remaining_qty
                    remaining_qty = 0
                    break
                if opt_high >= position["target"]:
                    exit_price, exit_reason = position["target"], "target_hit"
                    realized += (exit_price - position["entry"]) * remaining_qty
                    remaining_qty = 0
                    break

                result = risk_exits.evaluate_exit(position, opt_close, bar["timestamp"])
                if result["action"] == "partial_exit":
                    partial_qty = int(remaining_qty * result["exit_fraction"])
                    if partial_qty > 0:
                        realized += (opt_close - position["entry"]) * partial_qty
                        remaining_qty -= partial_qty
                    position["sl"] = result["new_sl"]
                    position["partial_done"] = True
                elif result["action"] == "trail_sl":
                    position["sl"] = result["new_sl"]
                elif result["action"] in ("time_stop", "square_off"):
                    exit_price, exit_reason = opt_close, result["action"]
                    realized += (exit_price - position["entry"]) * remaining_qty
                    remaining_qty = 0
                    break

                if j == day_end and remaining_qty > 0:
                    exit_price, exit_reason = opt_close, "square_off"
                    realized += (exit_price - position["entry"]) * remaining_qty
                    remaining_qty = 0
                    break
                j += 1

            gross_pnl = realized
            cost = costs.round_trip_cost(position["entry"], exit_price or position["entry"], qty_total)
            net_pnl = gross_pnl - cost

            trades.append({
                "date": str(day), "strategy": strategy_name, "instrument": instrument,
                "direction": signal.direction, "strike": strike, "entry": position["entry"],
                "exit": exit_price, "qty": qty_total, "gross_pnl": round(gross_pnl, 2),
                "cost": cost, "net_pnl": round(net_pnl, 2), "reason": exit_reason,
            })
            day_state["trades_today"] += 1
            day_state["daily_pnl_pct"] += net_pnl / capital * 100
            idx = j + 1

    return {"trades": trades, "summary": summarize(trades)}


def summarize(trades: list[dict]) -> dict:
    if not trades:
        return {"trades": 0, "win_rate_pct": None, "expectancy": 0.0,
                "profit_factor": None, "total_pnl": 0.0, "max_drawdown": 0.0}

    df = pd.DataFrame(trades)
    equity = df["net_pnl"].cumsum()
    drawdown = equity - equity.cummax()
    wins = df.loc[df["net_pnl"] > 0, "net_pnl"]
    losses = df.loc[df["net_pnl"] <= 0, "net_pnl"]
    profit_factor = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else None

    return {
        "trades": len(df),
        "win_rate_pct": round(len(wins) / len(df) * 100, 1),
        "expectancy": round(df["net_pnl"].mean(), 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "total_pnl": round(df["net_pnl"].sum(), 2),
        "max_drawdown": round(drawdown.min(), 2),
    }
