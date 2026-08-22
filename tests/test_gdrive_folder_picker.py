import asyncio

import flet as ft

from diezapp.features.google_drive.presentation.google_drive_folder_picker import (
    GoogleDriveFolderPicker,
)

COLORS = {
    key: "#000000"
    for key in (
        "on_surface_variant",
        "primary",
        "on_primary",
        "outline",
        "surface",
        "on_surface",
        "navigation_indicator",
        "divider",
        "hero_bg",
    )
}


def _visible_items(folder_list):
    return [
        item.title.value
        if isinstance(item, ft.ListTile)
        else f"placeholder:{item.content.value}"
        for item in folder_list.controls
    ]


class FakePage:
    """Records what the dialog shows on every repaint."""

    def __init__(self):
        self.picker = None
        self.tasks = []
        self.frames = []

    def _snapshot(self, label):
        self.frames.append(
            (
                label,
                self.picker._loading.visible,
                _visible_items(self.picker._folder_list),
            )
        )

    def show_dialog(self, dialog):
        del dialog
        self._snapshot("open")

    def pop_dialog(self):
        pass

    def run_task(self, handler, *args):
        self.tasks.append(handler(*args))

    def update(self):
        self._snapshot("update")


class FakeAccountService:
    def list_accounts(self):
        return [
            {"id": 1, "google_account_email": "user@example.com", "folder_id": None}
        ]

    def set_account_folder(self, *args):
        pass


class FakeValidationController:
    async def validate(self, account):
        del account
        await asyncio.sleep(0)
        return "valid", "token"


class FakeFolderService:
    def __init__(self, folders):
        self.folders = folders

    async def list(self, access_token, parent_id):
        del access_token, parent_id
        await asyncio.sleep(0)
        return self.folders


def _build_picker(page, folders):
    picker = GoogleDriveFolderPicker(
        page,
        COLORS,
        FakeAccountService(),
        None,
        FakeFolderService(folders),
        FakeValidationController(),
        lambda *args, **kwargs: None,
        {},
    )
    page.picker = picker
    return picker


def _open(page, picker):
    picker.open(1)(None)
    asyncio.run(_drain(page))


async def _drain(page):
    await asyncio.gather(*page.tasks)
    page.tasks.clear()


def test_reopening_the_picker_never_shows_the_previous_empty_state():
    page = FakePage()
    picker = _build_picker(page, [])
    _open(page, picker)

    picker._folder_service = FakeFolderService(
        [{"id": "a", "name": "Respaldos"}, {"id": "b", "name": "Fotos"}]
    )
    page.frames.clear()
    _open(page, picker)

    shown_while_loading = [items for _, _, items in page.frames[:-1]]
    assert all(items == [] for items in shown_while_loading), page.frames
    assert page.frames[-1][2] == ["Respaldos", "Fotos"]


def test_the_spinner_stays_until_the_folders_are_painted():
    page = FakePage()
    picker = _build_picker(page, [{"id": "a", "name": "Respaldos"}])

    _open(page, picker)

    for label, spinning, items in page.frames[:-1]:
        assert spinning, (label, page.frames)
        assert items == [], (label, page.frames)
    assert page.frames[-1] == ("update", False, ["Respaldos"])


def test_the_empty_placeholder_only_appears_once_the_load_finished():
    page = FakePage()
    picker = _build_picker(page, [])

    _open(page, picker)

    assert all(items == [] for _, _, items in page.frames[:-1]), page.frames
    assert page.frames[-1] == ("update", False, ["placeholder:No hay subcarpetas"])
