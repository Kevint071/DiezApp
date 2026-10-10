"""Native OS save/open file dialogs for desktop platforms (Windows/macOS/Linux).

Flet's `FilePicker` + `Share` services are built for mobile (share sheets,
content-URI based file access) and are awkward to use for plain filesystem
paths on desktop. On desktop we use tkinter's `filedialog` instead, which
gives a normal native "Save as" / "Open" dialog with a real path back.
"""

import asyncio

DB_FILETYPES = [("Base de datos SQLite", "*.db"), ("Todos los archivos", "*.*")]


def _pick_save_path(
    default_name: str,
    title: str,
    default_extension: str,
    filetypes: list[tuple[str, str]],
) -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.asksaveasfilename(
            title=title,
            initialfile=default_name,
            defaultextension=default_extension,
            filetypes=filetypes,
        )
    finally:
        root.destroy()
    return path or None


def _pick_open_path(title: str, filetypes: list[tuple[str, str]]) -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    finally:
        root.destroy()
    return path or None


async def pick_save_path(
    default_name: str,
    *,
    title: str,
    default_extension: str,
    filetypes: list[tuple[str, str]],
) -> str | None:
    """Show a native "Save as" dialog on a worker thread; returns the chosen path or None."""
    return await asyncio.to_thread(
        _pick_save_path, default_name, title, default_extension, filetypes
    )


async def pick_open_path(*, title: str, filetypes: list[tuple[str, str]]) -> str | None:
    """Show a native "Open" dialog on a worker thread; returns the chosen path or None."""
    return await asyncio.to_thread(_pick_open_path, title, filetypes)
