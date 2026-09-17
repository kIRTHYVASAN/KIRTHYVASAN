"""Central configuration: instruments, signal/selection/risk/filter/exit params, costs.

Everything an analysis or strategy module needs to tune should live here, not
be hard-coded inline, so risk limits stay auditable in one place.
"""

INSTRUMENTS = {
    "NIFTY": {
        "symbol": "NIFTY",
        "exchange": "NSE",
        "segment": "FNO",
        "lot_size": 65,  # verify against Groww contract master before live use
        "tick_size": 0.05,
        "strike_step": 50,
        "future_prefix": "NSE-NIFTY",
        "spot_symbol": "NSE-NIFTY-INDEX",
    },
    "BANKNIFTY": {
        "symbol": "BANKNIFTY",
        "exchange": "NSE",
        "segment": "FNO",
        "lot_size": 15,
        "tick_size": 0.05,
        "strike_step": 100,
        "future_prefix": "NSE-BANKNIFTY",
        "spot_symbol": "NSE-BANKNIFTY-INDEX",
    },
}

DEFAULT_INSTRUMENT = "NIFTY"

# --- Signal generation (trend_vwap, shared indicator thresholds) ---
SIGNAL = {
    "ema_fast": 20,
    "ema_slow": 50,
    "rsi_period": 14,
    "rsi_bull_range": (55, 75),
    "rsi_bear_range": (25, 45),
    "volume_multiplier": 1.2,
    "volume_lookback": 20,
    "min_score": 6,  # out of 7 checks
    "swing_lookback": 20,
}

# --- Option selection ---
SELECT = {
    "delta_min": 0.40,
    "delta_max": 0.60,
    "min_oi": 50_000,
    "max_spread_pct": 2.0,  # (ask-bid)/mid * 100
}

# --- Risk engine hard limits (analysis code must never override these) ---
RISK = {
    "risk_per_trade_pct": 1.0,
    "max_trades_per_day": 3,
    "max_daily_loss_pct": 3.0,
    "entry_window": ("09:30", "14:45"),
    "square_off_time": "15:15",
    "max_lots": 5,
    "sl_pct_of_premium": (0.10, 0.30),
    "reward_multiple": 2.0,  # 2R target
}

# --- Market / event filters ---
FILTERS = {
    "avoid_expiry_day": True,
    "vix_band": (10.0, 25.0),
    "event_days": [],  # list of "YYYY-MM-DD" strings, e.g. budget/RBI days
    "max_bid_ask_spread_pct": 2.0,
}

# --- Exit management ---
EXITS = {
    "partial_at_r": 1.0,
    "partial_fraction": 0.5,
    "trail_after_r": 1.5,
    "time_stop_minutes": 30,
    "square_off_time": "15:15",
}

# --- Strategy-specific params ---
ORB = {
    "range_start_time": "09:15",
    "range_end_time": "09:30",
    "min_range_pct": 0.15,
    "max_range_pct": 0.90,
    "entry_cutoff_time": "11:30",
}

VWAP_PULLBACK = {
    "touch_tolerance_pct": 0.10,
}

OI_BUILDUP = {
    "lookback_bars": 3,
}

# --- Backtest cost model ---
COSTS = {
    "brokerage_per_order": 20.0,
    "stt_sell_pct": 0.0625,  # % of premium on sell side (options)
    "exchange_txn_pct": 0.0503,
    "gst_pct": 18.0,  # on brokerage + exchange charges
    "sebi_fee_pct": 0.0001,
    "stamp_duty_buy_pct": 0.003,
    "slippage_rs": 0.10,
}

STRATEGIES = ["trend_vwap", "orb", "vwap_pullback", "oi_buildup"]
