"""
BloomCraft AI - PostgreSQL Database Layer
Single source of truth for login credentials, sessions, guest devices, question
papers history, faculty question sets and custom exam templates.

Configuration (environment):
    DATABASE_URL   postgresql://user:password@host:5432/dbname   (required)
    DB_POOL_MIN    minimum pooled connections (default 1)
    DB_POOL_MAX    maximum pooled connections (default 10)
"""

import os
import logging
import threading
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger("BloomDB")

_pool = None
_pool_lock = threading.Lock()
_schema_ready = False


class DatabaseNotConfigured(RuntimeError):
    """Raised when DATABASE_URL is missing."""


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    username        TEXT NOT NULL,
    display_name    TEXT NOT NULL,
    department      TEXT NOT NULL DEFAULT '',
    role            TEXT NOT NULL DEFAULT 'Faculty Member',
    is_guest        BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash   TEXT,
    recovery_hash   TEXT,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower ON users (LOWER(username));

CREATE TABLE IF NOT EXISTS sessions (
    token_hash   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL,
    user_agent   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS guest_devices (
    device_hash      TEXT PRIMARY KEY,
    guest_user_id    TEXT REFERENCES users(user_id) ON DELETE SET NULL,
    papers_generated INTEGER NOT NULL DEFAULT 0,
    first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS history (
    paper_id        TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_code     TEXT,
    course_name     TEXT,
    exam_title      TEXT,
    total_marks     INTEGER,
    duration        TEXT,
    question_count  INTEGER,
    cognitive_index DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paper_data      JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_user_date ON history (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS question_sets (
    user_id    TEXT PRIMARY KEY,
    sets_data  JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS custom_templates (
    template_id   TEXT PRIMARY KEY,
    owner_id      TEXT,
    template_data JSONB NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def get_database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        raise DatabaseNotConfigured(
            "DATABASE_URL is not set. BloomCraft stores logins, sessions and papers in PostgreSQL. "
            "Set DATABASE_URL=postgresql://user:password@host:5432/bloomcraft "
            "(see backend/.env.example or docker-compose.yml)."
        )
    # Some hosts (Heroku / Render) still hand out the legacy scheme
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    int(os.environ.get("DB_POOL_MIN", "1")),
                    int(os.environ.get("DB_POOL_MAX", "10")),
                    dsn=get_database_url(),
                    connect_timeout=10,
                )
    return _pool


@contextmanager
def get_cursor(commit: bool = True):
    """Yield a dict cursor from the pool. Commits on success, rolls back on error."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        # Recover connections the server closed while idle
        if conn.closed:
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
        else:
            conn.rollback()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        pool.putconn(conn)


def ensure_schema() -> None:
    """Create all tables if they do not exist yet (idempotent)."""
    global _schema_ready
    if _schema_ready:
        return
    with _pool_lock:
        if _schema_ready:
            return
    with get_cursor() as cur:
        # Advisory lock so several gunicorn workers starting together do not race
        cur.execute("SELECT pg_advisory_lock(727274)")
        try:
            cur.execute(SCHEMA_SQL)
            # databases created before college templates were per-user
            cur.execute("ALTER TABLE custom_templates ADD COLUMN IF NOT EXISTS owner_id TEXT")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_templates_owner ON custom_templates (owner_id)")
        finally:
            cur.execute("SELECT pg_advisory_unlock(727274)")
    _schema_ready = True
    logger.info("PostgreSQL schema verified.")
