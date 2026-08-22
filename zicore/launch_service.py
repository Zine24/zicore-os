"""
ZIO Aerospace Launch Intelligence (ZALI)
Multi-source launch monitoring with real-time countdown, events, and provider coverage.

Primary: Launch Library 2 (The Space Devs) — 15 req/hour public limit
Complementary: SpaceX API, NASA APOD/Mars, nextspaceflight.com (scrape)
"""

import time
import json
import os
import sqlite3
import asyncio
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import httpx

logger = logging.getLogger("zali")

LL2_BASE = "https://ll.thespacedevs.com/2.2.0"
SPACEX_BASE = "https://api.spacexdata.com/v5"
NASA_BASE = "https://api.nasa.gov"

_executor = ThreadPoolExecutor(max_workers=2)

_cache: Dict[str, Any] = {}
_cache_ttl: Dict[str, float] = {}


def _db_path() -> str:
    base = os.environ.get("ZICORE_DATA_DIR", "")
    if not base:
        fpath = Path(__file__).resolve().parent.parent / "data"
        base = str(fpath)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "zali.db")


def _init_db():
    conn = sqlite3.connect(_db_path())
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS launches (
            id TEXT PRIMARY KEY,
            name TEXT,
            mission TEXT,
            vehicle TEXT,
            booster TEXT,
            ship TEXT,
            provider TEXT,
            pad TEXT,
            location TEXT,
            country TEXT,
            status TEXT,
            status_abbrev TEXT,
            net TEXT,
            window_start TEXT,
            window_end TEXT,
            last_updated TEXT,
            webcast_live INTEGER DEFAULT 0,
            image_url TEXT,
            probability INTEGER,
            weather_concerns TEXT,
            holdreason TEXT,
            failreason TEXT,
            hashtag TEXT,
            stream_url TEXT,
            source_url TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS launch_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            launch_id TEXT,
            event_type TEXT,
            event_name TEXT,
            event_time TEXT,
            event_description TEXT,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (launch_id) REFERENCES launches(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS launch_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            launch_id TEXT,
            update_text TEXT,
            update_author TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (launch_id) REFERENCES launches(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id TEXT PRIMARY KEY,
            name TEXT,
            abbrev TEXT,
            type TEXT,
            info_url TEXT,
            wiki_url TEXT,
            logo_url TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


_init_db()


class LaunchService:
    def __init__(self):
        self._http: Optional[httpx.AsyncClient] = None
        self._last_ll2_request: float = 0
        self._ll2_interval: float = 240

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30, follow_redirects=True)
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    def _is_cache_valid(self, key: str) -> bool:
        if key not in _cache:
            return False
        return (time.time() - _cache_ttl.get(key, 0)) < 600

    async def _ll2_get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        now = time.time()
        if now - self._last_ll2_request < self._ll2_interval:
            logger.debug("LL2 rate limit protection, using cache")
            return None

        try:
            client = await self._client()
            url = f"{LL2_BASE}{endpoint}"
            resp = await client.get(url, params=params or {})
            self._last_ll2_request = time.time()
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                logger.warning("LL2 rate limit hit (429)")
                return None
            else:
                logger.warning(f"LL2 {resp.status_code} for {endpoint}")
                return None
        except Exception as e:
            logger.error(f"LL2 request failed: {e}")
            return None

    def _normalize_launch(self, raw: Dict) -> Dict:
        status = raw.get("status", {})
        pad = raw.get("pad", {}) or {}
        location = pad.get("location", {}) or {}
        mission = raw.get("mission", {}) or {}
        rocket = raw.get("rocket", {}) or {}
        rocket_config = rocket.get("configuration", {}) or {}
        launch_service_provider = raw.get("launch_service_provider", {}) or {}
        status_obj = raw.get("status", {}) or {}

        return {
            "id": str(raw.get("id", "")),
            "name": raw.get("name", ""),
            "mission": mission.get("name", ""),
            "mission_type": mission.get("type", ""),
            "mission_description": mission.get("description", ""),
            "vehicle": rocket_config.get("name", ""),
            "vehicle_full_name": rocket_config.get("full_name", ""),
            "provider": launch_service_provider.get("name", ""),
            "provider_abbrev": launch_service_provider.get("abbrev", ""),
            "pad": pad.get("name", ""),
            "location": location.get("name", ""),
            "country": location.get("country_code", ""),
            "status": status_obj.get("name", ""),
            "status_abbrev": status_obj.get("abbrev", ""),
            "net": raw.get("net", ""),
            "window_start": raw.get("window_start", ""),
            "window_end": raw.get("window_end", ""),
            "last_updated": raw.get("last_updated", ""),
            "webcast_live": raw.get("webcast_live", False),
            "image_url": raw.get("image", ""),
            "probability": raw.get("probability"),
            "weather_concerns": raw.get("weather_concerns", ""),
            "holdreason": raw.get("holdreason", ""),
            "failreason": raw.get("failreason", ""),
            "hashtag": raw.get("hashtag", ""),
            "stream_url": raw.get("vid_urls", [{}])[0].get("url", "") if raw.get("vid_urls") else "",
            "source_url": raw.get("url", ""),
            "inhold": raw.get("inhold", False),
            "inhibitcad": raw.get("inhibitcad", False),
        }

    def _store_launch(self, launch: Dict):
        conn = sqlite3.connect(_db_path())
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO launches
            (id, name, mission, vehicle, booster, ship, provider, pad, location,
             country, status, status_abbrev, net, window_start, window_end,
             last_updated, webcast_live, image_url, probability, weather_concerns,
             holdreason, failreason, hashtag, stream_url, source_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            launch["id"], launch["name"], launch["mission"], launch["vehicle"],
            launch.get("booster", ""), launch.get("ship", ""),
            launch["provider"], launch["pad"], launch["location"],
            launch["country"], launch["status"], launch["status_abbrev"],
            launch["net"], launch["window_start"], launch["window_end"],
            launch["last_updated"], 1 if launch["webcast_live"] else 0,
            launch["image_url"], launch.get("probability"),
            launch.get("weather_concerns", ""), launch.get("holdreason", ""),
            launch.get("failreason", ""), launch.get("hashtag", ""),
            launch.get("stream_url", ""), launch.get("source_url", ""),
        ))
        conn.commit()
        conn.close()

    async def fetch_upcoming(self, limit: int = 20) -> List[Dict]:
        cache_key = f"upcoming_{limit}"
        if self._is_cache_valid(cache_key):
            return _cache[cache_key]

        data = await self._ll2_get("/launch/upcoming/", {
            "limit": limit,
            "ordering": "net",
            "format": "json",
        })

        results = []
        if data and "results" in data:
            for raw in data["results"]:
                launch = self._normalize_launch(raw)
                self._store_launch(launch)
                results.append(launch)
            _cache[cache_key] = results
            _cache_ttl[cache_key] = time.time()
        else:
            results = self._get_from_db("upcoming")

        return results

    async def fetch_previous(self, limit: int = 10) -> List[Dict]:
        cache_key = f"previous_{limit}"
        if self._is_cache_valid(cache_key):
            return _cache[cache_key]

        data = await self._ll2_get("/launch/previous/", {
            "limit": limit,
            "ordering": "-net",
            "format": "json",
        })

        results = []
        if data and "results" in data:
            for raw in data["results"]:
                launch = self._normalize_launch(raw)
                self._store_launch(launch)
                results.append(launch)
            _cache[cache_key] = results
            _cache_ttl[cache_key] = time.time()
        else:
            results = self._get_from_db("previous")

        return results

    async def fetch_launch(self, launch_id: str) -> Optional[Dict]:
        cache_key = f"launch_{launch_id}"
        if self._is_cache_valid(cache_key):
            return _cache[cache_key]

        data = await self._ll2_get(f"/launch/{launch_id}/", {"format": "json"})

        if data:
            launch = self._normalize_launch(data)
            self._store_launch(launch)
            _cache[cache_key] = launch
            _cache_ttl[cache_key] = time.time()
            return launch

        return self._get_launch_from_db(launch_id)

    async def fetch_events(self, launch_id: str) -> List[Dict]:
        data = await self._ll2_get(f"/launch/{launch_id}/event/", {"format": "json"})
        events = []
        if data and "results" in data:
            for ev in data["results"]:
                events.append({
                    "id": ev.get("id"),
                    "type": ev.get("type", {}).get("name", ""),
                    "name": ev.get("name", ""),
                    "time": ev.get("time", ""),
                    "description": ev.get("description", ""),
                })
        return events

    async def fetch_updates(self, launch_id: str) -> List[Dict]:
        data = await self._ll2_get(f"/launch/{launch_id}/serial_number/", {"format": "json"})
        updates = []
        if data and "results" in data:
            for u in data["results"]:
                updates.append({
                    "id": u.get("id"),
                    "text": u.get("info", ""),
                    "author": u.get("created_by", {}).get("username", "") if isinstance(u.get("created_by"), dict) else str(u.get("created_by", "")),
                    "created_at": u.get("created", ""),
                })
        return updates

    async def fetch_providers(self) -> List[Dict]:
        cache_key = "providers"
        if self._is_cache_valid(cache_key):
            return _cache[cache_key]

        data = await self._ll2_get("/agencies/", {"format": "json", "limit": 50})
        providers = []
        if data and "results" in data:
            for p in data["results"]:
                providers.append({
                    "id": str(p.get("id", "")),
                    "name": p.get("name", ""),
                    "abbrev": p.get("abbrev", ""),
                    "type": p.get("type", ""),
                    "info_url": p.get("info_url", ""),
                    "wiki_url": p.get("wiki_url", ""),
                    "logo_url": p.get("logo_url", ""),
                })
            _cache[cache_key] = providers
            _cache_ttl[cache_key] = time.time()
        return providers

    def _get_from_db(self, status_type: str) -> List[Dict]:
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if status_type == "upcoming":
            c.execute("SELECT * FROM launches WHERE net >= datetime('now') ORDER BY net ASC LIMIT 30")
        else:
            c.execute("SELECT * FROM launches WHERE net < datetime('now') ORDER BY net DESC LIMIT 20")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def _get_launch_from_db(self, launch_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM launches WHERE id = ?", (launch_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_launches(self) -> List[Dict]:
        return self._get_from_db("upcoming") + self._get_from_db("previous")

    def get_countdown(self, net_str: str) -> Dict:
        if not net_str:
            return {"active": False, "message": "No NET available"}
        try:
            net_dt = datetime.fromisoformat(net_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = net_dt - now

            total_seconds = int(delta.total_seconds())
            if total_seconds > 0:
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return {
                    "active": True,
                    "t_minus": True,
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds,
                    "total_seconds": total_seconds,
                    "net_iso": net_dt.isoformat(),
                    "now_iso": now.isoformat(),
                    "message": f"T-{days}d {hours:02d}:{minutes:02d}:{seconds:02d}",
                }
            else:
                abs_delta = abs(delta)
                days = abs_delta.days
                hours, remainder = divmod(abs_delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return {
                    "active": True,
                    "t_minus": False,
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds,
                    "total_seconds": total_seconds,
                    "net_iso": net_dt.isoformat(),
                    "now_iso": now.isoformat(),
                    "message": f"T+{days}d {hours:02d}:{minutes:02d}:{seconds:02d}",
                }
        except Exception as e:
            logger.error(f"Countdown error: {e}")
            return {"active": False, "message": f"Error: {e}"}


launch_service = LaunchService()
