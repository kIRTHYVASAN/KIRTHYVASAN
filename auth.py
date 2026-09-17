"""Groww authentication: TOTP or key+secret, daily token cache (resets 06:00 IST).

Never log or print the API key, secret, or resulting access token.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

IST = ZoneInfo("Asia/Kolkata")
TOKEN_CACHE_PATH = Path(".token_cache.json")
RESET_HOUR_IST = 6


def _cache_is_fresh(cached_at: datetime, now: datetime) -> bool:
    """Cache is stale once we've crossed the most recent 06:00 IST boundary."""
    today_reset = now.replace(hour=RESET_HOUR_IST, minute=0, second=0, microsecond=0)
    last_reset = today_reset if now >= today_reset else today_reset - timedelta(days=1)
    return cached_at >= last_reset


def _load_cached_token() -> str | None:
    if not TOKEN_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE_PATH.read_text())
        cached_at = datetime.fromisoformat(data["cached_at"])
        if _cache_is_fresh(cached_at, datetime.now(IST)):
            return data["access_token"]
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return None


def _save_cached_token(access_token: str) -> None:
    TOKEN_CACHE_PATH.write_text(json.dumps({
        "access_token": access_token,
        "cached_at": datetime.now(IST).isoformat(),
    }))
    os.chmod(TOKEN_CACHE_PATH, 0o600)


def _generate_token() -> str:
    """Call growwapi's token endpoint using TOTP or key+secret.

    The OS credential store (via settings_store/keyring, filled in from the
    dashboard's Settings screen) is checked first; .env is the fallback for
    headless/CLI use, so scripts like backtest.py keep working unchanged.
    """
    from growwapi import GrowwAPI

    import settings_store

    creds = settings_store.load_credentials()
    api_key = creds.get("GROWW_API_KEY") or os.environ.get("GROWW_API_KEY")
    api_secret = creds.get("GROWW_API_SECRET") or os.environ.get("GROWW_API_SECRET")
    totp_secret = creds.get("GROWW_TOTP_SECRET") or os.environ.get("GROWW_TOTP_SECRET")
    if not api_key:
        raise RuntimeError("GROWW_API_KEY not set (Settings screen or .env)")

    if totp_secret:
        import pyotp

        totp = pyotp.TOTP(totp_secret).now()
        return GrowwAPI.get_access_token(api_key=api_key, totp=totp)
    if api_secret:
        return GrowwAPI.get_access_token(api_key=api_key, api_secret=api_secret)
    raise RuntimeError("Set either GROWW_TOTP_SECRET or GROWW_API_SECRET (Settings screen or .env)")


def get_session(force_refresh: bool = False) -> str:
    """Return a valid Groww access token, using the daily cache when possible."""
    load_dotenv()
    if not force_refresh:
        cached = _load_cached_token()
        if cached:
            return cached
    token = _generate_token()
    _save_cached_token(token)
    return token
