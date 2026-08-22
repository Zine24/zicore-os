"""
ZICORE GeoTrack — Geolocation service for system users.

Centralizes GPS/IP location reporting for every authenticated user across
the ecosystem (web, mobile app, APK). Stores a lightweight history of
geolocation points per user in SQLite.

Tables: geo_points
Sources: gps (device GPS), ip (approximate by IP), manual (form/API)

Usage::

    geo = GeoTrack()                          # returns the single instance
    geo.record(1, "alice", 19.43, -99.13, source="gps", app="mobile")
    latest = geo.latest_for_user(1)
    users  = geo.latest_all()
    stats  = geo.stats()
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_VALID_SOURCES = {"gps", "ip", "manual", "device"}
_VALID_APPS = {"web", "mobile", "apk", "api", "device"}

# Device quota per SSO plan (0 = unlimited). Configurable.
DEVICE_QUOTA_BY_PLAN: Dict[str, int] = {"free": 5, "pro": 20, "admin": 0}

_IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,lat,lon,timezone,isp,query"

# Small in-memory IP cache: ip -> (timestamp, result_dict)
_IP_CACHE: Dict[str, List[Any]] = {}
_IP_CACHE_TTL = 3600 * 24  # 24h


# ---------------------------------------------------------------------------
# GeoTrack singleton
# ---------------------------------------------------------------------------
class GeoTrack:
    """Singleton geolocation tracker backed by SQLite."""

    _instance: Optional["GeoTrack"] = None

    def __new__(cls, db_path: Optional[str] = None) -> "GeoTrack":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None) -> None:
        if self._initialized:
            return
        self._initialized = True

        if db_path is None:
            base = Path(__file__).resolve().parent.parent / "data"
            base.mkdir(parents=True, exist_ok=True)
            db_path = str(base / "geo.db")

        self.db_path: str = db_path
        self.conn: sqlite3.Connection = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.commit()
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geo_points (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                username    TEXT    NOT NULL,
                lat         REAL    NOT NULL,
                lon         REAL    NOT NULL,
                accuracy    REAL,
                altitude    REAL,
                speed       REAL,
                heading     REAL,
                source      TEXT    NOT NULL DEFAULT 'gps',
                app         TEXT    NOT NULL DEFAULT 'web',
                device_id   TEXT,
                ip          TEXT,
                user_agent  TEXT,
                city        TEXT,
                region      TEXT,
                country     TEXT,
                isp         TEXT,
                recorded_at TEXT    NOT NULL
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geo_user_time
            ON geo_points (user_id, recorded_at)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geo_time
            ON geo_points (recorded_at)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geo_devices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                type        TEXT    NOT NULL DEFAULT 'tracker',
                token_hash  TEXT    NOT NULL UNIQUE,
                owner_id    INTEGER NOT NULL DEFAULT 0,
                owner_name  TEXT,
                active      INTEGER NOT NULL DEFAULT 1,
                meta        TEXT,
                created_at  TEXT    NOT NULL,
                last_seen   TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geo_dev_owner
            ON geo_devices (owner_id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geo_bookmarks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                lat         REAL    NOT NULL,
                lon         REAL    NOT NULL,
                altitude    REAL,
                icon        TEXT    DEFAULT '📍',
                color       TEXT    DEFAULT '#00e5ff',
                notes       TEXT,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geo_bm_user
            ON geo_bookmarks (user_id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geo_tracking_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                started_at  TEXT    NOT NULL,
                stopped_at  TEXT,
                interval_s  INTEGER NOT NULL DEFAULT 60,
                points      INTEGER NOT NULL DEFAULT 0,
                status      TEXT    NOT NULL DEFAULT 'active'
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geo_ts_user
            ON geo_tracking_sessions (user_id, status)
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------
    def record(
        self,
        user_id: int,
        username: str,
        lat: float,
        lon: float,
        accuracy: Optional[float] = None,
        altitude: Optional[float] = None,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
        source: str = "gps",
        app: str = "web",
        device_id: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        geoip: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Record a geolocation point for a user. Returns the new row id."""
        if source not in _VALID_SOURCES:
            source = "gps"
        if app not in _VALID_APPS:
            app = "web"
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            return None
        if not (-90 <= lat_f <= 90) or not (-180 <= lon_f <= 180):
            return None

        now = datetime.utcnow().isoformat()
        geoip = geoip or {}
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO geo_points (
                    user_id, username, lat, lon, accuracy, altitude, speed, heading,
                    source, app, device_id, ip, user_agent,
                    city, region, country, isp, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    lat_f,
                    lon_f,
                    accuracy,
                    altitude,
                    speed,
                    heading,
                    source,
                    app,
                    device_id,
                    ip,
                    (user_agent or "")[:300],
                    geoip.get("city"),
                    geoip.get("region"),
                    geoip.get("country"),
                    geoip.get("isp"),
                    now,
                ),
            )
            self.conn.commit()
            return cur.lastrowid
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def latest_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM geo_points WHERE user_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def history_for_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM geo_points WHERE user_id = ? ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def latest_all(self) -> List[Dict[str, Any]]:
        """Most recent location per user, all users, newest first.
        Device/system points (user_id=0) are excluded — devices are
        queried separately via latest_for_device()."""
        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT gp.* FROM geo_points gp
            JOIN (
                SELECT user_id, MAX(id) AS max_id
                FROM geo_points WHERE user_id != 0 GROUP BY user_id
            ) last ON gp.id = last.max_id
            ORDER BY gp.recorded_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def history_all(self, limit: int = 500) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM geo_points ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM geo_points").fetchone()[0]
        users = cur.execute("SELECT COUNT(DISTINCT user_id) FROM geo_points WHERE user_id != 0").fetchone()[0]
        now = datetime.utcnow()
        last = cur.execute(
            "SELECT MAX(recorded_at) FROM geo_points"
        ).fetchone()[0]
        from datetime import timedelta

        cutoff = (now - timedelta(hours=24)).isoformat()
        last_24h = cur.execute(
            "SELECT COUNT(*) FROM geo_points WHERE recorded_at >= ?",
            (cutoff,),
        ).fetchone()[0]
        return {
            "total_points": total,
            "tracked_users": users,
            "last_update": last,
            "points_last_24h": last_24h,
        }

    def prune(self, days: int = 90) -> int:
        """Delete points older than N days. Returns the number removed."""
        if days <= 0:
            return 0
        cutoff = datetime.utcnow().timestamp() - days * 86400
        cutoff_iso = datetime.utcfromtimestamp(cutoff).isoformat()
        cur = self.conn.cursor()
        cur.execute("DELETE FROM geo_points WHERE recorded_at < ?", (cutoff_iso,))
        self.conn.commit()
        return cur.rowcount

    # ------------------------------------------------------------------
    # Geolocation devices (trackers / beacons / vehicles / mobile)
    # ------------------------------------------------------------------
    @staticmethod
    def device_quota(plan: Optional[str] = None) -> int:
        """Max devices allowed for a plan (0 = unlimited)."""
        return DEVICE_QUOTA_BY_PLAN.get((plan or "free").lower(), 5)

    def create_device(
        self,
        name: str,
        owner_id: int = 0,
        owner_name: Optional[str] = None,
        dtype: str = "tracker",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register a geolocation device. Returns the device + its secret token.
        The token is shown ONLY once; the DB stores a SHA-256 hash."""
        token = "zc_dev_" + secrets.token_urlsafe(24)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.utcnow().isoformat()
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO geo_devices (name, type, token_hash, owner_id, owner_name, active, meta, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (name[:120], dtype[:20], token_hash, int(owner_id), owner_name, meta_json, now),
        )
        self.conn.commit()
        dev_id = cur.lastrowid
        return {
            "id": dev_id,
            "device_id": f"dev-{dev_id}",
            "name": name[:120],
            "type": dtype[:20],
            "owner_id": owner_id,
            "owner_name": owner_name,
            "active": True,
            "token": token,  # shown once
            "created_at": now,
        }

    def get_device_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Resolve an active device from its secret token (constant-time compare via hash)."""
        if not token or not token.startswith("zc_dev_"):
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM geo_devices WHERE token_hash = ? AND active = 1", (token_hash,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["device_id"] = f"dev-{d['id']}"
        return d

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a device by its public id (dev-<id>)."""
        if not device_id or not str(device_id).startswith("dev-"):
            return None
        try:
            dev_id = int(str(device_id).split("-")[1])
        except (ValueError, IndexError):
            return None
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM geo_devices WHERE id = ?", (dev_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["device_id"] = f"dev-{d['id']}"
        return d

    def list_devices(self, owner_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List devices (never exposes token_hash). Optionally filter by owner."""
        cur = self.conn.cursor()
        if owner_id is not None:
            rows = cur.execute(
                "SELECT * FROM geo_devices WHERE owner_id = ? ORDER BY id DESC", (int(owner_id),)
            ).fetchall()
        else:
            rows = cur.execute("SELECT * FROM geo_devices ORDER BY id DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["device_id"] = f"dev-{d['id']}"
            d.pop("token_hash", None)
            latest = self.latest_for_device(d["device_id"])
            if latest:
                d["lat"] = latest.get("lat")
                d["lon"] = latest.get("lon")
                d["last_seen"] = latest.get("recorded_at")
            out.append(d)
        return out

    def device_count(self, owner_id: Optional[int] = None) -> int:
        cur = self.conn.cursor()
        if owner_id is not None:
            return cur.execute(
                "SELECT COUNT(*) FROM geo_devices WHERE owner_id = ?", (int(owner_id),)
            ).fetchone()[0]
        return cur.execute("SELECT COUNT(*) FROM geo_devices").fetchone()[0]

    def revoke_device(self, device_id: str) -> bool:
        dev = self.get_device(device_id)
        if not dev:
            return False
        cur = self.conn.cursor()
        cur.execute("UPDATE geo_devices SET active = 0 WHERE id = ?", (dev["id"],))
        self.conn.commit()
        return True

    def touch_device(self, device_id: str) -> None:
        dev = self.get_device(device_id)
        if not dev:
            return
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE geo_devices SET last_seen = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), dev["id"]),
        )
        self.conn.commit()

    def latest_for_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM geo_points WHERE device_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
            (device_id,),
        ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Bookmarks (saved locations)
    # ------------------------------------------------------------------
    def create_bookmark(
        self,
        user_id: int,
        name: str,
        lat: float,
        lon: float,
        altitude: Optional[float] = None,
        icon: str = "📍",
        color: str = "#00e5ff",
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        now = datetime.utcnow().isoformat()
        try:
            cur = self.conn.cursor()
            cur.execute(
                """INSERT INTO geo_bookmarks
                   (user_id, name, lat, lon, altitude, icon, color, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, name[:120], float(lat), float(lon), altitude, icon, color, notes, now, now),
            )
            self.conn.commit()
            return {
                "id": cur.lastrowid,
                "user_id": user_id,
                "name": name[:120],
                "lat": float(lat),
                "lon": float(lon),
                "altitude": altitude,
                "icon": icon,
                "color": color,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }
        except Exception:
            return None

    def list_bookmarks(self, user_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM geo_bookmarks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_bookmark(self, bookmark_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM geo_bookmarks WHERE id = ? AND user_id = ?",
            (bookmark_id, user_id),
        ).fetchone()
        return dict(row) if row else None

    def update_bookmark(
        self,
        bookmark_id: int,
        user_id: int,
        name: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        bm = self.get_bookmark(bookmark_id, user_id)
        if not bm:
            return False
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name[:120])
        if lat is not None:
            updates.append("lat = ?")
            params.append(float(lat))
        if lon is not None:
            updates.append("lon = ?")
            params.append(float(lon))
        if icon is not None:
            updates.append("icon = ?")
            params.append(icon)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if not updates:
            return True
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.extend([bookmark_id, user_id])
        cur = self.conn.cursor()
        cur.execute(f"UPDATE geo_bookmarks SET {', '.join(updates)} WHERE id = ? AND user_id = ?", params)
        self.conn.commit()
        return cur.rowcount > 0

    def delete_bookmark(self, bookmark_id: int, user_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM geo_bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id))
        self.conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Tracking sessions
    # ------------------------------------------------------------------
    def start_tracking_session(self, user_id: int, interval_s: int = 60) -> Optional[Dict[str, Any]]:
        """Start a new tracking session. Stops any active session for this user first."""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE geo_tracking_sessions SET status = 'stopped', stopped_at = ? WHERE user_id = ? AND status = 'active'",
            (datetime.utcnow().isoformat(), user_id),
        )
        now = datetime.utcnow().isoformat()
        interval_s = max(10, min(int(interval_s), 3600))
        cur.execute(
            "INSERT INTO geo_tracking_sessions (user_id, started_at, interval_s, status) VALUES (?, ?, ?, 'active')",
            (user_id, now, interval_s),
        )
        self.conn.commit()
        return {
            "id": cur.lastrowid,
            "user_id": user_id,
            "started_at": now,
            "interval_s": interval_s,
            "points": 0,
            "status": "active",
        }

    def stop_tracking_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute(
            "UPDATE geo_tracking_sessions SET status = 'stopped', stopped_at = ? WHERE user_id = ? AND status = 'active' RETURNING *",
            (now, user_id),
        )
        row = cur.fetchone()
        self.conn.commit()
        if not row:
            return None
        d = dict(row)
        d["status"] = "stopped"
        d["stopped_at"] = now
        return d

    def get_active_tracking(self, user_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM geo_tracking_sessions WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def touch_tracking_session(self, user_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE geo_tracking_sessions SET points = points + 1 WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        self.conn.commit()

    def tracking_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM geo_tracking_sessions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# IP → approximate location (offline-friendly, cached)
# ---------------------------------------------------------------------------
def ip_geolocate(client_ip: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    """Return approximate location for an IP via ip-api.com (free, no key).

    Results are cached in memory for 24h. Returns None when the lookup fails
    or the IP is private/local (no internet lookup needed).
    """
    if not client_ip or client_ip in ("127.0.0.1", "::1", "localhost", "unknown"):
        return None

    # Private/LAN ranges cannot be geolocated externally
    if client_ip.startswith(("10.", "192.168.", "172.")) or client_ip.startswith("fe80"):
        return None

    cached = _IP_CACHE.get(client_ip)
    if cached and (time.time() - cached[0]) < _IP_CACHE_TTL:
        return cached[1]

    try:
        url = _IP_API_URL.format(ip=client_ip)
        req = urllib.request.Request(url, headers={"User-Agent": "ZICORE/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8", "replace")
        import json

        obj = json.loads(data)
        if obj.get("status") != "success":
            return None
        result = {
            "ip": obj.get("query") or client_ip,
            "city": obj.get("city"),
            "region": obj.get("regionName"),
            "country": obj.get("country"),
            "countryCode": obj.get("countryCode"),
            "lat": obj.get("lat"),
            "lon": obj.get("lon"),
            "timezone": obj.get("timezone"),
            "isp": obj.get("isp"),
            "source": "ip",
        }
        _IP_CACHE[client_ip] = [time.time(), result]
        return result
    except Exception:
        return None
