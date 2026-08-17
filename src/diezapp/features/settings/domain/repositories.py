from typing import Protocol

from diezapp.features.settings.domain.models import AppSettings


class SettingsRepository(Protocol):
    def load(self) -> AppSettings: ...

    def save(self, settings: AppSettings) -> None: ...
