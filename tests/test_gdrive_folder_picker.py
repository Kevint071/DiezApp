import asyncio

import flet as ft

from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderError,
)
from diezapp.features.google_drive.application.validate_drive_account import (
    DRIVE_FOLDER_MIME_TYPE,
)
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
        "input_border",
        "input_focused",
        "card_bg",
        "error",
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
        self.popped = 0

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
        self.popped += 1

    def run_task(self, handler, *args):
        self.tasks.append(handler(*args))

    def update(self):
        self._snapshot("update")


class FakeAccountService:
    def __init__(self):
        self.saved = []

    def list_accounts(self):
        return [
            {"id": 1, "google_account_email": "user@example.com", "folder_id": None}
        ]

    def set_account_folder(self, *args):
        self.saved.append(args)


class FakeValidationController:
    def __init__(self):
        self.calls = 0

    async def validate(self, account):
        del account
        self.calls += 1
        await asyncio.sleep(0)
        return "valid", "token"


class FakeRefreshAccessToken:
    def __init__(self):
        self.calls = 0

    async def execute(self, account):
        del account
        self.calls += 1
        await asyncio.sleep(0)
        return "token"


class FakeFolderService:
    def __init__(self, folders):
        self.folders = folders
        self.missing = set()
        self.list_calls = 0
        self.create_calls = 0

    async def list(self, access_token, parent_id):
        del access_token, parent_id
        self.list_calls += 1
        await asyncio.sleep(0)
        return list(self.folders)

    async def create(self, access_token, folder_name, parent_id):
        del access_token, parent_id
        self.create_calls += 1
        await asyncio.sleep(0)
        return f"new-{self.create_calls}"

    async def get(self, access_token, folder_id):
        del access_token
        await asyncio.sleep(0)
        if folder_id in self.missing:
            raise DriveFolderError("Not found", status_code=404, reason="notFound")
        name = next(
            (item["name"] for item in self.folders if item["id"] == folder_id),
            folder_id,
        )
        return {
            "id": folder_id,
            "name": name,
            "mimeType": DRIVE_FOLDER_MIME_TYPE,
            "trashed": False,
        }


def _build_picker(page, folders):
    picker = GoogleDriveFolderPicker(
        page,
        COLORS,
        FakeAccountService(),
        FakeRefreshAccessToken(),
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
    picker._folders_loaded = False
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


def test_opening_after_a_prefetch_paints_the_folders_without_asking_drive_again():
    page = FakePage()
    picker = _build_picker(page, [{"id": "a", "name": "Respaldos"}])

    picker.prefetch(1)
    asyncio.run(_drain(page))
    page.frames.clear()

    picker.open(1)(None)

    assert picker._folder_service.list_calls == 1
    assert page.tasks == []
    assert page.frames == [("open", False, ["Respaldos"])]


def test_opening_while_the_prefetch_is_in_flight_only_asks_drive_once():
    page = FakePage()
    picker = _build_picker(page, [{"id": "a", "name": "Respaldos"}])

    picker.prefetch(1)
    picker.open(1)(None)
    asyncio.run(_drain(page))

    assert picker._folder_service.list_calls == 1
    assert page.frames[-1][2] == ["Respaldos"]


def test_using_a_deleted_folder_explains_it_in_the_dialog_and_reloads_the_list():
    page = FakePage()
    picker = _build_picker(
        page, [{"id": "a", "name": "Respaldos"}, {"id": "b", "name": "Fotos"}]
    )
    _open(page, picker)
    picker._select_folder({"id": "b", "name": "Fotos"})

    picker._folder_service.missing.add("b")
    picker._folder_service.folders = [{"id": "a", "name": "Respaldos"}]
    page.frames.clear()
    picker._use_button.on_click(None)
    asyncio.run(_drain(page))

    assert page.popped == 0
    assert picker._error_banner.visible is True
    assert "Fotos" in picker._error_text.value
    assert "no existe" in picker._error_text.value
    assert page.frames[-1][2] == ["Respaldos"]
    assert picker._account_service.saved == []


def test_using_a_folder_that_still_exists_saves_it_and_closes_the_dialog():
    page = FakePage()
    picker = _build_picker(page, [{"id": "a", "name": "Respaldos"}])
    _open(page, picker)
    picker._select_folder({"id": "a", "name": "Respaldos"})

    picker._use_button.on_click(None)
    asyncio.run(_drain(page))

    assert picker._account_service.saved == [(1, "a", "Respaldos")]
    assert page.popped == 1
    assert picker._error_banner.visible is False


def test_double_clicking_create_folder_only_creates_it_once():
    page = FakePage()
    picker = _build_picker(page, [])
    _open(page, picker)
    picker._name_field.value = "Respaldos DiezApp"

    page.run_task(picker._create_folder, None)
    page.run_task(picker._create_folder, None)
    asyncio.run(_drain(page))

    assert picker._folder_service.create_calls == 1
    assert len(picker._current_folders) == 1
    assert page.popped == 1


def test_reopening_after_a_check_was_left_in_flight_re_enables_the_use_button():
    page = FakePage()
    picker = _build_picker(page, [{"id": "a", "name": "Respaldos"}])
    _open(page, picker)
    picker._busy = True

    _open(page, picker)
    picker._select_folder({"id": "a", "name": "Respaldos"})

    assert picker._use_button.disabled is False
