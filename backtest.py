"""CLI: python backtest.py --days 60 [--strategy orb] [--instrument BANKNIFTY] [--demo]"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import config
from backtest.engine import run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an options strategy backtest")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--strategy", choices=config.STRATEGIES, default="trend_vwap")
    parser.add_argument("--instrument", choices=list(config.INSTRUMENTS), default=config.DEFAULT_INSTRUMENT)
    parser.add_argument("--demo", action="store_true", help="Use synthetic data (default; only mode wired up here)")
    parser.add_argument("--out", default="logs/backtest_trades.csv")
    args = parser.parse_args()

    result = run_backtest(args.instrument, args.strategy, days=args.days, demo=True)
    trades = result["trades"]
    summary = result["summary"]

    print(f"\n{args.strategy} on {args.instrument} — {args.days} trading days")
    print("-" * 50)
    for key, value in summary.items():
        print(f"{key:>15}: {value}")

    if trades:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(trades[0].keys()))
            writer.writeheader()
            writer.writerows(trades)
        print(f"\n{len(trades)} trades written to {out_path}")
    else:
        print("\nNo trades generated.")


if __name__ == "__main__":
    main()
