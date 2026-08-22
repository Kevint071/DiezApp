"""Route builders for the Google Drive feature's own views.

Kept in the feature package (rather than the composition root) so the app's
navigation wiring in bootstrap/composition.py doesn't need to know how the
Google Drive screens are put together.
"""

import flet as ft

from diezapp.features.google_drive.presentation.google_drive_page import (
    build_google_drive_account_view,
    build_google_drive_backup_detail_view,
    build_google_drive_history_view,
    build_google_drive_view,
)
from diezapp.navigation import routes
from diezapp.navigation.route_context import RouteContext


def build_google_drive_route(ctx: RouteContext) -> ft.View:
    dependencies = ctx.dependencies
    content = build_google_drive_view(
        ctx.page,
        ctx.colors_fn,
        dependencies.google_drive_link,
        dependencies.google_drive_oauth,
        lambda account_id: (
            ctx.page.session.store.set("gdrive_account_id", account_id),
            ctx.page.navigate(routes.GOOGLE_DRIVE_ACCOUNT),
        )[-1],
    )
    return ft.View(
        route=routes.GOOGLE_DRIVE,
        padding=0,
        appbar=ctx.build_appbar(
            "Copias de seguridad", show_back=True, back_route=routes.SETTINGS
        ),
        controls=[content],
    )


def build_google_drive_history_route(ctx: RouteContext) -> ft.View:
    dependencies = ctx.dependencies

    def navigate_to_detail(account, file):
        ctx.page.session.store.set(
            "gdrive_backup_detail", {"account": account, "file": file}
        )
        ctx.page.navigate(routes.GOOGLE_DRIVE_BACKUP_DETAIL)

    return ft.View(
        route=routes.GOOGLE_DRIVE_HISTORY,
        padding=0,
        appbar=ctx.build_appbar(
            "Copias realizadas", show_back=True, back_route=routes.GOOGLE_DRIVE
        ),
        controls=[
            build_google_drive_history_view(
                ctx.page,
                ctx.colors_fn,
                dependencies.google_drive_link,
                dependencies.google_drive_refresh_token,
                dependencies.local_backup,
                dependencies.calculations,
                dependencies.notes,
                dependencies.conflicts,
                navigate_to_detail,
            )
        ],
    )


def build_google_drive_backup_detail_route(ctx: RouteContext) -> ft.View:
    dependencies = ctx.dependencies
    detail = ctx.page.session.store.get("gdrive_backup_detail") or {}
    account = detail.get("account")
    file = detail.get("file")
    if account is None or file is None:
        return build_google_drive_history_route(ctx)

    return ft.View(
        route=routes.GOOGLE_DRIVE_BACKUP_DETAIL,
        padding=0,
        appbar=ctx.build_appbar(
            "Detalle de copia",
            show_back=True,
            back_route=routes.GOOGLE_DRIVE_HISTORY,
        ),
        controls=[
            build_google_drive_backup_detail_view(
                ctx.page,
                ctx.colors_fn,
                dependencies.google_drive_refresh_token,
                dependencies.local_backup,
                dependencies.calculations,
                dependencies.notes,
                dependencies.conflicts,
                account,
                file,
                lambda: ctx.page.navigate(routes.GOOGLE_DRIVE_HISTORY),
            )
        ],
    )


def build_google_drive_account_route(ctx: RouteContext) -> ft.View:
    dependencies = ctx.dependencies
    content = build_google_drive_account_view(
        ctx.page,
        ctx.colors_fn,
        ctx.page.session.store.get("gdrive_account_id"),
        dependencies.google_drive_link,
        dependencies.google_drive_refresh_token,
        dependencies.google_drive_folders,
        dependencies.google_drive_account_validator,
        dependencies.google_drive_schedule_settings,
        dependencies.google_drive_backup,
        lambda: ctx.page.navigate(routes.GOOGLE_DRIVE),
        lambda: ctx.page.navigate(routes.GOOGLE_DRIVE_HISTORY),
        ctx.show_snack,
    )
    return ft.View(
        route=routes.GOOGLE_DRIVE_ACCOUNT,
        padding=0,
        appbar=ctx.build_appbar(
            "Cuenta de respaldo",
            show_back=True,
            back_route=routes.GOOGLE_DRIVE,
        ),
        controls=[content],
    )
