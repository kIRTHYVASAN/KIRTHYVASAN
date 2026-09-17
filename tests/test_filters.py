from datetime import date

import filters


def test_is_expiry_day_matches_given_date():
    assert filters.is_expiry_day("17Sep25", today=date(2025, 9, 17))
    assert not filters.is_expiry_day("17Sep25", today=date(2025, 9, 16))


def test_vix_in_band():
    assert filters.vix_in_band(14.0)
    assert not filters.vix_in_band(30.0)
    assert not filters.vix_in_band(5.0)


def test_spread_ok_within_and_outside_threshold():
    assert filters.spread_ok(99.0, 101.0)  # ~2% spread, at threshold
    assert not filters.spread_ok(80.0, 120.0)  # 40% spread


def test_market_ok_blocks_on_expiry_day():
    allowed, reason = filters.market_ok("17Sep25", vix=14.0, today=date(2025, 9, 17))
    assert not allowed
    assert "expiry" in reason
