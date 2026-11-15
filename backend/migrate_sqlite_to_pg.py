"""
EVORA SQLite to Supabase PostgreSQL Data Migration Script
=========================================================
Migrates all existing records from local SQLite to Supabase PostgreSQL
without data loss.

Features:
- Idempotent: Uses `ON CONFLICT DO NOTHING` for safe re-runs.
- Dependency-order preservation: users -> sessions -> login_attempts -> signup_attempts -> datasets -> analysis_history.
- Preserves all primary keys (UUIDs), foreign key relations, timestamps, and JSON payloads.
- Masked logging: Never prints passwords or database credentials.
- Supports `--dry-run` to preview counts before transferring data.

Usage:
    python backend/migrate_sqlite_to_pg.py
    python backend/migrate_sqlite_to_pg.py --dry-run
    python backend/migrate_sqlite_to_pg.py --sqlite-path ./backend/data/evora.db --database-url "postgresql://..."
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import (
    DatabaseIntegrityError,
    EvoraConnection,
    close_connection_pool,
    database,
    initialize_database,
    is_postgres_configured,
    mask_database_url,
    normalize_postgres_url,
)

try:
    import psycopg
except ImportError:
    psycopg = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("evora.migration")


TABLE_ORDER = [
    "users",
    "sessions",
    "login_attempts",
    "signup_attempts",
    "datasets",
    "analysis_history",
]

TABLE_COLUMNS = {
    "users": ["id", "full_name", "email", "password_hash", "created_at"],
    "sessions": ["token_hash", "user_id", "expires_at"],
    "login_attempts": ["attempt_key", "attempt_count", "window_started_at"],
    "signup_attempts": ["attempt_key", "attempt_count", "window_started_at"],
    "datasets": [
        "id", "user_id", "original_filename", "stored_filename",
        "storage_path", "uploaded_at", "row_count", "column_count",
        "columns_json", "date_start", "date_end", "status",
    ],
    "analysis_history": [
        "id", "user_id", "dataset_id", "analysis_type", "created_at",
        "input_summary_json", "result_json", "status",
    ],
}

TABLE_CONFLICT_KEYS = {
    "users": "id",
    "sessions": "token_hash",
    "login_attempts": "attempt_key",
    "signup_attempts": "attempt_key",
    "datasets": "id",
    "analysis_history": "id",
}


def find_sqlite_db(custom_path: str | None = None) -> Path:
    """Finds the source SQLite database file."""
    if custom_path:
        p = Path(custom_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Specified SQLite file does not exist: {p}")
        return p

    candidates = [
        os.getenv("EVORA_DB_PATH"),
        str(PROJECT_ROOT / "backend" / "data" / "evora.db"),
        str(PROJECT_ROOT / "backend" / "evora.db"),
        str(PROJECT_ROOT / "evora.db"),
    ]

    for c in candidates:
        if c:
            p = Path(c).resolve()
            if p.is_file():
                return p

    # Default location even if not yet populated
    default_p = (PROJECT_ROOT / "backend" / "evora.db").resolve()
    return default_p


def get_sqlite_table_counts(sqlite_path: Path) -> dict[str, int]:
    """Inspects row counts in the SQLite database."""
    counts = {}
    if not sqlite_path.is_file():
        return {tbl: 0 for tbl in TABLE_ORDER}

    conn = sqlite3.connect(sqlite_path)
    try:
        cur = conn.cursor()
        for table in TABLE_ORDER:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0
    finally:
        conn.close()

    return counts


def migrate(
    sqlite_path: Path,
    target_pg_url: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Transfers records from SQLite to PostgreSQL in dependency order."""
    if not psycopg:
        raise RuntimeError("psycopg must be installed to run data migration.")

    normalized_url = normalize_postgres_url(target_pg_url)
    masked_url = mask_database_url(normalized_url)

    logger.info("Source SQLite: %s", sqlite_path)
    logger.info("Target PostgreSQL: %s", masked_url)

    sqlite_counts = get_sqlite_table_counts(sqlite_path)
    total_source_rows = sum(sqlite_counts.values())

    logger.info("Found %d total records across %d tables in SQLite.", total_source_rows, len(TABLE_ORDER))
    for tbl, cnt in sqlite_counts.items():
        logger.info("  - %s: %d records", tbl, cnt)

    if dry_run:
        logger.info("[DRY RUN] Dry run complete. No database modifications were performed.")
        return sqlite_counts

    if not sqlite_path.is_file() or total_source_rows == 0:
        logger.info("No records found in SQLite to migrate. Initializing target PostgreSQL tables...")
        os.environ["DATABASE_URL"] = normalized_url
        initialize_database()
        logger.info("Target PostgreSQL tables initialized successfully.")
        return {tbl: 0 for tbl in TABLE_ORDER}

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to PostgreSQL directly for migration batching
    pg_conn = psycopg.connect(normalized_url, prepare_threshold=None)

    migrated_counts: dict[str, int] = {tbl: 0 for tbl in TABLE_ORDER}

    try:
        # Initialize schema in PostgreSQL
        os.environ["DATABASE_URL"] = normalized_url
        initialize_database()

        with pg_conn.transaction():
            pg_cur = pg_conn.cursor()

            for table in TABLE_ORDER:
                cols = TABLE_COLUMNS[table]
                conflict_col = TABLE_CONFLICT_KEYS[table]
                col_names_str = ", ".join(cols)
                placeholders = ", ".join(["%s"] * len(cols))

                insert_sql = (
                    f"INSERT INTO {table} ({col_names_str}) "
                    f"VALUES ({placeholders}) "
                    f"ON CONFLICT ({conflict_col}) DO NOTHING"
                )

                sql_cur = sqlite_conn.cursor()
                try:
                    sql_cur.execute(f"SELECT {col_names_str} FROM {table}")
                    rows = sql_cur.fetchall()
                except sqlite3.OperationalError:
                    rows = []

                if not rows:
                    logger.info("  Table '%s': 0 records to migrate.", table)
                    continue

                batch_data = [tuple(r[c] for c in cols) for r in rows]
                pg_cur.executemany(insert_sql, batch_data)
                migrated_counts[table] = len(batch_data)
                logger.info("  Table '%s': Migrated %d records.", table, len(batch_data))

        logger.info("--- Migration Completed Successfully ---")
        for tbl, cnt in migrated_counts.items():
            logger.info("  Migrated %s: %d rows", tbl, cnt)

    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()
        close_connection_pool()

    return migrated_counts


def main():
    parser = argparse.ArgumentParser(description="EVORA SQLite to Supabase PostgreSQL Migration")
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Path to the source SQLite database file",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="PostgreSQL connection string (defaults to DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect source counts without writing to target database",
    )

    args = parser.parse_args()

    sqlite_path = find_sqlite_db(args.sqlite_path)
    target_url = (
        args.database_url
        or os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("POSTGRES_URL")
    )

    if not target_url and not args.dry_run:
        logger.error(
            "Target PostgreSQL URL not provided. Set DATABASE_URL or pass --database-url. "
            "Pass --dry-run to only inspect local SQLite data."
        )
        sys.exit(1)

    migrate(
        sqlite_path=sqlite_path,
        target_pg_url=target_url or "postgresql://localhost:5432/evora",
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
