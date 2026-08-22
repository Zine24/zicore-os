"""
ZiHost — ZICORE Free Hosting Panel
Manages hosted sites on VPS with free-tier quotas.
Quota: 2GB per account (ZICORE service + 512MB upload/generation).
"""

import os
import json
import shutil
import hashlib
import secrets
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("zicore.zihost")

HOSTING_ROOT = Path(os.environ.get("ZIHOST_ROOT", "/opt/zihost"))
SITES_DIR = HOSTING_ROOT / "sites"
CONFIG_FILE = HOSTING_ROOT / "config.json"
USERS_FILE = HOSTING_ROOT / "users.json"

# Free tier defaults
FREE_TIER = {
    "name": "free",
    "disk_mb": 2048,        # 2GB total (ZICORE ~1.5GB + 512MB data)
    "upload_mb": 512,       # 512MB for uploads + generation
    "bandwidth_mb": 10240,  # 10GB/month
    "domains": 1,
    "databases": 0,
    "processes": 4,
    "zicore_instance": True, # Can run one ZICORE instance
}


class ZiHost:
    def __init__(self):
        SITES_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
        self.users = self._load_users()
        logger.info(f"ZiHost initialized: {len(self.users)} accounts, root={HOSTING_ROOT}")

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
        cfg = {
            "tier": FREE_TIER,
            "created": datetime.now(timezone.utc).isoformat(),
            "total_disk_gb": 46,
            "used_disk_gb": 0,
        }
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        return cfg

    def _load_users(self) -> dict:
        if USERS_FILE.exists():
            return json.loads(USERS_FILE.read_text())
        return {}

    def _save_users(self):
        USERS_FILE.write_text(json.dumps(self.users, indent=2, default=str))

    def _save_config(self):
        CONFIG_FILE.write_text(json.dumps(self.config, indent=2, default=str))

    # ─── Account Management ──────────────────────────────

    def create_account(self, username: str, email: str, password: str = None) -> dict:
        """Create a new hosting account with free-tier defaults."""
        username = username.lower().strip()
        if not username or not username.isalnum():
            return {"success": False, "error": "Invalid username (alphanumeric only)"}
        if username in self.users:
            return {"success": False, "error": "Username already taken"}

        if not password:
            password = secrets.token_urlsafe(12)

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        site_dir = SITES_DIR / username
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "html").mkdir(exist_ok=True)
        (site_dir / "data").mkdir(exist_ok=True)
        (site_dir / "data" / "uploads").mkdir(exist_ok=True)
        (site_dir / "data" / "generation").mkdir(exist_ok=True)
        (site_dir / "logs").mkdir(exist_ok=True)

        account = {
            "username": username,
            "email": email,
            "password_hash": pw_hash,
            "tier": "free",
            "created": datetime.now(timezone.utc).isoformat(),
            "site_dir": str(site_dir),
            "disk_used_mb": 0,
            "bandwidth_used_mb": 0,
            "status": "active",
            "zicore_running": False,
            "port": None,
            "public_ip": "160.34.209.208",
            "domain": f"{username}.zihost.cloud",
            "api_key": secrets.token_urlsafe(32),
        }

        # Write default index.html
        index_html = f"""<!DOCTYPE html>
<html><head><title>{username} — ZiHost</title>
<style>body{{background:#0a0e16;color:#c8d0dc;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
.box{{text-align:center}}h1{{color:#00e5ff;font-size:2em}}p{{color:#607080}}</style></head>
<body><div class="box"><h1>ZiHost</h1><p>Welcome to <b>{username}</b>'s site</p><p style="color:#303848;font-size:0.8em">Powered by ZICORE</p></div></body></html>"""
        (site_dir / "html" / "index.html").write_text(index_html)

        # Write zicore config placeholder
        zicore_cfg = {
            "version": "5.0.0",
            "instance": username,
            "port": None,
            "data_dir": str(site_dir / "data"),
            "media_dir": str(site_dir / "data" / "generation"),
        }
        (site_dir / "zicore_config.json").write_text(json.dumps(zicore_cfg, indent=2))

        self.users[username] = account
        self._save_users()
        logger.info(f"ZiHost account created: {username} ({email})")
        return {"success": True, "username": username, "password": password,
                "site_dir": str(site_dir), "api_key": account["api_key"],
                "domain": account["domain"]}

    def delete_account(self, username: str) -> dict:
        if username not in self.users:
            return {"success": False, "error": "Account not found"}
        site_dir = Path(self.users[username].get("site_dir", SITES_DIR / username))
        if site_dir.exists():
            shutil.rmtree(site_dir)
        del self.users[username]
        self._save_users()
        logger.info(f"ZiHost account deleted: {username}")
        return {"success": True}

    def authenticate(self, username: str, password: str) -> dict:
        if username not in self.users:
            return {"success": False, "error": "Account not found"}
        acct = self.users[username]
        if acct.get("status") != "active":
            return {"success": False, "error": "Account suspended"}
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if acct.get("password_hash") != pw_hash:
            return {"success": False, "error": "Invalid password"}
        return {"success": True, "account": {k: v for k, v in acct.items() if k != "password_hash"}}

    # ─── Quota Management ────────────────────────────────

    def get_disk_usage(self, username: str) -> dict:
        """Calculate actual disk usage for an account."""
        site_dir = Path(self.users.get(username, {}).get("site_dir", SITES_DIR / username))
        if not site_dir.exists():
            return {"used_mb": 0, "limit_mb": FREE_TIER["disk_mb"]}
        total = sum(f.stat().st_size for f in site_dir.rglob("*") if f.is_file())
        used_mb = round(total / (1024 * 1024), 2)
        return {"used_mb": used_mb, "limit_mb": FREE_TIER["disk_mb"],
                "percent": round(used_mb / FREE_TIER["disk_mb"] * 100, 1)}

    def get_upload_usage(self, username: str) -> dict:
        upload_dir = Path(self.users.get(username, {}).get("site_dir", SITES_DIR / username)) / "data" / "uploads"
        gen_dir = Path(self.users.get(username, {}).get("site_dir", SITES_DIR / username)) / "data" / "generation"
        total = 0
        for d in [upload_dir, gen_dir]:
            if d.exists():
                total += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        used_mb = round(total / (1024 * 1024), 2)
        return {"used_mb": used_mb, "limit_mb": FREE_TIER["upload_mb"],
                "percent": round(used_mb / FREE_TIER["upload_mb"] * 100, 1)}

    def check_quota(self, username: str) -> dict:
        disk = self.get_disk_usage(username)
        upload = self.get_upload_usage(username)
        return {
            "disk": disk,
            "upload": upload,
            "within_quota": disk["used_mb"] <= disk["limit_mb"],
        }

    # ─── File Management ─────────────────────────────────

    def list_files(self, username: str, subpath: str = "html") -> dict:
        base = Path(self.users.get(username, {}).get("site_dir", SITES_DIR / username)) / subpath
        if not base.exists():
            return {"success": False, "error": "Directory not found"}
        files = []
        for f in sorted(base.iterdir()):
            stat = f.stat()
            files.append({
                "name": f.name,
                "is_dir": f.is_dir(),
                "size": stat.st_size if f.is_file() else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        return {"success": True, "files": files, "path": subpath}

    def write_file(self, username: str, subpath: str, filename: str, content: bytes) -> dict:
        """Write a file to the user's site."""
        quota = self.check_quota(username)
        if not quota["within_quota"]:
            return {"success": False, "error": "Disk quota exceeded"}
        base = Path(self.users.get(username, {}).get("site_dir", SITES_DIR / username)) / subpath
        base.mkdir(parents=True, exist_ok=True)
        filepath = base / filename
        filepath.write_bytes(content)
        self.users[username]["disk_used_mb"] = self.get_disk_usage(username)["used_mb"]
        self._save_users()
        return {"success": True, "size": len(content), "path": str(filepath)}

    def delete_file(self, username: str, subpath: str, filename: str) -> dict:
        base = Path(self.users.get(username, {}).get("site_dir", SITES_DIR / username)) / subpath
        filepath = base / filename
        if not filepath.exists():
            return {"success": False, "error": "File not found"}
        if filepath.is_dir():
            shutil.rmtree(filepath)
        else:
            filepath.unlink()
        self.users[username]["disk_used_mb"] = self.get_disk_usage(username)["used_mb"]
        self._save_users()
        return {"success": True}

    # ─── ZICORE Instance Management ──────────────────────

    def get_zicore_status(self, username: str) -> dict:
        """Check if a user's ZICORE instance is running."""
        acct = self.users.get(username, {})
        return {
            "running": acct.get("zicore_running", False),
            "port": acct.get("port"),
            "domain": acct.get("domain"),
        }

    def list_all(self) -> list:
        """List all accounts (admin)."""
        return [{k: v for k, v in acct.items() if k != "password_hash"}
                for acct in self.users.values()]

    def get_stats(self) -> dict:
        """Global hosting stats."""
        total_accounts = len(self.users)
        active = sum(1 for u in self.users.values() if u.get("status") == "active")
        total_disk = sum(self.get_disk_usage(u)["used_mb"] for u in self.users)
        return {
            "total_accounts": total_accounts,
            "active": active,
            "total_disk_mb": round(total_disk, 2),
            "tier": FREE_TIER["name"],
            "disk_limit_mb": FREE_TIER["disk_mb"],
        }


zihost = ZiHost()
