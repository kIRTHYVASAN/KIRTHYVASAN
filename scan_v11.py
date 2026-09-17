"""Raw data check: dump spot/future candles, chain, and indicators for one
instrument so you can eyeball the feed before trusting the strategies.

Usage: python scan_v11.py [--instrument NIFTY] [--demo]
"""
from __future__ import annotations

import argparse

import config
from analysis.indicators import ema, rsi, swing_high_low, vwap
from data import chain, feed
from providers import DemoProvider


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", default=config.DEFAULT_INSTRUMENT, choices=list(config.INSTRUMENTS))
    parser.add_argument("--demo", action="store_true", default=True)
    args = parser.parse_args()

    provider = DemoProvider()

    spot_5m = feed.spot_candles(provider, args.instrument, "5m", 100)
    future_5m = feed.future_candles(provider, args.instrument, "5m", 100)
    expiry = chain.nearest_expiry(provider, args.instrument)
    opt_chain = chain.option_chain(provider, args.instrument, expiry)

    print(f"Instrument: {args.instrument}   Expiry: {expiry}")
    print("\n--- Spot 5m (tail) ---")
    print(spot_5m.tail(5).to_string(index=False))
    print("\n--- Future 5m (tail) ---")
    print(future_5m.tail(5).to_string(index=False))

    print("\n--- Indicators (latest) ---")
    print(f"EMA20/EMA50 (spot): {ema(spot_5m['close'], 20).iloc[-1]:.2f} / {ema(spot_5m['close'], 50).iloc[-1]:.2f}")
    print(f"RSI(14): {rsi(spot_5m['close']).iloc[-1]:.1f}")
    print(f"Future VWAP: {vwap(future_5m).iloc[-1]:.2f}  (close {future_5m['close'].iloc[-1]:.2f})")
    print(f"Swing high/low (20 bars): {swing_high_low(spot_5m, 20)}")

    print("\n--- Option chain (ATM +-3) ---")
    atm = chain.atm_strike(spot_5m["close"].iloc[-1], args.instrument)
    step = config.INSTRUMENTS[args.instrument]["strike_step"]
    near = opt_chain[(opt_chain["strike"] >= atm - 3 * step) & (opt_chain["strike"] <= atm + 3 * step)]
    print(near.sort_values(["strike", "option_type"]).to_string(index=False))
    print("\nPCR:", chain.pcr_summary(opt_chain))


if __name__ == "__main__":
    main()
