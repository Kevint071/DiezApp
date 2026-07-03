import flet as ft

# ── Brand Palette ────────────────────────────────────────
# Modern emerald palette — clean, trustworthy, harmonious
# --emerald-600:    #059669
# --emerald-500:    #10B981
# --emerald-400:    #34D399
# --emerald-100:    #D1FAE5
# --emerald-900:    #064E3B
# --slate-50:       #F8FAFC
# --slate-900:      #0F172A

# ── Light Mode ───────────────────────────────────────────
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
SECONDARY = "#0D9488"

# ── Dark Mode ────────────────────────────────────────────
SURFACE_DARK = "#0F172A"
SURFACE_VARIANT_DARK = "#1E293B"
ON_SURFACE_DARK = "#F1F5F9"
ON_SURFACE_VARIANT_DARK = "#94A3B8"
OUTLINE_DARK = "#334155"
OUTLINE_DARK_INPUT = "#475569"
DIVIDER_DARK = "#1E293B"
PRIMARY_DARK = "#34D399"
HERO_BG_DARK = "#064E3B"
SECONDARY_DARK = "#2DD4BF"

# ── Themes ───────────────────────────────────────────────
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
# ── Focus / Input States ───────────────────────────────────────
FOCUS_LIGHT = "#64748B"       # slate-500 — subtle, neutral focus
FOCUS_DARK = "#94A3B8"        # slate-400 — visible on dark, not neon
ERROR_LIGHT = "#FEE2E2"       # red-100 bg
ERROR_TEXT_LIGHT = "#DC2626"  # red-600 text
ERROR_DARK = "#371520"        # dark red bg
ERROR_TEXT_DARK = "#FCA5A5"   # red-300 text
# ── Helpers ──────────────────────────────────────────────
APPBAR_BGCOLOR_LIGHT = PRIMARY
APPBAR_BGCOLOR_DARK = "#0a0c10"
