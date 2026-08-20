import flet as ft

from diezapp.features.google_drive.application.oauth_flow import GoogleDriveOAuthFlow


def _build_gdrive_backups_section(
    page: ft.Page,
    c: dict,
    show_snack,
    account_service,
    oauth_flow: GoogleDriveOAuthFlow,
    navigate_to_account,
):
    pending_message = page.session.store.get("gdrive_link_message")
    if pending_message:
        page.session.store.remove("gdrive_link_message")
        show_snack(pending_message, keep_open=False)

    accounts = account_service.list_accounts()

    async def _link_account(e):
        del e
        if not oauth_flow.is_configured():
            show_snack("OAuth de Google no configurado")
            return
        started = await oauth_flow.start(page.session.store, page.url)
        if not started:
            show_snack("Ya hay 2 cuentas vinculadas")

    def _account_row(account):
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=4),
            on_click=lambda e, account_id=account["id"]: navigate_to_account(
                account_id
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Icon(
                        ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                        size=26,
                        color=c["primary"],
                    ),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(
                                account["google_account_email"],
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=c["on_surface"],
                            ),
                        ],
                    ),
                    ft.IconButton(
                        ft.Icons.CHEVRON_RIGHT,
                        icon_size=20,
                        tooltip="Ver cuenta",
                        on_click=lambda e, account_id=account["id"]: (
                            navigate_to_account(account_id)
                        ),
                    ),
                ],
            ),
        )

    account_header = ft.Container(
        padding=ft.Padding.only(top=12, bottom=18, left=4, right=4),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text(
                    "Tus cuentas",
                    size=22,
                    weight=ft.FontWeight.W_600,
                    color=c["on_surface"],
                ),
                ft.Text(
                    "Aún no hay cuentas vinculadas"
                    if not accounts
                    else f"{len(accounts)} de 2 cuentas vinculadas",
                    size=13,
                    color=c["on_surface_variant"],
                ),
            ],
        ),
    )

    controls = [account_header]
    if account_service.can_add_account():
        controls.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=12, horizontal=18),
                alignment=ft.Alignment(0, 0),
                content=(
                    ft.FilledButton(
                        "Conectar Google",
                        icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                        on_click=_link_account,
                    )
                    if not accounts
                    else ft.OutlinedButton(
                        "Añadir cuenta", icon=ft.Icons.ADD, on_click=_link_account
                    )
                ),
            )
        )
    if accounts:
        for index, account in enumerate(accounts):
            controls.append(_account_row(account))
            if index < len(accounts) - 1:
                controls.append(ft.Divider(height=1, thickness=1, color=c["divider"]))

    return ft.Column(spacing=0, controls=controls)
