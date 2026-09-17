"""Securely persist Groww credentials via the OS credential store (Windows
Credential Manager, macOS Keychain, or the Linux Secret Service) through the
`keyring` package. Credentials are never written to a plaintext file by this
module -- .env stays as the fallback for headless/CLI use only.

Every keyring call is wrapped defensively: a missing/broken OS backend (no
Secret Service running, a broken crypto backend, keyring not configured on a
fresh machine) must degrade to "not available" rather than crash the caller.
A backend can fail via a genuine Rust panic surfacing through PyO3 bindings
(e.g. a broken `cryptography` install) -- those inherit from BaseException,
not Exception, specifically so they don't get silently swallowed by normal
error handling, so we must catch BaseException here on purpose.
"""
from __future__ import annotations

import keyring

SERVICE_NAME = "OptionsController"
FIELDS = ("GROWW_API_KEY", "GROWW_TOTP_SECRET", "GROWW_API_SECRET")


def _guard(fn, default):
    try:
        return fn()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        return default


def is_available() -> bool:
    return _guard(keyring.get_keyring, None) is not None


def _safe_get(field: str) -> str | None:
    return _guard(lambda: keyring.get_password(SERVICE_NAME, field), None)


def _safe_set(field: str, value: str) -> bool:
    return _guard(lambda: keyring.set_password(SERVICE_NAME, field, value) or True, False)


def _safe_delete(field: str) -> None:
    _guard(lambda: keyring.delete_password(SERVICE_NAME, field), None)


def save_credentials(**values: str | None) -> bool:
    """Persist the given fields; a falsy value clears that field. Returns
    False if the OS credential store isn't usable (nothing was saved)."""
    ok = True
    for field in FIELDS:
        value = values.get(field)
        if value:
            ok = _safe_set(field, value) and ok
        else:
            _safe_delete(field)
    return ok


def load_credentials() -> dict[str, str | None]:
    return {field: _safe_get(field) for field in FIELDS}


def clear_credentials() -> None:
    save_credentials()


def has_credentials() -> bool:
    creds = load_credentials()
    return bool(creds["GROWW_API_KEY"] and (creds["GROWW_TOTP_SECRET"] or creds["GROWW_API_SECRET"]))
