"""Desktop entry point: runs the existing Streamlit dashboard as a child
process and shows it in a native window via pywebview, so packaging with
PyInstaller produces a double-click .exe with no visible terminal and no
separate Python/browser install required (pywebview uses the OS's built-in
WebView2 on Windows 10/11).

Streamlit's server installs a SIGTERM handler that only works from a
process's main thread, so it cannot be started in a background thread of
this same process -- it is launched as a child process instead. In a
PyInstaller onefile build sys.executable *is* this app, so the child is the
same exe re-invoked with --run-server; in dev, it's this script re-run under
the current interpreter (the same trick multiprocessing.freeze_support()
uses).

The engine (controller/strategies/risk/paper/backtest) and app.py are
completely unchanged -- this only supplies a native window around them.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_TITLE = "Options Controller"


def resource_path(relative: str) -> Path:
    """Resolve a path both in dev and inside a PyInstaller onefile bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.3)
    return False


def run_server_blocking(port: int) -> None:
    """Run `streamlit run app.py` in this process (blocks). Only ever called
    in the dedicated child process, so the SIGTERM handler installs cleanly."""
    from streamlit.web import bootstrap

    app_path = str(resource_path("app.py"))
    flag_options = {
        "server.port": port,
        "server.address": "127.0.0.1",
        "server.headless": True,
        "browser.gatherUsageStats": False,
        "global.developmentMode": False,
    }
    bootstrap.load_config_options(flag_options=flag_options)
    bootstrap.run(app_path, is_hello=False, args=[], flag_options=flag_options)


def _server_subprocess_args(port: int) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run-server", str(port)]
    return [sys.executable, str(Path(__file__).resolve()), "--run-server", str(port)]


def launch_desktop_window() -> None:
    import webview

    port = find_free_port()
    server_proc = subprocess.Popen(
        _server_subprocess_args(port), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        if not wait_for_server(url):
            raise RuntimeError(f"Dashboard server did not start at {url}")

        icon_path = resource_path("assets/icon.ico")
        webview.create_window(
            APP_TITLE, url, width=1400, height=900, min_size=(900, 600),
        )
        webview.start(icon=str(icon_path) if icon_path.exists() else None)
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()


def main() -> None:
    if "--run-server" in sys.argv:
        port = int(sys.argv[sys.argv.index("--run-server") + 1])
        run_server_blocking(port)
        return
    launch_desktop_window()


if __name__ == "__main__":
    main()
