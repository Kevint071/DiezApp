"""Unit tests for the 2-account limit and independent unlink."""

import pytest

from diezapp.features.google_drive.application.link_account import LinkAccountService
from diezapp.infrastructure.persistence.sqlite_drive_account_repository import (
    SqliteDriveAccountRepository,
)


@pytest.fixture
def account_service():
    return LinkAccountService(SqliteDriveAccountRepository())


class TestAccountLimit:
    def test_can_add_account_reflects_limit(self, account_service):
        assert account_service.can_add_account() is True
        account_service.add_account("a@example.com", "tok1", "ref1", 3600)
        assert account_service.can_add_account() is True
        account_service.add_account("b@example.com", "tok2", "ref2", 3600)
        assert account_service.can_add_account() is False

    def test_third_account_is_rejected(self, account_service):
        account_service.add_account("a@example.com", "tok1", "ref1", 3600)
        account_service.add_account("b@example.com", "tok2", "ref2", 3600)
        with pytest.raises(ValueError):
            account_service.add_account("c@example.com", "tok3", "ref3", 3600)
        assert len(account_service.list_accounts()) == 2


class TestUnlinkIndependence:
    def test_unlinking_one_account_leaves_other_untouched(self, account_service):
        id_a = account_service.add_account("a@example.com", "tok1", "ref1", 3600)
        id_b = account_service.add_account("b@example.com", "tok2", "ref2", 3600)
        account_service.set_account_folder(id_a, "folder-a", "Folder A")
        account_service.set_account_folder(id_b, "folder-b", "Folder B")

        account_service.remove_account(id_a)

        remaining = account_service.list_accounts()
        assert len(remaining) == 1
        assert remaining[0]["id"] == id_b
        assert remaining[0]["folder_id"] == "folder-b"

    def test_unlinking_frees_a_slot(self, account_service):
        id_a = account_service.add_account("a@example.com", "tok1", "ref1", 3600)
        account_service.add_account("b@example.com", "tok2", "ref2", 3600)
        assert account_service.can_add_account() is False

        account_service.remove_account(id_a)

        assert account_service.can_add_account() is True
