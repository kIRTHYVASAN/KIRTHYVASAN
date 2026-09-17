"""Round-trip transaction cost model for backtesting (brokerage, STT, exchange
transaction charges, GST, SEBI fee, stamp duty). Slippage is applied to fill
price separately, not modeled as a cost here."""
from __future__ import annotations

import config


def round_trip_cost(entry_price: float, exit_price: float, qty: int) -> float:
    c = config.COSTS
    turnover_buy = entry_price * qty
    turnover_sell = exit_price * qty

    brokerage = c["brokerage_per_order"] * 2
    stt = turnover_sell * c["stt_sell_pct"] / 100
    exchange_txn = (turnover_buy + turnover_sell) * c["exchange_txn_pct"] / 100
    gst = (brokerage + exchange_txn) * c["gst_pct"] / 100
    sebi_fee = (turnover_buy + turnover_sell) * c["sebi_fee_pct"] / 100
    stamp_duty = turnover_buy * c["stamp_duty_buy_pct"] / 100

    return round(brokerage + stt + exchange_txn + gst + sebi_fee + stamp_duty, 2)


def slippage_adjusted(price: float, is_buy: bool) -> float:
    slip = config.COSTS["slippage_rs"]
    return round(price + slip if is_buy else price - slip, 2)
