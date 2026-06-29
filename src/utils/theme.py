import flet as ft

# ── Brand Palette ────────────────────────────────────────
# --black:           #050609
# --porcelain:       #fdfffc
# --light-sea-green: #0ca4a5
# --dim-grey:        #747274
# --sapphire:        #0353a4

# ── Light Mode ───────────────────────────────────────────
PRIMARY = "#0ca4a5"
PRIMARY_LIGHT = "#2ebcbd"
ON_PRIMARY = "#FFFFFF"
PRIMARY_CONTAINER = "#e0f6f6"
ON_PRIMARY_CONTAINER = "#053d3d"
SURFACE_LIGHT = "#fdfffc"
SURFACE_VARIANT_LIGHT = "#f2f7f7"
ON_SURFACE_LIGHT = "#050609"
ON_SURFACE_VARIANT_LIGHT = "#747274"
OUTLINE_LIGHT = "#c2c0c2"
DIVIDER_LIGHT = "#e4e2e4"
SECONDARY = "#0353a4"

# ── Dark Mode ────────────────────────────────────────────
SURFACE_DARK = "#050609"
SURFACE_VARIANT_DARK = "#161c24"
ON_SURFACE_DARK = "#fdfffc"
ON_SURFACE_VARIANT_DARK = "#b0aeb0"
OUTLINE_DARK = "#3d5254"
OUTLINE_DARK_INPUT = "#708e90"  # unfocused input border, lighter than OUTLINE_DARK
DIVIDER_DARK = "#263436"
PRIMARY_DARK = "#3ecbcc"
HERO_BG_DARK = "#0c2828"
SECONDARY_DARK = "#5b9fd6"

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
)

DARK_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=PRIMARY_DARK,
        on_primary="#050609",
        primary_container=HERO_BG_DARK,
        on_primary_container=PRIMARY_DARK,
        secondary=SECONDARY_DARK,
        surface=SURFACE_DARK,
        on_surface=ON_SURFACE_DARK,
        on_surface_variant=ON_SURFACE_VARIANT_DARK,
        outline=OUTLINE_DARK,
        surface_container_highest=SURFACE_VARIANT_DARK,
    ),
)

# ── Helpers ──────────────────────────────────────────────
APPBAR_BGCOLOR_LIGHT = PRIMARY
APPBAR_BGCOLOR_DARK = "#0a0c10"
