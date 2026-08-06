"""Android/hardware "back" button handling.

This app renders everything through a single root `ft.View` (content is
swapped in place via `page.controls.clear()/page.add()` instead of pushing
`page.views` entries), so Flutter's Navigator never has more than one route.
That means the system back button has nothing to pop and, by default, exits
the app immediately from any screen.

To fix that, the root view's `can_pop` is disabled and `on_confirm_pop` is
used to intercept every back attempt: if a "nested" view (note detail, a
conflict screen, the calculator, etc.) has registered a back action via
`set_back_action`, it is invoked instead of popping; otherwise the pop is
confirmed and the app exits/backgrounds as usual.
"""

from collections.abc import Callable

import flet as ft

_STORE_KEY = "back_nav_action"


def set_back_action(page: ft.Page, fn: Callable[[], None] | None) -> None:
    """Register (or clear, with `None`) the action the system back button
    should run while the current screen is showing. Views that build their
    own AppBar directly (bypassing the centralized app-bar helper) must call
    this themselves to stay in sync with the hardware back button."""
    page.session.store.set(_STORE_KEY, fn)


def install_back_handler(page: ft.Page) -> None:
    """Call once per session. Disables the default pop (which would exit the
    app) on the single root view and routes every back attempt through
    whatever action `set_back_action` currently holds."""
    root_view = page.views[0]
    root_view.can_pop = False

    async def _on_confirm_pop(e):
        fn = page.session.store.get(_STORE_KEY)
        if fn:
            fn()
            await e.control.confirm_pop(False)
        else:
            await e.control.confirm_pop(True)

    root_view.on_confirm_pop = _on_confirm_pop
