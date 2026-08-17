from diezapp.features.settings.application.settings_service import SettingsService


class InMemorySettingsRepository:
    def __init__(self):
        self.settings = {"theme_mode": "light", "fund_percentage": 1}

    def load(self):
        return dict(self.settings)

    def save(self, settings):
        self.settings = dict(settings)


def test_settings_service_loads_and_saves_settings():
    repository = InMemorySettingsRepository()
    service = SettingsService(repository)

    assert service.load() == {"theme_mode": "light", "fund_percentage": 1}
    saved = service.save("dark", 12)

    assert saved == {"theme_mode": "dark", "fund_percentage": 12}
    assert service.load() == saved
