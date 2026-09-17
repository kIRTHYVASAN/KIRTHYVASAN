import pandas as pd

from paper import broker, manager

SYMBOL = "NSE-NIFTY-17Sep26-24700-CE"


class FakeProvider:
    def __init__(self, ltp: float):
        self.ltp = ltp

    def get_option_chain(self, instrument, expiry):
        return pd.DataFrame([{"strike": 24700.0, "option_type": "CE", "ltp": self.ltp}])


def _fresh_state(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "STATE_DIR", tmp_path)
    monkeypatch.setattr(broker, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(broker, "FILLS_FILE", tmp_path / "fills.csv")
    return broker.load_state()


def test_refresh_positions_closes_on_stop_loss(tmp_path, monkeypatch):
    state = _fresh_state(tmp_path, monkeypatch)
    broker.place_order(state, SYMBOL, "bullish", 100.0, 90.0, 120.0, 65, "trend_vwap")

    actions = manager.refresh_positions(FakeProvider(85.0), state)

    assert len(actions) == 1
    assert actions[0]["action"] == "stop_loss"
    assert broker.get_positions(state) == []
    assert state["closed"][0]["exit_reason"] == "stop_loss"


def test_refresh_positions_holds_when_price_is_flat(tmp_path, monkeypatch):
    state = _fresh_state(tmp_path, monkeypatch)
    broker.place_order(state, SYMBOL, "bullish", 100.0, 90.0, 120.0, 65, "trend_vwap")

    actions = manager.refresh_positions(FakeProvider(101.0), state)

    assert actions == []
    assert len(broker.get_positions(state)) == 1


def test_refresh_positions_partial_exit_at_1r_moves_sl_to_breakeven(tmp_path, monkeypatch):
    state = _fresh_state(tmp_path, monkeypatch)
    broker.place_order(state, SYMBOL, "bullish", 100.0, 90.0, 120.0, 65, "trend_vwap")

    actions = manager.refresh_positions(FakeProvider(110.0), state)  # exactly 1R

    assert actions[0]["action"] == "partial_exit"
    remaining = broker.get_positions(state)
    assert len(remaining) == 1
    assert remaining[0]["sl"] == 100.0
    assert remaining[0]["partial_done"] is True
    assert remaining[0]["remaining_qty"] < 65


def test_refresh_positions_ignores_unparseable_symbol(tmp_path, monkeypatch):
    state = _fresh_state(tmp_path, monkeypatch)
    broker.place_order(state, "not-a-groww-symbol", "bullish", 100.0, 90.0, 120.0, 65, "trend_vwap")

    actions = manager.refresh_positions(FakeProvider(85.0), state)

    assert actions == []
    assert len(broker.get_positions(state)) == 1
