from diezapp.features.google_drive.application.link_account import LinkAccountService


class FakeDriveAccountRepository:
    def __init__(self):
        self.accounts = []

    def list(self):
        return self.accounts

    def count(self):
        return len(self.accounts)

    def add(self, email, access_token, refresh_token, expires_in):
        account = {
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
        }
        self.accounts.append(account)
        return f"account-{len(self.accounts)}"

    def remove(self, account_id):
        del account_id

    def set_folder(self, account_id, folder_id, folder_name):
        del account_id, folder_id, folder_name

    def update_token(self, account_id, access_token, expiry_iso):
        del account_id, access_token, expiry_iso


def test_complete_link_adds_account_from_valid_callback():
    repository = FakeDriveAccountRepository()
    service = LinkAccountService(repository)

    result = service.complete_link(
        {
            "app_state": "expected-state",
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "email": "user@example.com",
            "expires_in": "1800",
        },
        pending_state="expected-state",
        is_web_runtime=False,
    )

    assert result == {"ok": True, "message": "Cuenta user@example.com vinculada"}
    assert repository.accounts[0]["expires_in"] == 1800


def test_complete_link_rejects_invalid_state():
    repository = FakeDriveAccountRepository()
    service = LinkAccountService(repository)

    result = service.complete_link(
        {"app_state": "unexpected-state", "access_token": "token", "email": "user"},
        pending_state="expected-state",
        is_web_runtime=False,
    )

    assert result == {"ok": False, "message": "No se pudo completar la vinculación"}
    assert repository.accounts == []


def test_complete_link_reports_cancelled_callback():
    repository = FakeDriveAccountRepository()
    service = LinkAccountService(repository)

    result = service.complete_link(
        {"app_state": "expected-state", "error": "access_denied"},
        pending_state="expected-state",
        is_web_runtime=False,
    )

    assert result == {"ok": False, "message": "Vinculación cancelada"}
    assert repository.accounts == []
