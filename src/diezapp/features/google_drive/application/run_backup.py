import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import datetime

from diezapp.features.google_drive.domain.backup_results import (
    BackupResult,
    BackupSummary,
)
from diezapp.shared.datetime_utils import local_now

Account = dict
TokenProvider = Callable[[Account], Awaitable[str | None]]
UploadFile = Callable[[str, str, str, str], Awaitable[object]]


class GoogleDriveBackupService:
    def __init__(
        self,
        list_accounts: Callable[[], list[Account]],
        snapshot_db: Callable[[], str],
        upload_file: UploadFile,
        write_history: Callable[[datetime, datetime, str, list[BackupResult]], None],
        save_success_at: Callable[[datetime], None],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        retry_delays: list[int] | None = None,
    ):
        self._list_accounts = list_accounts
        self._snapshot_db = snapshot_db
        self._upload_file = upload_file
        self._write_history = write_history
        self._save_success_at = save_success_at
        self._sleep = sleep
        self._retry_delays = retry_delays or [5, 30, 120]
        self._running = False

    async def run(
        self,
        token_provider: TokenProvider,
        account_ids: set[str] | None = None,
    ) -> BackupSummary:
        if self._running:
            return {
                "status": "skipped",
                "results": [],
                "message": "Ya hay una copia de seguridad en curso",
            }
        self._running = True
        try:
            return await self._run(token_provider, account_ids)
        finally:
            self._running = False

    async def _run(
        self,
        token_provider: TokenProvider,
        account_ids: set[str] | None,
    ) -> BackupSummary:
        accounts = [
            account
            for account in self._list_accounts()
            if account.get("folder_id")
            and (account_ids is None or account["id"] in account_ids)
        ]
        if not accounts:
            return {
                "status": "skipped",
                "results": [],
                "message": "No hay cuentas configuradas",
            }

        started_at = local_now()
        file_path = self._snapshot_db()
        file_name = os.path.basename(file_path)
        try:
            results = await asyncio.gather(
                *[
                    self._upload_with_retry(
                        token_provider, account, file_path, file_name
                    )
                    for account in accounts
                ]
            )
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)

        ok_count = sum(1 for result in results if result["ok"])
        if ok_count == len(results):
            status = "success"
        elif ok_count > 0:
            status = "partial"
        else:
            status = "failed"

        finished_at = local_now()
        if status in ("success", "partial"):
            self._save_success_at(finished_at)
        self._write_history(started_at, finished_at, status, results)
        return {"status": status, "results": results}

    async def _upload_with_retry(
        self,
        token_provider: TokenProvider,
        account: Account,
        file_path: str,
        file_name: str,
    ) -> BackupResult:
        last_error = "Error desconocido"
        for delay in [0, *self._retry_delays[:-1]]:
            if delay:
                await self._sleep(delay)
            access_token = await token_provider(account)
            if not access_token:
                last_error = "No se pudo renovar el token de acceso"
                continue
            try:
                await self._upload_file(
                    access_token, account["folder_id"], file_path, file_name
                )
                return {"email": account["google_account_email"], "ok": True}
            except Exception as error:  # noqa: BLE001 - upload failures are retried
                last_error = str(error)
        return {
            "email": account["google_account_email"],
            "ok": False,
            "error": last_error,
        }
