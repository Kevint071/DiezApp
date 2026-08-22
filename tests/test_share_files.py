from diezapp.shared.presentation.share_files import build_share_file


def test_native_client_shares_the_file_by_path(tmp_path):
    backup = tmp_path / "backup_20260822_102429.db"
    backup.write_bytes(b"sqlite-bytes")

    share_file = build_share_file(str(backup), "backup_20260822_102429.db", web=False)

    assert share_file.path == str(backup)
    assert share_file.data is None


def test_web_client_shares_the_file_by_bytes(tmp_path):
    backup = tmp_path / "backup_20260822_102429.db"
    backup.write_bytes(b"sqlite-bytes")

    share_file = build_share_file(str(backup), "backup_20260822_102429.db", web=True)

    assert share_file.path is None
    assert share_file.data == b"sqlite-bytes"
    assert share_file.name == "backup_20260822_102429.db"
    assert share_file.mime_type is not None
