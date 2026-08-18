import flet as ft

from diezapp.shared.presentation.theme import (
    HERO_BG_DARK,
    ON_PRIMARY,
    ON_PRIMARY_CONTAINER,
    ON_SURFACE_DARK,
    ON_SURFACE_LIGHT,
    ON_SURFACE_VARIANT_DARK,
    ON_SURFACE_VARIANT_LIGHT,
    OUTLINE_DARK,
    OUTLINE_LIGHT,
    PRIMARY,
    PRIMARY_CONTAINER,
    PRIMARY_DARK,
    SECONDARY,
    SECONDARY_DARK,
    SURFACE_DARK,
    SURFACE_LIGHT,
    SURFACE_VARIANT_DARK,
    SURFACE_VARIANT_LIGHT,
)

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
