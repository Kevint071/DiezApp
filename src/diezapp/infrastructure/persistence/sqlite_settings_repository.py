import sqlite3

from diezapp.features.settings.domain.models import AppSettings
from utils.db import get_setting, set_setting

_DEFAULTS: AppSettings = {"theme_mode": "light", "fund_percentage": 1}


class SqliteSettingsRepository:
    def load(self) -> AppSettings:
        try:
            theme_mode = get_setting("theme_mode", _DEFAULTS["theme_mode"])
            raw_percentage = get_setting(
                "fund_percentage", str(_DEFAULTS["fund_percentage"])
            )
        except sqlite3.Error:
            return dict(_DEFAULTS)
        try:
            fund_percentage = int(raw_percentage)
        except TypeError, ValueError:
            fund_percentage = _DEFAULTS["fund_percentage"]
        return {"theme_mode": theme_mode, "fund_percentage": fund_percentage}

    def save(self, settings: AppSettings) -> None:
        set_setting("theme_mode", settings["theme_mode"])
        set_setting("fund_percentage", str(settings["fund_percentage"]))
