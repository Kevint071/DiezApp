import flet as ft

PRIMARY = "#059669"
PRIMARY_LIGHT = "#10B981"
ON_PRIMARY = "#FFFFFF"
PRIMARY_CONTAINER = "#D1FAE5"
ON_PRIMARY_CONTAINER = "#064E3B"
SURFACE_LIGHT = "#F8FAFC"
SURFACE_VARIANT_LIGHT = "#FFFFFF"
ON_SURFACE_LIGHT = "#1E293B"
ON_SURFACE_VARIANT_LIGHT = "#64748B"
OUTLINE_LIGHT = "#E2E8F0"
OUTLINE_LIGHT_INPUT = "#94A3B8"
DIVIDER_LIGHT = "#F1F5F9"
HEADER_DIVIDER_LIGHT = "#E1E2E4"
SECONDARY = "#0D9488"

SURFACE_DARK = "#0F172A"
SURFACE_VARIANT_DARK = "#1E293B"
ON_SURFACE_DARK = "#F1F5F9"
ON_SURFACE_VARIANT_DARK = "#94A3B8"
OUTLINE_DARK = "#334155"
OUTLINE_DARK_INPUT = "#475569"
DIVIDER_DARK = "#1E293B"
HEADER_DIVIDER_DARK = "#2D323A"
PRIMARY_DARK = "#34D399"
HERO_BG_DARK = "#064E3B"
SECONDARY_DARK = "#2DD4BF"

LIGHT_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=PRIMARY,
        on_primary=ON_PRIMARY,
        primary_container=PRIMARY_CONTAINER,
        on_primary_container=ON_PRIMARY_CONTAINER,
        secondary=SECONDARY,
        surface=SURFACE_LIGHT,
        on_surface=ON_SURFACE_LIGHT,
        on_surface_variant=ON_SURFACE_VARIANT_LIGHT,
        outline=OUTLINE_LIGHT,
        surface_container_highest=SURFACE_VARIANT_LIGHT,
    ),
    system_overlay_style=ft.SystemOverlayStyle(
        system_navigation_bar_color=SURFACE_LIGHT,
        system_navigation_bar_icon_brightness=ft.Brightness.DARK,
        status_bar_color=ft.Colors.TRANSPARENT,
        status_bar_icon_brightness=ft.Brightness.DARK,
    ),
)

DARK_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=PRIMARY_DARK,
        on_primary="#064E3B",
        primary_container=HERO_BG_DARK,
        on_primary_container="#A7F3D0",
        secondary=SECONDARY_DARK,
        surface=SURFACE_DARK,
        on_surface=ON_SURFACE_DARK,
        on_surface_variant=ON_SURFACE_VARIANT_DARK,
        outline=OUTLINE_DARK,
        surface_container_highest=SURFACE_VARIANT_DARK,
    ),
    system_overlay_style=ft.SystemOverlayStyle(
        system_navigation_bar_color=SURFACE_DARK,
        system_navigation_bar_icon_brightness=ft.Brightness.LIGHT,
        status_bar_color=ft.Colors.TRANSPARENT,
        status_bar_icon_brightness=ft.Brightness.LIGHT,
    ),
)

FOCUS_LIGHT = "#64748B"
FOCUS_DARK = "#94A3B8"
ERROR_LIGHT = "#FEE2E2"
ERROR_TEXT_LIGHT = "#DC2626"
ERROR_DARK = "#371520"
ERROR_TEXT_DARK = "#FCA5A5"
APPBAR_BGCOLOR_LIGHT = PRIMARY
APPBAR_BGCOLOR_DARK = "#0a0c10"


def is_light(page: ft.Page) -> bool:
    return page.theme_mode == ft.ThemeMode.LIGHT


def get_colors(page: ft.Page) -> dict:
    light = is_light(page)
    return {
        "surface": SURFACE_LIGHT if light else SURFACE_DARK,
        "surface_variant": SURFACE_VARIANT_LIGHT if light else SURFACE_VARIANT_DARK,
        "on_surface": ON_SURFACE_LIGHT if light else ON_SURFACE_DARK,
        "on_surface_variant": ON_SURFACE_VARIANT_LIGHT
        if light
        else ON_SURFACE_VARIANT_DARK,
        "outline": OUTLINE_LIGHT if light else OUTLINE_DARK,
        "divider": DIVIDER_LIGHT if light else DIVIDER_DARK,
        "header_divider": HEADER_DIVIDER_LIGHT if light else HEADER_DIVIDER_DARK,
        "card_bg": SURFACE_VARIANT_LIGHT if light else SURFACE_VARIANT_DARK,
        "hero_bg": PRIMARY_CONTAINER if light else HERO_BG_DARK,
        "hero_fg": ON_PRIMARY_CONTAINER if light else "#A7F3D0",
        "navigation_indicator": "#DCFCE7" if light else "#064E3B",
        "input_border": OUTLINE_LIGHT_INPUT if light else OUTLINE_DARK_INPUT,
        "input_focused": FOCUS_LIGHT if light else FOCUS_DARK,
        "primary": PRIMARY if light else PRIMARY_DARK,
        "primary_light": PRIMARY_LIGHT if light else "#34D399",
        "summary_total_bg": PRIMARY if light else SURFACE_VARIANT_DARK,
        "summary_total_fg": ON_PRIMARY if light else ON_SURFACE_DARK,
        "summary_total_border": None if light else ft.Border.all(1, PRIMARY_DARK),
        "secondary": SECONDARY if light else SECONDARY_DARK,
        "on_primary": ON_PRIMARY if light else "#F1F5F9",
    }


def get_navigation_bar_style(colors: dict) -> dict:
    return {
        "label_behavior": ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        "elevation": 0,
        "shadow_color": ft.Colors.TRANSPARENT,
        "indicator_color": colors["navigation_indicator"],
        "indicator_shape": ft.RoundedRectangleBorder(radius=16),
        "label_padding": ft.Padding.only(top=2, bottom=2),
        "animation_duration": 180,
        "overlay_color": ft.Colors.TRANSPARENT,
    }
