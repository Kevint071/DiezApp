from typing import Protocol


class DriveFolderError(Exception):
    def __init__(self, message: str, status_code: int | None = None, reason: str = ""):
        self.message = message
        self.status_code = status_code
        self.reason = reason
        super().__init__(message)


class DriveFolderClient(Protocol):
    async def list(self, access_token: str, parent_id: str) -> list[dict[str, str]]: ...

    async def create(
        self, access_token: str, folder_name: str, parent_id: str
    ) -> str: ...

    async def delete(self, access_token: str, folder_id: str) -> None: ...


class DriveFolderService:
    def __init__(self, client: DriveFolderClient):
        self._client = client

    async def list(self, access_token: str, parent_id: str) -> list[dict[str, str]]:
        return await self._client.list(access_token, parent_id)

    async def create(self, access_token: str, folder_name: str, parent_id: str) -> str:
        return await self._client.create(access_token, folder_name, parent_id)

    async def delete(self, access_token: str, folder_id: str) -> None:
        await self._client.delete(access_token, folder_id)
