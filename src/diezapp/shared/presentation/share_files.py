"""Send files to the platform share sheet from any Flet client."""

import asyncio
import mimetypes
from pathlib import Path

import flet as ft

_FALLBACK_MIME = "application/octet-stream"


def build_share_file(path: str, name: str, *, web: bool) -> ft.ShareFile:
    """Wrap ``path`` in a ``ShareFile`` the current client can actually read.

    On the web client Python runs on the server, so a filesystem path means
    nothing to the browser: it resolves it as a blob URL and fails with
    "Could not load Blob from its URL". Send the bytes instead.
    """
    if not web:
        return ft.ShareFile.from_path(path, name=name)
    data = Path(path).read_bytes()
    mime_type = mimetypes.guess_type(name)[0] or _FALLBACK_MIME
    return ft.ShareFile.from_bytes(data, mime_type=mime_type, name=name)


async def share_local_file(
    page: ft.Page, path: str, name: str, *, title: str | None = None
) -> ft.ShareResult:
    """Open the share sheet for the local file at ``path``."""
    share_file = await asyncio.to_thread(
        build_share_file, path, name, web=bool(page.web)
    )
    share = ft.Share()
    return await share.share_files([share_file], title=title)
