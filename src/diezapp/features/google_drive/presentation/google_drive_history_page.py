"""The "Copias realizadas" screen for a single linked Drive account.

A flat log of every copy in the account's Drive folder, newest first, cut into
pages. Screen-level options (refresh, page size) live in the app bar rather
than in a strip above the list, so the content area is nothing but the log;
the pager is pinned above the thumb instead of trailing the list, so moving
through a long history never means scrolling to find the controls. Only one
page of rows is ever built, which is what keeps a large account from landing
on Flet all at once.
"""

import math

import flet as ft

from diezapp.infrastructure.google.drive_client import list_backup_files
from diezapp.shared.datetime_utils import local_now, to_local_datetime
from diezapp.shared.presentation.byte_format import format_bytes, total_bytes
from diezapp.shared.presentation.date_labels import clock, short_date
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)

STALE_AFTER_DAYS = 7
PAGE_SIZES = (5, 10, 20, 50)
DEFAULT_PAGE_SIZE = 10


def _parse_time(file):
    raw = file.get("modifiedTime") or file.get("createdTime")
    if not raw:
        return None
    try:
        return to_local_datetime(raw)
    except TypeError, ValueError:
        return None


def _newest_first(files):
    """Sort descending by date; undated copies sink to the end.

    Trailing them keeps the dated run contiguous, so page N always covers a
    real slice of time.
    """
    entries = [(file, _parse_time(file)) for file in files]
    dated = sorted(
        (e for e in entries if e[1] is not None), key=lambda e: e[1], reverse=True
    )
    undated = [e for e in entries if e[1] is None]
    return dated + undated


def _row_date(moment):
    """``lun 17 ago 2026`` — always carrying the year, never abbreviated away.

    A history that spans years is unreadable without it, and the copies of a
    single day differ only by the clock, so the year costs nothing to scan.
    """
    return f"{short_date(moment)} {moment.year}"


def build_google_drive_history_view(
    page: ft.Page,
    colors_fn,
    account_id,
    account_service,
    refresh_access_token,
    navigate_to_detail,
):
    """Return ``(content, appbar_actions)``.

    The view owns its app-bar actions because they drive its own state; the
    route builder just hands them to the shared app bar.
    """
    colors = colors_fn(page)
    account = next(
        (item for item in account_service.list_accounts() if item["id"] == account_id),
        None,
    )
    body = ft.Column(spacing=0)
    state = {"entries": [], "page": 0, "size": DEFAULT_PAGE_SIZE}

    # ── Primitives ────────────────────────────────────────
    def hairline():
        # `divider` collapses into `card_bg` in dark mode, so in-card separators
        # use `outline`, which keeps contrast in both themes.
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16),
            content=ft.Divider(height=1, thickness=1, color=colors["outline"]),
        )

    def card(*controls, padding_v=6):
        return ft.Container(
            bgcolor=colors["card_bg"],
            border_radius=16,
            padding=ft.Padding.symmetric(vertical=padding_v, horizontal=0),
            content=ft.Column(spacing=0, controls=list(controls)),
        )

    def badge(icon, size=48, fg=None, bg=None):
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=bg or colors["hero_bg"],
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon, size=size * 0.5, color=fg or colors["primary"]),
        )

    def caption(value, color=None, size=12):
        return ft.Text(value, size=size, color=color or colors["on_surface_variant"])

    # ── Row: the clock leads, because same-day copies differ only by it ──
    def backup_row(file, moment, is_last):
        title = _row_date(moment) if moment else file.get("name", "Copia sin fecha")
        row = ft.Container(
            padding=ft.Padding.symmetric(vertical=10, horizontal=14),
            on_click=lambda e: navigate_to_detail(account, file),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=58,
                        height=40,
                        border_radius=10,
                        bgcolor=colors["hero_bg"],
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            clock(moment) if moment else "--:--",
                            size=14,
                            weight=ft.FontWeight.W_700,
                            color=colors["primary"],
                        ),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(
                                title,
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color=colors["on_surface"],
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            caption(format_bytes(file.get("size")), size=11.5),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=20,
                        color=colors["on_surface_variant"],
                    ),
                ],
            ),
        )
        if is_last:
            return row
        return ft.Column(spacing=0, controls=[row, hairline()])

    list_column = ft.Column(spacing=0)

    # ── Pinned pager: thumb-reachable, never scrolled away ─
    page_label = ft.Text(
        "", size=13, weight=ft.FontWeight.W_700, color=colors["on_surface"]
    )
    range_label = caption("", size=11)

    def nav_button(icon, delta, tooltip):
        return ft.Container(
            width=46,
            height=46,
            border_radius=23,
            alignment=ft.Alignment.CENTER,
            tooltip=tooltip,
            animate=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
            on_click=lambda e: go(delta),
            content=ft.Icon(icon, size=22),
        )

    prev_button = nav_button(ft.Icons.CHEVRON_LEFT_ROUNDED, -1, "Página anterior")
    next_button = nav_button(ft.Icons.CHEVRON_RIGHT_ROUNDED, 1, "Página siguiente")

    def paint_nav(control, enabled):
        # Disabled reads as a flat, low-contrast well rather than a filled
        # button, so the state is carried by shape and not by colour alone.
        control.disabled = not enabled
        control.bgcolor = colors["primary"] if enabled else colors["divider"]
        control.content.color = (
            colors["on_primary"] if enabled else colors["on_surface_variant"]
        )

    pager = ft.Container(
        visible=False,
        bgcolor=colors["surface"],
        border=ft.Border.only(top=ft.BorderSide(1, colors["outline"])),
        padding=ft.Padding.symmetric(vertical=10, horizontal=16),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                prev_button,
                ft.Column(
                    expand=True,
                    spacing=1,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[page_label, range_label],
                ),
                next_button,
            ],
        ),
    )

    # ── App-bar actions: screen options belong here, not over the list ──
    size_menu_items = []

    def size_menu():
        for value in PAGE_SIZES:
            size_menu_items.append(
                ft.PopupMenuItem(
                    content=ft.Text(f"{value} por página"),
                    checked=value == DEFAULT_PAGE_SIZE,
                    on_click=lambda e, v=value: set_size(v),
                )
            )
        return ft.PopupMenuButton(
            icon=ft.Icons.TUNE_ROUNDED,
            icon_color=colors["on_surface_variant"],
            icon_size=20,
            tooltip="Copias por página",
            items=size_menu_items,
        )

    appbar_actions = [
        ft.IconButton(
            ft.Icons.REFRESH,
            icon_size=20,
            icon_color=colors["on_surface_variant"],
            tooltip="Actualizar",
            on_click=lambda e: page.run_task(load_backups),
        ),
        size_menu(),
        ft.Container(width=4),
    ]

    def paint_menu():
        for item, value in zip(size_menu_items, PAGE_SIZES):
            item.checked = value == state["size"]

    # ── Paging ────────────────────────────────────────────
    def total_pages():
        return max(1, math.ceil(len(state["entries"]) / state["size"]))

    def paint_page():
        pages = total_pages()
        state["page"] = max(0, min(state["page"], pages - 1))
        start = state["page"] * state["size"]
        window = state["entries"][start : start + state["size"]]
        list_column.controls = [
            backup_row(file, moment, index == len(window) - 1)
            for index, (file, moment) in enumerate(window)
        ]
        page_label.value = f"Página {state['page'] + 1} de {pages}"
        range_label.value = (
            f"{start + 1}–{start + len(window)} de {len(state['entries'])}"
        )
        paint_nav(prev_button, state["page"] > 0)
        paint_nav(next_button, state["page"] < pages - 1)
        pager.visible = pages > 1

    def scroll_to_top():
        # `scroll_to` is a coroutine in Flet, so it has to be handed to the
        # loop — calling it from a sync handler would silently do nothing.
        page.run_task(scroll_column.scroll_to, offset=0, duration=260)

    def go(delta):
        state["page"] = max(0, min(total_pages() - 1, state["page"] + delta))
        paint_page()
        page.update()
        # A new page starts at its first row, not wherever the old one was left.
        scroll_to_top()

    def set_size(value):
        if value == state["size"]:
            return
        # Keep the row the user is looking at on screen instead of snapping
        # back to page 1.
        first = state["page"] * state["size"]
        state["size"] = value
        state["page"] = first // value
        paint_menu()
        paint_page()
        page.update()
        scroll_to_top()

    def summary_strip(files):
        count = len(files)
        return ft.Container(
            padding=ft.Padding.only(left=4, top=12, bottom=2),
            content=ft.Text(
                f"{count} {'copia' if count == 1 else 'copias'} · "
                f"{format_bytes(total_bytes(files))} en total",
                size=12,
                color=colors["on_surface_variant"],
            ),
        )

    def stale_banner():
        return ft.Container(
            margin=ft.Margin.only(top=10),
            padding=ft.Padding.symmetric(vertical=10, horizontal=12),
            border_radius=12,
            bgcolor=colors["warning_bg"],
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(
                        ft.Icons.WARNING_AMBER_ROUNDED,
                        size=16,
                        color=colors["warning"],
                    ),
                    ft.Text(
                        "Hace más de una semana que no respaldas",
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=colors["warning"],
                        expand=True,
                    ),
                ],
            ),
        )

    # ── States ────────────────────────────────────────────
    def placeholder(height, width=None, radius=8):
        return ft.Container(
            height=height,
            width=width,
            border_radius=radius,
            bgcolor=colors["outline"],
        )

    def skeleton():
        return ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=4, top=12, bottom=14),
                    content=placeholder(11, 150),
                ),
                card(
                    *[
                        ft.Container(
                            padding=ft.Padding.symmetric(vertical=10, horizontal=14),
                            content=ft.Row(
                                spacing=12,
                                controls=[
                                    placeholder(40, 58, radius=10),
                                    ft.Column(
                                        expand=True,
                                        spacing=7,
                                        controls=[
                                            placeholder(12, 128),
                                            placeholder(10, 64),
                                        ],
                                    ),
                                ],
                            ),
                        )
                        for _ in range(6)
                    ]
                ),
            ],
        )

    def message_state(icon, title, message, tone=None, action=None):
        controls = [
            badge(
                icon,
                size=64,
                fg=tone or colors["on_surface_variant"],
                bg=colors["divider"],
            ),
            ft.Container(height=16),
            ft.Text(
                title,
                size=16,
                weight=ft.FontWeight.W_600,
                color=colors["on_surface"],
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=6),
            ft.Text(
                message,
                size=13,
                color=colors["on_surface_variant"],
                text_align=ft.TextAlign.CENTER,
            ),
        ]
        if action is not None:
            controls.extend([ft.Container(height=20), action])
        return ft.Container(
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=56, left=24, right=24),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                controls=controls,
            ),
        )

    def retry_button():
        return ft.FilledTonalButton(
            "Reintentar",
            icon=ft.Icons.REFRESH,
            on_click=lambda e: page.run_task(load_backups),
        )

    # ── Assembly ──────────────────────────────────────────
    def render(files):
        state["entries"] = _newest_first(files)
        state["page"] = 0
        controls = [summary_strip(files)]
        newest = max((moment for _, moment in state["entries"] if moment), default=None)
        if newest is not None and (local_now() - newest).days >= STALE_AFTER_DAYS:
            controls.append(stale_banner())
        controls.append(
            ft.Container(
                padding=ft.Padding.only(top=10, bottom=20),
                content=card(list_column),
            )
        )
        paint_menu()
        paint_page()
        return controls

    async def load_backups():
        pager.visible = False
        body.controls = [skeleton()]
        page.update()
        try:
            token = await refresh_access_token.execute(account)
            if not token:
                raise ValueError("sin token")
            files = await list_backup_files(token, account["folder_id"])
        except Exception:  # noqa: BLE001 - any Drive failure is the same to the user
            body.controls = [
                message_state(
                    ft.Icons.CLOUD_OFF_OUTLINED,
                    "No se pudo leer la carpeta",
                    "Revisa tu conexión o vuelve a vincular la cuenta de Google Drive.",
                    tone=colors["error"],
                    action=retry_button(),
                )
            ]
            page.update()
            return
        if not files:
            body.controls = [
                message_state(
                    ft.Icons.INBOX_OUTLINED,
                    "Todavía no hay copias",
                    "Usa «Respaldar ahora» en la cuenta para guardar tu primera "
                    "copia en Google Drive.",
                    action=retry_button(),
                )
            ]
        else:
            body.controls = render(files)
        page.update()

    if account is None:
        body.controls = [
            message_state(
                ft.Icons.PERSON_OFF_OUTLINED,
                "Cuenta no encontrada",
                "Vuelve atrás y elige una cuenta vinculada.",
                tone=colors["error"],
            )
        ]
    elif not account.get("folder_id"):
        body.controls = [
            message_state(
                ft.Icons.FOLDER_OFF_OUTLINED,
                "Falta la carpeta de respaldo",
                "Elige una carpeta de Google Drive en la cuenta para empezar a "
                "guardar copias.",
            )
        ]
    else:
        page.run_task(load_backups)

    divider = build_scroll_divider()
    scroll_column = ft.Column(
        expand=True,
        scroll=ft.Scrollbar(thickness=6, radius=4),
        on_scroll=make_scroll_divider_handler(divider, colors),
        controls=[
            ft.Container(margin=ft.Margin.symmetric(horizontal=20), content=body)
        ],
    )
    content = ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[divider, scroll_column, pager],
            ),
        ),
    )
    return content, appbar_actions
