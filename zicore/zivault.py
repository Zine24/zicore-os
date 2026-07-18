"""
ZiVault — Universal Asset Vault
Part of the ZICORE Ecosystem

Zero Debt. User Ownership First. Security by Design.
NOT a bank. Never creates debt, issues loans, or grants credit.
Digital Treasury for every digital and physical asset.
"""

import uuid
import json
import time
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("zicore.zivault")

VAULT_DB = Path(__file__).parent.parent / "data" / "zivault.db"

ASSET_TYPES = [
    "cash", "bank_account", "crypto", "stock", "etf", "real_estate", "vehicle",
    "domain", "patent", "license", "research", "ai_model", "dataset", "satellite",
    "drone", "robot", "server", "cloud_infra", "solar_plant", "hydrogen_system",
    "carbon_credit", "energy_production", "book", "publication", "digital_art",
    "nft", "business_ownership", "equipment", "custom"
]

TX_TYPES = [
    "purchase", "sale", "transfer", "donation", "inheritance", "tokenization",
    "energy_production", "energy_consumption", "publication", "merge", "split",
    "retirement", "appreciation", "depreciation", "valuation_update"
]


def _db():
    conn = sqlite3.connect(str(VAULT_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    VAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = _db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS organizations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        owner_id INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS org_members (
        org_id TEXT REFERENCES organizations(id),
        user_id INTEGER REFERENCES users(id),
        role TEXT DEFAULT 'member',
        PRIMARY KEY (org_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS assets (
        id TEXT PRIMARY KEY,
        owner_id INTEGER REFERENCES users(id),
        org_id TEXT,
        asset_type TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        current_value REAL DEFAULT 0,
        currency TEXT DEFAULT 'ZNT',
        acquisition_date TEXT,
        acquisition_cost REAL DEFAULT 0,
        location TEXT DEFAULT '',
        serial_number TEXT DEFAULT '',
        blockchain_hash TEXT DEFAULT '',
        digital_signature TEXT DEFAULT '',
        tags TEXT DEFAULT '[]',
        metadata TEXT DEFAULT '{}',
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS portfolios (
        id TEXT PRIMARY KEY,
        owner_id INTEGER REFERENCES users(id),
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        portfolio_type TEXT DEFAULT 'personal',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS portfolio_assets (
        portfolio_id TEXT REFERENCES portfolios(id),
        asset_id TEXT REFERENCES assets(id),
        weight REAL DEFAULT 1.0,
        added_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (portfolio_id, asset_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        owner_id INTEGER REFERENCES users(id),
        asset_id TEXT REFERENCES assets(id),
        tx_type TEXT NOT NULL,
        amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'ZNT',
        counterparty TEXT DEFAULT '',
        description TEXT DEFAULT '',
        tx_date TEXT DEFAULT (datetime('now')),
        digital_signature TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ownership (
        id TEXT PRIMARY KEY,
        asset_id TEXT REFERENCES assets(id),
        owner_id INTEGER REFERENCES users(id),
        verified INTEGER DEFAULT 0,
        certificate_id TEXT DEFAULT '',
        transfer_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS vault_files (
        id TEXT PRIMARY KEY,
        owner_id INTEGER REFERENCES users(id),
        asset_id TEXT,
        filename TEXT NOT NULL,
        file_type TEXT DEFAULT '',
        file_size INTEGER DEFAULT 0,
        checksum TEXT DEFAULT '',
        encrypted INTEGER DEFAULT 1,
        version INTEGER DEFAULT 1,
        storage_path TEXT DEFAULT '',
        digital_signature TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        resource_type TEXT DEFAULT '',
        resource_id TEXT DEFAULT '',
        details TEXT DEFAULT '{}',
        ip_address TEXT DEFAULT '',
        device TEXT DEFAULT '',
        digital_signature TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        title TEXT NOT NULL,
        message TEXT DEFAULT '',
        channel TEXT DEFAULT 'web',
        read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS currencies (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        symbol TEXT DEFAULT '',
        is_crypto INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS exchange_rates (
        from_currency TEXT,
        to_currency TEXT,
        rate REAL DEFAULT 1.0,
        updated_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (from_currency, to_currency)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS blockchain_records (
        id TEXT PRIMARY KEY,
        asset_id TEXT REFERENCES assets(id),
        chain TEXT NOT NULL,
        tx_hash TEXT DEFAULT '',
        block_number INTEGER DEFAULT 0,
        contract_address TEXT DEFAULT '',
        token_id TEXT DEFAULT '',
        metadata TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        key_hash TEXT NOT NULL,
        name TEXT DEFAULT '',
        permissions TEXT DEFAULT '[]',
        expires_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS tags (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        name TEXT NOT NULL,
        color TEXT DEFAULT '#00e5ff',
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, name)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS asset_tags (
        asset_id TEXT REFERENCES assets(id),
        tag_id TEXT REFERENCES tags(id),
        PRIMARY KEY (asset_id, tag_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        resource_type TEXT NOT NULL,
        resource_id TEXT NOT NULL,
        title TEXT DEFAULT '',
        content TEXT DEFAULT '',
        pinned INTEGER DEFAULT 0,
        color TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    # Seed default currencies
    default_currencies = [
        ("ZNT", "Zitón", "Z", 1),
        ("BTC", "Bitcoin", "₿", 1),
        ("ETH", "Ethereum", "Ξ", 1),
        ("USD", "US Dollar", "$", 0),
        ("EUR", "Euro", "€", 0),
        ("MXN", "Mexican Peso", "$", 0),
    ]
    for code, name, sym, crypto in default_currencies:
        c.execute("INSERT OR IGNORE INTO currencies (code, name, symbol, is_crypto) VALUES (?,?,?,?)",
                  (code, name, sym, crypto))

    # Seed exchange rates
    rates = [
        ("ZNT", "USD", 2.47), ("USD", "ZNT", 0.4049),
        ("BTC", "USD", 67500), ("ETH", "USD", 3450),
        ("ZNT", "BTC", 0.0000366), ("ZNT", "ETH", 0.000716),
    ]
    for f, t, r in rates:
        c.execute("INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate) VALUES (?,?,?)",
                  (f, t, r))

    conn.commit()
    conn.close()
    logger.info("ZiVault database initialized")


class ZiVault:
    def __init__(self):
        init_db()

    def _log(self, user_id, action, resource_type="", resource_id="", details="", ip="", device=""):
        conn = _db()
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip, device) VALUES (?,?,?,?,?,?,?)",
            (user_id, action, resource_type, resource_id, details, ip, device)
        )
        conn.commit()
        conn.close()

    # ── USERS ────────────────────────────────────────────────────────────────

    def get_or_create_user(self, email: str, name: str = "") -> dict:
        conn = _db()
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            conn.close()
            return dict(row)
        uid = str(uuid.uuid4().hex[:12])
        conn.execute("INSERT INTO users (id, email, name) VALUES (?,?,?)", (uid, email, name))
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
        conn.close()
        self._log(uid, "user_created", "user", uid)
        return user

    # ── ASSETS ───────────────────────────────────────────────────────────────

    def create_asset(self, owner_id: str, asset_type: str, name: str, **kwargs) -> dict:
        aid = "av_" + uuid.uuid4().hex[:16]
        conn = _db()
        conn.execute("""INSERT INTO assets
            (id, owner_id, org_id, asset_type, name, description, current_value, currency,
             acquisition_date, acquisition_cost, location, serial_number, blockchain_hash,
             digital_signature, tags, metadata, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (aid, owner_id, kwargs.get("org_id", ""), asset_type, name,
             kwargs.get("description", ""), kwargs.get("current_value", 0),
             kwargs.get("currency", "ZNT"), kwargs.get("acquisition_date", ""),
             kwargs.get("acquisition_cost", 0), kwargs.get("location", ""),
             kwargs.get("serial_number", ""), kwargs.get("blockchain_hash", ""),
             kwargs.get("digital_signature", ""),
             json.dumps(kwargs.get("tags", [])),
             json.dumps(kwargs.get("metadata", {})),
             "active"))
        conn.commit()
        asset = dict(conn.execute("SELECT * FROM assets WHERE id=?", (aid,)).fetchone())
        conn.close()

        # Auto-create ownership record
        self._create_ownership(aid, owner_id)
        self._log(owner_id, "asset_created", "asset", aid, name)
        return asset

    def get_asset(self, asset_id: str) -> Optional[dict]:
        conn = _db()
        row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["tags"] = json.loads(d.get("tags", "[]"))
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            return d
        return None

    def list_assets(self, owner_id: str, asset_type: str = "", status: str = "active",
                    limit: int = 100, offset: int = 0) -> list:
        conn = _db()
        q = "SELECT * FROM assets WHERE owner_id=?"
        params: list = [owner_id]
        if asset_type:
            q += " AND asset_type=?"
            params.append(asset_type)
        if status:
            q += " AND status=?"
            params.append(status)
        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(q, params).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags", "[]"))
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            result.append(d)
        return result

    def update_asset(self, asset_id: str, **kwargs) -> Optional[dict]:
        conn = _db()
        updates = []
        params = []
        for k in ("name", "description", "current_value", "currency", "location",
                   "serial_number", "blockchain_hash", "digital_signature", "status"):
            if k in kwargs:
                updates.append(f"{k}=?")
                params.append(kwargs[k])
        if "tags" in kwargs:
            updates.append("tags=?")
            params.append(json.dumps(kwargs["tags"]))
        if "metadata" in kwargs:
            updates.append("metadata=?")
            params.append(json.dumps(kwargs["metadata"]))
        updates.append("updated_at=datetime('now')")
        params.append(asset_id)
        conn.execute(f"UPDATE assets SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        asset = self.get_asset(asset_id)
        conn.close()
        if asset:
            self._log(asset["owner_id"], "asset_updated", "asset", asset_id)
        return asset

    def delete_asset(self, asset_id: str) -> bool:
        conn = _db()
        row = conn.execute("SELECT owner_id FROM assets WHERE id=?", (asset_id,)).fetchone()
        if not row:
            conn.close()
            return False
        owner_id = row["owner_id"]
        conn.execute("UPDATE assets SET status='archived', updated_at=datetime('now') WHERE id=?", (asset_id,))
        conn.commit()
        conn.close()
        self._log(owner_id, "asset_archived", "asset", asset_id)
        return True

    def search_assets(self, owner_id: str, query: str) -> list:
        conn = _db()
        q = "%{}%".format(query)
        rows = conn.execute(
            "SELECT * FROM assets WHERE owner_id=? AND (name LIKE ? OR description LIKE ? OR tags LIKE ?) AND status='active' LIMIT 50",
            (owner_id, q, q, q)
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags", "[]"))
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            result.append(d)
        return result

    # ── PORTFOLIOS ───────────────────────────────────────────────────────────

    def create_portfolio(self, owner_id: str, name: str, ptype: str = "personal", desc: str = "") -> dict:
        pid = "pf_" + uuid.uuid4().hex[:12]
        conn = _db()
        conn.execute("INSERT INTO portfolios (id, owner_id, name, description, portfolio_type) VALUES (?,?,?,?,?)",
                     (pid, owner_id, name, desc, ptype))
        conn.commit()
        p = dict(conn.execute("SELECT * FROM portfolios WHERE id=?", (pid,)).fetchone())
        conn.close()
        return p

    def list_portfolios(self, owner_id: str) -> list:
        conn = _db()
        rows = conn.execute("SELECT * FROM portfolios WHERE owner_id=? ORDER BY created_at DESC", (owner_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_asset_to_portfolio(self, portfolio_id: str, asset_id: str) -> bool:
        conn = _db()
        try:
            conn.execute("INSERT INTO portfolio_assets (portfolio_id, asset_id) VALUES (?,?)",
                         (portfolio_id, asset_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False

    def get_portfolio_assets(self, portfolio_id: str) -> list:
        conn = _db()
        rows = conn.execute("""
            SELECT a.* FROM assets a
            JOIN portfolio_assets pa ON a.id = pa.asset_id
            WHERE pa.portfolio_id = ?
        """, (portfolio_id,)).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags", "[]"))
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            result.append(d)
        return result

    # ── TRANSACTIONS ─────────────────────────────────────────────────────────

    def create_transaction(self, owner_id: str, asset_id: str, tx_type: str,
                           amount: float = 0, currency: str = "ZNT",
                           counterparty: str = "", description: str = "") -> dict:
        tid = "tx_" + uuid.uuid4().hex[:16]
        sig = hashlib.sha256(f"{tid}:{owner_id}:{tx_type}:{amount}:{time.time()}".encode()).hexdigest()[:32]
        conn = _db()
        conn.execute("""INSERT INTO transactions
            (id, owner_id, asset_id, tx_type, amount, currency, counterparty, description, digital_signature)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (tid, owner_id, asset_id, tx_type, amount, currency, counterparty, description, sig))
        conn.commit()
        tx = dict(conn.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone())
        conn.close()
        self._log(owner_id, "transaction_created", "transaction", tid, f"{tx_type}: {amount} {currency}")
        return tx

    def list_transactions(self, owner_id: str, asset_id: str = "", limit: int = 50) -> list:
        conn = _db()
        if asset_id:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE owner_id=? AND asset_id=? ORDER BY created_at DESC LIMIT ?",
                (owner_id, asset_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE owner_id=? ORDER BY created_at DESC LIMIT ?",
                (owner_id, limit)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── OWNERSHIP ────────────────────────────────────────────────────────────

    def _create_ownership(self, asset_id: str, owner_id: str):
        oid = "own_" + uuid.uuid4().hex[:12]
        cert_id = "CERT-" + uuid.uuid4().hex[:8].upper()
        conn = _db()
        conn.execute("""INSERT INTO ownership (id, asset_id, owner_id, verified, certificate_id)
            VALUES (?,?,?,1,?)""", (oid, asset_id, owner_id, cert_id))
        conn.commit()
        conn.close()

    def get_ownership(self, asset_id: str) -> Optional[dict]:
        conn = _db()
        row = conn.execute("SELECT * FROM ownership WHERE asset_id=?", (asset_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def transfer_ownership(self, asset_id: str, from_owner: str, to_owner: str) -> bool:
        conn = _db()
        conn.execute("UPDATE ownership SET owner_id=?, verified=0, transfer_count=transfer_count+1 WHERE asset_id=?",
                     (to_owner, asset_id))
        conn.execute("UPDATE assets SET owner_id=?, updated_at=datetime('now') WHERE id=?", (to_owner, asset_id))
        conn.commit()
        conn.close()
        self._log(from_owner, "ownership_transferred", "asset", asset_id, f"to {to_owner}")
        return True

    # ── VAULT FILES ──────────────────────────────────────────────────────────

    def upload_file(self, owner_id: str, filename: str, file_type: str = "",
                    file_size: int = 0, asset_id: str = "") -> dict:
        fid = "vf_" + uuid.uuid4().hex[:12]
        checksum = hashlib.sha256(f"{filename}:{file_size}:{time.time()}".encode()).hexdigest()[:32]
        sig = hashlib.sha256(f"{fid}:{owner_id}:{checksum}".encode()).hexdigest()[:32]
        conn = _db()
        conn.execute("""INSERT INTO vault_files
            (id, owner_id, asset_id, filename, file_type, file_size, checksum, encrypted, digital_signature)
            VALUES (?,?,?,?,?,?,?,1,?)""",
            (fid, owner_id, asset_id, filename, file_type, file_size, checksum, sig))
        conn.commit()
        f = dict(conn.execute("SELECT * FROM vault_files WHERE id=?", (fid,)).fetchone())
        conn.close()
        self._log(owner_id, "file_uploaded", "vault_file", fid, filename)
        return f

    def list_files(self, owner_id: str, asset_id: str = "") -> list:
        conn = _db()
        if asset_id:
            rows = conn.execute(
                "SELECT * FROM vault_files WHERE owner_id=? AND asset_id=? ORDER BY created_at DESC",
                (owner_id, asset_id)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM vault_files WHERE owner_id=? ORDER BY created_at DESC",
                (owner_id,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_file(self, file_id: str) -> bool:
        conn = _db()
        row = conn.execute("SELECT owner_id FROM vault_files WHERE id=?", (file_id,)).fetchone()
        if not row:
            conn.close()
            return False
        conn.execute("DELETE FROM vault_files WHERE id=?", (file_id,))
        conn.commit()
        conn.close()
        self._log(row["owner_id"], "file_deleted", "vault_file", file_id)
        return True

    # ── DASHBOARD / PORTFOLIO SUMMARY ────────────────────────────────────────

    def get_dashboard(self, owner_id: str) -> dict:
        conn = _db()

        # Total assets count
        total_assets = conn.execute(
            "SELECT COUNT(*) as cnt FROM assets WHERE owner_id=? AND status='active'", (owner_id,)
        ).fetchone()["cnt"]

        # Total value by currency
        value_rows = conn.execute(
            "SELECT currency, SUM(current_value) as total FROM assets WHERE owner_id=? AND status='active' GROUP BY currency",
            (owner_id,)
        ).fetchall()
        total_value = {r["currency"]: r["total"] for r in value_rows}

        # Assets by type
        type_rows = conn.execute(
            "SELECT asset_type, COUNT(*) as cnt, SUM(current_value) as val FROM assets WHERE owner_id=? AND status='active' GROUP BY asset_type",
            (owner_id,)
        ).fetchall()
        by_type = [{"type": r["asset_type"], "count": r["cnt"], "value": r["val"] or 0} for r in type_rows]

        # Recent transactions
        recent_tx = conn.execute(
            "SELECT * FROM transactions WHERE owner_id=? ORDER BY created_at DESC LIMIT 10", (owner_id,)
        ).fetchall()

        # Total files
        total_files = conn.execute(
            "SELECT COUNT(*) as cnt FROM vault_files WHERE owner_id=?", (owner_id,)
        ).fetchone()["cnt"]

        # Total transactions
        total_tx = conn.execute(
            "SELECT COUNT(*) as cnt FROM transactions WHERE owner_id=?", (owner_id,)
        ).fetchone()["cnt"]

        # Notifications
        unread = conn.execute(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND read=0", (owner_id,)
        ).fetchone()["cnt"]

        conn.close()

        # Get USD equivalent
        usd_total = 0
        for cur, val in total_value.items():
            if cur == "USD":
                usd_total += val
            elif cur == "ZNT":
                usd_total += val * 2.47
            elif cur == "BTC":
                usd_total += val * 67500
            elif cur == "ETH":
                usd_total += val * 3450

        return {
            "total_assets": total_assets,
            "total_value": total_value,
            "total_value_usd": round(usd_total, 2),
            "by_type": by_type,
            "recent_transactions": [dict(r) for r in recent_tx],
            "total_files": total_files,
            "total_transactions": total_tx,
            "unread_notifications": unread,
        }

    # ── NOTIFICATIONS ────────────────────────────────────────────────────────

    def create_notification(self, user_id: str, title: str, message: str = "", channel: str = "web") -> dict:
        nid = "ntf_" + uuid.uuid4().hex[:12]
        conn = _db()
        conn.execute("INSERT INTO notifications (id, user_id, title, message, channel) VALUES (?,?,?,?,?)",
                     (nid, user_id, title, message, channel))
        conn.commit()
        conn.close()
        return {"id": nid, "title": title, "message": message}

    def list_notifications(self, user_id: str, unread_only: bool = False) -> list:
        conn = _db()
        q = "SELECT * FROM notifications WHERE user_id=?"
        if unread_only:
            q += " AND read=0"
        q += " ORDER BY created_at DESC LIMIT 50"
        rows = conn.execute(q, (user_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def mark_notification_read(self, notification_id: str) -> bool:
        conn = _db()
        conn.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
        conn.commit()
        conn.close()
        return True

    # ── AUDIT LOG ────────────────────────────────────────────────────────────

    def get_audit_logs(self, user_id: str, limit: int = 100) -> list:
        conn = _db()
        rows = conn.execute(
            "SELECT * FROM audit_logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── CURRENCIES ───────────────────────────────────────────────────────────

    def list_currencies(self) -> list:
        conn = _db()
        rows = conn.execute("SELECT * FROM currencies ORDER BY code").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_exchange_rate(self, from_cur: str, to_cur: str) -> float:
        conn = _db()
        row = conn.execute(
            "SELECT rate FROM exchange_rates WHERE from_currency=? AND to_currency=?",
            (from_cur, to_cur)
        ).fetchone()
        conn.close()
        return row["rate"] if row else 0

    # ── REPORTS ──────────────────────────────────────────────────────────────

    def generate_portfolio_report(self, owner_id: str) -> dict:
        assets = self.list_assets(owner_id, limit=1000)
        dashboard = self.get_dashboard(owner_id)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "owner_id": owner_id,
            "summary": {
                "total_assets": dashboard["total_assets"],
                "total_value_usd": dashboard["total_value_usd"],
                "total_value": dashboard["total_value"],
                "total_transactions": dashboard["total_transactions"],
            },
            "assets_by_type": dashboard["by_type"],
            "assets": [{
                "id": a["id"],
                "name": a["name"],
                "type": a["asset_type"],
                "value": a["current_value"],
                "currency": a["currency"],
                "status": a["status"],
                "acquisition_date": a["acquisition_date"],
            } for a in assets],
        }
        return report

    # ── ZNT STAKING (backwards compat) ──────────────────────────────────────

    def get_staking(self, owner_id: str) -> list:
        conn = _db()
        try:
            rows = conn.execute("SELECT * FROM staking WHERE user_id=?", (owner_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            conn.close()
            return []

    # ── TAGS ───────────────────────────────────────────────────────────────────

    def create_tag(self, user_id: str, name: str, color: str = "#00e5ff") -> dict:
        tid = "tg_" + uuid.uuid4().hex[:12]
        conn = _db()
        try:
            conn.execute("INSERT INTO tags (id, user_id, name, color) VALUES (?,?,?,?)",
                         (tid, user_id, name.strip(), color))
            conn.commit()
            tag = dict(conn.execute("SELECT * FROM tags WHERE id=?", (tid,)).fetchone())
            conn.close()
            return tag
        except sqlite3.IntegrityError:
            conn.close()
            row = conn.execute("SELECT * FROM tags WHERE user_id=? AND name=?", (user_id, name.strip())).fetchone()
            return dict(row) if row else {"id": tid, "name": name, "color": color}

    def list_tags(self, user_id: str) -> list:
        conn = _db()
        rows = conn.execute("SELECT * FROM tags WHERE user_id=? ORDER BY name", (user_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_tag(self, tag_id: str) -> bool:
        conn = _db()
        conn.execute("DELETE FROM asset_tags WHERE tag_id=?", (tag_id,))
        conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))
        conn.commit()
        conn.close()
        return True

    def add_tag_to_asset(self, asset_id: str, tag_id: str) -> bool:
        conn = _db()
        try:
            conn.execute("INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?,?)", (asset_id, tag_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False

    def remove_tag_from_asset(self, asset_id: str, tag_id: str) -> bool:
        conn = _db()
        conn.execute("DELETE FROM asset_tags WHERE asset_id=? AND tag_id=?", (asset_id, tag_id))
        conn.commit()
        conn.close()
        return True

    def get_asset_tags(self, asset_id: str) -> list:
        conn = _db()
        rows = conn.execute("""
            SELECT t.* FROM tags t
            JOIN asset_tags at ON t.id = at.tag_id
            WHERE at.asset_id = ?
        """, (asset_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_assets_by_tag(self, user_id: str, tag_id: str) -> list:
        conn = _db()
        rows = conn.execute("""
            SELECT a.* FROM assets a
            JOIN asset_tags at ON a.id = at.asset_id
            WHERE at.tag_id = ? AND a.owner_id = ? AND a.status = 'active'
        """, (tag_id, user_id)).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags", "[]"))
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            result.append(d)
        return result

    # ── NOTES ──────────────────────────────────────────────────────────────────

    def create_note(self, user_id: str, resource_type: str, resource_id: str,
                    title: str = "", content: str = "", color: str = "") -> dict:
        nid = "nt_" + uuid.uuid4().hex[:12]
        conn = _db()
        conn.execute("""INSERT INTO notes (id, user_id, resource_type, resource_id, title, content, color)
            VALUES (?,?,?,?,?,?,?)""", (nid, user_id, resource_type, resource_id, title, content, color))
        conn.commit()
        note = dict(conn.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone())
        conn.close()
        self._log(user_id, "note_created", resource_type, resource_id, title)
        return note

    def list_notes(self, user_id: str, resource_type: str = "", resource_id: str = "") -> list:
        conn = _db()
        q = "SELECT * FROM notes WHERE user_id=?"
        params: list = [user_id]
        if resource_type:
            q += " AND resource_type=?"
            params.append(resource_type)
        if resource_id:
            q += " AND resource_id=?"
            params.append(resource_id)
        q += " ORDER BY pinned DESC, updated_at DESC"
        rows = conn.execute(q, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_note(self, note_id: str) -> Optional[dict]:
        conn = _db()
        row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_note(self, note_id: str, **kwargs) -> Optional[dict]:
        conn = _db()
        updates = []
        params = []
        for k in ("title", "content", "pinned", "color"):
            if k in kwargs:
                updates.append(f"{k}=?")
                params.append(kwargs[k])
        if updates:
            updates.append("updated_at=datetime('now')")
            params.append(note_id)
            conn.execute(f"UPDATE notes SET {', '.join(updates)} WHERE id=?", params)
            conn.commit()
        note = self.get_note(note_id)
        conn.close()
        return note

    def delete_note(self, note_id: str) -> bool:
        conn = _db()
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.commit()
        conn.close()
        return True

    def pin_note(self, note_id: str, pinned: bool = True) -> bool:
        conn = _db()
        conn.execute("UPDATE notes SET pinned=?, updated_at=datetime('now') WHERE id=?", (1 if pinned else 0, note_id))
        conn.commit()
        conn.close()
        return True

    def search_notes(self, user_id: str, query: str) -> list:
        conn = _db()
        q = "%{}%".format(query)
        rows = conn.execute(
            "SELECT * FROM notes WHERE user_id=? AND (title LIKE ? OR content LIKE ?) ORDER BY updated_at DESC LIMIT 50",
            (user_id, q, q)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
