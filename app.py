"""Streamlit dashboard: Scan tab (chart + proposal + approve/reject),
Backtest tab, and Settings tab (secure credential storage). Paper trading
only — no live orders are ever placed here.
"""
from __future__ import annotations

from datetime import datetime, time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import controller
import settings_store
from analysis.indicators import ema
from backtest.engine import run_backtest
from notify import notify
from paper import broker as paper_broker
from paper import manager as paper_manager
from providers import DemoProvider

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

st.set_page_config(page_title="Options Controller", layout="wide")


def _is_market_hours(now: datetime) -> bool:
    return now.weekday() < 5 and time(9, 15) <= now.time() <= time(15, 30)


@st.cache_resource
def get_demo_provider() -> DemoProvider:
    return DemoProvider()


def get_provider(demo: bool):
    if demo:
        return get_demo_provider()
    import auth
    from providers import GrowwProvider

    session = auth.get_session()
    return GrowwProvider(session)


def candlestick_chart(spot_5m: pd.DataFrame, proposal: dict | None) -> go.Figure:
    fig = go.Figure(data=[go.Candlestick(
        x=spot_5m["timestamp"], open=spot_5m["open"], high=spot_5m["high"],
        low=spot_5m["low"], close=spot_5m["close"], name="spot",
    )])
    fig.add_trace(go.Scatter(
        x=spot_5m["timestamp"], y=ema(spot_5m["close"], config.SIGNAL["ema_fast"]),
        line=dict(color="orange", width=1), name="EMA20",
    ))
    fig.add_trace(go.Scatter(
        x=spot_5m["timestamp"], y=ema(spot_5m["close"], config.SIGNAL["ema_slow"]),
        line=dict(color="blue", width=1), name="EMA50",
    ))
    if proposal and proposal.get("tradeable"):
        for level, label, color in [
            (proposal.get("swing_high"), "R", "grey"), (proposal.get("swing_low"), "S", "grey"),
        ]:
            if level:
                fig.add_hline(y=level, line_dash="dot", line_color=color, annotation_text=label)
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def render_proposal(proposal: dict) -> None:
    st.subheader("Proposal")
    top = st.columns(4)
    top[0].metric("Direction", proposal["direction"])
    top[1].metric("Score", proposal["score"])
    top[2].metric("VIX", proposal["vix"])
    top[3].metric("PCR", proposal["pcr"])

    if not proposal["tradeable"]:
        st.info(f"No trade: {proposal['reason']}")
        return

    st.write(f"**{proposal['option_symbol']}** ({proposal['option_type']} @ {proposal['strike']})")
    cols = st.columns(5)
    cols[0].metric("Entry", proposal["entry"])
    cols[1].metric("Stop Loss", proposal["sl"])
    cols[2].metric("Target", proposal["target"])
    cols[3].metric("Qty (lots)", f"{proposal['lots']} ({proposal['qty']})")
    cols[4].metric("Risk ₹", proposal["risk_amount"])

    approve_col, reject_col = st.columns(2)
    if approve_col.button("✅ APPROVE", type="primary", use_container_width=True):
        state = paper_broker.load_state()
        paper_broker.place_order(
            state, proposal["option_symbol"], proposal["direction"], proposal["entry"],
            proposal["sl"], proposal["target"], proposal["qty"], proposal["strategy"],
        )
        st.success("Order filled in paper trading.")
        st.rerun()
    if reject_col.button("❌ REJECT", use_container_width=True):
        st.warning("Proposal rejected.")


def scan_tab() -> None:
    with st.sidebar:
        st.header("Controls")
        demo = st.toggle("Demo mode", value=True)
        instrument = st.selectbox("Instrument", list(config.INSTRUMENTS), index=0)
        strategy_name = st.selectbox("Strategy", config.STRATEGIES, index=0)
        auto_refresh = st.toggle("Auto-refresh positions (30s, market hours)", value=False)
        if auto_refresh and st_autorefresh is None:
            st.caption("Install `streamlit-autorefresh` to enable this.")

    provider = get_provider(demo)
    now = datetime.now()

    if auto_refresh and st_autorefresh is not None and _is_market_hours(now):
        st_autorefresh(interval=30_000, key="position_autorefresh")

    if st.button("🔍 Scan now", type="primary"):
        with st.spinner("Scanning..."):
            proposal = controller.scan(provider, strategy_name, instrument)
            st.session_state["proposal"] = proposal
            st.session_state["chart_data"] = provider.get_spot_candles(instrument, "5m", 150)
        if proposal["tradeable"]:
            notify(
                "Options Controller: setup found",
                f"{proposal['direction'].upper()} {proposal['option_symbol']} @ {proposal['entry']}",
            )

    proposal = st.session_state.get("proposal")
    chart_data = st.session_state.get("chart_data")

    left, right = st.columns([2, 1])
    with left:
        if chart_data is not None:
            st.plotly_chart(candlestick_chart(chart_data, proposal), use_container_width=True)
        else:
            st.info("Click 'Scan now' to fetch data and generate a proposal.")
    with right:
        if proposal:
            render_proposal(proposal)

    st.divider()
    st.subheader("Open positions")
    state = paper_broker.load_state()
    for action in paper_manager.refresh_positions(provider, state, now):
        st.toast(f"{action['symbol']}: {action['action']} @ {action['price']}")
        notify("Options Controller: position update", f"{action['symbol']} {action['action']} @ {action['price']}")

    positions = paper_broker.get_positions(state)
    if positions:
        st.dataframe(pd.DataFrame(positions), use_container_width=True)
    else:
        st.caption("No open paper positions.")

    pnl = paper_broker.pnl_summary(state)
    pcols = st.columns(5)
    pcols[0].metric("Trades today", pnl["trades_today"])
    pcols[1].metric("Realized P&L", pnl["realized_pnl_today"])
    pcols[2].metric("Daily P&L %", pnl["daily_pnl_pct"])
    pcols[3].metric("Open positions", pnl["open_positions"])
    pcols[4].metric("Win rate %", pnl["win_rate"])


def backtest_tab() -> None:
    c1, c2, c3, c4 = st.columns(4)
    days = c1.number_input("Days", min_value=10, max_value=250, value=60, step=10)
    strategy_name = c2.selectbox("Strategy", config.STRATEGIES, key="bt_strategy")
    instrument = c3.selectbox("Instrument", list(config.INSTRUMENTS), key="bt_instrument")
    run = c4.button("▶ Run backtest", type="primary")

    if run:
        with st.spinner("Running backtest on synthetic demo data..."):
            result = run_backtest(instrument, strategy_name, days=int(days), demo=True)
        st.session_state["bt_result"] = result

    result = st.session_state.get("bt_result")
    if not result:
        st.info("Configure and run a backtest.")
        return

    summary = result["summary"]
    cols = st.columns(6)
    for col, (key, value) in zip(cols, summary.items()):
        col.metric(key.replace("_", " ").title(), value)

    trades = result["trades"]
    if trades:
        df = pd.DataFrame(trades)
        st.plotly_chart(
            go.Figure(go.Scatter(y=df["net_pnl"].cumsum(), mode="lines", name="Equity")).update_layout(
                title="Equity curve", height=350, margin=dict(l=10, r=10, t=40, b=10)
            ),
            use_container_width=True,
        )
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "⬇ Download trades CSV", df.to_csv(index=False).encode(),
            file_name=f"backtest_{strategy_name}_{instrument}_{datetime.now():%Y%m%d_%H%M}.csv",
        )
    else:
        st.warning("No trades were generated over this period.")


def settings_tab() -> None:
    st.subheader("Groww credentials")
    st.caption(
        "Stored securely via your OS credential manager (Windows Credential "
        "Manager, macOS Keychain, or the Linux Secret Service) -- never "
        "written to a plaintext file. Demo mode works without any of this."
    )

    if not settings_store.is_available():
        st.warning(
            "No OS credential store is available on this machine (Windows "
            "Credential Manager / Keychain / Secret Service), so credentials "
            "can't be saved here. Use a .env file instead (see .env.example)."
        )

    existing = settings_store.load_credentials()
    if settings_store.has_credentials():
        st.success("Credentials are currently configured.")
    else:
        st.info("No credentials configured yet.")

    api_key = st.text_input(
        "GROWW_API_KEY", type="password",
        placeholder="•••••••• (unchanged)" if existing["GROWW_API_KEY"] else "",
    )
    method = st.radio("Auth method", ["TOTP secret", "API secret"], horizontal=True)
    totp_secret = api_secret = ""
    if method == "TOTP secret":
        totp_secret = st.text_input(
            "GROWW_TOTP_SECRET", type="password",
            placeholder="•••••••• (unchanged)" if existing["GROWW_TOTP_SECRET"] else "",
        )
    else:
        api_secret = st.text_input(
            "GROWW_API_SECRET", type="password",
            placeholder="•••••••• (unchanged)" if existing["GROWW_API_SECRET"] else "",
        )

    col_save, col_clear = st.columns(2)
    if col_save.button("💾 Save credentials", type="primary"):
        saved = settings_store.save_credentials(
            GROWW_API_KEY=api_key or existing["GROWW_API_KEY"],
            GROWW_TOTP_SECRET=totp_secret or existing["GROWW_TOTP_SECRET"],
            GROWW_API_SECRET=api_secret or existing["GROWW_API_SECRET"],
        )
        if saved:
            st.success("Credentials saved.")
        else:
            st.error("Could not save: no OS credential store available on this machine.")
        st.rerun()
    if col_clear.button("🗑 Clear credentials"):
        settings_store.clear_credentials()
        st.warning("Credentials cleared.")
        st.rerun()


st.title("Options Controller")
tab_scan, tab_backtest, tab_settings = st.tabs(["Scan", "Backtest", "Settings"])
with tab_scan:
    scan_tab()
with tab_backtest:
    backtest_tab()
with tab_settings:
    settings_tab()
