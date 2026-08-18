from collections.abc import Awaitable
from typing import Protocol


class UrlOpener(Protocol):
    def open_url(self, url: str) -> Awaitable[None]: ...
