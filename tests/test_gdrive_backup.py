"""Unit tests for gdrive_backup.run_backup_now() aggregation + scheduler."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from utils import gdrive_backup


class _FakePage:
    platform = None


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


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


@pytest.fixture(autouse=True)
def _no_real_delay(monkeypatch):
    """Retry backoff delays would slow tests down for no benefit."""

    async def _instant_sleep(_seconds):
        return None

    monkeypatch.setattr(gdrive_backup.asyncio, "sleep", _instant_sleep)


class TestRunBackupNowAggregation:
    def test_no_accounts_linked_is_skipped(self):
        result = asyncio.run(gdrive_backup.run_backup_now(_FakePage()))
        assert result["status"] == "skipped"

    def test_accounts_without_folder_are_excluded(self, monkeypatch):
        acc_no_folder = _account(1, folder_id=None)
        monkeypatch.setattr(gdrive_backup, "list_accounts", lambda: [acc_no_folder])

        result = asyncio.run(gdrive_backup.run_backup_now(_FakePage()))
        assert result["status"] == "skipped"

    def test_all_accounts_succeed_is_success(self, monkeypatch):
        accounts = [_account(1), _account(2)]
        monkeypatch.setattr(gdrive_backup, "list_accounts", lambda: accounts)
        monkeypatch.setattr(
            gdrive_backup, "ensure_fresh_access_token", _async_return("tok")
        )
        monkeypatch.setattr(
            gdrive_backup, "upload_backup_file", _async_return("file-id")
        )

        result = asyncio.run(gdrive_backup.run_backup_now(_FakePage()))

        assert result["status"] == "success"
        assert all(r["ok"] for r in result["results"])
        assert gdrive_backup.get_last_backup_at() is not None

    def test_partial_success_when_one_of_two_accounts_fails(self, monkeypatch):
        acc_ok = _account(1, folder_id="folder-a")
        acc_fail = _account(2, folder_id="folder-b")
        monkeypatch.setattr(gdrive_backup, "list_accounts", lambda: [acc_ok, acc_fail])
        monkeypatch.setattr(
            gdrive_backup, "ensure_fresh_access_token", _async_return("tok")
        )

        async def _upload(access_token, folder_id, file_path, file_name):
            if folder_id == "folder-b":
                raise RuntimeError("network error")
            return "file-id"

        monkeypatch.setattr(gdrive_backup, "upload_backup_file", _upload)

        result = asyncio.run(gdrive_backup.run_backup_now(_FakePage()))

        assert result["status"] == "partial"
        oks = {r["email"]: r["ok"] for r in result["results"]}
        assert oks[acc_ok["google_account_email"]] is True
        assert oks[acc_fail["google_account_email"]] is False
        # Partial success still updates last_backup_success_at (design.md Decision 6).
        assert gdrive_backup.get_last_backup_at() is not None

    def test_all_accounts_fail_is_failed_and_last_backup_not_updated(self, monkeypatch):
        acc = _account(1)
        monkeypatch.setattr(gdrive_backup, "list_accounts", lambda: [acc])
        monkeypatch.setattr(
            gdrive_backup, "ensure_fresh_access_token", _async_return("tok")
        )

        async def _upload(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(gdrive_backup, "upload_backup_file", _upload)

        result = asyncio.run(gdrive_backup.run_backup_now(_FakePage()))

        assert result["status"] == "failed"
        assert gdrive_backup.get_last_backup_at() is None

    def test_every_run_writes_a_history_row(self, monkeypatch):
        acc = _account(1)
        monkeypatch.setattr(gdrive_backup, "list_accounts", lambda: [acc])
        monkeypatch.setattr(
            gdrive_backup, "ensure_fresh_access_token", _async_return("tok")
        )
        monkeypatch.setattr(
            gdrive_backup, "upload_backup_file", _async_return("file-id")
        )

        asyncio.run(gdrive_backup.run_backup_now(_FakePage()))

        history = gdrive_backup.list_history()
        assert len(history) == 1
        assert history[0]["status"] == "success"

    def test_overlapping_runs_are_skipped(self, monkeypatch):
        acc = _account(1)
        upload_started = asyncio.Event()
        release_upload = asyncio.Event()
        monkeypatch.setattr(gdrive_backup, "list_accounts", lambda: [acc])
        monkeypatch.setattr(
            gdrive_backup, "ensure_fresh_access_token", _async_return("tok")
        )

        async def _upload(*args, **kwargs):
            upload_started.set()
            await release_upload.wait()
            return "file-id"

        monkeypatch.setattr(gdrive_backup, "upload_backup_file", _upload)

        async def _run_both():
            first = asyncio.create_task(gdrive_backup.run_backup_now(_FakePage()))
            await upload_started.wait()
            second = await gdrive_backup.run_backup_now(_FakePage())
            release_upload.set()
            return await first, second

        first, second = asyncio.run(_run_both())

        assert first["status"] == "success"
        assert second["status"] == "skipped"
        assert "curso" in second["message"]


class TestScheduler:
    def test_no_interval_configured_returns_none(self):
        assert gdrive_backup.seconds_until_due() is None
        assert gdrive_backup.is_due() is False

    def test_due_immediately_when_never_backed_up(self):
        gdrive_backup.set_interval_seconds(3600)
        assert gdrive_backup.is_due() is True

    def test_not_due_before_interval_elapses(self):
        gdrive_backup.set_interval_seconds(3600)
        now = datetime.now(UTC)
        gdrive_backup.set_setting(gdrive_backup.LAST_BACKUP_SETTING, now.isoformat())
        assert gdrive_backup.is_due(now=now + timedelta(minutes=30)) is False

    def test_due_after_interval_elapses(self):
        gdrive_backup.set_interval_seconds(3600)
        now = datetime.now(UTC)
        gdrive_backup.set_setting(gdrive_backup.LAST_BACKUP_SETTING, now.isoformat())
        assert gdrive_backup.is_due(now=now + timedelta(hours=2)) is True
