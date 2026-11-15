"""
EVORA Unified Database Adapter
==============================
Provides high-performance, concurrency-safe database operations supporting
Supabase PostgreSQL via `psycopg` (v3) and ConnectionPool, with safe, explicit
fallback to local SQLite for offline development and testing.

Key Capabilities:
- Supabase PostgreSQL with connection pooling (psycopg_pool.ConnectionPool)
- Production guard: prevents silent fallback to SQLite in production
- Credential masking: ensures passwords and sensitive URLs are never logged
- Unified EvoraRow abstraction: identical dictionary and tuple access across engines
- Dynamic query placeholder adaptation (? -> %s for PostgreSQL)
- Concurrency-safe rate-limiting support (PostgreSQL table/row locking & SQLite BEGIN IMMEDIATE)
- Unified exception handling (DatabaseIntegrityError for unique/FK violations)
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from dotenv import load_dotenv

# Automatically load environment variables from backend/.env and project root .env
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    import psycopg
    from psycopg import errors as pg_errors
    from psycopg_pool import ConnectionPool
    PSYCOPG_AVAILABLE = True
except ImportError:
    psycopg = None
    pg_errors = None
    ConnectionPool = None
    PSYCOPG_AVAILABLE = False


logger = logging.getLogger("evora.database")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL_RAW = (
    os.getenv("DATABASE_URL")
    or os.getenv("SUPABASE_DB_URL")
    or os.getenv("POSTGRES_URL")
    or ""
).strip()

ENVIRONMENT = (
    os.getenv("ENVIRONMENT")
    or os.getenv("ENV")
    or os.getenv("NODE_ENV")
    or "development"
).strip().lower()

EVORA_DB_PATH = Path(
    os.getenv(
        "EVORA_DB_PATH",
        str(Path(__file__).resolve().parent / "evora.db"),
    )
)

EVORA_DB_POOL_MIN = int(os.getenv("EVORA_DB_POOL_MIN", "1"))
EVORA_DB_POOL_MAX = int(os.getenv("EVORA_DB_POOL_MAX", "10"))
EVORA_DB_POOL_TIMEOUT = float(os.getenv("EVORA_DB_POOL_TIMEOUT", "30.0"))

# Global connection pool singleton for PostgreSQL
_pool: Optional[Any] = None
_pool_lock = threading.Lock()
_logged_fallback_warning = False


# ---------------------------------------------------------------------------
# Exceptions & Helpers
# ---------------------------------------------------------------------------

class DatabaseIntegrityError(Exception):
    """Raised when a unique constraint or foreign key constraint is violated."""
    pass


def mask_database_url(url: str) -> str:
    """
    Safely masks user credentials in a database URL for logging and error reporting.
    Never exposes passwords.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.password:
            user = parsed.username or "user"
            host = parsed.hostname or "localhost"
            port_part = f":{parsed.port}" if parsed.port else ""
            masked_netloc = f"{user}:***@{host}{port_part}"
            return urlunparse(parsed._replace(netloc=masked_netloc))
        return url
    except Exception:
        return "postgresql://***:***@***"


def is_postgres_configured() -> bool:
    """Returns True if a valid PostgreSQL/Supabase URL is present in the environment."""
    raw = (
        os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("POSTGRES_URL")
        or ""
    ).strip().lower()
    return bool(raw.startswith("postgresql://") or raw.startswith("postgres://"))


def get_database_backend() -> str:
    """Returns the name of the active database backend ('postgresql' or 'sqlite')."""
    return "postgresql" if is_postgres_configured() else "sqlite"


def normalize_postgres_url(raw_url: str) -> str:
    """
    Normalizes PostgreSQL URL for psycopg:
    - Replaces 'postgres://' with 'postgresql://'
    - Auto-encodes literal '@' inside password if unescaped
    - Ensures sslmode=require for remote hosts (e.g. Supabase cloud)
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # Safely handle unencoded '@' in password if multiple '@' exist
    if url.count("@") > 1 and "://" in url:
        prefix, rest = url.split("://", 1)
        last_at = rest.rfind("@")
        user_pass = rest[:last_at]
        host_db = rest[last_at + 1:]
        if ":" in user_pass:
            user, password = user_pass.split(":", 1)
            encoded_password = quote(password, safe="~-._")
            url = f"{prefix}://{user}:{encoded_password}@{host_db}"

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        is_remote = hostname not in ("localhost", "127.0.0.1", "")

        query_params = parse_qs(parsed.query)
        if is_remote and "sslmode" not in query_params:
            query_params["sslmode"] = ["require"]
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse(parsed._replace(query=new_query))
    except Exception as exc:
        logger.debug("URL normalization exception: %s", exc)

    return url


def adapt_query_for_postgres(sql: str) -> str:
    """
    Translates SQLite '?' placeholders to PostgreSQL '%s' placeholders,
    preserving '?' characters that appear inside single-quoted string literals.
    """
    if "?" not in sql:
        return sql
    parts = sql.split("'")
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("?", "%s")
    return "'".join(parts)


# ---------------------------------------------------------------------------
# EvoraRow: Drop-in Replacement for sqlite3.Row & DictRow
# ---------------------------------------------------------------------------

class EvoraRow(Mapping):
    """
    A unified, immutable row object that supports:
    1. Integer index access: row[0], row[1]
    2. Exact and case-insensitive column name lookup: row["id"], row["user_id"]
    3. Dictionary casting: dict(row)
    4. Mapping protocol: row.get("id"), "id" in row, row.keys(), row.values(), row.items()
    """
    __slots__ = ("_values", "_keys", "_dict", "_lower_map")

    def __init__(self, names: Sequence[Union[str, Any]], values: Sequence[Any]):
        self._values = tuple(values)
        self._keys = [
            n.name if hasattr(n, "name") else (n if isinstance(n, str) else str(n))
            for n in names
        ]
        self._dict: Dict[str, Any] = dict(zip(self._keys, self._values))
        self._lower_map: Dict[str, str] = {k.lower(): k for k in self._keys}

    def __getitem__(self, key: Union[int, slice, str]) -> Any:
        if isinstance(key, (int, slice)):
            return self._values[key]
        if key in self._dict:
            return self._dict[key]
        lower_key = str(key).lower()
        if lower_key in self._lower_map:
            return self._dict[self._lower_map[lower_key]]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: Any) -> bool:
        if not isinstance(key, str):
            return False
        return key in self._dict or key.lower() in self._lower_map

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def keys(self) -> List[str]:
        return list(self._keys)

    def values(self) -> Tuple[Any, ...]:
        return self._values

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._dict.items())

    def __repr__(self) -> str:
        return f"EvoraRow({self._dict})"


# ---------------------------------------------------------------------------
# EvoraCursor & EvoraConnection
# ---------------------------------------------------------------------------

class EvoraCursor:
    """Wraps underlying database cursors and yields EvoraRow instances."""

    def __init__(self, raw_cursor: Any):
        self._cursor = raw_cursor

    @property
    def description(self) -> Optional[Sequence[Any]]:
        return getattr(self._cursor, "description", None) if self._cursor else None

    @property
    def rowcount(self) -> int:
        return getattr(self._cursor, "rowcount", -1) if self._cursor else -1

    @property
    def lastrowid(self) -> Optional[Any]:
        return getattr(self._cursor, "lastrowid", None) if self._cursor else None

    def fetchone(self) -> Optional[EvoraRow]:
        if not self._cursor:
            return None
        row = self._cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, EvoraRow):
            return row
        desc = self._cursor.description
        if not desc:
            return None
        names = [col[0] if isinstance(col, (tuple, list)) else getattr(col, "name", str(col)) for col in desc]
        return EvoraRow(names, row)

    def fetchall(self) -> List[EvoraRow]:
        if not self._cursor:
            return []
        rows = self._cursor.fetchall()
        if not rows:
            return []
        desc = self._cursor.description
        if not desc:
            return []
        names = [col[0] if isinstance(col, (tuple, list)) else getattr(col, "name", str(col)) for col in desc]
        result: List[EvoraRow] = []
        for r in rows:
            if isinstance(r, EvoraRow):
                result.append(r)
            else:
                result.append(EvoraRow(names, r))
        return result

    def fetchmany(self, size: int = 1) -> List[EvoraRow]:
        if not self._cursor:
            return []
        rows = self._cursor.fetchmany(size)
        if not rows:
            return []
        desc = self._cursor.description
        if not desc:
            return []
        names = [col[0] if isinstance(col, (tuple, list)) else getattr(col, "name", str(col)) for col in desc]
        return [r if isinstance(r, EvoraRow) else EvoraRow(names, r) for r in rows]

    def __iter__(self) -> Iterator[EvoraRow]:
        while True:
            row = self.fetchone()
            if row is None:
                break
            yield row

    def __enter__(self) -> "EvoraCursor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor and hasattr(self._cursor, "close"):
            try:
                self._cursor.close()
            except Exception:
                pass


class EvoraConnection:
    """
    Unified database connection interface. Transparently manages:
    - Dialect-specific query formatting (? vs %s)
    - BEGIN IMMEDIATE vs table locking
    - SQLite PRAGMAs
    - Driver-agnostic integrity exception translation
    """

    def __init__(self, raw_conn: Any, is_postgres: bool):
        self._raw_conn = raw_conn
        self._is_postgres = is_postgres

    @property
    def is_postgres(self) -> bool:
        return self._is_postgres

    @property
    def raw_connection(self) -> Any:
        return self._raw_conn

    def execute(self, sql: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> EvoraCursor:
        stripped_sql = sql.strip()
        upper_sql = stripped_sql.upper()

        # Handle BEGIN IMMEDIATE: SQLite command for reserving write lock
        if upper_sql == "BEGIN IMMEDIATE":
            if self._is_postgres:
                # In PostgreSQL, transactions start automatically.
                return EvoraCursor(None)
            cursor = self._raw_conn.execute("BEGIN IMMEDIATE")
            return EvoraCursor(cursor)

        # Handle SQLite PRAGMAs: Ignore on PostgreSQL
        if upper_sql.startswith("PRAGMA"):
            if self._is_postgres:
                return EvoraCursor(None)
            cursor = self._raw_conn.execute(sql)
            return EvoraCursor(cursor)

        # Adapt SQL query for target database
        final_sql = adapt_query_for_postgres(sql) if self._is_postgres else sql

        try:
            if self._is_postgres:
                cursor = self._raw_conn.cursor()
                if params is not None:
                    cursor.execute(final_sql, params)
                else:
                    cursor.execute(final_sql)
                return EvoraCursor(cursor)
            else:
                if params is not None:
                    cursor = self._raw_conn.execute(final_sql, params)
                else:
                    cursor = self._raw_conn.execute(final_sql)
                return EvoraCursor(cursor)

        except Exception as exc:
            # Map driver-specific integrity errors to unified DatabaseIntegrityError
            if self._is_postgres:
                if pg_errors and isinstance(exc, (pg_errors.IntegrityError, pg_errors.UniqueViolation, pg_errors.ForeignKeyViolation)):
                    raise DatabaseIntegrityError(str(exc)) from exc
            else:
                if isinstance(exc, sqlite3.IntegrityError):
                    raise DatabaseIntegrityError(str(exc)) from exc
            raise

    def executemany(self, sql: str, seq_of_params: Sequence[Union[Sequence[Any], Dict[str, Any]]]) -> EvoraCursor:
        final_sql = adapt_query_for_postgres(sql) if self._is_postgres else sql
        try:
            if self._is_postgres:
                cursor = self._raw_conn.cursor()
                cursor.executemany(final_sql, seq_of_params)
                return EvoraCursor(cursor)
            else:
                cursor = self._raw_conn.executemany(final_sql, seq_of_params)
                return EvoraCursor(cursor)
        except Exception as exc:
            if self._is_postgres:
                if pg_errors and isinstance(exc, (pg_errors.IntegrityError, pg_errors.UniqueViolation, pg_errors.ForeignKeyViolation)):
                    raise DatabaseIntegrityError(str(exc)) from exc
            else:
                if isinstance(exc, sqlite3.IntegrityError):
                    raise DatabaseIntegrityError(str(exc)) from exc
            raise

    def begin_immediate(self, table_name: Optional[str] = None) -> None:
        """
        Acquires an immediate write or table lock to serialize concurrent operations.
        In SQLite: executes BEGIN IMMEDIATE.
        In PostgreSQL: executes LOCK TABLE <table_name> IN SHARE ROW EXCLUSIVE MODE.
        """
        if self._is_postgres:
            if table_name:
                try:
                    self.execute(f"LOCK TABLE {table_name} IN SHARE ROW EXCLUSIVE MODE")
                except Exception as exc:
                    logger.debug("PostgreSQL table lock notice on %s: %s", table_name, exc)
        else:
            self._raw_conn.execute("BEGIN IMMEDIATE")

    def commit(self) -> None:
        if self._raw_conn and hasattr(self._raw_conn, "commit"):
            self._raw_conn.commit()

    def rollback(self) -> None:
        if self._raw_conn and hasattr(self._raw_conn, "rollback"):
            self._raw_conn.rollback()

    def close(self) -> None:
        if self._raw_conn and hasattr(self._raw_conn, "close"):
            self._raw_conn.close()


# ---------------------------------------------------------------------------
# Connection Pool Management
# ---------------------------------------------------------------------------

def get_connection_pool() -> Any:
    """Lazily initializes and returns the PostgreSQL ConnectionPool singleton."""
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        if not PSYCOPG_AVAILABLE:
            raise RuntimeError(
                "psycopg and psycopg_pool must be installed to connect to PostgreSQL. "
                "Install with: pip install 'psycopg[binary,pool]>=3.2'"
            )

        raw_url = (
            os.getenv("DATABASE_URL")
            or os.getenv("SUPABASE_DB_URL")
            or os.getenv("POSTGRES_URL")
            or ""
        ).strip()

        if not raw_url:
            raise RuntimeError("DATABASE_URL is not configured.")

        normalized_url = normalize_postgres_url(raw_url)
        masked_url = mask_database_url(normalized_url)

        # Detect transaction poolers (such as Supabase port 6543)
        # In transaction pooling mode, client-side prepared statement caching must be disabled
        connect_kwargs: Dict[str, Any] = {}
        try:
            parsed = urlparse(normalized_url)
            if parsed.port == 6543 or os.getenv("EVORA_DB_PREPARE_THRESHOLD") == "0":
                connect_kwargs["prepare_threshold"] = None
        except Exception:
            pass

        try:
            logger.info("Initializing EVORA PostgreSQL ConnectionPool for: %s", masked_url)
            pool = ConnectionPool(
                conninfo=normalized_url,
                min_size=EVORA_DB_POOL_MIN,
                max_size=EVORA_DB_POOL_MAX,
                timeout=EVORA_DB_POOL_TIMEOUT,
                kwargs=connect_kwargs if connect_kwargs else None,
                open=True,
            )
            # Verify connectivity immediately
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            _pool = pool
            logger.info("EVORA PostgreSQL ConnectionPool verified and ready.")
            return _pool
        except Exception as exc:
            error_msg = (
                f"Failed to connect to PostgreSQL database ({masked_url}): {exc}. "
                "Please verify your DATABASE_URL, network connectivity, and Supabase credentials."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from exc


def close_connection_pool() -> None:
    """Closes all connections in the PostgreSQL ConnectionPool."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception as exc:
                logger.debug("Error closing connection pool: %s", exc)
            finally:
                _pool = None


# ---------------------------------------------------------------------------
# Database Context Manager & Initialization
# ---------------------------------------------------------------------------

@contextmanager
def database() -> Iterator[EvoraConnection]:
    """
    Main database context manager for EVORA.
    - If DATABASE_URL is configured: borrows a connection from the PostgreSQL ConnectionPool.
    - If DATABASE_URL is unset:
      - If ENVIRONMENT == 'production': raises a fatal configuration error.
      - If non-production: falls back explicitly to local SQLite for offline development/testing.
    """
    global _logged_fallback_warning

    if is_postgres_configured():
        pool = get_connection_pool()
        with pool.connection() as pg_conn:
            evora_conn = EvoraConnection(pg_conn, is_postgres=True)
            try:
                yield evora_conn
                evora_conn.commit()
            except Exception:
                evora_conn.rollback()
                raise
    else:
        # Check production guard
        env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or os.getenv("NODE_ENV") or "development").strip().lower()
        if env == "production":
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: DATABASE_URL is not configured. "
                "A PostgreSQL database URL is required in production environment. "
                "Silent fallback to SQLite is strictly forbidden."
            )

        # Explicit local development / test fallback
        db_path = Path(os.getenv("EVORA_DB_PATH", str(EVORA_DB_PATH)))
        if not _logged_fallback_warning:
            logger.warning(
                "[DATABASE] DATABASE_URL is not configured. "
                "Using local SQLite fallback for development/testing: %s",
                db_path,
            )
            _logged_fallback_warning = True

        db_path.parent.mkdir(parents=True, exist_ok=True)
        raw_sqlite = sqlite3.connect(db_path, timeout=10)
        raw_sqlite.execute("PRAGMA foreign_keys = ON")

        evora_conn = EvoraConnection(raw_sqlite, is_postgres=False)
        try:
            yield evora_conn
            evora_conn.commit()
        except Exception:
            evora_conn.rollback()
            raise
        finally:
            evora_conn.close()


def initialize_database() -> None:
    """
    Idempotently creates all 6 tables and 3 indexes across either PostgreSQL or SQLite.
    Faithfully reproduces column types, primary keys, foreign keys, cascade deletes,
    check constraints, and default values.
    """
    with database() as connection:
        # 1. users table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at BIGINT NOT NULL
            )
        """)

        # 2. sessions table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at BIGINT NOT NULL
            )
        """)

        # 3. login_attempts table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                attempt_key TEXT PRIMARY KEY,
                attempt_count INTEGER NOT NULL,
                window_started_at BIGINT NOT NULL
            )
        """)

        # 4. signup_attempts table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS signup_attempts (
                attempt_key TEXT PRIMARY KEY,
                attempt_count INTEGER NOT NULL,
                window_started_at BIGINT NOT NULL
            )
        """)

        # 5. datasets table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                storage_path TEXT NOT NULL,
                uploaded_at BIGINT NOT NULL,
                row_count INTEGER NOT NULL CHECK (row_count >= 0),
                column_count INTEGER NOT NULL CHECK (column_count >= 0),
                columns_json TEXT NOT NULL,
                date_start TEXT,
                date_end TEXT,
                status TEXT NOT NULL DEFAULT 'ready'
            )
        """)

        # 6. analysis_history table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
                analysis_type TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                input_summary_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'success'
            )
        """)

        # Indexes
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_datasets_user_uploaded
            ON datasets(user_id, uploaded_at DESC)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_user_created
            ON analysis_history(user_id, created_at DESC)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_dataset
            ON analysis_history(dataset_id)
        """)
