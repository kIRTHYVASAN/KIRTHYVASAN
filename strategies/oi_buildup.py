"""OI buildup: future price and OI rising together over N bars, plus 15m trend."""
from __future__ import annotations

import config
from analysis.indicators import ema, swing_high_low
from strategies.common import Signal

NAME = "oi_buildup"


def generate(context: dict) -> Signal:
    spot_15m = context["spot_15m"]
    spot_5m = context["spot_5m"]
    future_5m = context["future_5m"]
    n = config.OI_BUILDUP["lookback_bars"]

    if "oi" not in future_5m.columns or len(future_5m) < n + 1:
        return Signal("no-trade", NAME, 0, "no OI data available")

    recent = future_5m.tail(n + 1)
    price_deltas = recent["close"].diff().dropna()
    oi_deltas = recent["oi"].diff().dropna()

    price_up = (price_deltas > 0).all()
    price_down = (price_deltas < 0).all()
    oi_up = (oi_deltas > 0).all()
    oi_down = (oi_deltas < 0).all()

    trend_fast = ema(spot_15m["close"], config.SIGNAL["ema_fast"]).iloc[-1]
    trend_slow = ema(spot_15m["close"], config.SIGNAL["ema_slow"]).iloc[-1]

    swing = swing_high_low(spot_5m, config.SIGNAL["swing_lookback"])
    if price_up and oi_up and trend_fast > trend_slow:
        return Signal("bullish", NAME, 3, "long buildup: price+OI rising with uptrend", swing)
    if price_down and oi_up and trend_fast < trend_slow:
        return Signal("bearish", NAME, 3, "short buildup: price falling, OI rising, downtrend", swing)
    return Signal("no-trade", NAME, 0, "no consistent OI buildup")
