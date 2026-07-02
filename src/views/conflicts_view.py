import flet as ft
from datetime import datetime

from utils.conflicts import load_conflicts, save_conflicts, clear_conflicts
from utils.storage import load_calculations, save_calculations
from utils.theme import ON_SURFACE_LIGHT, ON_SURFACE_DARK

# Persistent resolution state across navigations
_conflict_choices: dict = {}
_conflict_resolved: set = set()
_conflict_fingerprint: list = []


def _reset_conflict_state() -> None:
    global _conflict_choices, _conflict_resolved, _conflict_fingerprint
    _conflict_choices = {}
    _conflict_resolved = set()
    _conflict_fingerprint = []


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _format_date(date_str: str) -> str:
    try:
        d = datetime.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return "Sin fecha"


def _apply_appbar(page: ft.Page, title: str, on_back):
    light = page.theme_mode == ft.ThemeMode.LIGHT
    fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
    page.appbar = ft.AppBar(
        leading=ft.Container(
            width=40,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: on_back(),
            content=ft.Image(
                src="chevron-left.svg",
                width=24,
                height=24,
                color=fg,
            ),
        ),
        title=ft.Text(
            title,
            color=fg,
            weight=ft.FontWeight.W_700,
            size=17,
        ),
        center_title=False,
        leading_width=40,
        title_spacing=0,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
    )


def apply_conflicts_appbar(page: ft.Page, on_back):
    _apply_appbar(page, "Resolver conflictos", on_back)


# ═══════════════════════════════════════════════════════════════════
# Detail view — shows comparison for a single conflict
# ═══════════════════════════════════════════════════════════════════

def _build_conflict_detail_view(page: ft.Page, colors_fn, index: int, conflicts: list, choices: dict, resolved_set: set, on_back_to_grid):
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT
    conflict = conflicts[index]
    existing = conflict["existing"]
    imported = conflict["imported"]

    selected = {"version": choices.get(index, "existing")}

    green_bg = "#059669" if light else "#34D399"
    green_fg = "#FFFFFF" if light else "#064E3B"
    fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK

    def _save_choice(e):
        choices[index] = selected["version"]
        resolved_set.add(index)
        on_back_to_grid()

    save_btn = ft.FilledButton(
        "Guardar",
        on_click=_save_choice,
        style=ft.ButtonStyle(
            bgcolor=green_bg,
            color=green_fg,
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.Padding.symmetric(vertical=8, horizontal=16),
            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_700),
            elevation=0,
        ),
    )

    page.appbar = ft.AppBar(
        leading=ft.Container(
            width=40,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: on_back_to_grid(),
            content=ft.Image(src="chevron-left.svg", width=24, height=24, color=fg),
        ),
        title=ft.Text(f"Conflicto {index + 1}", color=fg, weight=ft.FontWeight.W_700, size=17),
        center_title=False,
        leading_width=40,
        title_spacing=0,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
        actions=[ft.Container(padding=ft.Padding.only(right=12), content=save_btn)],
    )

    cards_column = ft.Column(spacing=16)

    def _build_card(title: str, calc: dict, version: str):
        is_selected = selected["version"] == version
        amount = calc.get("amount", 0)
        envio = calc.get("envio_21", 0)
        fondo = calc.get("fondo_local", 0)
        sost = calc.get("sostenimiento", 0)
        fund_pct = calc.get("fund_percentage", 1)
        date_str = _format_date(calc.get("created_at", ""))

        def _row(label: str, value: str):
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=8, horizontal=16),
                border=ft.Border(bottom=ft.BorderSide(1, c["divider"])),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(label, size=13, color=c["on_surface_variant"]),
                        ft.Text(value, size=13, weight=ft.FontWeight.W_600, color=c["on_surface"]),
                    ],
                ),
            )

        def _on_tap(e):
            selected["version"] = version
            _refresh_cards()

        radio_icon = ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED
        radio_color = c["primary"] if is_selected else c["on_surface_variant"]
        border_color = c["primary"] if is_selected else ft.Colors.TRANSPARENT

        return ft.Container(
            bgcolor=c["card_bg"],
            border_radius=16,
            border=ft.Border.all(2, border_color),
            padding=ft.Padding.only(top=16, bottom=12),
            on_click=_on_tap,
            ink=True,
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=16),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(title, size=15, weight=ft.FontWeight.W_700, color=c["on_surface"]),
                                ft.Icon(radio_icon, size=22, color=radio_color),
                            ],
                        ),
                    ),
                    ft.Container(height=8),
                    _row("Monto", _format_currency(amount)),
                    _row("Envio (21%)", _format_currency(envio)),
                    _row("Fondo local", _format_currency(fondo)),
                    _row("Sostenimiento", _format_currency(sost)),
                    _row("Porcentaje fondo", f"{fund_pct}%"),
                    ft.Container(
                        padding=ft.Padding.symmetric(vertical=8, horizontal=16),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Fecha", size=13, color=c["on_surface_variant"]),
                                ft.Text(date_str, size=13, weight=ft.FontWeight.W_600, color=c["on_surface"]),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _refresh_cards():
        cards_column.controls = [
            _build_card("Version actual", existing, "existing"),
            _build_card("Version importada", imported, "imported"),
        ]
        page.update()

    _refresh_cards()

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                controls=[cards_column],
            ),
        ),
    )


# ═══════════════════════════════════════════════════════════════════
# Grid view — numbered tiles for each conflict
# ═══════════════════════════════════════════════════════════════════

def build_conflicts_view(page: ft.Page, colors_fn, on_back):
    c = colors_fn(page)
    data = load_conflicts()
    conflicts = data.get("conflicts", [])
    pending_add = data.get("pending_add", [])

    if not conflicts:
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(top=80, left=24, right=24, bottom=24),
                alignment=ft.Alignment.TOP_CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, size=48, color=c["primary"]),
                        ft.Container(height=12),
                        ft.Text(
                            "Sin conflictos",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=c["on_surface"],
                        ),
                        ft.Text(
                            "No hay conflictos pendientes por resolver",
                            size=13,
                            color=c["on_surface_variant"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
        )

    global _conflict_choices, _conflict_resolved, _conflict_fingerprint
    current_fp = [conflict.get("existing", {}).get("id") for conflict in conflicts]
    if current_fp != _conflict_fingerprint:
        _conflict_fingerprint = current_fp
        _conflict_choices = {i: "existing" for i in range(len(conflicts))}
        _conflict_resolved = set()
    choices = _conflict_choices
    resolved_set = _conflict_resolved

    def _navigate_to_detail(index: int):
        _apply_appbar(page, f"Conflicto {index + 1}", _show_grid)
        page.controls.clear()
        page.add(_build_conflict_detail_view(page, colors_fn, index, conflicts, choices, resolved_set, _show_grid))

    def _show_grid():
        apply_conflicts_appbar(page, on_back)
        page.controls.clear()
        page.add(_build_grid_content())

    def _build_grid_content():
        tiles = []
        for i in range(len(conflicts)):
            is_resolved = i in resolved_set
            tile_bg = ft.Colors.with_opacity(0.08, c["primary"]) if is_resolved else c["card_bg"]

            tile = ft.Container(
                width=72,
                height=72,
                bgcolor=tile_bg,
                border_radius=16,
                border=ft.Border.all(2, c["primary"]) if is_resolved else None,
                alignment=ft.Alignment.CENTER,
                on_click=lambda e, idx=i: _navigate_to_detail(idx),
                ink=True,
                content=ft.Column(
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            str(i + 1),
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=c["primary"] if is_resolved else c["on_surface"],
                        ),
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE_ROUNDED if is_resolved else ft.Icons.CIRCLE_OUTLINED,
                            size=14,
                            color=c["primary"] if is_resolved else c["on_surface_variant"],
                        ),
                    ],
                ),
            )
            tiles.append(tile)

        # Grid rows of 4
        rows = []
        for i in range(0, len(tiles), 4):
            row_tiles = tiles[i:i + 4]
            rows.append(
                ft.Row(
                    spacing=12,
                    alignment=ft.MainAxisAlignment.START,
                    controls=row_tiles,
                )
            )

        # Header
        header = ft.Container(
            padding=ft.Padding.only(bottom=20),
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Container(
                        width=44,
                        height=44,
                        border_radius=14,
                        bgcolor=ft.Colors.with_opacity(0.1, c["primary"]),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.SYNC_PROBLEM_ROUNDED, color=c["primary"], size=22),
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                f"{len(conflicts)} conflicto{'s' if len(conflicts) > 1 else ''}",
                                size=16,
                                weight=ft.FontWeight.W_700,
                                color=c["on_surface"],
                            ),
                            ft.Text(
                                "Toca cada número para comparar",
                                size=13,
                                color=c["on_surface_variant"],
                            ),
                        ],
                    ),
                ],
            ),
        )

        # Progress
        n_resolved = len(resolved_set)
        progress_text = ft.Text(
            f"{n_resolved} de {len(conflicts)} resueltos",
            size=13,
            weight=ft.FontWeight.W_500,
            color=c["primary"] if n_resolved == len(conflicts) else c["on_surface_variant"],
        )

        # Buttons
        has_resolved = n_resolved > 0

        resolve_btn = ft.FilledButton(
            "Aplicar cambios",
            icon=ft.Icons.CHECK_ROUNDED,
            disabled=not has_resolved,
            on_click=_resolve_all,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=14, horizontal=20),
                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
            ),
            width=float("inf"),
        )

        discard_btn = ft.OutlinedButton(
            "Descartar importación",
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            on_click=_discard_all,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=14, horizontal=20),
                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
            ),
            width=float("inf"),
        )

        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        header,
                        ft.Column(spacing=12, controls=rows),
                        ft.Container(height=4),
                        progress_text,
                        ft.Container(expand=True),
                        resolve_btn,
                        discard_btn,
                    ],
                ),
            ),
        )

    def _resolve_all(e):
        existing_calcs = load_calculations()
        existing_map = {calc["id"]: calc for calc in existing_calcs if "id" in calc}

        unresolved = []
        n_applied = 0
        for i, conflict in enumerate(conflicts):
            if i in resolved_set:
                calc_id = conflict["existing"]["id"]
                choice = choices.get(i, "existing")
                if choice == "imported":
                    existing_map[calc_id] = conflict["imported"]
                n_applied += 1
            else:
                unresolved.append(conflict)

        resolved = [existing_map.get(calc.get("id"), calc) for calc in existing_calcs]

        if not unresolved:
            resolved = resolved + pending_add
            save_calculations(resolved)
            clear_conflicts()
            msg = f"{n_applied} conflictos resueltos, {len(pending_add)} nuevos agregados"
        else:
            save_calculations(resolved)
            save_conflicts(unresolved, pending_add)
            msg = f"{n_applied} resueltos, {len(unresolved)} pendientes"

        snack = ft.SnackBar(content=ft.Text(msg), open=True)
        page.overlay.append(snack)
        _reset_conflict_state()
        on_back()

    def _discard_all(e):
        clear_conflicts()
        snack = ft.SnackBar(content=ft.Text("Importación descartada"), open=True)
        page.overlay.append(snack)
        _reset_conflict_state()
        on_back()

    return _build_grid_content()
