import asyncio
from collections.abc import Awaitable, Callable

from diezapp.features.google_drive.application.backup_scheduler import BackupScheduler
from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)
from diezapp.features.google_drive.application.run_backup import (
    GoogleDriveBackupService,
)


async def run_google_drive_scheduler(
    scheduler: BackupScheduler,
    backup_service: GoogleDriveBackupService,
    refresh_access_token: RefreshAccessToken,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Run startup catch-up and the recurring in-app backup loop."""
    if scheduler.is_due():
        await backup_service.run(refresh_access_token.execute)
    while True:
        remaining = scheduler.seconds_until_due()
        await sleep(60 if remaining is None else max(1, min(remaining, 60)))
        if scheduler.is_due():
            await backup_service.run(refresh_access_token.execute)
