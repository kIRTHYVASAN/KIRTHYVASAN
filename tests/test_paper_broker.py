from paper import broker


def test_place_order_and_full_exit_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "STATE_DIR", tmp_path)
    monkeypatch.setattr(broker, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(broker, "FILLS_FILE", tmp_path / "fills.csv")

    state = broker.load_state()
    position = broker.place_order(state, "NIFTY-24700-CE", "bullish", 100.0, 90.0, 120.0, 65, "trend_vwap")

    assert state["trades_today"] == 1
    assert len(broker.get_positions(state)) == 1
    assert broker.FILLS_FILE.exists()

    realized = broker.apply_exit(state, position["id"], 120.0, 65, "target_hit")
    assert realized == (120.0 - 100.0) * 65
    assert len(broker.get_positions(state)) == 0
    assert len(state["closed"]) == 1

    summary = broker.pnl_summary(state)
    assert summary["realized_pnl_today"] == realized
    assert summary["closed_trades"] == 1


def test_partial_exit_keeps_position_open_with_reduced_qty(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "STATE_DIR", tmp_path)
    monkeypatch.setattr(broker, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(broker, "FILLS_FILE", tmp_path / "fills.csv")

    state = broker.load_state()
    position = broker.place_order(state, "NIFTY-24700-CE", "bullish", 100.0, 90.0, 120.0, 65, "trend_vwap")

    broker.apply_exit(state, position["id"], 110.0, 33, "partial_exit", new_sl=100.0)

    remaining = broker.get_positions(state)
    assert len(remaining) == 1
    assert remaining[0]["remaining_qty"] == 32
    assert remaining[0]["partial_done"] is True
    assert remaining[0]["sl"] == 100.0
