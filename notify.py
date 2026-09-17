"""Best-effort desktop notifications (Windows toast / macOS / Linux). Never
raises -- a missing notification backend must not break the dashboard."""
from __future__ import annotations


def notify(title: str, message: str) -> None:
    try:
        from plyer import notification

        notification.notify(title=title, message=message, app_name="Options Controller", timeout=8)
    except Exception:
        pass
