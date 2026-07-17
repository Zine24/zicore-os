"""
ZICORE SSO Module — Single Sign-On for the ZICORE ecosystem.

Provides centralized authentication, session management, and service integration
for all ZICORE modules (ZIO, Materializer, Mission Control, etc.).

Tables: users, sessions, services, user_services, audit_log
Auth: bcrypt (with hashlib fallback), secrets.token_urlsafe
Sessions: 30-day expiry
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# bcrypt import with fallback
# ---------------------------------------------------------------------------
try:
    import bcrypt as _bcrypt

    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

    def _verify_password(password: str, hashed: str) -> bool:
        """Verify a password against a bcrypt hash."""
        return _bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

except ImportError:
    import uuid as _uuid

    def _hash_password(password: str) -> str:  # type: ignore[misc]
        """Hash a password using SHA-256 (fallback when bcrypt is unavailable)."""
        salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"sha256${salt}${digest}"

    def _verify_password(password: str, hashed: str) -> bool:  # type: ignore[misc]
        """Verify a password against a SHA-256 hash."""
        if not hashed.startswith("sha256$"):
            return False
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        _, salt, expected = parts
        actual = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return secrets.compare_digest(actual, expected)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_SESSION_EXPIRY_DAYS: int = 30
_TOKEN_BYTES: int = 32

_DEFAULT_SERVICES: List[Dict[str, str]] = [
    {"name": "ZIO AI", "description": "ZICORE AI copilot and conversational engine"},
    {"name": "Materializer", "description": "Procedural 3D generation engine"},
    {"name": "Mission Control", "description": "Mission planning, telemetry, ground ops"},
    {"name": "Flight Simulator", "description": "Aerospace flight simulation"},
    {"name": "Engineering", "description": "Structural analysis, CAD, manufacturing"},
    {"name": "Game Center", "description": "HTML5 games and leaderboards"},
    {"name": "Settings", "description": "System configuration and preferences"},
    {"name": "Knowledge Base", "description": "ZiCodex knowledge store and documentation"},
]


# ---------------------------------------------------------------------------
# SSO Singleton
# ---------------------------------------------------------------------------
class ZICORESSO:
    """Singleton SSO manager for the ZICORE ecosystem.

    Usage::

        sso = ZICORESSO()          # returns the single instance
        sso.register_user("alice", "secret", email="alice@zicore.space")
        result = sso.login("alice", "secret")
        token = result["token"]
        authed = sso.verify_token(token)
    """

    _instance: Optional["ZICORESSO"] = None

    def __new__(cls, db_path: Optional[str] = None) -> "ZICORESSO":
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self, db_path: Optional[str] = None) -> None:
        if self._initialized:
            return
        self._initialized = True

        if db_path is None:
            base = Path(__file__).resolve().parent.parent / "data"
            base.mkdir(parents=True, exist_ok=True)
            db_path = str(base / "sso.db")

        self.db_path: str = db_path
        self.conn: sqlite3.Connection = sqlite3.connect(
            db_path, check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.commit()

        self._create_tables()
        self._seed_services()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _create_tables(self) -> None:
        """Create all SSO tables if they do not already exist."""
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,
                email       TEXT,
                display_name TEXT,
                role        TEXT    NOT NULL DEFAULT 'user',
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                token       TEXT    NOT NULL UNIQUE,
                service     TEXT,
                ip_address  TEXT,
                user_agent  TEXT,
                created_at  TEXT    NOT NULL,
                expires_at  TEXT    NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_services (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                service_id  INTEGER NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'user',
                granted_at  TEXT    NOT NULL,
                FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
                UNIQUE(user_id, service_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                action      TEXT    NOT NULL,
                detail      TEXT,
                ip_address  TEXT,
                timestamp   TEXT    NOT NULL
            )
        """)

        self.conn.commit()

    def _seed_services(self) -> None:
        """Insert default services if the services table is empty."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM services")
        count: int = cur.fetchone()[0]
        if count > 0:
            return

        now = datetime.utcnow().isoformat()
        for svc in _DEFAULT_SERVICES:
            cur.execute(
                "INSERT INTO services (name, description, is_active, created_at) VALUES (?, ?, 1, ?)",
                (svc["name"], svc["description"], now),
            )
        self.conn.commit()

    def _now(self) -> str:
        """Return the current UTC timestamp in ISO format."""
        return datetime.utcnow().isoformat()

    def _future(self, days: int = _DEFAULT_SESSION_EXPIRY_DAYS) -> str:
        """Return a UTC timestamp *days* in the future."""
        return (datetime.utcnow() + timedelta(days=days)).isoformat()

    def _log_audit(
        self,
        user_id: Optional[int],
        action: str,
        detail: str = "",
        ip_address: Optional[str] = None,
    ) -> None:
        """Write an entry to the audit_log table."""
        try:
            self.conn.execute(
                "INSERT INTO audit_log (user_id, action, detail, ip_address, timestamp) VALUES (?, ?, ?, ?, ?)",
                (user_id, action, detail, ip_address, self._now()),
            )
            self.conn.commit()
        except Exception:
            pass  # audit failures must never break the caller

    def _user_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a users row to a plain dict (password excluded)."""
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "display_name": row["display_name"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    def register_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        role: str = "user",
    ) -> Dict[str, Any]:
        """Register a new user.

        Returns::

            {"success": True, "user": {...}}  on success
            {"success": False, "error": "..."} on failure
        """
        if not username or not username.strip():
            return {"success": False, "error": "Username is required"}
        if not password or len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}

        username = username.strip().lower()

        try:
            existing = self.conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                return {"success": False, "error": "Username already exists"}

            now = self._now()
            hashed = _hash_password(password)
            cur = self.conn.execute(
                """INSERT INTO users (username, password, email, display_name, role, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (username, hashed, email, display_name or username, role, now, now),
            )
            self.conn.commit()
            user_id = cur.lastrowid

            self._log_audit(user_id, "register", f"User '{username}' created")

            user_row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return {"success": True, "user": self._user_row_to_dict(user_row)}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def login(
        self,
        username: str,
        password: str,
        service: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authenticate a user and create a session token.

        Returns::

            {"success": True, "token": "...", "expires_at": "...", "user": {...}}
            {"success": False, "error": "..."}
        """
        if not username or not password:
            return {"success": False, "error": "Username and password are required"}

        username = username.strip().lower()

        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            if not row:
                self._log_audit(None, "login_failed", f"Unknown user '{username}'", ip_address)
                return {"success": False, "error": "Invalid credentials"}

            if not row["is_active"]:
                self._log_audit(row["id"], "login_blocked", "Account disabled", ip_address)
                return {"success": False, "error": "Account is disabled"}

            if not _verify_password(password, row["password"]):
                self._log_audit(row["id"], "login_failed", "Bad password", ip_address)
                return {"success": False, "error": "Invalid credentials"}

            token = secrets.token_urlsafe(_TOKEN_BYTES)
            now = self._now()
            expires = self._future()

            self.conn.execute(
                """INSERT INTO sessions (user_id, token, service, ip_address, user_agent, created_at, expires_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (row["id"], token, service, ip_address, user_agent, now, expires),
            )
            self.conn.commit()

            self._log_audit(row["id"], "login", f"service={service}", ip_address)

            return {
                "success": True,
                "token": token,
                "expires_at": expires,
                "user": self._user_row_to_dict(row),
            }

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def logout(self, token: str) -> Dict[str, Any]:
        """Invalidate a session token.

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        if not token:
            return {"success": False, "error": "Token is required"}

        try:
            session = self.conn.execute(
                "SELECT id, user_id FROM sessions WHERE token = ? AND is_active = 1", (token,)
            ).fetchone()
            if not session:
                return {"success": False, "error": "Invalid or expired session"}

            self.conn.execute(
                "UPDATE sessions SET is_active = 0 WHERE id = ?", (session["id"],)
            )
            self.conn.commit()

            self._log_audit(session["user_id"], "logout")
            return {"success": True}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a session token and return the associated user.

        Returns::

            {"success": True, "user": {...}, "session": {...}}
            {"success": False, "error": "..."}
        """
        if not token:
            return {"success": False, "error": "Token is required"}

        try:
            session = self.conn.execute(
                "SELECT * FROM sessions WHERE token = ? AND is_active = 1", (token,)
            ).fetchone()
            if not session:
                return {"success": False, "error": "Invalid session"}

            if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
                self.conn.execute(
                    "UPDATE sessions SET is_active = 0 WHERE id = ?", (session["id"],)
                )
                self.conn.commit()
                return {"success": False, "error": "Session expired"}

            user = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (session["user_id"],)
            ).fetchone()
            if not user or not user["is_active"]:
                return {"success": False, "error": "User not found or disabled"}

            return {
                "success": True,
                "user": self._user_row_to_dict(user),
                "session": {
                    "id": session["id"],
                    "token": session["token"],
                    "service": session["service"],
                    "ip_address": session["ip_address"],
                    "created_at": session["created_at"],
                    "expires_at": session["expires_at"],
                },
            }

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Fetch a user by ID.

        Returns::

            {"success": True, "user": {...}} or {"success": False, "error": "..."}
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}
            return {"success": True, "user": self._user_row_to_dict(row)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """Fetch a user by username.

        Returns::

            {"success": True, "user": {...}} or {"success": False, "error": "..."}
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE username = ?", (username.strip().lower(),)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}
            return {"success": True, "user": self._user_row_to_dict(row)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_users(self, include_inactive: bool = False) -> Dict[str, Any]:
        """List all users.

        Returns::

            {"success": True, "users": [...]}
        """
        try:
            if include_inactive:
                rows = self.conn.execute("SELECT * FROM users ORDER BY id").fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT * FROM users WHERE is_active = 1 ORDER BY id"
                ).fetchall()
            return {"success": True, "users": [self._user_row_to_dict(r) for r in rows]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update user profile fields (email, display_name, role).

        Returns::

            {"success": True, "user": {...}} or {"success": False, "error": "..."}
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}

            new_email = email if email is not None else row["email"]
            new_name = display_name if display_name is not None else row["display_name"]
            new_role = role if role is not None else row["role"]
            now = self._now()

            self.conn.execute(
                """UPDATE users SET email = ?, display_name = ?, role = ?, updated_at = ?
                   WHERE id = ?""",
                (new_email, new_name, new_role, now, user_id),
            )
            self.conn.commit()

            self._log_audit(user_id, "update_profile", f"role={new_role}")

            updated = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return {"success": True, "user": self._user_row_to_dict(updated)}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> Dict[str, Any]:
        """Change a user's password after verifying the old one.

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        if not new_password or len(new_password) < 6:
            return {"success": False, "error": "New password must be at least 6 characters"}

        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}

            if not _verify_password(old_password, row["password"]):
                self._log_audit(user_id, "password_change_failed", "Bad old password")
                return {"success": False, "error": "Current password is incorrect"}

            hashed = _hash_password(new_password)
            now = self._now()
            self.conn.execute(
                "UPDATE users SET password = ?, updated_at = ? WHERE id = ?",
                (hashed, now, user_id),
            )
            self.conn.commit()

            self._log_audit(user_id, "password_changed")
            return {"success": True}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def admin_reset_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """Reset a user's password without requiring the old one (admin action).

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        if not new_password or len(new_password) < 6:
            return {"success": False, "error": "New password must be at least 6 characters"}

        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}

            hashed = _hash_password(new_password)
            now = self._now()
            self.conn.execute(
                "UPDATE users SET password = ?, updated_at = ? WHERE id = ?",
                (hashed, now, user_id),
            )
            self.conn.commit()

            self._log_audit(user_id, "admin_password_reset")
            return {"success": True}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def deactivate_user(self, user_id: int) -> Dict[str, Any]:
        """Soft-deactivate a user (sets is_active=0, invalidates all sessions).

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}

            now = self._now()
            self.conn.execute(
                "UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?", (now, user_id)
            )
            self.conn.execute(
                "UPDATE sessions SET is_active = 0 WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            self.conn.commit()

            self._log_audit(user_id, "deactivated")
            return {"success": True}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Permanently delete a user and all related data (cascades).

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "User not found"}

            self.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()

            self._log_audit(None, "user_deleted", f"user_id={user_id}, username={row['username']}")
            return {"success": True}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------
    def list_services(self) -> Dict[str, Any]:
        """List all registered services.

        Returns::

            {"success": True, "services": [...]}
        """
        try:
            rows = self.conn.execute(
                "SELECT * FROM services ORDER BY id"
            ).fetchall()
            services = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "is_active": bool(r["is_active"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
            return {"success": True, "services": services}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def register_service(self, name: str, description: str = "") -> Dict[str, Any]:
        """Register a new service.

        Returns::

            {"success": True, "service": {...}} or {"success": False, "error": "..."}
        """
        if not name or not name.strip():
            return {"success": False, "error": "Service name is required"}

        try:
            existing = self.conn.execute(
                "SELECT id FROM services WHERE name = ?", (name.strip(),)
            ).fetchone()
            if existing:
                return {"success": False, "error": "Service already exists"}

            now = self._now()
            cur = self.conn.execute(
                "INSERT INTO services (name, description, is_active, created_at) VALUES (?, ?, 1, ?)",
                (name.strip(), description, now),
            )
            self.conn.commit()

            return {
                "success": True,
                "service": {
                    "id": cur.lastrowid,
                    "name": name.strip(),
                    "description": description,
                    "is_active": True,
                    "created_at": now,
                },
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_service(self, service_id: int) -> Dict[str, Any]:
        """Fetch a service by ID.

        Returns::

            {"success": True, "service": {...}} or {"success": False, "error": "..."}
        """
        try:
            row = self.conn.execute(
                "SELECT * FROM services WHERE id = ?", (service_id,)
            ).fetchone()
            if not row:
                return {"success": False, "error": "Service not found"}
            return {
                "success": True,
                "service": {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                },
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # User ↔ Service grants
    # ------------------------------------------------------------------
    def grant_service(
        self, user_id: int, service_id: int, role: str = "user"
    ) -> Dict[str, Any]:
        """Grant a user access to a service.

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        try:
            user = self.conn.execute(
                "SELECT id FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not user:
                return {"success": False, "error": "User not found"}

            svc = self.conn.execute(
                "SELECT id FROM services WHERE id = ?", (service_id,)
            ).fetchone()
            if not svc:
                return {"success": False, "error": "Service not found"}

            existing = self.conn.execute(
                "SELECT id FROM user_services WHERE user_id = ? AND service_id = ?",
                (user_id, service_id),
            ).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE user_services SET role = ? WHERE id = ?",
                    (role, existing["id"]),
                )
                self.conn.commit()
                self._log_audit(user_id, "service_role_updated", f"service_id={service_id} role={role}")
                return {"success": True}

            now = self._now()
            self.conn.execute(
                "INSERT INTO user_services (user_id, service_id, role, granted_at) VALUES (?, ?, ?, ?)",
                (user_id, service_id, role, now),
            )
            self.conn.commit()

            self._log_audit(user_id, "service_granted", f"service_id={service_id} role={role}")
            return {"success": True}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def revoke_service(self, user_id: int, service_id: int) -> Dict[str, Any]:
        """Revoke a user's access to a service.

        Returns::

            {"success": True} or {"success": False, "error": "..."}
        """
        try:
            self.conn.execute(
                "DELETE FROM user_services WHERE user_id = ? AND service_id = ?",
                (user_id, service_id),
            )
            self.conn.commit()
            self._log_audit(user_id, "service_revoked", f"service_id={service_id}")
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_user_services(self, user_id: int) -> Dict[str, Any]:
        """List all services granted to a user.

        Returns::

            {"success": True, "services": [...]} or {"success": False, "error": "..."}
        """
        try:
            rows = self.conn.execute(
                """SELECT s.id, s.name, s.description, us.role, us.granted_at
                   FROM user_services us
                   JOIN services s ON us.service_id = s.id
                   WHERE us.user_id = ?
                   ORDER BY s.name""",
                (user_id,),
            ).fetchall()
            services = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "role": r["role"],
                    "granted_at": r["granted_at"],
                }
                for r in rows
            ]
            return {"success": True, "services": services}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_service_users(self, service_id: int) -> Dict[str, Any]:
        """List all users with access to a service.

        Returns::

            {"success": True, "users": [...]} or {"success": False, "error": "..."}
        """
        try:
            rows = self.conn.execute(
                """SELECT u.id, u.username, u.email, u.display_name, us.role, us.granted_at
                   FROM user_services us
                   JOIN users u ON us.user_id = u.id
                   WHERE us.service_id = ? AND u.is_active = 1
                   ORDER BY u.username""",
                (service_id,),
            ).fetchall()
            users = [
                {
                    "id": r["id"],
                    "username": r["username"],
                    "email": r["email"],
                    "display_name": r["display_name"],
                    "role": r["role"],
                    "granted_at": r["granted_at"],
                }
                for r in rows
            ]
            return {"success": True, "users": users}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def check_service_access(self, user_id: int, service_name: str) -> Dict[str, Any]:
        """Check if a user has access to a named service.

        Returns::

            {"success": True, "has_access": bool, "role": str|None}
        """
        try:
            row = self.conn.execute(
                """SELECT us.role
                   FROM user_services us
                   JOIN services s ON us.service_id = s.id
                   WHERE us.user_id = ? AND s.name = ?""",
                (user_id, service_name),
            ).fetchone()
            if row:
                return {"success": True, "has_access": True, "role": row["role"]}
            return {"success": True, "has_access": False, "role": None}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def get_active_sessions(self, user_id: int) -> Dict[str, Any]:
        """List all active (non-expired) sessions for a user.

        Returns::

            {"success": True, "sessions": [...]}
        """
        try:
            now = self._now()
            rows = self.conn.execute(
                """SELECT * FROM sessions
                   WHERE user_id = ? AND is_active = 1 AND expires_at > ?
                   ORDER BY created_at DESC""",
                (user_id, now),
            ).fetchall()
            sessions = [
                {
                    "id": r["id"],
                    "token": r["token"],
                    "service": r["service"],
                    "ip_address": r["ip_address"],
                    "user_agent": r["user_agent"],
                    "created_at": r["created_at"],
                    "expires_at": r["expires_at"],
                }
                for r in rows
            ]
            return {"success": True, "sessions": sessions}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def invalidate_all_sessions(self, user_id: int) -> Dict[str, Any]:
        """Invalidate every active session for a user (force logout everywhere).

        Returns::

            {"success": True, "revoked": int}
        """
        try:
            cur = self.conn.execute(
                "UPDATE sessions SET is_active = 0 WHERE user_id = ? AND is_active = 1",
                (user_id,),
            )
            self.conn.commit()
            self._log_audit(user_id, "all_sessions_invalidated", f"revoked={cur.rowcount}")
            return {"success": True, "revoked": cur.rowcount}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Deactivate all sessions past their expiry date.

        Returns::

            {"success": True, "cleaned": int}
        """
        try:
            now = self._now()
            cur = self.conn.execute(
                "UPDATE sessions SET is_active = 0 WHERE is_active = 1 AND expires_at <= ?",
                (now,),
            )
            self.conn.commit()
            return {"success": True, "cleaned": cur.rowcount}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------
    def get_audit_log(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query the audit log with optional filters.

        Returns::

            {"success": True, "entries": [...]}
        """
        try:
            clauses: List[str] = []
            params: List[Any] = []
            if user_id is not None:
                clauses.append("user_id = ?")
                params.append(user_id)
            if action is not None:
                clauses.append("action = ?")
                params.append(action)

            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            query = f"SELECT * FROM audit_log{where} ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = self.conn.execute(query, params).fetchall()
            entries = [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "action": r["action"],
                    "detail": r["detail"],
                    "ip_address": r["ip_address"],
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]
            return {"success": True, "entries": entries}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Token-based SSO flow (service-to-service)
    # ------------------------------------------------------------------
    def create_sso_token(
        self,
        user_id: int,
        service: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Issue a token for a specific service (SSO handshake).

        Returns::

            {"success": True, "token": "...", "expires_at": "..."}
            {"success": False, "error": "..."}
        """
        try:
            user = self.conn.execute(
                "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
            ).fetchone()
            if not user:
                return {"success": False, "error": "User not found or disabled"}

            token = secrets.token_urlsafe(_TOKEN_BYTES)
            now = self._now()
            expires = self._future()

            self.conn.execute(
                """INSERT INTO sessions (user_id, token, service, ip_address, user_agent, created_at, expires_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (user_id, token, service, ip_address, "SSO-Token", now, expires),
            )
            self.conn.commit()

            self._log_audit(user_id, "sso_token_created", f"service={service}", ip_address)

            return {"success": True, "token": token, "expires_at": expires}

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def exchange_sso_token(self, token: str, target_service: str) -> Dict[str, Any]:
        """Exchange an existing token for a new one targeting a different service.

        Returns::

            {"success": True, "token": "...", "expires_at": "...", "user": {...}}
            {"success": False, "error": "..."}
        """
        try:
            verification = self.verify_token(token)
            if not verification["success"]:
                return {"success": False, "error": verification["error"]}

            user = verification["user"]

            new_token = secrets.token_urlsafe(_TOKEN_BYTES)
            now = self._now()
            expires = self._future()

            self.conn.execute(
                """INSERT INTO sessions (user_id, token, service, ip_address, user_agent, created_at, expires_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (user["id"], new_token, target_service, None, "SSO-Exchange", now, expires),
            )
            self.conn.commit()

            self._log_audit(user["id"], "sso_token_exchanged", f"target={target_service}")

            return {
                "success": True,
                "token": new_token,
                "expires_at": expires,
                "user": user,
            }

        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Stats / health
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the SSO system.

        Returns::

            {"success": True, "users": int, "active_sessions": int,
             "services": int, "audit_entries": int}
        """
        try:
            users = self.conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0]
            sessions = self.conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE is_active = 1 AND expires_at > ?",
                (self._now(),),
            ).fetchone()[0]
            services = self.conn.execute("SELECT COUNT(*) FROM services WHERE is_active = 1").fetchone()[0]
            audit = self.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

            return {
                "success": True,
                "users": users,
                "active_sessions": sessions,
                "services": services,
                "audit_entries": audit,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def close(self) -> None:
        """Close the database connection and reset the singleton."""
        try:
            self.conn.close()
        except Exception:
            pass
        ZICORESSO._instance = None
        self._initialized = False
