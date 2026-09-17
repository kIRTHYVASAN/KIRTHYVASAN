from datetime import datetime

from risk.engine import build_plan, gate


def _now(hh, mm):
    return datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)


def test_gate_blocks_outside_entry_window():
    allowed, reason = gate({}, now=_now(8, 0))
    assert not allowed
    assert "entry window" in reason


def test_gate_blocks_after_max_trades():
    state = {"trades_today": 3}
    allowed, reason = gate(state, now=_now(11, 0))
    assert not allowed
    assert "max trades" in reason


def test_gate_blocks_after_daily_loss_stop():
    state = {"daily_pnl_pct": -3.5}
    allowed, reason = gate(state, now=_now(11, 0))
    assert not allowed
    assert "daily loss stop" in reason


def test_gate_allows_within_limits():
    allowed, reason = gate({"trades_today": 1, "daily_pnl_pct": -1.0}, now=_now(11, 0))
    assert allowed
    assert reason == ""


def test_build_plan_sizes_within_risk_and_clamps_sl_pct():
    option = {"ask": 100.0, "delta": 0.5}
    swing = {"swing_low": 24500.0, "swing_high": 24700.0}
    plan = build_plan("bullish", spot=24650.0, swing=swing, option=option, capital=100_000, lot_size=65)

    assert plan["sl"] < plan["entry"] < plan["target"]
    assert plan["qty"] % 65 == 0
    assert plan["qty"] >= 0
    # SL distance clamped to 10-30% of premium
    premium_risk_pct = plan["premium_risk_per_unit"] / plan["entry"]
    assert 0.10 - 1e-9 <= premium_risk_pct <= 0.30 + 1e-9
