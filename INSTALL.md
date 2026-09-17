# Options Controller — Installation Guide

Paper-trading only. No live order is ever sent without your explicit
approval in the dashboard. This guide covers two ways to run it on Windows:

- **Path A — Quick start (Python required):** fastest way to try it today.
- **Path B — Standalone desktop app (build once):** produces a double-click
  `OptionsController.exe` with no terminal window, for everyday use.

You can do either one, or both. Path B needs Path A's Python install as a
one-time build step, but the resulting `.exe` runs standalone after that.

---

## 0. Get the code

1. Unzip `OptionsController.zip` (or clone the repo) to a folder, e.g.
   `C:\OptionsController`.
2. Open that folder — everything below assumes you're inside it.

---

## Path A — Quick start (runs in your browser)

### A1. Install Python

1. Download Python 3.12+ from **https://www.python.org/downloads/**.
2. Run the installer. On the first screen, **check "Add python.exe to PATH"**
   before clicking Install — this step is easy to miss and everything below
   depends on it.
3. Verify it worked: open Command Prompt (Win+R, type `cmd`, Enter) and run:
   ```
   python --version
   ```
   It should print `Python 3.12.x` or newer. If it says "not recognized",
   Python isn't on PATH — reinstall and check that box.

### A2. Run the app

1. Double-click **`Start Options Controller.bat`** in the project folder.
2. First run only: it creates a virtual environment (`.venv`) and installs
   dependencies — this takes a minute or two. Subsequent runs are instant.
3. A browser tab opens automatically at `http://localhost:8501` with the
   dashboard. Leave the black Command Prompt window open — closing it stops
   the app.
4. To stop: close the Command Prompt window, or press `Ctrl+C` inside it.

### A3. First look around

- **Demo mode** is on by default (top-left toggle) — it uses synthetic data,
  no Groww account or credentials needed. Click **Scan now** to see a
  proposal, and try the **Backtest** tab.
- Leave Demo mode on until you've read the Non-negotiable rules in
  `CLAUDE.md` and are ready to connect a real Groww account (see step 4
  below).

---

## Path B — Standalone desktop app (build once, run forever)

This produces a single `OptionsController.exe` that opens in its own window
— no browser tab, no Command Prompt, no visible terminal. You only need
Python installed on the machine that *builds* it; the resulting `.exe` does
not require Python to run.

### B1. Prerequisites

Complete **A1** above (Python installed and on PATH) if you haven't already.

### B2. Build it

1. Double-click **`Build Desktop App.bat`** in the project folder.
2. This creates a separate build environment (`.venv-build`), installs the
   extra packaging dependencies, and runs PyInstaller. This takes a few
   minutes and prints a lot of output — that's normal.
3. When it finishes, you'll see:
   ```
   Build succeeded: dist\OptionsController.exe
   ```
4. If it instead prints an error, scroll up in the window to find the actual
   PyInstaller error message — see Troubleshooting below.

### B3. Run it

1. Go to the `dist` folder and double-click **`OptionsController.exe`**.
2. A native window opens with the same dashboard as Path A. That's it — no
   terminal, no browser tab to manage.
3. Optional: copy `OptionsController.exe` to your Desktop or pin it to the
   Start menu / Taskbar for quick access. It's a single file — copy it
   anywhere and it still works.
4. Rebuilding: if you pull code updates later, just re-run
   `Build Desktop App.bat` to produce a fresh `.exe`.

---

## 1. Demo mode vs. connecting your real Groww account

**Demo mode** (the default) needs nothing further — it's fully synthetic
data for trying out the dashboard, strategies, and backtests safely.

To connect your **real Groww account** for live data (still paper trading —
no orders are placed without your approval):

1. You need a Groww **Trading API** subscription (separate from a regular
   Groww account) and API credentials from Groww's developer portal.
2. In the dashboard, open the **Settings** tab.
3. Enter your `GROWW_API_KEY`, and either your `GROWW_TOTP_SECRET` (if you
   log in via TOTP/authenticator) or `GROWW_API_SECRET` (if you use a
   secret key) — pick the "Auth method" that matches how your Groww API
   credentials work.
4. Click **Save credentials**. These are stored in your Windows Credential
   Manager, not in a plain file.
5. Turn off the **Demo mode** toggle in the sidebar and click **Scan now**.

   If Settings shows *"No OS credential store is available"*, your Windows
   Credential Manager isn't reachable in that environment — as a fallback,
   copy `.env.example` to `.env` in the project folder and fill in the same
   three values there instead. Never share or commit your `.env` file.

---

## 2. Everyday use

- **Scan tab**: pick an instrument (NIFTY/BANKNIFTY) and strategy, click
  **Scan now**. If a setup is found you'll see entry/stop-loss/target/qty —
  click **APPROVE** to record a paper trade, or **REJECT** to discard it.
  Nothing is ever sent to Groww from this button.
- **Auto-refresh positions** (sidebar toggle): during market hours, checks
  your open paper positions every 30 seconds and applies exits
  automatically (partial at 1R, trailing stop, time stop, square-off at
  15:15) — exactly the same rules used in backtesting.
- **Backtest tab**: pick a strategy/instrument/day count and run a backtest
  on synthetic historical data; download results as CSV.
- **Settings tab**: manage your Groww credentials (see above).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not recognized in Command Prompt | Reinstall Python, check "Add python.exe to PATH" during setup. |
| `Start Options Controller.bat` window closes instantly | Right-click the .bat file → Edit, or run it from an already-open Command Prompt (`cd` into the folder, then type the filename) to see the error text before the window closes. |
| Antivirus/SmartScreen blocks `OptionsController.exe` | This is expected for an unsigned, freshly-built .exe. Click "More info" → "Run anyway" (Windows SmartScreen), or add an exclusion in your antivirus for the `dist` folder. |
| `Build Desktop App.bat` fails partway through | Scroll up in the window for the actual error from `pip` or `PyInstaller`. Most common cause: an outdated pip — the script already runs `pip install --upgrade pip`, but very old Python installs may still need a manual `python -m pip install --upgrade pip` first. |
| Settings tab says no credential store is available | Use the `.env` fallback described in section 1, step 5. |
| Port 8501 already in use (Path A) | Another Streamlit app is already running. Close it, or edit `Start Options Controller.bat` and add `--server.port 8502` (or any free port) to the `streamlit run app.py` line. |

---

## Uninstalling / cleaning up

- Path A: delete the `.venv` folder inside the project folder (safe — it's
  just the installed Python packages, not your data).
- Path B: delete `.venv-build`, `build`, and `dist` folders to remove build
  artifacts; keep or delete `dist\OptionsController.exe` as you wish.
- Your paper-trading history lives in `logs\paper\` — back it up before
  deleting anything if you want to keep it.
