from diezapp.infrastructure.database.connection import get_connection
from diezapp.infrastructure.persistence.sqlite_drive_account_repository import (
    SqliteDriveAccountRepository,
)
from diezapp.infrastructure.persistence.sqlite_drive_token_repository import (
    SqliteDriveTokenRepository,
)


def test_update_changes_only_selected_account_token():
    account_repository = SqliteDriveAccountRepository()
    account_a = account_repository.add("a@example.com", "token-a", "refresh-a", 3600)
    account_b = account_repository.add("b@example.com", "token-b", "refresh-b", 3600)
    repository = SqliteDriveTokenRepository()

    repository.update(account_a, "new-token-a", "2030-01-01T00:00:00+00:00")

    rows = (
        get_connection()
        .execute(
            "SELECT id, access_token, token_expiry_at FROM gdrive_accounts ORDER BY id"
        )
        .fetchall()
    )
    by_id = {row[0]: row[1:] for row in rows}
    assert by_id[account_a] == ("new-token-a", "2030-01-01T00:00:00+00:00")
    assert by_id[account_b] == ("token-b", by_id[account_b][1])
