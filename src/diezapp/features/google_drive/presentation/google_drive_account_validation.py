import uuid
from collections.abc import Callable

from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderError,
)
from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)
from diezapp.features.google_drive.application.validate_drive_account import (
    DriveAccountValidation,
    ValidateDriveAccount,
)


class GoogleDriveAccountValidationController:
    def __init__(
        self,
        page,
        accounts,
        refresh_access_token: RefreshAccessToken,
        account_validator: ValidateDriveAccount,
        on_result: Callable[[dict, DriveAccountValidation], None],
    ):
        self._page = page
        self._accounts = accounts
        self._refresh_access_token = refresh_access_token
        self._account_validator = account_validator
        self._on_result = on_result

    async def validate(self, account) -> tuple[str, str | None]:
        access_token = await self._refresh_access_token.execute(account)
        if not access_token:
            result: DriveAccountValidation = {
                "status": "unauthenticated",
                "folder_name": None,
            }
            self._on_result(account, result)
            return result["status"], None

        try:
            result = await self._account_validator.execute(
                access_token,
                account["google_account_email"],
                account.get("folder_id"),
            )
        except (
            DriveFolderError,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            result = {
                "status": "access_unavailable",
                "folder_name": None,
            }
        self._on_result(account, result)
        return result["status"], access_token

    def start(self):
        previous = self._page.session.store.get("gdrive_validation_task")
        if previous:
            previous.cancel()
        run_id = uuid.uuid4().hex
        self._page.session.store.set("gdrive_validation_run_id", run_id)
        task = self._page.run_task(self._validate_all, run_id)
        self._page.session.store.set("gdrive_validation_task", task)

    async def _validate_all(self, run_id):
        for account in self._accounts:
            if self._current_run(run_id) is False:
                return
            await self.validate(account)
        if self._current_run(run_id):
            self._page.update()

    def _current_run(self, run_id) -> bool:
        return self._page.session.store.get("gdrive_validation_run_id") == run_id
