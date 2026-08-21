from collections.abc import Callable
from dataclasses import dataclass

import flet as ft

from diezapp.bootstrap.dependencies import AppDependencies


@dataclass
class RouteContext:
    """Shared collaborators handed to feature-owned route builders.

    Bundles the composition root's page-scoped helpers so each feature can
    build its own views without composition.py knowing their internals.
    """

    page: ft.Page
    dependencies: AppDependencies
    colors_fn: Callable[[ft.Page], dict]
    build_appbar: Callable[..., ft.AppBar]
    show_snack: Callable[[str, bool], None]
