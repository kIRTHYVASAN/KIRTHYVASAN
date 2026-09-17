import pandas as pd

from analysis.selector import select_option


def _chain():
    rows = [
        {"strike": 24600, "option_type": "CE", "delta": 0.70, "oi": 100_000, "bid": 99.0, "ask": 101.0},
        {"strike": 24700, "option_type": "CE", "delta": 0.50, "oi": 80_000, "bid": 60.0, "ask": 61.0},
        {"strike": 24800, "option_type": "CE", "delta": 0.20, "oi": 60_000, "bid": 20.0, "ask": 20.5},
        {"strike": 24700, "option_type": "PE", "delta": -0.55, "oi": 90_000, "bid": 55.0, "ask": 56.0},
        {"strike": 24600, "option_type": "PE", "delta": -0.30, "oi": 40_000, "bid": 30.0, "ask": 30.2},
    ]
    return pd.DataFrame(rows)


def test_selects_call_in_delta_band_with_liquidity():
    option = select_option(_chain(), "bullish")
    assert option is not None
    assert option["option_type"] == "CE"
    assert 0.40 <= option["delta"] <= 0.60


def test_selects_put_in_delta_band_with_liquidity():
    option = select_option(_chain(), "bearish")
    assert option is not None
    assert option["option_type"] == "PE"
    assert option["strike"] == 24700


def test_returns_none_when_no_option_meets_liquidity():
    thin_chain = _chain().copy()
    thin_chain["oi"] = 100  # below min_oi everywhere
    assert select_option(thin_chain, "bullish") is None
