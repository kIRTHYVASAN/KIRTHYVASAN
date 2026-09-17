# CLAUDE.md — Options Controller (project handoff)

## Goal
AI-assisted intraday options trading controller on Groww:
Scan → analyse → choose CE/PE → entry/SL/target/qty → show proposal → USER APPROVES → execute.
Currently paper trading only. Desktop packaging (Windows) is done; next is real-data validation.

## Non-negotiable rules
- No order is ever sent without explicit user approval (APPROVE button).
- Paper trading first; live Groww orders only after backtest + 1–2 months of paper results justify it.
- Risk limits in config.RISK are hard limits; analysis code must not override them.
- Never log or display API keys/secrets. .env and .token_cache.json stay out of git.
- ASTRA (screen/browser control) may read/display charts only — never click Buy.

## Status (V1.7)
Done:
- V1.1 Groww auth (TOTP or key+secret, daily token cache, resets 06:00 IST), spot/future candles, option chain with OI + Greeks
- V1.2 indicators (EMA 20/50, VWAP, RSI, swings), bullish/bearish/no-trade, CE/PE selection (delta 0.40–0.60 + liquidity)
- V1.3 risk engine: entry at ask, SL from underlying swing × delta (10–30% of premium), 2R target, 1% risk/trade, max 3 trades/day, 3% daily loss stop, entries 09:30–14:45, square-off 15:15, max 5 lots
- V1.4 Streamlit dashboard: candlestick chart (Groww data) + EMA/S-R/SL lines, proposal card, APPROVE/REJECT
- V1.5 paper trading: positions, fills log, P&L
- V1.6 4 strategies, market filters, exit management, backtest engine with costs, instrument selector,
  Windows launcher "Start Options Controller.bat"
- V1.7 Windows desktop packaging: PyInstaller + pywebview wrapper (desktop/launcher.py,
  desktop/options_controller.spec, "Build Desktop App.bat") producing a double-click
  OptionsController.exe; Settings tab with credentials stored via the OS credential manager
  (settings_store.py, keyring — .env stays as the headless/CLI fallback); paper/manager.py
  wires the existing risk/exits logic to a live loop over open positions (previously that
  logic only ran inside the backtest engine); auto-refresh toggle (streamlit-autorefresh,
  market hours only) and best-effort desktop notifications (notify.py, plyer) on a new
  tradeable setup or a position exit; app icon (assets/icon.ico); step-by-step install guide
  for a non-technical Windows user (INSTALL.md / INSTALL.txt)

Not done:
- Real-data validation (backtest must be run on user's PC against real Groww history; not yet run)
- The actual .exe has NOT been built/tested on a real Windows machine — PyInstaller can't
  cross-compile from the Linux dev environment this was built in, so only the spec's module
  collection logic and the in-process-vs-subprocess server design were validated there.
  Build it via "Build Desktop App.bat" on Windows and smoke-test before relying on it.
- V2 ASTRA + TradingView/GoCharting integration (TradingView only via paid-plan webhooks; GoCharting has no API)
- Live Groww execution (after validation), iOS app (Flutter + cloud server), MCX commodities

## Tech
Python 3.12+, growwapi 1.5.0, pandas, numpy, pyotp, python-dotenv, streamlit, plotly, pytest,
keyring, plyer, streamlit-autorefresh (runtime); pywebview, pyinstaller, pillow (build-only,
see requirements-build.txt).
User is on Windows. User knows Flutter well (BLoC, Dio, biometrics) — relevant for a future mobile app.

## Structure
    app.py                      Streamlit dashboard (Scan / Backtest / Settings tabs)
    controller.py                scan(provider, strategy) -> proposal dict (never places orders)
    providers.py                 GrowwProvider (live) / DemoProvider (synthetic) — same interface
    config.py                    Instrument presets, SIGNAL, SELECT, RISK, FILTERS, EXITS, strategy params, COSTS
    auth.py                      Groww token handling (keyring first, then .env)
    settings_store.py            Settings-tab credential storage via OS credential manager (keyring)
    notify.py                    Best-effort desktop notifications (plyer), never raises
    data/feed.py                 spot/future candles, LTP, near-month future
    data/chain.py                expiries, option chain, ATM, PCR summary
    analysis/                    indicators.py, signal.py (trend_vwap), selector.py, optionpricing.py (BS pricing for demo data)
    strategies/                  orb.py, vwap_pullback.py, oi_buildup.py, common.py, registry in __init__.py
    filters.py                   expiry day, VIX band, event days, bid-ask spread
    risk/engine.py                gate() limits, build_plan() sizing
    risk/exits.py                 partial at 1R -> SL to entry, trail after 1.5R, 30-min time stop, square-off
    paper/broker.py               JSON state + CSV fills in logs/paper/
    paper/manager.py              live loop applying risk/exits to open paper positions (Scan tab auto-refresh)
    backtest/                     engine.py, history.py (GrowwHistory cached / DemoHistory), costs.py
    backtest.py                   CLI
    scan_v11.py                   raw data check
    desktop/launcher.py           pywebview window + Streamlit-as-subprocess (SIGTERM handler needs main thread)
    desktop/options_controller.spec  PyInstaller onefile spec (must be built ON Windows)
    assets/icon.ico               app icon
    "Start Options Controller.bat"  Path A launcher (Python + browser)
    "Build Desktop App.bat"        Path B: builds dist/OptionsController.exe
    INSTALL.md / INSTALL.txt       step-by-step install guide for end users
    tests/                        52 offline tests (pytest -q)

## Strategies
- trend_vwap: 7 checks (15m trend, 5m trend, future VWAP, volume >1.2x avg, RSI 55–75/25–45,
  breakout or EMA retest with room to S/R, PCR); both trends required, score >= 6/7
- orb: first 15-min range breakout until 11:30, range width 0.15–0.9%, 15m trend + VWAP
- vwap_pullback: 15m trend, future touches VWAP and rejects, RSI side, 5m vs EMA20
- oi_buildup: future price and OI rising together over 3 bars + 15m trend
All are unproven starting points. Judge by expectancy, profit factor, drawdown over 100+ trades — not win rate.

## Groww / regulatory facts
- Trading API subscription required; token generation limited (150/day)
- Historical candles: CASH and FNO segments; option groww_symbol format NSE-NIFTY-30Sep25-24650-CE
- Index candles have no volume → volume/VWAP/OI come from near-month future
- SEBI retail algo rules (from 1 Apr 2026): static whitelisted IP for API orders, daily 2FA, 10 orders/sec,
  market orders converted to market-price-protection → use limit orders
- Verify: NIFTY lot size (fallback 65 in config), charges in config.COSTS

## Backtest assumptions
Signal on closed 5m candle; entry at next option candle open + ₹0.10 slippage; ATM option of nearest expiry;
stop checked before target within a candle; gaps fill at open; PCR skipped; data cached in cache/.
Option OHLC in the backtest is synthesized via Black-Scholes (analysis/optionpricing.py) against
demo spot/future data — there is no real historical option chain wired up yet.

## Known gotchas (found the hard way — don't re-break these)
- Streamlit's server installs a SIGTERM handler that only works on a process's main thread.
  desktop/launcher.py runs the server as a subprocess (the frozen exe re-invokes itself with
  --run-server), not a background thread — a thread-based approach crashes on startup.
- A broken/unavailable OS keyring backend can raise a PyO3 `PanicException`, which inherits
  from BaseException, not Exception — a bare `except Exception` in settings_store.py will miss
  it and crash the whole Settings tab. Guard with `except (KeyboardInterrupt, SystemExit): raise`
  then `except BaseException`. Regression test: tests/test_settings_store.py.
- rsi()/vwap() in analysis/indicators.py: a strictly monotonic price series pushes RSI to ~100
  (overbought, outside the intended 55–75/25–45 bands) and never "breaks out" of its own bar's
  high — synthetic test fixtures need a consolidation-then-breakout shape, not a pure ramp, to
  exercise trend_vwap realistically (see tests/test_signal.py's _trending_df).
- PyInstaller cannot cross-compile: "Build Desktop App.bat" must be run ON the target Windows
  machine, not from a Linux dev/CI environment.

## Next task
Real-data validation: run backtest.py against real Groww history on the user's PC once a Trading
API subscription is active, and build+smoke-test OptionsController.exe on an actual Windows
machine (see INSTALL.md Path B). After that, evaluate whether any strategy's expectancy/profit
factor over 100+ trades justifies moving toward live execution.

## Commands
    pip install -r requirements.txt
    streamlit run app.py
    python backtest.py --days 60 [--strategy orb] [--instrument BANKNIFTY] [--demo]
    python -m pytest -q
    # Windows only, one-time per machine:
    "Build Desktop App.bat"          # -> dist\OptionsController.exe
