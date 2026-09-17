from backtest import costs
from backtest.engine import run_backtest, summarize


def test_round_trip_cost_is_positive_and_reasonable():
    cost = costs.round_trip_cost(entry_price=100.0, exit_price=120.0, qty=65)
    assert 0 < cost < 500


def test_slippage_adjusted_moves_price_against_the_trader():
    assert costs.slippage_adjusted(100.0, is_buy=True) > 100.0
    assert costs.slippage_adjusted(100.0, is_buy=False) < 100.0


def test_run_backtest_returns_well_formed_result_on_demo_data():
    result = run_backtest("NIFTY", "trend_vwap", days=8, demo=True)
    assert "trades" in result and "summary" in result
    assert isinstance(result["trades"], list)
    summary = result["summary"]
    assert "win_rate_pct" in summary and "expectancy" in summary


def test_summarize_empty_trades_is_safe():
    summary = summarize([])
    assert summary["trades"] == 0
    assert summary["profit_factor"] is None
