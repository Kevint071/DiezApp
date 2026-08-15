"""Backup engine: snapshot `app.db` and upload it to every linked Google account.

Single entry point `run_backup_now()` is used by the manual "Respaldar
ahora" button and both scheduler triggers (in-app timer + startup catch-up),
per design.md Decision 4 (one code path for "a backup happens").
"""

import asyncio
import json
import os
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime

import flet as ft

from utils.db import get_connection, get_setting, set_setting
from utils.gdrive_auth import ensure_fresh_access_token, list_accounts
from utils.gdrive_client import upload_backup_file

RETRY_DELAYS_SECONDS = [5, 30, 120]
LAST_BACKUP_SETTING = "last_backup_success_at"
INTERVAL_SETTING = "backup_interval_seconds"


def _snapshot_db() -> str:
    """Consistent snapshot of app.db via SQLite's Online Backup API."""
    file_name = datetime.now(UTC).strftime("backup_%Y%m%d_%H%M%S.db")
    dest_path = os.path.join(tempfile.gettempdir(), file_name)
    src_conn = get_connection()
    dest_conn = sqlite3.connect(dest_path)
    try:
        src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
    return dest_path


async def _upload_with_retry(page: ft.Page, account: dict, file_path: str, file_name: str) -> dict:
    last_error = "Error desconocido"
    # 3 attempts total; pre-delays before attempts 2/3 use the first two
    # backoff values (5s, 30s) — the 3rd (2min) is the ceiling if a future
    # attempt count is added, unused with exactly 3 attempts.
    for delay in [0, *RETRY_DELAYS_SECONDS[:-1]]:
        if delay:
            await asyncio.sleep(delay)
        access_token = await ensure_fresh_access_token(page, account)
        if not access_token:
            last_error = "No se pudo renovar el token de acceso"
            continue
        try:
            await upload_backup_file(
                access_token, account["folder_id"], file_path, file_name
            )
            return {"email": account["google_account_email"], "ok": True}
        except Exception as e:  # noqa: BLE001 — any upload failure should retry, not crash the run
            last_error = str(e)
    return {
        "email": account["google_account_email"],
        "ok": False,
        "error": last_error,
    }


async def run_backup_now(page: ft.Page) -> dict:
    """Snapshot + upload to all linked accounts with a configured folder.

    Returns {"status": "success"|"partial"|"failed"|"skipped", "results": [...]}.
    """
    accounts = [a for a in list_accounts() if a.get("folder_id")]
    if not accounts:
        return {"status": "skipped", "results": [], "message": "No hay cuentas configuradas"}

    started_at = datetime.now(UTC)
    file_path = _snapshot_db()
    file_name = os.path.basename(file_path)
    try:
        results = await asyncio.gather(
            *[_upload_with_retry(page, acc, file_path, file_name) for acc in accounts]
        )
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)

    ok_count = sum(1 for r in results if r["ok"])
    if ok_count == len(results):
        status = "success"
    elif ok_count > 0:
        status = "partial"
    else:
        status = "failed"

    finished_at = datetime.now(UTC)
    if status in ("success", "partial"):
        set_setting(LAST_BACKUP_SETTING, finished_at.isoformat())

    _write_history(started_at, finished_at, status, results)
    return {"status": status, "results": results}


def _write_history(started_at: datetime, finished_at: datetime, status: str, results: list[dict]):
    conn = get_connection()
    conn.execute(
        "INSERT INTO backup_history (id, started_at, finished_at, status, details) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex,
            started_at.isoformat(),
            finished_at.isoformat(),
            status,
            json.dumps(results),
        ),
    )
    conn.commit()


def list_history(limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, started_at, finished_at, status, details "
        "FROM backup_history ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    history = []
    for row in rows:
        try:
            details = json.loads(row[4])
        except (json.JSONDecodeError, TypeError):
            details = []
        history.append(
            {
                "id": row[0],
                "started_at": row[1],
                "finished_at": row[2],
                "status": row[3],
                "details": details,
            }
        )
    return history


# ── Scheduling helpers (interval stored as seconds in `settings`) ────


def get_interval_seconds() -> int | None:
    raw = get_setting(INTERVAL_SETTING)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def set_interval_seconds(seconds: int):
    set_setting(INTERVAL_SETTING, str(seconds))


def get_last_backup_at() -> datetime | None:
    raw = get_setting(LAST_BACKUP_SETTING)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def seconds_until_due(now: datetime | None = None) -> float | None:
    """Seconds remaining until the next backup is due.

    Returns None if no interval is configured. A value <= 0 means a backup
    is due right now. `now` is injectable for tests.
    """
    interval = get_interval_seconds()
    if interval is None:
        return None
    now = now or datetime.now(UTC)
    last = get_last_backup_at()
    if last is None:
        return 0.0
    elapsed = (now - last).total_seconds()
    return interval - elapsed


def is_due(now: datetime | None = None) -> bool:
    remaining = seconds_until_due(now)
    return remaining is not None and remaining <= 0
