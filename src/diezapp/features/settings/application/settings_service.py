from diezapp.features.settings.domain.models import AppSettings
from diezapp.features.settings.domain.repositories import SettingsRepository


class SettingsService:
    def __init__(self, repository: SettingsRepository):
        self.repository = repository

    def load(self) -> AppSettings:
        return self.repository.load()

    def save(self, theme_mode: str, fund_percentage: int) -> AppSettings:
        settings: AppSettings = {
            "theme_mode": theme_mode,
            "fund_percentage": fund_percentage,
        }
        self.repository.save(settings)
        return settings
