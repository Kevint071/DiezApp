"""Persisted app-level settings (theme mode, fund split percentage)."""

import sqlite3

from utils.db import get_setting, set_setting

_DEFAULTS = {"theme_mode": "light", "fund_percentage": 1}


def load_settings() -> dict:
    """Load theme_mode and fund_percentage from the local database.

    Falls back to defaults (instead of blocking/crashing startup) if the DB
    is unreachable for any reason, so the first frame always renders.
    """
    try:
        theme_mode = get_setting("theme_mode", _DEFAULTS["theme_mode"])
        raw_pct = get_setting("fund_percentage", str(_DEFAULTS["fund_percentage"]))
    except sqlite3.Error:
        return dict(_DEFAULTS)
    try:
        fund_percentage = int(raw_pct)
    except (TypeError, ValueError):
        fund_percentage = _DEFAULTS["fund_percentage"]
    return {"theme_mode": theme_mode, "fund_percentage": fund_percentage}


def save_settings(theme_mode: str, fund_percentage: int):
    set_setting("theme_mode", theme_mode)
    set_setting("fund_percentage", str(fund_percentage))
