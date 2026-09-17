import sys
import types

import notify


def test_notify_swallows_backend_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("no notification backend on this OS")

    fake_plyer = types.SimpleNamespace(notification=types.SimpleNamespace(notify=boom))
    monkeypatch.setitem(sys.modules, "plyer", fake_plyer)

    notify.notify("title", "message")  # must not raise


def test_notify_calls_plyer_with_expected_args(monkeypatch):
    calls = []

    def record(**kwargs):
        calls.append(kwargs)

    fake_plyer = types.SimpleNamespace(notification=types.SimpleNamespace(notify=record))
    monkeypatch.setitem(sys.modules, "plyer", fake_plyer)

    notify.notify("Setup found", "CE 24700 @ 59")

    assert calls[0]["title"] == "Setup found"
    assert calls[0]["message"] == "CE 24700 @ 59"
