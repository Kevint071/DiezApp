"""Unit tests for the Google Drive backup use case and scheduler."""

import asyncio
from datetime import UTC, datetime, timedelta

from diezapp.features.google_drive.application.backup_scheduler import BackupScheduler
from diezapp.features.google_drive.application.run_backup import (
    GoogleDriveBackupService,
)


def _account(id_suffix, folder_id="folder1"):
    return {
        "id": f"acc-{id_suffix}",
        "google_account_email": f"user{id_suffix}@example.com",
        "folder_id": folder_id,
        "folder_name": "Backups",
        "access_token": "tok",
        "refresh_token": "refresh",
        "token_expiry_at": None,
    }


async def _async_noop():
    return None


class BackupHarness:
    def __init__(self, accounts):
        self.accounts = accounts
        self.history = []
        self.last_backup_at = None
        self.upload = self._upload

    def snapshot(self):
        path = "backup-test.db"
        with open(path, "wb") as file:
            file.write(b"snapshot")
        return path

    async def _upload(self, access_token, folder_id, file_path, file_name):
        return "file-id"

    async def token_provider(self, account):
        return "tok"

    def build(self):
        return GoogleDriveBackupService(
            list_accounts=lambda: self.accounts,
            snapshot_db=self.snapshot,
            upload_file=self.upload,
            write_history=lambda started, finished, status, results: (
                self.history.append((started, finished, status, results))
            ),
            save_success_at=lambda timestamp: setattr(
                self, "last_backup_at", timestamp
            ),
            sleep=lambda _seconds: _async_noop(),
            retry_delays=[1],
        )


class TestRunBackupAggregation:
    def test_no_accounts_linked_is_skipped(self):
        harness = BackupHarness([])

        result = asyncio.run(harness.build().run(harness.token_provider))

        assert result["status"] == "skipped"

    def test_accounts_without_folder_are_excluded(self):
        harness = BackupHarness([_account(1, folder_id=None)])

        result = asyncio.run(harness.build().run(harness.token_provider))

        assert result["status"] == "skipped"

    def test_all_accounts_succeed_is_success(self):
        harness = BackupHarness([_account(1), _account(2)])

        result = asyncio.run(harness.build().run(harness.token_provider))

        assert result["status"] == "success"
        assert all(item["ok"] for item in result["results"])
        assert harness.last_backup_at is not None

    def test_partial_success_when_one_of_two_accounts_fails(self):
        harness = BackupHarness([_account(1, "folder-a"), _account(2, "folder-b")])

        async def upload(access_token, folder_id, file_path, file_name):
            if folder_id == "folder-b":
                raise RuntimeError("network error")
            return "file-id"

        harness.upload = upload
        result = asyncio.run(harness.build().run(harness.token_provider))

        assert result["status"] == "partial"
        oks = {item["email"]: item["ok"] for item in result["results"]}
        assert oks["user1@example.com"] is True
        assert oks["user2@example.com"] is False
        assert harness.last_backup_at is not None

    def test_all_accounts_fail_is_failed_and_last_backup_not_updated(self):
        harness = BackupHarness([_account(1)])

        async def upload(*args, **kwargs):
            raise RuntimeError("boom")

        harness.upload = upload
        result = asyncio.run(harness.build().run(harness.token_provider))

        assert result["status"] == "failed"
        assert harness.last_backup_at is None

    def test_every_run_writes_a_history_row(self):
        harness = BackupHarness([_account(1)])

        asyncio.run(harness.build().run(harness.token_provider))

        assert len(harness.history) == 1
        assert harness.history[0][2] == "success"

    def test_overlapping_runs_are_skipped(self):
        upload_started = asyncio.Event()
        release_upload = asyncio.Event()
        harness = BackupHarness([_account(1)])

        async def upload(*args, **kwargs):
            upload_started.set()
            await release_upload.wait()
            return "file-id"

        harness.upload = upload
        service = harness.build()

        async def run_both():
            first = asyncio.create_task(service.run(harness.token_provider))
            await upload_started.wait()
            second = await service.run(harness.token_provider)
            release_upload.set()
            return await first, second

        first, second = asyncio.run(run_both())

        assert first["status"] == "success"
        assert second["status"] == "skipped"
        assert "curso" in second["message"]


class TestScheduler:
    def test_no_interval_configured_returns_none(self):
        scheduler = BackupScheduler(lambda: None, lambda: None)

        assert scheduler.seconds_until_due() is None
        assert scheduler.is_due() is False

    def test_due_immediately_when_never_backed_up(self):
        scheduler = BackupScheduler(lambda: 3600, lambda: None)

        assert scheduler.is_due() is True

    def test_not_due_before_interval_elapses(self):
        now = datetime.now(UTC)
        scheduler = BackupScheduler(lambda: 3600, lambda: now)

        assert scheduler.is_due(now=now + timedelta(minutes=30)) is False

    def test_due_after_interval_elapses(self):
        now = datetime.now(UTC)
        scheduler = BackupScheduler(lambda: 3600, lambda: now)

        assert scheduler.is_due(now=now + timedelta(hours=2)) is True
