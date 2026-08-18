import flet as ft


class FletUrlOpener:
    async def open_url(self, url: str) -> None:
        await ft.UrlLauncher().launch_url(url)
