import flet as ft

# ── Modern Palette ───────────────────────────────────────
# Light — clean white with violet accent
PRIMARY = "#7C5CFC"
PRIMARY_LIGHT = "#9B82FC"
ON_PRIMARY = "#FFFFFF"
PRIMARY_CONTAINER = "#EDE7FF"
ON_PRIMARY_CONTAINER = "#2D0F7A"
SURFACE_LIGHT = "#FAFAFA"
SURFACE_VARIANT_LIGHT = "#F3F0FF"
ON_SURFACE_LIGHT = "#1A1A2E"
ON_SURFACE_VARIANT_LIGHT = "#5C5670"
OUTLINE_LIGHT = "#B0A8C0"
DIVIDER_LIGHT = "#E0D8F0"

# Dark — true dark with vibrant accents
SURFACE_DARK = "#0F0F14"
SURFACE_VARIANT_DARK = "#1A1A24"
ON_SURFACE_DARK = "#EAEAF0"
ON_SURFACE_VARIANT_DARK = "#A0A0B8"
OUTLINE_DARK = "#4A4A60"
DIVIDER_DARK = "#2E2E40"
PRIMARY_DARK = "#A78BFA"
HERO_BG_DARK = "#1E1B30"

# ── Themes ───────────────────────────────────────────────
LIGHT_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=PRIMARY,
        on_primary=ON_PRIMARY,
        primary_container=PRIMARY_CONTAINER,
        on_primary_container=ON_PRIMARY_CONTAINER,
        surface=SURFACE_LIGHT,
        on_surface=ON_SURFACE_LIGHT,
        on_surface_variant=ON_SURFACE_VARIANT_LIGHT,
        outline=OUTLINE_LIGHT,
        surface_container_highest=SURFACE_VARIANT_LIGHT,
    ),
)

DARK_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=PRIMARY_DARK,
        on_primary="#1A1A2E",
        primary_container=HERO_BG_DARK,
        on_primary_container=PRIMARY_DARK,
        surface=SURFACE_DARK,
        on_surface=ON_SURFACE_DARK,
        on_surface_variant=ON_SURFACE_VARIANT_DARK,
        outline=OUTLINE_DARK,
        surface_container_highest=SURFACE_VARIANT_DARK,
    ),
)

# ── Helpers ──────────────────────────────────────────────
APPBAR_BGCOLOR_LIGHT = PRIMARY
APPBAR_BGCOLOR_DARK = "#16161E"
