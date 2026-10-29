"""
BloomCraft AI - User Authentication & Past Paper History Service
Manages local academic user profiles, authentication, and persistent examination paper history.
"""

import os
import json
import time
import uuid
import hashlib
import hmac
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
USER_STORE_FILE = os.path.join(DATA_DIR, "user_store.json")


def _get_default_users() -> Dict[str, Any]:
    """Empty store: teachers create their own account on the Sign Up tab."""
    return {"users": {}, "history": {}, "sessions": {}}


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
    # legacy unsalted sha256 hashes from older versions of this project
    return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)


def _load_store() -> Dict[str, Any]:
    if not os.path.exists(USER_STORE_FILE):
        store = _get_default_users()
        _save_store(store)
        return store
    try:
        with open(USER_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        store = _get_default_users()
        _save_store(store)
        return store


def _save_store(store: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(USER_STORE_FILE), exist_ok=True)
    with open(USER_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def create_session(user_id: str) -> str:
    """Create and persist a secure session token for an authenticated faculty user."""
    store = _load_store()
    if "sessions" not in store:
        store["sessions"] = {}
    token = f"tok_{uuid.uuid4().hex}"
    store["sessions"][token] = {
        "user_id": user_id,
        "created_at": time.time()
    }
    _save_store(store)
    return token


def get_user_by_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve and authenticate faculty profile using session token."""
    if not token:
        return None
    clean_token = token.replace("Bearer ", "").strip()
    store = _load_store()
    session = store.get("sessions", {}).get(clean_token)
    if not session:
        return None
    user_id = session.get("user_id")
    for u in store.get("users", {}).values():
        if u.get("user_id") == user_id:
            return {
                "user_id": u["user_id"],
                "username": u["username"],
                "display_name": u["display_name"],
                "department": u.get("department", "Computer Science"),
                "role": u.get("role", "Faculty")
            }
    return None


def destroy_session(token: Optional[str]) -> bool:
    """Revoke session token on logout."""
    if not token:
        return False
    clean_token = token.replace("Bearer ", "").strip()
    store = _load_store()
    if "sessions" in store and clean_token in store["sessions"]:
        del store["sessions"][clean_token]
        _save_store(store)
        return True
    return False


def authenticate_user(username: str, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the teacher profile only when username AND password both match."""
    store = _load_store()
    clean_username = (username or "").strip().lower().replace(" ", "_")
    if not clean_username or not password:
        return None
    for key, user in store.get("users", {}).items():
        if user.get("username", "").lower() == clean_username or key.lower() == clean_username:
            if not _verify_password(password, user.get("password_hash")):
                return None
            if not str(user.get("password_hash", "")).startswith("pbkdf2$"):
                user["password_hash"] = _hash_password(password)      # upgrade legacy hash
                _save_store(store)
            return {
                "user_id": user["user_id"],
                "username": user["username"],
                "display_name": user["display_name"],
                "department": user.get("department", ""),
                "role": user.get("role", "Faculty"),
            }
    return None


def register_user(username: str, display_name: str, department: str = "", password: str = "") -> Dict[str, Any]:
    """Register a new faculty account."""
    store = _load_store()
    clean_username = username.strip().lower().replace(" ", "_")

    for u in store["users"].values():
        if u["username"].lower() == clean_username:
            raise ValueError("Username is already registered. Please choose another or log in.")

    if not clean_username:
        raise ValueError("Username is required.")
    if len(password or "") < 6:
        raise ValueError("Password must be at least 6 characters long.")

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    pwd_hash = _hash_password(password)

    new_user = {
        "user_id": user_id,
        "username": clean_username,
        "display_name": display_name.strip() or clean_username.title(),
        "department": department.strip(),
        "role": "Faculty Member",
        "password_hash": pwd_hash,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    store["users"][clean_username] = new_user
    store["history"][user_id] = []
    _save_store(store)

    return {
        "user_id": user_id,
        "username": new_user["username"],
        "display_name": new_user["display_name"],
        "department": new_user["department"],
        "role": new_user["role"]
    }


def reset_user_password(username: str, new_password: str) -> bool:
    """Reset the password of an EXISTING teacher account (never creates accounts)."""
    if not username or not new_password or len(new_password) < 6:
        return False
    store = _load_store()
    clean_username = username.strip().lower().replace(" ", "_")
    for key, user in store.get("users", {}).items():
        if user.get("username", "").lower() == clean_username or key.lower() == clean_username:
            user["password_hash"] = _hash_password(new_password)
            # sign out every device of this teacher
            store["sessions"] = {t: v for t, v in store.get("sessions", {}).items() if v.get("user_id") != user["user_id"]}
            _save_store(store)
            return True
    return False


def list_users() -> List[Dict[str, Any]]:
    """Return public metadata of available user profiles."""
    store = _load_store()
    result = []
    for u in store["users"].values():
        result.append({
            "user_id": u["user_id"],
            "username": u["username"],
            "display_name": u["display_name"],
            "department": u.get("department", ""),
            "role": u.get("role", "Faculty")
        })
    return result


def save_paper_to_history(user_id: str, paper_data: Dict[str, Any]) -> str:
    """Saves a newly synthesized question paper to the user's history."""
    store = _load_store()
    if "history" not in store:
        store["history"] = {}
    if user_id not in store["history"]:
        store["history"][user_id] = []

    paper_id = f"pap_{uuid.uuid4().hex[:10]}"
    history_record = {
        "paper_id": paper_id,
        "course_code": paper_data.get("course_code", "EXAM"),
        "course_name": paper_data.get("course_name", "Curriculum Examination"),
        "exam_title": paper_data.get("exam_title", "Semester Examination"),
        "total_marks": paper_data.get("total_marks", 100),
        "duration": paper_data.get("duration", "3 Hours"),
        "question_count": len(paper_data.get("all_questions", [])),
        "cognitive_index": paper_data.get("analytics", {}).get("cognitive_index", 3.0),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "paper_data": paper_data
    }

    # Prepend to history so newest is first
    store["history"][user_id].insert(0, history_record)
    # Keep up to 30 past papers per user
    store["history"][user_id] = store["history"][user_id][:30]
    _save_store(store)

    return paper_id


def get_user_history(user_id: str) -> List[Dict[str, Any]]:
    """Retrieve history records for a user without heavy embedded data for listing."""
    store = _load_store()
    records = store.get("history", {}).get(user_id, [])

    summary_list = []
    for r in records:
        summary_list.append({
            "paper_id": r.get("paper_id"),
            "course_code": r.get("course_code"),
            "course_name": r.get("course_name"),
            "exam_title": r.get("exam_title"),
            "total_marks": r.get("total_marks"),
            "duration": r.get("duration"),
            "question_count": r.get("question_count"),
            "cognitive_index": r.get("cognitive_index"),
            "created_at": r.get("created_at")
        })
    return summary_list


def get_history_paper(user_id: str, paper_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete past question paper by ID."""
    store = _load_store()
    records = store.get("history", {}).get(user_id, [])
    for r in records:
        if r.get("paper_id") == paper_id:
            return r.get("paper_data")
    return None


def delete_history_paper(user_id: str, paper_id: str) -> bool:
    """Delete a past paper from history."""
    store = _load_store()
    if user_id in store.get("history", {}):
        orig_len = len(store["history"][user_id])
        store["history"][user_id] = [p for p in store["history"][user_id] if p.get("paper_id") != paper_id]
        if len(store["history"][user_id]) < orig_len:
            _save_store(store)
            return True
    return False
