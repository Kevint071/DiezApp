import flet as ft

# ── MD3 Palette ──────────────────────────────────────────
PRIMARY = "#6750A4"
ON_PRIMARY = "#FFFFFF"
PRIMARY_CONTAINER = "#EADDFF"
ON_PRIMARY_CONTAINER = "#21005D"
SURFACE_LIGHT = "#FFFBFE"
SURFACE_VARIANT_LIGHT = "#F7F2FA"
ON_SURFACE_LIGHT = "#1C1B1F"
ON_SURFACE_VARIANT_LIGHT = "#49454F"
OUTLINE_LIGHT = "#79747E"
DIVIDER_LIGHT = "#D0BCFF"

SURFACE_DARK = "#1C1B1F"
SURFACE_VARIANT_DARK = "#2B2930"
ON_SURFACE_DARK = "#E6E1E5"
ON_SURFACE_VARIANT_DARK = "#CAC4D0"
OUTLINE_DARK = "#938F99"
DIVIDER_DARK = "#4F378B"

# ── Themes ───────────────────────────────────────────────
LIGHT_THEME = ft.Theme(
    color_scheme_seed=PRIMARY,
    color_scheme=ft.ColorScheme(
        primary=PRIMARY,
        on_primary=ON_PRIMARY,
        primary_container=PRIMARY_CONTAINER,
        on_primary_container=ON_PRIMARY_CONTAINER,
        surface=SURFACE_LIGHT,
        on_surface=ON_SURFACE_LIGHT,
        outline=OUTLINE_LIGHT,
    ),
)

DARK_THEME = ft.Theme(
    color_scheme_seed=PRIMARY,
    color_scheme=ft.ColorScheme(
        primary=PRIMARY_CONTAINER,
        on_primary=ON_PRIMARY_CONTAINER,
        primary_container=PRIMARY,
        on_primary_container=ON_PRIMARY,
        surface=SURFACE_DARK,
        on_surface=ON_SURFACE_DARK,
        outline=OUTLINE_DARK,
    ),
)

# ── Helpers ──────────────────────────────────────────────
APPBAR_BGCOLOR_LIGHT = PRIMARY
APPBAR_BGCOLOR_DARK = SURFACE_VARIANT_DARK
