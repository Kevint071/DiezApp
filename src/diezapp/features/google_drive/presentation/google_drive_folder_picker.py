from collections.abc import Callable

import flet as ft

from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderError,
    DriveFolderService,
)
from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)
from diezapp.features.google_drive.presentation.google_drive_account_validation import (
    GoogleDriveAccountValidationController,
)


class GoogleDriveFolderPicker:
    def __init__(
        self,
        page: ft.Page,
        colors: dict,
        account_service,
        refresh_access_token: RefreshAccessToken,
        folder_service: DriveFolderService,
        validation_controller: GoogleDriveAccountValidationController,
        show_snack: Callable,
        folder_labels: dict,
    ):
        self._page = page
        self._colors = colors
        self._account_service = account_service
        self._refresh_access_token = refresh_access_token
        self._folder_service = folder_service
        self._validation_controller = validation_controller
        self._show_snack = show_snack
        self._folder_labels = folder_labels

        self._dialog_state = {
            "account_id": None,
            "parent_id": "root",
            "parent_name": "Mi unidad",
        }
        self._selection = {"id": None, "name": None}
        self._delete_state = {"active": False, "selected": set()}
        self._current_folders = []
        self._name_field = ft.TextField(label="Nombre de la carpeta")
        self._path = ft.Text("Mi unidad", size=13, color=colors["on_surface_variant"])
        self._loading = ft.ProgressRing(width=22, height=22, visible=False)
        self._folder_list = ft.Column(spacing=0, tight=True, scroll=ft.ScrollMode.AUTO)
        self._folder_actions = ft.Row(spacing=0, controls=[])
        self._use_button = ft.FilledButton(
            "Usar carpeta",
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: colors["primary"],
                    ft.ControlState.DISABLED: colors["outline"],
                },
                color={
                    ft.ControlState.DEFAULT: colors["on_primary"],
                    ft.ControlState.DISABLED: colors["on_surface_variant"],
                },
            ),
        )
        self._use_button.on_click = self._select_current_folder
        self._create_dialog = self._build_create_dialog()
        self._dialog = self._build_dialog()

    def open(self, account_id):
        def _handler(e):
            del e
            self._dialog_state.update(
                account_id=account_id,
                parent_id="root",
                parent_name="Mi unidad",
            )
            self._delete_state["active"] = False
            self._delete_state["selected"].clear()
            self._current_folders.clear()
            self._selection.update(id=None, name=None)
            self._name_field.value = "Respaldos DiezApp"
            self._path.value = "Mi unidad"
            self._update_dialog_actions()
            self._page.show_dialog(self._dialog)
            self._page.run_task(self._load_folder_list)

        return _handler

    def _account(self):
        account_id = self._dialog_state["account_id"]
        return next(
            (a for a in self._account_service.list_accounts() if a["id"] == account_id),
            None,
        )

    async def _load_folder_list(self):
        account = self._account()
        if account is None:
            return
        validation_status, access_token = await self._validation_controller.validate(
            account
        )
        if not access_token or validation_status == "unauthenticated":
            self._show_snack("No se pudo autenticar la cuenta")
            return

        self._dialog_state.update(parent_id="root", parent_name="Mi unidad")
        self._path.value = "Mi unidad"
        self._loading.visible = True
        self._folder_list.controls = []
        self._page.update()
        try:
            folders = await self._folder_service.list(access_token, "root")
        except DriveFolderError as error:
            self._show_folder_error(error)
            return
        finally:
            self._loading.visible = False
            self._page.update()
        self._current_folders[:] = folders
        self._render_folder_list()
        self._page.update()

    def _show_folder_error(self, error: DriveFolderError):
        if error.status_code is not None:
            self._show_snack(
                f"Drive {error.status_code} ({error.reason}): {error.message}"
            )
        else:
            self._show_snack(error.message)

    def _render_folder_list(self):
        if self._delete_state["active"]:
            controls = [
                ft.ListTile(
                    leading=ft.Checkbox(
                        value=folder["id"] in self._delete_state["selected"],
                        on_change=lambda e, folder_id=folder["id"]: (
                            self._delete_state["selected"].add(folder_id)
                            if e.control.value
                            else self._delete_state["selected"].discard(folder_id)
                        ),
                    ),
                    title=ft.Text(folder["name"]),
                )
                for folder in self._current_folders
            ]
        else:
            controls = [
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.FOLDER_OUTLINED, color=self._colors["primary"]
                    ),
                    title=ft.Text(folder["name"]),
                    selected=folder["id"] == self._selection["id"],
                    selected_tile_color=self._colors["navigation_indicator"],
                    on_click=lambda e, item=folder: self._select_folder(item),
                    trailing=ft.Icon(
                        ft.Icons.CHECK,
                        color=self._colors["primary"],
                        visible=folder["id"] == self._selection["id"],
                    ),
                )
                for folder in self._current_folders
            ]
        self._folder_list.controls = controls or [
            ft.Container(
                padding=ft.Padding.symmetric(vertical=16),
                content=ft.Text(
                    "No hay subcarpetas", color=self._colors["on_surface_variant"]
                ),
            )
        ]

    def _set_delete_mode(self, active):
        self._delete_state["active"] = active
        if not active:
            self._delete_state["selected"].clear()
        self._render_folder_list()
        self._update_dialog_actions()
        self._page.update()

    async def _delete_selected_folders(self, e):
        del e
        selected_ids = set(self._delete_state["selected"])
        if not selected_ids:
            self._show_snack("Selecciona al menos una carpeta")
            return
        account = self._account()
        if account is None:
            return
        access_token = await self._refresh_access_token.execute(account)
        if not access_token:
            self._show_snack("No se pudo autenticar la cuenta")
            return
        try:
            for folder_id in selected_ids:
                await self._folder_service.delete(access_token, folder_id)
        except DriveFolderError as error:
            self._show_folder_error(error)
            return
        if account.get("folder_id") in selected_ids:
            self._account_service.set_account_folder(account["id"], None, None)
        self._current_folders[:] = [
            folder
            for folder in self._current_folders
            if folder["id"] not in selected_ids
        ]
        if self._selection["id"] in selected_ids:
            self._selection.update(id=None, name=None)
        self._delete_state["selected"].clear()
        self._delete_state["active"] = False
        self._render_folder_list()
        self._update_dialog_actions()
        self._page.update()
        self._show_snack("Carpetas eliminadas", keep_open=False)

    def _update_dialog_actions(self):
        if self._delete_state["active"]:
            self._folder_actions.controls = [
                ft.IconButton(
                    ft.Icons.CLOSE,
                    tooltip="Cancelar eliminación",
                    icon_color=self._colors["on_surface_variant"],
                    width=48,
                    height=48,
                    padding=0,
                    on_click=lambda e: self._set_delete_mode(False),
                ),
                ft.IconButton(
                    ft.Icons.CHECK,
                    tooltip="Eliminar seleccionadas",
                    icon_color=self._colors["primary"],
                    width=48,
                    height=48,
                    padding=0,
                    on_click=lambda e: self._page.run_task(
                        self._delete_selected_folders, e
                    ),
                ),
            ]
        else:
            self._folder_actions.controls = [
                ft.IconButton(
                    ft.Icons.ADD,
                    tooltip="Crear carpeta",
                    icon_color=self._colors["primary"],
                    width=48,
                    height=48,
                    padding=0,
                    on_click=lambda e: self._open_create_dialog(),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    tooltip="Eliminar carpetas",
                    icon_color=ft.Colors.RED_600,
                    width=48,
                    height=48,
                    padding=0,
                    on_click=lambda e: self._set_delete_mode(True),
                ),
            ]
        self._use_button.disabled = self._selection["id"] is None

    def _select_folder(self, folder):
        if self._selection["id"] == folder["id"]:
            self._selection.update(id=None, name=None)
        else:
            self._selection.update(id=folder["id"], name=folder["name"])
        self._render_folder_list()
        self._update_dialog_actions()
        self._page.update()

    def _select_current_folder(self, e):
        del e
        if self._selection["id"] is None:
            return
        account_id = self._dialog_state["account_id"]
        self._account_service.set_account_folder(
            account_id, self._selection["id"], self._selection["name"]
        )
        self._page.pop_dialog()
        folder_label = self._folder_labels.get(account_id)
        if folder_label:
            folder_label.value = f"Carpeta: {self._selection['name']}"
            folder_label.color = self._colors["on_surface_variant"]
        self._page.update()

    async def _create_folder(self, e):
        del e
        account = self._account()
        folder_name = (self._name_field.value or "").strip()
        if not account or not folder_name:
            self._show_snack("Escribe un nombre para la carpeta")
            return
        access_token = await self._refresh_access_token.execute(account)
        if not access_token:
            self._show_snack("No se pudo autenticar la cuenta")
            return
        try:
            folder_id = await self._folder_service.create(
                access_token, folder_name, self._dialog_state["parent_id"]
            )
        except DriveFolderError as error:
            self._show_folder_error(error)
            return
        self._current_folders.append({"id": folder_id, "name": folder_name})
        self._select_folder(self._current_folders[-1])
        self._name_field.value = ""
        self._page.pop_dialog()
        self._page.update()

    def _build_create_dialog(self):
        return ft.AlertDialog(
            modal=True,
            bgcolor=self._colors["surface"],
            title=ft.Text("Nueva carpeta", color=self._colors["on_surface"]),
            content=self._name_field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._page.pop_dialog()),
                ft.FilledButton("Crear", on_click=self._create_folder),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _open_create_dialog(self):
        self._name_field.value = ""
        self._page.show_dialog(self._create_dialog)

    def _build_dialog(self):
        return ft.AlertDialog(
            bgcolor=self._colors["surface"],
            title=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Seleccionar carpeta",
                                size=17,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                "Elige dónde guardar tus respaldos",
                                size=12,
                                color=self._colors["on_surface_variant"],
                            ),
                            self._path,
                        ],
                    ),
                    self._folder_actions,
                ],
            ),
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[ft.Container(expand=True), self._loading],
                    ),
                    ft.Container(height=260, content=self._folder_list),
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._page.pop_dialog()),
                self._use_button,
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
