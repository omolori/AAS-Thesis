"""Migrate all runs from the local SQLite database to Supabase.

Run this once after setting up Supabase to upload your existing runs.
After migration, new runs go directly to Supabase automatically.

Usage:
    # Set DATABASE_URL first (or put it in .streamlit/secrets.toml)
    $env:DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
    python scripts/migrate_to_supabase.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config_loader import config
from digital_twin_core.recorder import (
    list_runs, load_run, _use_supabase, _pg_init, _pg_save_run, init_db,
)


def main() -> int:
    db_path = PROJECT_ROOT / config["storage"]["db_path"]

    if not _use_supabase():
        print("ERROR: DATABASE_URL is not set.")
        print("Set it before running:")
        print('  $env:DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"')
        return 1

    if not db_path.exists():
        print(f"No local database found at {db_path}")
        print("Nothing to migrate.")
        return 0

    # Read from local SQLite
    import os
    db_url_backup = os.environ.get("DATABASE_URL")
    os.environ.pop("DATABASE_URL", None)

    # Temporarily disable Supabase to read from SQLite
    import digital_twin_core.recorder as rec
    original = rec._get_database_url
    rec._get_database_url = lambda: None

    runs = list_runs(db_path)
    print(f"Found {len(runs)} runs in local SQLite database.")

    if not runs:
        rec._get_database_url = original
        return 0

    # Restore Supabase connection
    rec._get_database_url = original
    if db_url_backup:
        os.environ["DATABASE_URL"] = db_url_backup

    # Init Supabase tables
    _pg_init()

    # Migrate each run
    for i, meta in enumerate(runs, 1):
        print(f"  [{i}/{len(runs)}] {meta.pipeline}  {meta.run_id[:16]}...", end=" ", flush=True)
        rec._get_database_url = lambda: None
        _, samples = load_run(db_path, meta.run_id)
        rec._get_database_url = original
        if db_url_backup:
            os.environ["DATABASE_URL"] = db_url_backup
        _pg_save_run(meta, samples)
        print(f"OK  ({len(samples)} samples)")

    print(f"\nMigration complete. {len(runs)} runs uploaded to Supabase.")
    print("New runs will now go directly to Supabase automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
