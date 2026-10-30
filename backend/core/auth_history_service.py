"""
BloomCraft AI - User Authentication & Past Paper History Service (SQLite Engine)
High-performance, memory-efficient SQLite persistence for academic user profiles,
sessions, and examination paper archives with zero external dependencies.
"""

import os
import json
import time
import uuid
import hashlib
import hmac
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Any, Optional

DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_FILE = os.path.join(DATA_DIR, "bloomcraft.db")
USER_STORE_FILE = os.path.join(DATA_DIR, "user_store.json")
SEED_USERS_FILE = os.path.join(DATA_DIR, "seed_users.json")


@contextmanager
def _get_connection():
    """Return a configured SQLite database connection with row factory, WAL mode, and guaranteed auto-close."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    """Salted PBKDF2-SHA256 hash, stored as 'pbkdf2$<salt>$<hash>'."""
    salt = salt or uuid.uuid4().hex
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"pbkdf2${salt}${digest}"


def _verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or not password:
        return False
    if stored.startswith("pbkdf2$"):
        try:
            _, salt, _digest = stored.split("$", 2)
        except ValueError:
            return False
        return hmac.compare_digest(_hash_password(password, salt), stored)
    # legacy unsalted sha256 hashes
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)


def _sync_all_users_to_seed(conn: sqlite3.Connection) -> None:
    """Backup active faculty accounts to seed_users.json so credentials survive resets."""
    try:
        cur = conn.execute("SELECT user_id, username, display_name, department, role, password_hash, created_at FROM users")
        records = [dict(row) for row in cur.fetchall()]
        with open(SEED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": records}, f, indent=2)
    except Exception:
        pass


def _init_db() -> None:
    """Initialize database tables and indexes, and restore persistent accounts."""
    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE COLLATE NOCASE,
                display_name TEXT,
                department TEXT,
                role TEXT,
                password_hash TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS history (
                paper_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                course_code TEXT,
                course_name TEXT,
                exam_title TEXT,
                total_marks INTEGER,
                duration TEXT,
                question_count INTEGER,
                cognitive_index REAL,
                created_at TEXT,
                paper_data TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_history_user_date ON history(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);
        """)

        # 1. Restore from backup seed file if present
        _restore_from_seed(conn)

        # 2. Migrate legacy user_store.json or user_store.json.migrated if present
        _migrate_legacy_json(conn)

        # 3. Ensure demo academic accounts exist for automated verification & faculty testing
        _seed_demo_accounts(conn)

        # 4. Save synced seed backup to disk
        _sync_all_users_to_seed(conn)


def _restore_from_seed(conn: sqlite3.Connection) -> None:
    """Restore registered faculty accounts from seed_users.json if database was re-created."""
    if not os.path.exists(SEED_USERS_FILE):
        return
    try:
        with open(SEED_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for u in data.get("users", []):
            conn.execute("""
                INSERT OR IGNORE INTO users (user_id, username, display_name, department, role, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                u.get("user_id"),
                u.get("username"),
                u.get("display_name"),
                u.get("department", "Computer Science"),
                u.get("role", "Faculty"),
                u.get("password_hash"),
                u.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            ))
        conn.commit()
    except Exception:
        pass


def _migrate_legacy_json(conn: sqlite3.Connection) -> None:
    """One-time migration from memory-heavy user_store.json into SQLite tables."""
    source_file = USER_STORE_FILE if os.path.exists(USER_STORE_FILE) else USER_STORE_FILE + ".migrated"
    if not os.path.exists(source_file):
        return

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        users = data.get("users", {})
        for u in users.values():
            conn.execute("""
                INSERT OR IGNORE INTO users (user_id, username, display_name, department, role, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                u.get("user_id"),
                u.get("username"),
                u.get("display_name"),
                u.get("department", "Computer Science"),
                u.get("role", "Faculty"),
                u.get("password_hash"),
                u.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            ))

        sessions = data.get("sessions", {})
        for token, sess in sessions.items():
            conn.execute("""
                INSERT OR IGNORE INTO sessions (token, user_id, created_at)
                VALUES (?, ?, ?)
            """, (token, sess.get("user_id"), sess.get("created_at", time.time())))

        history = data.get("history", {})
        for uid, papers in history.items():
            for p in papers:
                conn.execute("""
                    INSERT OR IGNORE INTO history (
                        paper_id, user_id, course_code, course_name, exam_title,
                        total_marks, duration, question_count, cognitive_index,
                        created_at, paper_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get("paper_id"),
                    uid,
                    p.get("course_code"),
                    p.get("course_name"),
                    p.get("exam_title"),
                    p.get("total_marks", 100),
                    p.get("duration", "3 Hours"),
                    p.get("question_count", 0),
                    p.get("cognitive_index", 3.0),
                    p.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
                    json.dumps(p.get("paper_data", {}))
                ))

        conn.commit()

        if os.path.exists(USER_STORE_FILE):
            bak_file = USER_STORE_FILE + ".migrated"
            if not os.path.exists(bak_file):
                os.rename(USER_STORE_FILE, bak_file)
    except Exception:
        pass


def _seed_demo_accounts(conn: sqlite3.Connection) -> None:
    """Seeds standard demo faculty profiles for testing and demonstration if absent."""
    demo_users = [
        ("usr_turing", "prof.turing", "Prof. Alan Turing", "Computer Science & AI", "password123"),
        ("usr_hopper", "dr.hopper", "Dr. Grace Hopper", "Information Systems", "password123"),
        ("usr_2f4bb8b7", "pranav11", "Pranav Suryawanshi", "Data Science", "password123"),
    ]
    for uid, uname, dname, dept, pwd in demo_users:
        cur = conn.execute("SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (uname,))
        if not cur.fetchone():
            conn.execute("""
                INSERT OR IGNORE INTO users (user_id, username, display_name, department, role, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (uid, uname, dname, dept, "Faculty Member", _hash_password(pwd), time.strftime("%Y-%m-%dT%H:%M:%SZ")))
    conn.commit()


# Initialize database on module load
_init_db()


def create_session(user_id: str) -> str:
    """Create and persist a secure session token for an authenticated faculty user."""
    token = f"tok_{uuid.uuid4().hex}"
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, time.time())
        )
        conn.commit()
    return token


def get_user_by_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve and authenticate faculty profile using session token."""
    if not token:
        return None
    clean_token = token.replace("Bearer ", "").strip()
    with _get_connection() as conn:
        cur = conn.execute("""
            SELECT u.user_id, u.username, u.display_name, u.department, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.token = ?
        """, (clean_token,))
        row = cur.fetchone()
        if row:
            return {
                "user_id": row["user_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "department": row["department"] or "Computer Science",
                "role": row["role"] or "Faculty"
            }
    return None


def destroy_session(token: Optional[str]) -> bool:
    """Revoke session token on logout."""
    if not token:
        return False
    clean_token = token.replace("Bearer ", "").strip()
    with _get_connection() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE token = ?", (clean_token,))
        conn.commit()
        return cur.rowcount > 0


def authenticate_user(username: str, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the teacher profile when credentials match.
    Matches username, user_id, or display_name flexibly to prevent locked-out faculty.
    Handles surrounding whitespace gracefully for mobile/autofill compatibility.
    """
    raw_ident = (username or "").strip()
    clean_username = raw_ident.lower().replace(" ", "_")
    if not clean_username or not password:
        return None

    with _get_connection() as conn:
        cur = conn.execute("""
            SELECT user_id, username, display_name, department, role, password_hash
            FROM users
            WHERE username = ? COLLATE NOCASE
               OR user_id = ? COLLATE NOCASE
               OR display_name = ? COLLATE NOCASE
               OR username = ? COLLATE NOCASE
        """, (clean_username, raw_ident, raw_ident, raw_ident))
        row = cur.fetchone()
        if not row:
            return None

        stored_hash = row["password_hash"]
        verified = _verify_password(password, stored_hash)
        if not verified and password.strip() != password:
            verified = _verify_password(password.strip(), stored_hash)
        if not verified:
            return None

        # Upgrade legacy hash to PBKDF2 if needed
        if not str(stored_hash).startswith("pbkdf2$"):
            new_hash = _hash_password(password.strip())
            conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_hash, row["user_id"]))
            conn.commit()
            _sync_all_users_to_seed(conn)

        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "department": row["department"] or "",
            "role": row["role"] or "Faculty"
        }


def register_user(username: str, display_name: str, department: str = "", password: str = "") -> Dict[str, Any]:
    """Register a new faculty account."""
    raw_username = (username or "").strip()
    clean_username = raw_username.lower().replace(" ", "_")
    clean_pwd = (password or "").strip()

    if not clean_username:
        raise ValueError("Username is required.")
    if len(clean_pwd) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    with _get_connection() as conn:
        cur = conn.execute("""
            SELECT 1 FROM users 
            WHERE username = ? COLLATE NOCASE 
               OR user_id = ? COLLATE NOCASE
               OR username = ? COLLATE NOCASE
        """, (clean_username, raw_username, raw_username))
        if cur.fetchone():
            raise ValueError("Username is already registered. Please choose another or log in.")

        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        pwd_hash = _hash_password(clean_pwd)
        disp_name = display_name.strip() or clean_username.title()
        dept_name = department.strip()
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        conn.execute("""
            INSERT INTO users (user_id, username, display_name, department, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, clean_username, disp_name, dept_name, "Faculty Member", pwd_hash, created_at))
        conn.commit()

        _sync_all_users_to_seed(conn)

        return {
            "user_id": user_id,
            "username": clean_username,
            "display_name": disp_name,
            "department": dept_name,
            "role": "Faculty Member"
        }


def reset_user_password(username: str, new_password: str) -> bool:
    """Reset the password of an EXISTING teacher account (never creates accounts)."""
    raw_ident = (username or "").strip()
    clean_username = raw_ident.lower().replace(" ", "_")
    clean_pwd = (new_password or "").strip()
    if not clean_username or not clean_pwd or len(clean_pwd) < 6:
        return False

    with _get_connection() as conn:
        cur = conn.execute("""
            SELECT user_id FROM users 
            WHERE username = ? COLLATE NOCASE 
               OR user_id = ? COLLATE NOCASE 
               OR display_name = ? COLLATE NOCASE
               OR username = ? COLLATE NOCASE
        """, (clean_username, raw_ident, raw_ident, raw_ident))
        row = cur.fetchone()
        if not row:
            return False

        user_id = row["user_id"]
        new_hash = _hash_password(clean_pwd)
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_hash, user_id))
        # Revoke all active sessions for this user across all devices
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.commit()

        _sync_all_users_to_seed(conn)
        return True


def list_users() -> List[Dict[str, Any]]:
    """Return public metadata of available user profiles."""
    with _get_connection() as conn:
        cur = conn.execute("SELECT user_id, username, display_name, department, role FROM users ORDER BY username ASC")
        return [
            {
                "user_id": row["user_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "department": row["department"] or "",
                "role": row["role"] or "Faculty"
            }
            for row in cur.fetchall()
        ]


def save_paper_to_history(user_id: str, paper_data: Dict[str, Any]) -> str:
    """Saves a newly synthesized question paper to the user's history."""
    paper_id = f"pap_{uuid.uuid4().hex[:10]}"
    course_code = paper_data.get("course_code", "EXAM")
    course_name = paper_data.get("course_name", "Curriculum Examination")
    exam_title = paper_data.get("exam_title", "Semester Examination")
    total_marks = paper_data.get("total_marks", 100)
    duration = paper_data.get("duration", "3 Hours")
    question_count = len(paper_data.get("all_questions", []))
    cognitive_index = paper_data.get("analytics", {}).get("cognitive_index", 3.0)
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    paper_json = json.dumps(paper_data)

    with _get_connection() as conn:
        conn.execute("""
            INSERT INTO history (
                paper_id, user_id, course_code, course_name, exam_title,
                total_marks, duration, question_count, cognitive_index,
                created_at, paper_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_id, user_id, course_code, course_name, exam_title,
            total_marks, duration, question_count, cognitive_index,
            created_at, paper_json
        ))

        # Enforce maximum 30 history records per faculty member to keep disk usage lean
        conn.execute("""
            DELETE FROM history
            WHERE user_id = ? AND paper_id NOT IN (
                SELECT paper_id FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 30
            )
        """, (user_id, user_id))

        conn.commit()

    return paper_id


def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve lightweight history summaries for a user.
    NOTE: Heavy paper_data JSON blobs are NOT loaded from disk, keeping RAM consumption minimal!
    """
    with _get_connection() as conn:
        cur = conn.execute("""
            SELECT paper_id, course_code, course_name, exam_title, total_marks,
                   duration, question_count, cognitive_index, created_at
            FROM history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 30
        """, (user_id,))
        return [
            {
                "paper_id": row["paper_id"],
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "exam_title": row["exam_title"],
                "total_marks": row["total_marks"],
                "duration": row["duration"],
                "question_count": row["question_count"],
                "cognitive_index": row["cognitive_index"],
                "created_at": row["created_at"]
            }
            for row in cur.fetchall()
        ]


def get_history_paper(user_id: str, paper_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete past question paper JSON by ID on-demand."""
    with _get_connection() as conn:
        cur = conn.execute("""
            SELECT paper_data
            FROM history
            WHERE user_id = ? AND paper_id = ?
        """, (user_id, paper_id))
        row = cur.fetchone()
        if row and row["paper_data"]:
            try:
                return json.loads(row["paper_data"])
            except Exception:
                return None
    return None


def delete_history_paper(user_id: str, paper_id: str) -> bool:
    """Delete a past paper from history."""
    with _get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM history WHERE user_id = ? AND paper_id = ?",
            (user_id, paper_id)
        )
        conn.commit()
        return cur.rowcount > 0
