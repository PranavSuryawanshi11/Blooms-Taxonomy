"""
BloomCraft AI - Authentication, Guest Access & Past Paper History (PostgreSQL)

Security model
--------------
* Passwords are hashed with Argon2id (memory-hard, per-user random salt, auto-upgrading parameters).
* Session tokens are 384-bit random values; only their SHA-256 digest is stored, so a database
  leak does not expose usable sessions. Sessions live 90 days and slide forward while in use,
  so faculty stay signed in for a long time without re-entering credentials.
* Repeated wrong passwords lock the account for a short period (brute-force protection).
* Password reset requires a one-time recovery code issued at registration (stored hashed too).
* Guest access is limited to ONE generated paper per device (device-id hash stored server-side).
"""

import re
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple

import psycopg2.extras
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from core.database import get_cursor, ensure_schema

# ----------------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------------
SESSION_TTL_DAYS = 90            # faculty sessions (sliding)
GUEST_SESSION_TTL_DAYS = 30
SESSION_TOUCH_INTERVAL_SEC = 3600
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
GUEST_PAPER_LIMIT = 1
HISTORY_LIMIT_PER_USER = 30

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
_DUMMY_HASH = _hasher.hash("timing-equaliser")

_COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890", "qwerty123",
    "qwertyuiop", "iloveyou1", "admin123", "welcome1", "welcome123", "letmein123", "abc12345",
    "changeme1", "teacher123", "faculty123", "college123", "bloomcraft1",
}

_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


def init_service() -> None:
    """Create tables (idempotent). Called once at application start-up."""
    ensure_schema()
    with get_cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE expires_at < NOW()")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_secret(secret: str) -> str:
    return _hasher.hash(secret)


def _verify_secret(secret: str, stored: Optional[str]) -> bool:
    if not stored or not secret:
        return False
    try:
        return _hasher.verify(stored, secret)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def normalize_username(username: str) -> str:
    return re.sub(r"\s+", "_", (username or "").strip().lower())


def validate_password_strength(password: str, username: str = "") -> Optional[str]:
    """Return an error message when the password is too weak, otherwise None."""
    pwd = password or ""
    if len(pwd) < 8:
        return "Password must be at least 8 characters long."
    if len(pwd) > 128:
        return "Password must be 128 characters or fewer."
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        return "Password must contain at least one letter and one number."
    if pwd.lower() in _COMMON_PASSWORDS:
        return "That password is too common. Please choose a less predictable one."
    if username and pwd.lower() == username.lower():
        return "Password must not be the same as your username."
    return None


def _public_user(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "department": row.get("department") or "",
        "role": row.get("role") or "Faculty Member",
        "is_guest": bool(row.get("is_guest")),
    }


def _generate_recovery_code() -> str:
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no look-alike characters
    raw = "".join(secrets.choice(alphabet) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def _clean_recovery_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


# ----------------------------------------------------------------------------
# Sessions
# ----------------------------------------------------------------------------
def create_session(user_id: str, user_agent: str = "", is_guest: bool = False) -> str:
    """Create a long-lived session; returns the raw token (never stored)."""
    token = secrets.token_urlsafe(48)
    ttl = GUEST_SESSION_TTL_DAYS if is_guest else SESSION_TTL_DAYS
    expires = _now() + timedelta(days=ttl)
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, user_agent) VALUES (%s, %s, %s, %s)",
            (_sha256(token), user_id, expires, (user_agent or "")[:300]),
        )
        cur.execute("DELETE FROM sessions WHERE user_id = %s AND expires_at < NOW()", (user_id,))
    return token


def _clean_token(token: Optional[str]) -> str:
    return (token or "").replace("Bearer ", "").strip()


def get_user_by_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve the user for a session token and slide its expiry forward."""
    clean = _clean_token(token)
    if not clean:
        return None
    token_hash = _sha256(clean)
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.user_id, u.username, u.display_name, u.department, u.role, u.is_guest,
                   s.last_used_at
            FROM sessions s JOIN users u ON u.user_id = s.user_id
            WHERE s.token_hash = %s AND s.expires_at > NOW()
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        if not row:
            return None
        if (_now() - row["last_used_at"]).total_seconds() > SESSION_TOUCH_INTERVAL_SEC:
            ttl = GUEST_SESSION_TTL_DAYS if row["is_guest"] else SESSION_TTL_DAYS
            cur.execute(
                "UPDATE sessions SET last_used_at = NOW(), expires_at = %s WHERE token_hash = %s",
                (_now() + timedelta(days=ttl), token_hash),
            )
        return _public_user(row)


def destroy_session(token: Optional[str]) -> bool:
    clean = _clean_token(token)
    if not clean:
        return False
    with get_cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE token_hash = %s", (_sha256(clean),))
        return cur.rowcount > 0


# ----------------------------------------------------------------------------
# Registration / login / password reset
# ----------------------------------------------------------------------------
def register_user(username: str, display_name: str, department: str = "", password: str = "") -> Dict[str, Any]:
    """Register a faculty account. Returns the public user plus a one-time `recovery_code`."""
    clean_username = normalize_username(username)
    if not _USERNAME_RE.match(clean_username):
        raise ValueError("Username must be 3-32 characters (letters, numbers, dot, dash or underscore).")
    if clean_username.startswith("guest"):
        raise ValueError("Usernames starting with 'guest' are reserved. Please choose another.")
    weak = validate_password_strength(password, clean_username)
    if weak:
        raise ValueError(weak)

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    disp_name = (display_name or "").strip() or clean_username.title()
    dept = (department or "").strip()
    recovery_code = _generate_recovery_code()

    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE LOWER(username) = %s", (clean_username,))
        if cur.fetchone():
            raise ValueError("Username is already registered. Please choose another or sign in.")
        cur.execute(
            """
            INSERT INTO users (user_id, username, display_name, department, role, is_guest,
                               password_hash, recovery_hash)
            VALUES (%s, %s, %s, %s, 'Faculty Member', FALSE, %s, %s)
            """,
            (user_id, clean_username, disp_name, dept,
             _hash_secret(password), _hash_secret(_clean_recovery_code(recovery_code))),
        )

    return {
        "user_id": user_id,
        "username": clean_username,
        "display_name": disp_name,
        "department": dept,
        "role": "Faculty Member",
        "is_guest": False,
        "recovery_code": recovery_code,
    }


def authenticate_user(username: str, password: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Verify credentials. Returns (user, error). `error` is a user-facing message when the
    account is temporarily locked; otherwise None (a bad password just yields (None, None)).
    """
    clean_username = normalize_username(username)
    if not clean_username or not password:
        return None, None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT user_id, username, display_name, department, role, is_guest, password_hash,
                   failed_attempts, locked_until
            FROM users WHERE LOWER(username) = %s AND is_guest = FALSE
            FOR UPDATE
            """,
            (clean_username,),
        )
        row = cur.fetchone()
        if not row:
            # Burn comparable time so unknown usernames are not distinguishable by latency
            _verify_secret(password, _DUMMY_HASH)
            return None, None

        if row["locked_until"] and row["locked_until"] > _now():
            mins = max(1, int((row["locked_until"] - _now()).total_seconds() // 60) + 1)
            return None, f"Too many failed attempts. Try again in about {mins} minute(s)."

        if not _verify_secret(password, row["password_hash"]):
            attempts = row["failed_attempts"] + 1
            if attempts >= MAX_FAILED_ATTEMPTS:
                cur.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = %s WHERE user_id = %s",
                    (_now() + timedelta(minutes=LOCKOUT_MINUTES), row["user_id"]),
                )
            else:
                cur.execute("UPDATE users SET failed_attempts = %s WHERE user_id = %s", (attempts, row["user_id"]))
            return None, None

        new_hash = None
        try:
            if _hasher.check_needs_rehash(row["password_hash"]):
                new_hash = _hash_secret(password)
        except Exception:
            pass
        cur.execute(
            """
            UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login_at = NOW(),
                   password_hash = COALESCE(%s, password_hash)
            WHERE user_id = %s
            """,
            (new_hash, row["user_id"]),
        )
        return _public_user(row), None


def reset_user_password(username: str, new_password: str, recovery_code: str) -> Tuple[bool, str, Optional[str]]:
    """
    Reset the password of an existing faculty account using its recovery code.
    Returns (ok, message, new_recovery_code). All active sessions are revoked.
    """
    clean_username = normalize_username(username)
    weak = validate_password_strength(new_password, clean_username)
    if weak:
        return False, weak, None

    generic = "Username or recovery code is incorrect."
    with get_cursor() as cur:
        cur.execute(
            "SELECT user_id, recovery_hash, locked_until, failed_attempts FROM users "
            "WHERE LOWER(username) = %s AND is_guest = FALSE FOR UPDATE",
            (clean_username,),
        )
        row = cur.fetchone()
        if not row:
            _verify_secret("x", _DUMMY_HASH)
            return False, generic, None
        if row["locked_until"] and row["locked_until"] > _now():
            return False, "Too many failed attempts. Try again later.", None
        if not _verify_secret(_clean_recovery_code(recovery_code), row["recovery_hash"]):
            attempts = row["failed_attempts"] + 1
            if attempts >= MAX_FAILED_ATTEMPTS:
                cur.execute("UPDATE users SET failed_attempts = 0, locked_until = %s WHERE user_id = %s",
                            (_now() + timedelta(minutes=LOCKOUT_MINUTES), row["user_id"]))
            else:
                cur.execute("UPDATE users SET failed_attempts = %s WHERE user_id = %s", (attempts, row["user_id"]))
            return False, generic, None

        new_code = _generate_recovery_code()
        cur.execute(
            "UPDATE users SET password_hash = %s, recovery_hash = %s, failed_attempts = 0, locked_until = NULL "
            "WHERE user_id = %s",
            (_hash_secret(new_password), _hash_secret(_clean_recovery_code(new_code)), row["user_id"]),
        )
        cur.execute("DELETE FROM sessions WHERE user_id = %s", (row["user_id"],))
        return True, "Password updated. Your previous sessions were signed out.", new_code


def list_users() -> List[Dict[str, Any]]:
    with get_cursor(commit=False) as cur:
        cur.execute(
            "SELECT user_id, username, display_name, department, role, is_guest FROM users "
            "WHERE is_guest = FALSE ORDER BY username ASC"
        )
        return [_public_user(r) for r in cur.fetchall()]


# ----------------------------------------------------------------------------
# Guest access (one paper per device)
# ----------------------------------------------------------------------------
def _device_hashes(device_ids: List[str]) -> List[str]:
    seen, out = set(), []
    for d in device_ids:
        d = (d or "").strip()
        if 16 <= len(d) <= 128 and re.match(r"^[A-Za-z0-9_\-]+$", d):
            h = _sha256("bloomcraft-device:" + d)
            if h not in seen:
                seen.add(h)
                out.append(h)
    return out


def create_guest_session(device_ids: List[str], user_agent: str = "") -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]:
    """
    Sign in as guest. The same device always maps back to the same guest profile, so the
    one-paper quota cannot be reset by simply pressing "Continue as Guest" again.
    """
    hashes = _device_hashes(device_ids)
    if not hashes:
        return None, None, {"error": "Could not identify this device. Please refresh the page and try again."}

    with get_cursor() as cur:
        cur.execute(
            "SELECT device_hash, guest_user_id, papers_generated FROM guest_devices "
            "WHERE device_hash = ANY(%s) FOR UPDATE",
            (hashes,),
        )
        rows = cur.fetchall()
        used = max([r["papers_generated"] for r in rows], default=0)
        guest_user_id = next((r["guest_user_id"] for r in rows if r["guest_user_id"]), None)

        user_row = None
        if guest_user_id:
            cur.execute(
                "SELECT user_id, username, display_name, department, role, is_guest FROM users WHERE user_id = %s",
                (guest_user_id,),
            )
            user_row = cur.fetchone()

        if not user_row:
            guest_user_id = f"gst_{uuid.uuid4().hex[:12]}"
            username = f"guest_{uuid.uuid4().hex[:8]}"
            cur.execute(
                "INSERT INTO users (user_id, username, display_name, department, role, is_guest) "
                "VALUES (%s, %s, 'Guest User', 'Guest', 'Guest', TRUE)",
                (guest_user_id, username),
            )
            user_row = {"user_id": guest_user_id, "username": username, "display_name": "Guest User",
                        "department": "Guest", "role": "Guest", "is_guest": True}

        for h in hashes:
            cur.execute(
                """
                INSERT INTO guest_devices (device_hash, guest_user_id, papers_generated)
                VALUES (%s, %s, %s)
                ON CONFLICT (device_hash) DO UPDATE
                SET guest_user_id = EXCLUDED.guest_user_id,
                    papers_generated = GREATEST(guest_devices.papers_generated, EXCLUDED.papers_generated),
                    last_seen_at = NOW()
                """,
                (h, guest_user_id, used),
            )

    token = create_session(user_row["user_id"], user_agent, is_guest=True)
    quota = {"limit": GUEST_PAPER_LIMIT, "used": used, "remaining": max(0, GUEST_PAPER_LIMIT - used)}
    return _public_user(user_row), token, quota


def get_guest_quota(user_id: str) -> Dict[str, Any]:
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT COALESCE(MAX(papers_generated), 0) AS used FROM guest_devices WHERE guest_user_id = %s",
                    (user_id,))
        used = cur.fetchone()["used"]
    return {"limit": GUEST_PAPER_LIMIT, "used": used, "remaining": max(0, GUEST_PAPER_LIMIT - used)}


def reserve_guest_paper(user_id: str) -> bool:
    """Atomically consume the guest's single paper. Returns False when the quota is already used."""
    with get_cursor() as cur:
        cur.execute("SELECT device_hash, papers_generated FROM guest_devices WHERE guest_user_id = %s FOR UPDATE",
                    (user_id,))
        rows = cur.fetchall()
        if not rows:
            return False
        if max(r["papers_generated"] for r in rows) >= GUEST_PAPER_LIMIT:
            return False
        cur.execute("UPDATE guest_devices SET papers_generated = papers_generated + 1, last_seen_at = NOW() "
                    "WHERE guest_user_id = %s", (user_id,))
        return True


def release_guest_paper(user_id: str) -> None:
    """Give the quota back when generation failed, so a server error does not burn the guest's paper."""
    with get_cursor() as cur:
        cur.execute("UPDATE guest_devices SET papers_generated = GREATEST(0, papers_generated - 1) "
                    "WHERE guest_user_id = %s", (user_id,))


# ----------------------------------------------------------------------------
# Past paper history
# ----------------------------------------------------------------------------
def _fmt_ts(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def save_paper_to_history(user_id: str, paper_data: Dict[str, Any]) -> str:
    paper_id = f"pap_{uuid.uuid4().hex[:10]}"
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO history (paper_id, user_id, course_code, course_name, exam_title, total_marks,
                                 duration, question_count, cognitive_index, paper_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                paper_id, user_id,
                paper_data.get("course_code", "EXAM"),
                paper_data.get("course_name", "Curriculum Examination"),
                paper_data.get("exam_title", "Semester Examination"),
                int(paper_data.get("total_marks", 100) or 100),
                paper_data.get("duration", "3 Hours"),
                len(paper_data.get("all_questions", [])),
                float((paper_data.get("analytics") or {}).get("cognitive_index", 3.0) or 3.0),
                psycopg2.extras.Json(paper_data),
            ),
        )
        cur.execute(
            """
            DELETE FROM history WHERE user_id = %s AND paper_id NOT IN (
                SELECT paper_id FROM history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
            )
            """,
            (user_id, user_id, HISTORY_LIMIT_PER_USER),
        )
    return paper_id


def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    with get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT paper_id, course_code, course_name, exam_title, total_marks, duration,
                   question_count, cognitive_index, created_at
            FROM history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
            """,
            (user_id, HISTORY_LIMIT_PER_USER),
        )
        rows = cur.fetchall()
    for r in rows:
        r["created_at"] = _fmt_ts(r["created_at"])
    return rows


def get_history_paper(user_id: str, paper_id: str) -> Optional[Dict[str, Any]]:
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT paper_data FROM history WHERE user_id = %s AND paper_id = %s", (user_id, paper_id))
        row = cur.fetchone()
    return row["paper_data"] if row else None


def delete_history_paper(user_id: str, paper_id: str) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM history WHERE user_id = %s AND paper_id = %s", (user_id, paper_id))
        return cur.rowcount > 0


# ----------------------------------------------------------------------------
# Question sets & custom templates (also stored in PostgreSQL)
# ----------------------------------------------------------------------------
def load_question_sets(user_id: str) -> Optional[List[Dict[str, Any]]]:
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT sets_data FROM question_sets WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
    return row["sets_data"] if row else None


def save_question_sets(user_id: str, sets_data: List[Dict[str, Any]]) -> None:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO question_sets (user_id, sets_data, updated_at) VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET sets_data = EXCLUDED.sets_data, updated_at = NOW()
            """,
            (user_id, psycopg2.extras.Json(sets_data)),
        )


MAX_TEMPLATES_PER_USER = 25


def load_custom_templates(owner_id: Optional[str]) -> Dict[str, Any]:
    """Templates that belong to one faculty member (nobody else can see them)."""
    if not owner_id:
        return {}
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT template_id, template_data FROM custom_templates WHERE owner_id = %s ORDER BY updated_at DESC",
                    (owner_id,))
        return {r["template_id"]: r["template_data"] for r in cur.fetchall()}


def save_custom_template_db(template_id: str, template_data: Dict[str, Any], owner_id: str) -> bool:
    """Create or update a template owned by `owner_id`. Returns False if the id belongs to someone else or the limit is hit."""
    with get_cursor() as cur:
        cur.execute("SELECT owner_id FROM custom_templates WHERE template_id = %s FOR UPDATE", (template_id,))
        row = cur.fetchone()
        if row and row["owner_id"] != owner_id:
            return False
        if not row:
            cur.execute("SELECT COUNT(*) AS n FROM custom_templates WHERE owner_id = %s", (owner_id,))
            if cur.fetchone()["n"] >= MAX_TEMPLATES_PER_USER:
                raise ValueError(f"You can keep up to {MAX_TEMPLATES_PER_USER} templates. Delete one first.")
        cur.execute(
            """
            INSERT INTO custom_templates (template_id, owner_id, template_data, updated_at) VALUES (%s, %s, %s, NOW())
            ON CONFLICT (template_id) DO UPDATE SET template_data = EXCLUDED.template_data, updated_at = NOW()
            """,
            (template_id, owner_id, psycopg2.extras.Json(template_data)),
        )
        return True


def delete_custom_template_db(template_id: str, owner_id: str) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM custom_templates WHERE template_id = %s AND owner_id = %s", (template_id, owner_id))
        return cur.rowcount > 0
