from datetime import datetime, timedelta

from risk.exits import evaluate_exit


def _position(**overrides):
    base = {
        "entry": 100.0, "sl": 90.0, "original_sl": 90.0, "target": 120.0,
        "entered_at": datetime.now().replace(hour=10, minute=0, second=0, microsecond=0),
        "partial_done": False,
    }
    base.update(overrides)
    return base


def test_stop_loss_triggers_full_exit():
    pos = _position()
    now = pos["entered_at"] + timedelta(minutes=5)
    result = evaluate_exit(pos, current_price=89.0, now=now)
    assert result["action"] == "stop_loss"
    assert result["exit_fraction"] == 1.0


def test_target_hit_triggers_full_exit():
    pos = _position()
    now = pos["entered_at"] + timedelta(minutes=5)
    result = evaluate_exit(pos, current_price=121.0, now=now)
    assert result["action"] == "target_hit"


def test_partial_exit_at_1r_moves_sl_to_breakeven():
    pos = _position()
    now = pos["entered_at"] + timedelta(minutes=5)
    result = evaluate_exit(pos, current_price=110.0, now=now)  # exactly 1R
    assert result["action"] == "partial_exit"
    assert result["new_sl"] == 100.0


def test_trail_sl_after_1_5r_once_partial_done():
    pos = _position(sl=100.0, partial_done=True)  # sl already moved to breakeven
    now = pos["entered_at"] + timedelta(minutes=10)
    result = evaluate_exit(pos, current_price=115.0, now=now)  # 1.5R
    assert result["action"] == "trail_sl"
    assert result["new_sl"] > pos["sl"]


def test_time_stop_when_flat_after_30_minutes():
    pos = _position()
    now = pos["entered_at"] + timedelta(minutes=35)
    result = evaluate_exit(pos, current_price=101.0, now=now)  # barely moved
    assert result["action"] == "time_stop"


def test_square_off_after_cutoff_time():
    pos = _position()
    now = pos["entered_at"].replace(hour=15, minute=20)
    result = evaluate_exit(pos, current_price=105.0, now=now)
    assert result["action"] == "square_off"
