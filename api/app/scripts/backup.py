#!/usr/bin/env python3
"""Backup script — backs up PostgreSQL database + storage files.

Usage:
    python -m app.scripts.backup                    # backup to default location
    python -m app.scripts.backup --output /mnt/bak   # backup to custom location

For dev (SQLite), backs up the .db file + storage/ directory.
For prod (PostgreSQL), uses pg_dump + storage files.

Includes a restore test: restores to a temp DB, runs a few queries, drops it.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import settings


def backup_database(output_dir: Path) -> Path:
    """Back up the database. Returns the backup file path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if settings.is_sqlite:
        db_path = settings.database_url.replace("sqlite:///", "")
        backup_path = output_dir / f"db_{timestamp}.db"
        shutil.copy2(db_path, backup_path)
        print(f"  [ok] SQLite backed up -> {backup_path}")
        return backup_path
    else:
        backup_path = output_dir / f"db_{timestamp}.sql"
        cmd = ["pg_dump", settings.database_url, "-f", str(backup_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [FAIL] pg_dump failed: {result.stderr}", file=sys.stderr)
            raise RuntimeError("pg_dump failed")
        print(f"  [ok] PostgreSQL backed up -> {backup_path}")
        return backup_path


def backup_storage(output_dir: Path) -> Path | None:
    """Back up the storage directory (uploaded files)."""
    if settings.storage_backend != "local":
        print("  [skip] Storage backend is not local (S3 backups handled separately)")
        return None
    storage_path = Path(settings.storage_local_dir)
    if not storage_path.exists():
        print("  [skip] Storage directory does not exist")
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = output_dir / f"storage_{timestamp}.tar.gz"
    result = subprocess.run(
        ["tar", "-czf", str(backup_path), "-C", str(storage_path.parent), storage_path.name],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  [FAIL] tar failed: {result.stderr}", file=sys.stderr)
        return None
    print(f"  [ok] Storage backed up -> {backup_path}")
    return backup_path


def test_restore(backup_path: Path) -> bool:
    """Restore the backup to a temp DB, run a sanity query, drop it."""
    print(f"  [..] Testing restore from {backup_path}...")
    try:
        if backup_path.suffix == ".db":
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                shutil.copy2(backup_path, tmp.name)
                tmp_path = Path(tmp.name)
            import sqlite3
            conn = sqlite3.connect(str(tmp_path))
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM users")
            count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM departments")
            depts = cur.fetchone()[0]
            conn.close()
            tmp_path.unlink()
            print(f"  [ok] Restore test passed -- users: {count}, departments: {depts}")
            return True
        else:
            tmp_db = f"csit_restore_test_{int(datetime.now(timezone.utc).timestamp())}"
            subprocess.run(["createdb", tmp_db], check=True, capture_output=True)
            subprocess.run(["psql", tmp_db, "-f", str(backup_path)], check=True, capture_output=True)
            result = subprocess.run(
                ["psql", tmp_db, "-t", "-c", "SELECT count(*) FROM users;"],
                capture_output=True, text=True,
            )
            count = result.stdout.strip()
            subprocess.run(["dropdb", tmp_db], check=True, capture_output=True)
            print(f"  [ok] Restore test passed -- users: {count}")
            return True
    except Exception as exc:
        print(f"  [FAIL] Restore test failed: {exc}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Backup database + storage")
    parser.add_argument("--output", default="./backups", help="Output directory")
    parser.add_argument("--no-restore-test", action="store_true", help="Skip restore test")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Backup started at {datetime.now(timezone.utc).isoformat()}")
    print(f"  env: {settings.app_env}")
    print(f"  db: {settings.database_url}")
    print(f"  storage: {settings.storage_backend} -> {settings.storage_local_dir}")

    db_backup = backup_database(output_dir)
    storage_backup = backup_storage(output_dir)

    if not args.no_restore_test:
        if not test_restore(db_backup):
            print("\n[FAIL] Restore test failed -- backup may be corrupt!", file=sys.stderr)
            sys.exit(1)

    print("\n[done] Backup complete.")
    print(f"  DB: {db_backup}")
    if storage_backup:
        print(f"  Storage: {storage_backup}")


if __name__ == "__main__":
    main()
