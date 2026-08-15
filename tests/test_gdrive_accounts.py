"""Unit tests for the 2-account limit and independent unlink (gdrive_auth)."""

import pytest

from utils import gdrive_auth


class TestAccountLimit:
    def test_can_add_account_reflects_limit(self):
        assert gdrive_auth.can_add_account() is True
        gdrive_auth.add_account("a@example.com", "tok1", "ref1", 3600)
        assert gdrive_auth.can_add_account() is True
        gdrive_auth.add_account("b@example.com", "tok2", "ref2", 3600)
        assert gdrive_auth.can_add_account() is False

    def test_third_account_is_rejected(self):
        gdrive_auth.add_account("a@example.com", "tok1", "ref1", 3600)
        gdrive_auth.add_account("b@example.com", "tok2", "ref2", 3600)
        with pytest.raises(ValueError):
            gdrive_auth.add_account("c@example.com", "tok3", "ref3", 3600)
        assert gdrive_auth.count_accounts() == 2


class TestUnlinkIndependence:
    def test_unlinking_one_account_leaves_other_untouched(self):
        id_a = gdrive_auth.add_account("a@example.com", "tok1", "ref1", 3600)
        id_b = gdrive_auth.add_account("b@example.com", "tok2", "ref2", 3600)
        gdrive_auth.set_account_folder(id_a, "folder-a", "Folder A")
        gdrive_auth.set_account_folder(id_b, "folder-b", "Folder B")

        gdrive_auth.remove_account(id_a)

        remaining = gdrive_auth.list_accounts()
        assert len(remaining) == 1
        assert remaining[0]["id"] == id_b
        assert remaining[0]["folder_id"] == "folder-b"

    def test_unlinking_frees_a_slot(self):
        id_a = gdrive_auth.add_account("a@example.com", "tok1", "ref1", 3600)
        gdrive_auth.add_account("b@example.com", "tok2", "ref2", 3600)
        assert gdrive_auth.can_add_account() is False

        gdrive_auth.remove_account(id_a)

        assert gdrive_auth.can_add_account() is True
