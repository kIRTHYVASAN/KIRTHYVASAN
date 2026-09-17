from datetime import datetime

import strategies
from providers import DemoProvider


def _context(instrument="NIFTY"):
    provider = DemoProvider()
    return {
        "spot_15m": provider.get_spot_candles(instrument, "15m", 80),
        "spot_5m": provider.get_spot_candles(instrument, "5m", 150),
        "future_5m": provider.get_future_candles(instrument, "5m", 150),
        "now": datetime.now().replace(hour=11, minute=0),
        "pcr": 1.05,
    }


def test_all_registered_strategies_run_without_error():
    ctx = _context()
    for name in strategies.REGISTRY:
        signal = strategies.generate(name, ctx)
        assert signal.direction in ("bullish", "bearish", "no-trade")


def test_unknown_strategy_raises():
    import pytest

    with pytest.raises(ValueError):
        strategies.generate("does-not-exist", _context())
