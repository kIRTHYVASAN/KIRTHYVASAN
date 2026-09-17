import socket
import sys

from desktop.launcher import _server_subprocess_args, find_free_port, resource_path, wait_for_server


def test_find_free_port_returns_bindable_port():
    port = find_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))  # must not raise (port was actually free)


def test_wait_for_server_times_out_on_closed_port():
    port = find_free_port()
    assert wait_for_server(f"http://127.0.0.1:{port}", timeout=0.5) is False


def test_resource_path_resolves_to_existing_app_file():
    path = resource_path("app.py")
    assert path.name == "app.py"
    assert path.exists()


def test_server_subprocess_args_uses_current_interpreter_in_dev(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    args = _server_subprocess_args(12345)
    assert args[0] == sys.executable
    assert "--run-server" in args
    assert "12345" in args


def test_server_subprocess_args_reinvokes_frozen_exe(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    args = _server_subprocess_args(12345)
    assert args == [sys.executable, "--run-server", "12345"]
