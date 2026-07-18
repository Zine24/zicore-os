"""
ZiVault — Universal Asset Vault v1.0
Part of the ZICORE Ecosystem

Zero Debt. User Ownership First. Security by Design.
NOT a bank. Never creates debt, issues loans, or grants credit.
Digital Treasury for every digital and physical asset.

13 Modules: Dashboard, Asset Registry, Portfolio Manager, Digital Vault,
Ownership Engine, Transactions, AI Asset Manager, Blockchain Gateway,
Audit Center, Notifications, Reports, Tags & Notes, Accounts
"""

import uuid
import json
import time
import sqlite3
import hashlib
import logging
import csv
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("zicore.zivault")

VAULT_DB = Path(__file__).parent.parent / "data" / "zivault.db"

ZNT_DISCOUNT_PERCENT = 15

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

PORTFOLIO_TYPES = ["personal", "business", "research", "investment",
                   "space_mission", "energy", "infrastructure"]

ALERT_TYPES = ["system", "security", "transaction", "asset", "portfolio", "ai"]
ALERT_SEVERITIES = ["info", "warning", "critical", "error"]

AI_ANALYSIS_TYPES = ["categorization", "valuation", "risk", "optimization",
                     "duplicate_detection", "portfolio_analysis"]

CHAINS = ["ethereum", "bitcoin", "solana", "polygon", "bsc", "avalanche",
          "arbitrum", "optimism", "polygon_zkevm", "base", "custom"]

REPORT_TYPES = ["full", "summary", "tax", "asset_detail", "organization"]

FILE_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg",
              "gif", "svg", "mp3", "mp4", "wav", "txt", "json", "csv",
              "zip", "stl", "obj", "step", "iges", "other"]


def _db():
    conn = sqlite3.connect(str(VAULT_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _sign(*parts):
    raw = ":".join(str(p) for p in parts) + ":" + str(time.time())
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def init_db():
    VAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = _db()
    c = conn.cursor()

    # ── EXISTING TABLES (18) ──────────────────────────────────────────────

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
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
        metadata TEXT DEFAULT '{}',
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
        description TEXT DEFAULT '',
        file_data TEXT DEFAULT '',
        deleted INTEGER DEFAULT 0,
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
        severity TEXT DEFAULT 'info',
        read INTEGER DEFAULT 0,
        metadata TEXT DEFAULT '{}',
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

    # ── NEW TABLES (6) ────────────────────────────────────────────────────

    c.execute("""CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        asset_id TEXT,
        alert_type TEXT NOT NULL,
        severity TEXT DEFAULT 'info',
        title TEXT NOT NULL,
        message TEXT,
        resolved INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id TEXT PRIMARY KEY,
        portfolio_id TEXT NOT NULL,
        snapshot_date TEXT NOT NULL,
        total_value REAL DEFAULT 0,
        currency TEXT DEFAULT 'ZNT',
        asset_count INTEGER DEFAULT 0,
        metadata TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ai_analysis (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        asset_id TEXT,
        analysis_type TEXT NOT NULL,
        result TEXT NOT NULL,
        confidence REAL DEFAULT 0,
        metadata TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS blockchain_wallets (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        chain TEXT NOT NULL,
        address TEXT NOT NULL,
        label TEXT,
        is_primary INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS device_sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        device_name TEXT,
        device_type TEXT,
        ip_address TEXT,
        user_agent TEXT,
        last_active TEXT DEFAULT (datetime('now')),
        revoked INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS api_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key_id TEXT,
        endpoint TEXT,
        method TEXT,
        status_code INTEGER,
        response_time_ms INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # ── SEED DATA ─────────────────────────────────────────────────────────

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
    logger.info("ZiVault database initialized (24 tables)")


class ZiVault:
    def __init__(self):
        init_db()

    # ═══════════════════════════════════════════════════════════════════════
    #  AUDIT HELPER
    # ═══════════════════════════════════════════════════════════════════════

    def _log(self, user_id, action, resource_type="", resource_id="", details="", ip="", device=""):
        try:
            conn = _db()
            conn.execute(
                "INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address, device) VALUES (?,?,?,?,?,?,?)",
                (user_id, action, resource_type, resource_id, details, ip, device)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"_log failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    #  1. DASHBOARD MODULE
    # ═══════════════════════════════════════════════════════════════════════

    def get_dashboard(self, owner_id):
        try:
            conn = _db()

            total_assets = conn.execute(
                "SELECT COUNT(*) as cnt FROM assets WHERE owner_id=? AND status='active'", (owner_id,)
            ).fetchone()["cnt"]

            value_rows = conn.execute(
                "SELECT currency, SUM(current_value) as total FROM assets WHERE owner_id=? AND status='active' GROUP BY currency",
                (owner_id,)
            ).fetchall()
            total_value = {r["currency"]: r["total"] for r in value_rows}

            type_rows = conn.execute(
                "SELECT asset_type, COUNT(*) as cnt, SUM(current_value) as val FROM assets WHERE owner_id=? AND status='active' GROUP BY asset_type",
                (owner_id,)
            ).fetchall()
            by_type = [{"type": r["asset_type"], "count": r["cnt"], "value": r["val"] or 0} for r in type_rows]

            recent_tx = conn.execute(
                "SELECT * FROM transactions WHERE owner_id=? ORDER BY created_at DESC LIMIT 10", (owner_id,)
            ).fetchall()

            recent_audit = conn.execute(
                "SELECT * FROM audit_logs WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (owner_id,)
            ).fetchall()

            unread_notifications = conn.execute(
                "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND read=0", (owner_id,)
            ).fetchone()["cnt"]

            unresolved_alerts = conn.execute(
                "SELECT * FROM alerts WHERE user_id=? AND resolved=0 ORDER BY created_at DESC", (owner_id,)
            ).fetchall()

            portfolio_rows = conn.execute(
                "SELECT * FROM portfolios WHERE owner_id=?", (owner_id,)
            ).fetchall()
            portfolio_health = []
            for p in portfolio_rows:
                pid = p["id"]
                asset_rows = conn.execute(
                    "SELECT a.* FROM assets a JOIN portfolio_assets pa ON a.id=pa.asset_id WHERE pa.portfolio_id=?", (pid,)
                ).fetchall()
                pv = sum(r["current_value"] or 0 for r in asset_rows)
                portfolio_health.append({
                    "portfolio_id": pid,
                    "name": p["name"],
                    "type": p["portfolio_type"],
                    "value": pv,
                    "asset_count": len(asset_rows),
                    "growth_30d": 0,
                    "risk_score": 0,
                })

            ai_recommendations = conn.execute(
                "SELECT * FROM ai_analysis WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (owner_id,)
            ).fetchall()

            top_assets = conn.execute(
                "SELECT * FROM assets WHERE owner_id=? AND status='active' ORDER BY current_value DESC LIMIT 5",
                (owner_id,)
            ).fetchall()

            total_files = conn.execute(
                "SELECT COUNT(*) as cnt FROM vault_files WHERE owner_id=? AND deleted=0", (owner_id,)
            ).fetchone()["cnt"]

            total_tx = conn.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE owner_id=?", (owner_id,)
            ).fetchone()["cnt"]

            conn.close()

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
                "net_worth": total_value,
                "net_worth_usd": round(usd_total, 2),
                "by_type": by_type,
                "recent_transactions": [dict(r) for r in recent_tx],
                "recent_activity": [dict(r) for r in recent_audit],
                "unread_notifications": unread_notifications,
                "alerts": [dict(r) for r in unresolved_alerts],
                "portfolio_health": portfolio_health,
                "ai_recommendations": [dict(r) for r in ai_recommendations],
                "top_assets": [dict(r) for r in top_assets],
                "total_files": total_files,
                "total_transactions": total_tx,
            }
        except Exception as e:
            logger.error(f"get_dashboard failed: {e}")
            return {"error": str(e)}

    def get_net_worth(self, owner_id):
        try:
            conn = _db()
            rows = conn.execute(
                "SELECT currency, SUM(current_value) as total FROM assets WHERE owner_id=? AND status='active' GROUP BY currency",
                (owner_id,)
            ).fetchall()
            conn.close()
            result = {r["currency"]: r["total"] for r in rows}
            usd = 0
            for cur, val in result.items():
                if cur == "USD":
                    usd += val
                elif cur == "ZNT":
                    usd += val * 2.47
                elif cur == "BTC":
                    usd += val * 67500
                elif cur == "ETH":
                    usd += val * 3450
            return {"by_currency": result, "usd_equivalent": round(usd, 2)}
        except Exception as e:
            logger.error(f"get_net_worth failed: {e}")
            return {"by_currency": {}, "usd_equivalent": 0}

    def get_asset_distribution(self, owner_id):
        try:
            conn = _db()
            rows = conn.execute(
                "SELECT asset_type, COUNT(*) as count, SUM(current_value) as value FROM assets WHERE owner_id=? AND status='active' GROUP BY asset_type",
                (owner_id,)
            ).fetchall()
            conn.close()
            return [{"type": r["asset_type"], "count": r["count"], "value": r["value"] or 0} for r in rows]
        except Exception as e:
            logger.error(f"get_asset_distribution failed: {e}")
            return []

    def get_historical_value(self, owner_id, days=30):
        try:
            conn = _db()
            snapshots = []
            for i in range(days, -1, -1):
                dt = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                val_rows = conn.execute(
                    "SELECT SUM(current_value) as total FROM assets WHERE owner_id=? AND status='active' AND created_at <= ?",
                    (owner_id, dt)
                ).fetchall()
                total = sum(r["total"] or 0 for r in val_rows)
                snapshots.append({"date": dt, "value": total})
            conn.close()
            return snapshots
        except Exception as e:
            logger.error(f"get_historical_value failed: {e}")
            return []

    def create_alert(self, user_id, alert_type, severity, title, message, asset_id=None):
        try:
            aid = "al_" + uuid.uuid4().hex[:12]
            conn = _db()
            conn.execute(
                "INSERT INTO alerts (id, user_id, asset_id, alert_type, severity, title, message) VALUES (?,?,?,?,?,?,?)",
                (aid, user_id, asset_id, alert_type, severity, title, message)
            )
            conn.commit()
            alert = dict(conn.execute("SELECT * FROM alerts WHERE id=?", (aid,)).fetchone())
            conn.close()
            self._log(user_id, "alert_created", "alert", aid, title)
            return alert
        except Exception as e:
            logger.error(f"create_alert failed: {e}")
            return {"error": str(e)}

    def list_alerts(self, user_id, unresolved_only=False):
        try:
            conn = _db()
            q = "SELECT * FROM alerts WHERE user_id=?"
            if unresolved_only:
                q += " AND resolved=0"
            q += " ORDER BY created_at DESC"
            rows = conn.execute(q, (user_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_alerts failed: {e}")
            return []

    def resolve_alert(self, alert_id):
        try:
            conn = _db()
            conn.execute("UPDATE alerts SET resolved=1 WHERE id=?", (alert_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"resolve_alert failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  2. ASSET REGISTRY
    # ═══════════════════════════════════════════════════════════════════════

    def create_asset(self, owner_id, asset_type, name, **kwargs):
        try:
            aid = "av_" + uuid.uuid4().hex[:16]
            sig = _sign(aid, owner_id, asset_type, name)
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
                 sig,
                 json.dumps(kwargs.get("tags", [])),
                 json.dumps(kwargs.get("metadata", {})),
                 "active"))
            conn.commit()
            asset = dict(conn.execute("SELECT * FROM assets WHERE id=?", (aid,)).fetchone())
            conn.close()

            self._create_ownership(aid, owner_id)
            self._log(owner_id, "asset_created", "asset", aid, name)
            return asset
        except Exception as e:
            logger.error(f"create_asset failed: {e}")
            return {"error": str(e)}

    def get_asset(self, asset_id):
        try:
            conn = _db()
            row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
            conn.close()
            if row:
                d = dict(row)
                d["tags"] = json.loads(d.get("tags", "[]"))
                d["metadata"] = json.loads(d.get("metadata", "{}"))
                return d
            return None
        except Exception as e:
            logger.error(f"get_asset failed: {e}")
            return None

    def list_assets(self, owner_id, asset_type="", status="active", limit=100, offset=0):
        try:
            conn = _db()
            q = "SELECT * FROM assets WHERE owner_id=?"
            params = [owner_id]
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
        except Exception as e:
            logger.error(f"list_assets failed: {e}")
            return []

    def update_asset(self, asset_id, **kwargs):
        try:
            conn = _db()
            updates = []
            params = []
            for k in ("name", "description", "current_value", "currency", "location",
                       "serial_number", "blockchain_hash", "digital_signature", "status",
                       "org_id", "acquisition_date", "acquisition_cost"):
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
        except Exception as e:
            logger.error(f"update_asset failed: {e}")
            return None

    def delete_asset(self, asset_id):
        try:
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
        except Exception as e:
            logger.error(f"delete_asset failed: {e}")
            return False

    def search_assets(self, owner_id, query):
        try:
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
        except Exception as e:
            logger.error(f"search_assets failed: {e}")
            return []

    def get_asset_history(self, asset_id):
        try:
            conn = _db()
            transactions = [dict(r) for r in conn.execute(
                "SELECT * FROM transactions WHERE asset_id=? ORDER BY created_at DESC", (asset_id,)
            ).fetchall()]
            ownership = [dict(r) for r in conn.execute(
                "SELECT * FROM ownership WHERE asset_id=? ORDER BY created_at DESC", (asset_id,)
            ).fetchall()]
            notes = [dict(r) for r in conn.execute(
                "SELECT * FROM notes WHERE resource_type='asset' AND resource_id=? ORDER BY created_at DESC",
                (asset_id,)
            ).fetchall()]
            blockchain = [dict(r) for r in conn.execute(
                "SELECT * FROM blockchain_records WHERE asset_id=? ORDER BY created_at DESC", (asset_id,)
            ).fetchall()]
            conn.close()
            return {
                "transactions": transactions,
                "ownership": ownership,
                "notes": notes,
                "blockchain": blockchain,
            }
        except Exception as e:
            logger.error(f"get_asset_history failed: {e}")
            return {"transactions": [], "ownership": [], "notes": [], "blockchain": []}

    # ═══════════════════════════════════════════════════════════════════════
    #  3. PORTFOLIO MANAGER
    # ═══════════════════════════════════════════════════════════════════════

    def create_portfolio(self, owner_id, name, ptype="personal", desc=""):
        try:
            pid = "pf_" + uuid.uuid4().hex[:12]
            conn = _db()
            conn.execute("INSERT INTO portfolios (id, owner_id, name, description, portfolio_type) VALUES (?,?,?,?,?)",
                         (pid, owner_id, name, desc, ptype))
            conn.commit()
            p = dict(conn.execute("SELECT * FROM portfolios WHERE id=?", (pid,)).fetchone())
            conn.close()
            self._log(owner_id, "portfolio_created", "portfolio", pid, name)
            return p
        except Exception as e:
            logger.error(f"create_portfolio failed: {e}")
            return {"error": str(e)}

    def list_portfolios(self, owner_id):
        try:
            conn = _db()
            rows = conn.execute("SELECT * FROM portfolios WHERE owner_id=? ORDER BY created_at DESC", (owner_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_portfolios failed: {e}")
            return []

    def add_asset_to_portfolio(self, portfolio_id, asset_id):
        try:
            conn = _db()
            conn.execute("INSERT OR IGNORE INTO portfolio_assets (portfolio_id, asset_id) VALUES (?,?)",
                         (portfolio_id, asset_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"add_asset_to_portfolio failed: {e}")
            return False

    def remove_asset_from_portfolio(self, portfolio_id, asset_id):
        try:
            conn = _db()
            conn.execute("DELETE FROM portfolio_assets WHERE portfolio_id=? AND asset_id=?", (portfolio_id, asset_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"remove_asset_from_portfolio failed: {e}")
            return False

    def get_portfolio_assets(self, portfolio_id):
        try:
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
        except Exception as e:
            logger.error(f"get_portfolio_assets failed: {e}")
            return []

    def get_portfolio_summary(self, portfolio_id):
        try:
            conn = _db()
            p = conn.execute("SELECT * FROM portfolios WHERE id=?", (portfolio_id,)).fetchone()
            if not p:
                conn.close()
                return {"error": "Portfolio not found"}

            asset_rows = conn.execute("""
                SELECT a.* FROM assets a
                JOIN portfolio_assets pa ON a.id=pa.asset_id
                WHERE pa.portfolio_id=?
            """, (portfolio_id,)).fetchall()

            total_value = sum(r["current_value"] or 0 for r in asset_rows)
            asset_count = len(asset_rows)

            type_map = {}
            for r in asset_rows:
                t = r["asset_type"]
                if t not in type_map:
                    type_map[t] = {"count": 0, "value": 0}
                type_map[t]["count"] += 1
                type_map[t]["value"] += r["current_value"] or 0

            risk_score = self.calculate_risk_score(portfolio_id)

            snapshots = conn.execute(
                "SELECT total_value FROM portfolio_snapshots WHERE portfolio_id=? ORDER BY snapshot_date DESC LIMIT 30",
                (portfolio_id,)
            ).fetchall()
            conn.close()

            growth_30d = 0
            if snapshots and len(snapshots) >= 2:
                current = snapshots[0]["total_value"]
                old = snapshots[-1]["total_value"]
                if old > 0:
                    growth_30d = round(((current - old) / old) * 100, 2)

            return {
                "portfolio_id": portfolio_id,
                "name": p["name"],
                "type": p["portfolio_type"],
                "total_value": total_value,
                "asset_count": asset_count,
                "by_type": type_map,
                "risk_score": risk_score,
                "growth_30d": growth_30d,
            }
        except Exception as e:
            logger.error(f"get_portfolio_summary failed: {e}")
            return {"error": str(e)}

    def snapshot_portfolio(self, portfolio_id):
        try:
            sid = "ps_" + uuid.uuid4().hex[:12]
            conn = _db()
            asset_rows = conn.execute("""
                SELECT a.* FROM assets a
                JOIN portfolio_assets pa ON a.id=pa.asset_id
                WHERE pa.portfolio_id=?
            """, (portfolio_id,)).fetchall()

            total_value = sum(r["current_value"] or 0 for r in asset_rows)
            asset_count = len(asset_rows)

            conn.execute(
                "INSERT INTO portfolio_snapshots (id, portfolio_id, snapshot_date, total_value, asset_count, metadata) VALUES (?,?,?,?,?,?)",
                (sid, portfolio_id, datetime.now(timezone.utc).isoformat(), total_value, asset_count, "{}")
            )
            conn.commit()
            snap = dict(conn.execute("SELECT * FROM portfolio_snapshots WHERE id=?", (sid,)).fetchone())
            conn.close()
            return snap
        except Exception as e:
            logger.error(f"snapshot_portfolio failed: {e}")
            return {"error": str(e)}

    def get_portfolio_history(self, portfolio_id, days=30):
        try:
            conn = _db()
            rows = conn.execute(
                "SELECT * FROM portfolio_snapshots WHERE portfolio_id=? ORDER BY snapshot_date DESC LIMIT ?",
                (portfolio_id, days)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_portfolio_history failed: {e}")
            return []

    def calculate_risk_score(self, portfolio_id):
        try:
            conn = _db()
            asset_rows = conn.execute("""
                SELECT a.asset_type, a.current_value FROM assets a
                JOIN portfolio_assets pa ON a.id=pa.asset_id
                WHERE pa.portfolio_id=?
            """, (portfolio_id,)).fetchall()
            conn.close()

            if not asset_rows:
                return 0

            total = sum(r["current_value"] or 0 for r in asset_rows)
            if total == 0:
                return 0

            type_values = {}
            for r in asset_rows:
                t = r["asset_type"]
                type_values[t] = type_values.get(t, 0) + (r["current_value"] or 0)

            num_types = len(type_values)
            if num_types <= 1:
                concentration_risk = 100
            else:
                max_pct = max((v / total) * 100 for v in type_values.values())
                concentration_risk = min(max_pct, 100)

            high_risk_types = {"crypto", "nft", "ai_model", "carbon_credit"}
            high_risk_count = sum(1 for r in asset_rows if r["asset_type"] in high_risk_types)
            volatility_risk = (high_risk_count / len(asset_rows)) * 100

            risk_score = round((concentration_risk * 0.6 + volatility_risk * 0.4), 2)
            return min(risk_score, 100)
        except Exception as e:
            logger.error(f"calculate_risk_score failed: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════════════
    #  4. DIGITAL VAULT
    # ═══════════════════════════════════════════════════════════════════════

    def upload_file(self, owner_id, filename, file_type="", file_size=0,
                    file_data=None, asset_id=None, encrypted=True, description=""):
        try:
            fid = "vf_" + uuid.uuid4().hex[:12]
            checksum = hashlib.sha256(f"{filename}:{file_size}:{time.time()}".encode()).hexdigest()
            sig = _sign(fid, owner_id, checksum)
            conn = _db()

            existing = conn.execute(
                "SELECT id, version FROM vault_files WHERE owner_id=? AND filename=? AND deleted=0 ORDER BY version DESC LIMIT 1",
                (owner_id, filename)
            ).fetchone()
            version = (existing["version"] + 1) if existing else 1

            conn.execute("""INSERT INTO vault_files
                (id, owner_id, asset_id, filename, file_type, file_size, checksum, encrypted, version,
                 digital_signature, description, file_data)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fid, owner_id, asset_id or "", filename, file_type, file_size, checksum,
                 1 if encrypted else 0, version, sig, description, file_data or ""))
            conn.commit()
            f = dict(conn.execute("SELECT * FROM vault_files WHERE id=?", (fid,)).fetchone())
            conn.close()
            self._log(owner_id, "file_uploaded", "vault_file", fid, filename)
            return f
        except Exception as e:
            logger.error(f"upload_file failed: {e}")
            return {"error": str(e)}

    def list_files(self, owner_id, asset_id=""):
        try:
            conn = _db()
            if asset_id:
                rows = conn.execute(
                    "SELECT * FROM vault_files WHERE owner_id=? AND asset_id=? AND deleted=0 ORDER BY created_at DESC",
                    (owner_id, asset_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM vault_files WHERE owner_id=? AND deleted=0 ORDER BY created_at DESC",
                    (owner_id,)
                ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_files failed: {e}")
            return []

    def get_file_versions(self, file_id):
        try:
            conn = _db()
            file_row = conn.execute("SELECT filename, owner_id FROM vault_files WHERE id=?", (file_id,)).fetchone()
            if not file_row:
                conn.close()
                return []
            rows = conn.execute(
                "SELECT * FROM vault_files WHERE owner_id=? AND filename=? AND deleted=0 ORDER BY version DESC",
                (file_row["owner_id"], file_row["filename"])
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_file_versions failed: {e}")
            return []

    def get_file(self, file_id):
        try:
            conn = _db()
            row = conn.execute("SELECT * FROM vault_files WHERE id=? AND deleted=0", (file_id,)).fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"get_file failed: {e}")
            return None

    def download_file(self, file_id, owner_id):
        try:
            conn = _db()
            row = conn.execute(
                "SELECT * FROM vault_files WHERE id=? AND owner_id=? AND deleted=0",
                (file_id, owner_id)
            ).fetchone()
            conn.close()
            if not row:
                return None
            self._log(owner_id, "file_downloaded", "vault_file", file_id)
            return dict(row)
        except Exception as e:
            logger.error(f"download_file failed: {e}")
            return None

    def delete_file(self, file_id):
        try:
            conn = _db()
            row = conn.execute("SELECT owner_id FROM vault_files WHERE id=?", (file_id,)).fetchone()
            if not row:
                conn.close()
                return False
            conn.execute("UPDATE vault_files SET deleted=1 WHERE id=?", (file_id,))
            conn.commit()
            conn.close()
            self._log(row["owner_id"], "file_deleted", "vault_file", file_id)
            return True
        except Exception as e:
            logger.error(f"delete_file failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  5. OWNERSHIP ENGINE
    # ═══════════════════════════════════════════════════════════════════════

    def _create_ownership(self, asset_id, owner_id):
        try:
            oid = "own_" + uuid.uuid4().hex[:12]
            cert_id = "CERT-" + uuid.uuid4().hex[:8].upper()
            sig = _sign(oid, asset_id, owner_id, cert_id)
            conn = _db()
            conn.execute("""INSERT INTO ownership (id, asset_id, owner_id, verified, certificate_id)
                VALUES (?,?,?,1,?)""", (oid, asset_id, owner_id, cert_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"_create_ownership failed: {e}")

    def create_ownership_certificate(self, asset_id, owner_id):
        try:
            oid = "own_" + uuid.uuid4().hex[:12]
            cert_id = "CERT-" + uuid.uuid4().hex[:8].upper()
            sig = _sign(oid, asset_id, owner_id, cert_id)
            conn = _db()
            conn.execute("""INSERT INTO ownership (id, asset_id, owner_id, verified, certificate_id)
                VALUES (?,?,?,1,?)""", (oid, asset_id, owner_id, cert_id))
            conn.commit()
            cert = dict(conn.execute("SELECT * FROM ownership WHERE id=?", (oid,)).fetchone())
            conn.close()
            self._log(owner_id, "ownership_certificate_created", "ownership", oid, cert_id)
            return cert
        except Exception as e:
            logger.error(f"create_ownership_certificate failed: {e}")
            return {"error": str(e)}

    def get_ownership(self, asset_id):
        try:
            conn = _db()
            row = conn.execute("SELECT * FROM ownership WHERE asset_id=?", (asset_id,)).fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"get_ownership failed: {e}")
            return None

    def verify_ownership(self, asset_id, owner_id):
        try:
            conn = _db()
            row = conn.execute(
                "SELECT * FROM ownership WHERE asset_id=? AND owner_id=? AND verified=1",
                (asset_id, owner_id)
            ).fetchone()
            conn.close()
            return row is not None
        except Exception as e:
            logger.error(f"verify_ownership failed: {e}")
            return False

    def get_ownership_history(self, asset_id):
        try:
            conn = _db()
            rows = conn.execute(
                "SELECT * FROM ownership WHERE asset_id=? ORDER BY created_at DESC", (asset_id,)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_ownership_history failed: {e}")
            return []

    def transfer_ownership(self, asset_id, from_owner, to_owner, price=0, currency="ZNT"):
        try:
            conn = _db()
            conn.execute(
                "UPDATE ownership SET verified=0, transfer_count=transfer_count+1 WHERE asset_id=? AND owner_id=?",
                (asset_id, from_owner)
            )
            conn.execute("UPDATE assets SET owner_id=?, updated_at=datetime('now') WHERE id=?", (to_owner, asset_id))
            conn.commit()
            conn.close()

            self.create_ownership_certificate(asset_id, to_owner)

            if price > 0:
                self.create_transaction(from_owner, asset_id, "sale", price, currency, to_owner,
                                        f"Ownership transfer of {asset_id}")
                self.create_transaction(to_owner, asset_id, "purchase", price, currency, from_owner,
                                        f"Ownership acquisition of {asset_id}")

            self._log(from_owner, "ownership_transferred", "asset", asset_id, f"to {to_owner}")
            return True
        except Exception as e:
            logger.error(f"transfer_ownership failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  6. TRANSACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def create_transaction(self, owner_id, asset_id, tx_type, amount=0, currency="ZNT",
                           counterparty="", description="", metadata=None):
        try:
            tid = "tx_" + uuid.uuid4().hex[:16]
            sig = _sign(tid, owner_id, asset_id, tx_type, amount, currency)
            conn = _db()
            conn.execute("""INSERT INTO transactions
                (id, owner_id, asset_id, tx_type, amount, currency, counterparty, description,
                 digital_signature, metadata)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (tid, owner_id, asset_id, tx_type, amount, currency, counterparty, description,
                 sig, json.dumps(metadata or {})))
            conn.commit()
            tx = dict(conn.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone())
            conn.close()
            self._log(owner_id, "transaction_created", "transaction", tid, f"{tx_type}: {amount} {currency}")
            return tx
        except Exception as e:
            logger.error(f"create_transaction failed: {e}")
            return {"error": str(e)}

    def list_transactions(self, owner_id, asset_id="", limit=50):
        try:
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
        except Exception as e:
            logger.error(f"list_transactions failed: {e}")
            return []

    def get_transaction_summary(self, owner_id, days=30):
        try:
            conn = _db()
            rows = conn.execute("""
                SELECT tx_type, COUNT(*) as count, SUM(amount) as total_amount, currency
                FROM transactions WHERE owner_id=?
                AND created_at >= datetime('now', ?)
                GROUP BY tx_type, currency
            """, (owner_id, f"-{days} days")).fetchall()
            conn.close()
            summary = {}
            for r in rows:
                t = r["tx_type"]
                if t not in summary:
                    summary[t] = {"count": 0, "amounts": {}}
                summary[t]["count"] += r["count"]
                summary[t]["amounts"][r["currency"]] = summary[t]["amounts"].get(r["currency"], 0) + (r["total_amount"] or 0)
            return summary
        except Exception as e:
            logger.error(f"get_transaction_summary failed: {e}")
            return {}

    # ═══════════════════════════════════════════════════════════════════════
    #  7. AI ASSET MANAGER
    # ═══════════════════════════════════════════════════════════════════════

    def ai_categorize(self, asset_id):
        try:
            asset = self.get_asset(asset_id)
            if not asset:
                return {"error": "Asset not found"}

            name_lower = (asset["name"] + " " + asset.get("description", "")).lower()
            suggestions = []

            keyword_map = {
                "crypto": ["bitcoin", "btc", "eth", "ethereum", "crypto", "token", "coin", "defi"],
                "stock": ["stock", "share", "equity", "ticker", "nasdaq", "nyse"],
                "real_estate": ["property", "house", "land", "building", "apartment", "real estate"],
                "vehicle": ["car", "truck", "bike", "motorcycle", "boat", "aircraft", "vehicle"],
                "server": ["server", "hosting", "vps", "dedicated", "cloud server"],
                "satellite": ["satellite", "orbit", "leo", "geo", "constellation"],
                "ai_model": ["model", "neural", "transformer", "llm", "gpt", "diffusion"],
                "domain": ["domain", ".com", ".net", ".org", "website"],
                "digital_art": ["art", "nft", "digital art", "generative", "canvas"],
                "patent": ["patent", "invention", "filing", "intellectual property"],
                "publication": ["paper", "journal", "publication", "research", "article"],
                "solar_plant": ["solar", "panel", "pv", "photovoltaic"],
            }

            for cat, keywords in keyword_map.items():
                if any(kw in name_lower for kw in keywords):
                    suggestions.append({"type": cat, "confidence": 0.85})

            if not suggestions:
                suggestions.append({"type": "custom", "confidence": 0.3})

            self.ai_store_analysis(asset["owner_id"], "categorization", asset_id,
                                   json.dumps(suggestions), suggestions[0]["confidence"])
            return {"current_type": asset["asset_type"], "suggestions": suggestions}
        except Exception as e:
            logger.error(f"ai_categorize failed: {e}")
            return {"error": str(e)}

    def ai_detect_duplicates(self, owner_id):
        try:
            assets = self.list_assets(owner_id, limit=1000)
            duplicates = []
            seen = {}
            for a in assets:
                key = (a["name"].lower().strip(), a["asset_type"])
                if key in seen:
                    duplicates.append({
                        "pair": [seen[key], a["id"]],
                        "reason": "Same name and type",
                        "confidence": 0.9
                    })
                else:
                    seen[key] = a["id"]

                if a.get("serial_number"):
                    for other in assets:
                        if other["id"] != a["id"] and other.get("serial_number") == a["serial_number"]:
                            duplicates.append({
                                "pair": [a["id"], other["id"]],
                                "reason": "Same serial number",
                                "confidence": 0.95
                            })
            return {"duplicates": duplicates, "total_checked": len(assets)}
        except Exception as e:
            logger.error(f"ai_detect_duplicates failed: {e}")
            return {"duplicates": [], "total_checked": 0}

    def ai_estimate_value(self, asset_id):
        try:
            asset = self.get_asset(asset_id)
            if not asset:
                return {"error": "Asset not found"}

            current = asset.get("current_value", 0) or 0
            cost = asset.get("acquisition_cost", 0) or 0
            created = asset.get("acquisition_date", "") or asset.get("created_at", "")

            depreciation_types = {"vehicle": 0.15, "server": 0.25, "equipment": 0.20,
                                  "robot": 0.18, "drone": 0.22}
            appreciation_types = {"real_estate": 0.05, "domain": 0.10, "patent": 0.08,
                                  "stock": 0.12, "crypto": 0.15}

            asset_type = asset.get("asset_type", "")
            rate = depreciation_types.get(asset_type, appreciation_types.get(asset_type, 0.05))

            if cost > 0:
                estimated = cost * (1 + rate)
            else:
                estimated = current * (1 + rate) if current > 0 else 0

            result = {
                "asset_id": asset_id,
                "current_value": current,
                "estimated_value": round(estimated, 2),
                "rate_applied": rate,
                "asset_type": asset_type,
            }

            self.ai_store_analysis(asset["owner_id"], "valuation", asset_id,
                                   json.dumps(result), 0.7)
            return result
        except Exception as e:
            logger.error(f"ai_estimate_value failed: {e}")
            return {"error": str(e)}

    def ai_portfolio_optimization(self, owner_id):
        try:
            assets = self.list_assets(owner_id, limit=1000)
            if not assets:
                return {"suggestions": [], "total_assets": 0}

            total_value = sum(a.get("current_value", 0) or 0 for a in assets)
            type_values = {}
            for a in assets:
                t = a["asset_type"]
                type_values[t] = type_values.get(t, 0) + (a.get("current_value", 0) or 0)

            suggestions = []
            if total_value > 0:
                for t, val in type_values.items():
                    pct = (val / total_value) * 100
                    if pct > 40:
                        suggestions.append({
                            "action": "reduce",
                            "type": t,
                            "current_pct": round(pct, 1),
                            "message": f"{t} represents {pct:.1f}% of portfolio — consider diversifying"
                        })
                    elif pct < 5 and len(type_values) < 5:
                        suggestions.append({
                            "action": "increase",
                            "type": t,
                            "current_pct": round(pct, 1),
                            "message": f"{t} is only {pct:.1f}% — small allocation"
                        })

            if len(type_values) < 3:
                suggestions.append({
                    "action": "diversify",
                    "message": f"Portfolio has only {len(type_values)} asset types — consider adding more"
                })

            return {"suggestions": suggestions, "total_assets": len(assets),
                    "total_value": total_value, "type_distribution": type_values}
        except Exception as e:
            logger.error(f"ai_portfolio_optimization failed: {e}")
            return {"suggestions": [], "total_assets": 0}

    def ai_risk_analysis(self, owner_id):
        try:
            assets = self.list_assets(owner_id, limit=1000)
            if not assets:
                return {"overall_risk": 0, "factors": []}

            total = sum(a.get("current_value", 0) or 0 for a in assets)
            factors = []

            high_risk = {"crypto", "nft", "ai_model", "carbon_credit", "custom"}
            high_risk_val = sum(a.get("current_value", 0) or 0 for a in assets if a["asset_type"] in high_risk)
            if total > 0:
                high_risk_pct = (high_risk_val / total) * 100
                if high_risk_pct > 30:
                    factors.append({"factor": "high_risk_concentration", "severity": "high",
                                    "detail": f"{high_risk_pct:.1f}% in high-risk assets"})

            type_counts = {}
            for a in assets:
                type_counts[a["asset_type"]] = type_counts.get(a["asset_type"], 0) + 1
            if len(type_counts) < 3:
                factors.append({"factor": "low_diversification", "severity": "medium",
                                "detail": f"Only {len(type_counts)} asset types"})

            zero_val = sum(1 for a in assets if (a.get("current_value", 0) or 0) == 0)
            if zero_val > 0:
                factors.append({"factor": "zero_value_assets", "severity": "low",
                                "detail": f"{zero_val} assets with zero value"})

            risk = min(len(factors) * 25, 100)
            return {"overall_risk": risk, "factors": factors, "total_assets": len(assets)}
        except Exception as e:
            logger.error(f"ai_risk_analysis failed: {e}")
            return {"overall_risk": 0, "factors": []}

    def ai_store_analysis(self, user_id, analysis_type, asset_id, result, confidence):
        try:
            aid = "aia_" + uuid.uuid4().hex[:12]
            conn = _db()
            conn.execute(
                "INSERT INTO ai_analysis (id, user_id, asset_id, analysis_type, result, confidence) VALUES (?,?,?,?,?,?)",
                (aid, user_id, asset_id, analysis_type, result, confidence)
            )
            conn.commit()
            conn.close()
            return aid
        except Exception as e:
            logger.error(f"ai_store_analysis failed: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    #  8. BLOCKCHAIN GATEWAY
    # ═══════════════════════════════════════════════════════════════════════

    def register_wallet(self, user_id, chain, address, label=""):
        try:
            wid = "bw_" + uuid.uuid4().hex[:12]
            conn = _db()
            existing = conn.execute(
                "SELECT COUNT(*) as cnt FROM blockchain_wallets WHERE user_id=?", (user_id,)
            ).fetchone()["cnt"]
            is_primary = 1 if existing == 0 else 0
            conn.execute(
                "INSERT INTO blockchain_wallets (id, user_id, chain, address, label, is_primary) VALUES (?,?,?,?,?,?)",
                (wid, user_id, chain, address, label, is_primary)
            )
            conn.commit()
            wallet = dict(conn.execute("SELECT * FROM blockchain_wallets WHERE id=?", (wid,)).fetchone())
            conn.close()
            self._log(user_id, "wallet_registered", "blockchain_wallet", wid, f"{chain}: {address}")
            return wallet
        except Exception as e:
            logger.error(f"register_wallet failed: {e}")
            return {"error": str(e)}

    def list_wallets(self, user_id):
        try:
            conn = _db()
            rows = conn.execute(
                "SELECT * FROM blockchain_wallets WHERE user_id=? ORDER BY is_primary DESC, created_at DESC",
                (user_id,)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_wallets failed: {e}")
            return []

    def create_blockchain_record(self, asset_id, chain, tx_hash, block_number=None,
                                 contract_address=None, token_id=None):
        try:
            rid = "bcr_" + uuid.uuid4().hex[:12]
            conn = _db()
            conn.execute("""INSERT INTO blockchain_records
                (id, asset_id, chain, tx_hash, block_number, contract_address, token_id)
                VALUES (?,?,?,?,?,?,?)""",
                (rid, asset_id, chain, tx_hash, block_number or 0,
                 contract_address or "", token_id or ""))
            conn.commit()
            rec = dict(conn.execute("SELECT * FROM blockchain_records WHERE id=?", (rid,)).fetchone())
            conn.close()
            self._log("", "blockchain_record_created", "blockchain_record", rid, f"{chain}: {tx_hash}")
            return rec
        except Exception as e:
            logger.error(f"create_blockchain_record failed: {e}")
            return {"error": str(e)}

    def verify_blockchain_record(self, record_id):
        try:
            conn = _db()
            row = conn.execute("SELECT * FROM blockchain_records WHERE id=?", (record_id,)).fetchone()
            conn.close()
            if not row:
                return {"exists": False, "verified": False}
            rec = dict(row)
            verified = bool(rec.get("tx_hash") and rec.get("chain"))
            return {"exists": True, "verified": verified, "record": rec}
        except Exception as e:
            logger.error(f"verify_blockchain_record failed: {e}")
            return {"exists": False, "verified": False}

    # ═══════════════════════════════════════════════════════════════════════
    #  9. AUDIT CENTER
    # ═══════════════════════════════════════════════════════════════════════

    def get_audit_logs(self, user_id, limit=50, offset=0, action_filter=None,
                       resource_type=None, date_from=None, date_to=None):
        try:
            conn = _db()
            q = "SELECT * FROM audit_logs WHERE user_id=?"
            params = [user_id]
            if action_filter:
                q += " AND action=?"
                params.append(action_filter)
            if resource_type:
                q += " AND resource_type=?"
                params.append(resource_type)
            if date_from:
                q += " AND created_at>=?"
                params.append(date_from)
            if date_to:
                q += " AND created_at<=?"
                params.append(date_to)
            q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(q, params).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_audit_logs failed: {e}")
            return []

    def export_audit_logs(self, user_id, format="json", date_from=None, date_to=None):
        try:
            conn = _db()
            q = "SELECT * FROM audit_logs WHERE user_id=?"
            params = [user_id]
            if date_from:
                q += " AND created_at>=?"
                params.append(date_from)
            if date_to:
                q += " AND created_at<=?"
                params.append(date_to)
            q += " ORDER BY created_at DESC"
            rows = conn.execute(q, params).fetchall()
            conn.close()
            data = [dict(r) for r in rows]

            if format == "csv":
                if not data:
                    return ""
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue()
            return data
        except Exception as e:
            logger.error(f"export_audit_logs failed: {e}")
            return [] if format != "csv" else ""

    # ═══════════════════════════════════════════════════════════════════════
    #  10. NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def create_notification(self, user_id, title, message="", channel="web",
                            severity="info", metadata=None):
        try:
            nid = "ntf_" + uuid.uuid4().hex[:12]
            conn = _db()
            conn.execute(
                "INSERT INTO notifications (id, user_id, title, message, channel, severity, metadata) VALUES (?,?,?,?,?,?,?)",
                (nid, user_id, title, message, channel, severity, json.dumps(metadata or {}))
            )
            conn.commit()
            n = dict(conn.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone())
            conn.close()
            return n
        except Exception as e:
            logger.error(f"create_notification failed: {e}")
            return {"error": str(e)}

    def list_notifications(self, user_id, unread_only=False, limit=50):
        try:
            conn = _db()
            q = "SELECT * FROM notifications WHERE user_id=?"
            if unread_only:
                q += " AND read=0"
            q += " ORDER BY created_at DESC LIMIT ?"
            rows = conn.execute(q, (user_id, limit)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_notifications failed: {e}")
            return []

    def mark_notification_read(self, notification_id):
        try:
            conn = _db()
            conn.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"mark_notification_read failed: {e}")
            return False

    def mark_all_read(self, user_id):
        try:
            conn = _db()
            conn.execute("UPDATE notifications SET read=1 WHERE user_id=? AND read=0", (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"mark_all_read failed: {e}")
            return False

    def delete_notification(self, notification_id):
        try:
            conn = _db()
            conn.execute("DELETE FROM notifications WHERE id=?", (notification_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"delete_notification failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  11. REPORTS
    # ═══════════════════════════════════════════════════════════════════════

    def generate_portfolio_report(self, owner_id, report_type="full"):
        try:
            dashboard = self.get_dashboard(owner_id)
            assets = self.list_assets(owner_id, limit=1000)

            report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "owner_id": owner_id,
                "report_type": report_type,
            }

            if report_type in ("full", "summary"):
                report["summary"] = {
                    "total_assets": dashboard.get("total_assets", 0),
                    "net_worth_usd": dashboard.get("net_worth_usd", 0),
                    "net_worth": dashboard.get("net_worth", {}),
                    "total_transactions": dashboard.get("total_transactions", 0),
                    "total_files": dashboard.get("total_files", 0),
                }
                report["by_type"] = dashboard.get("by_type", [])

            if report_type in ("full", "asset_detail"):
                report["assets"] = [{
                    "id": a["id"],
                    "name": a["name"],
                    "type": a["asset_type"],
                    "value": a["current_value"],
                    "currency": a["currency"],
                    "status": a["status"],
                    "acquisition_date": a.get("acquisition_date", ""),
                } for a in assets]

            if report_type == "tax":
                summary = self.get_transaction_summary(owner_id, days=365)
                report["tax_summary"] = summary
                report["assets"] = [{
                    "id": a["id"], "name": a["name"], "type": a["asset_type"],
                    "value": a["current_value"], "acquisition_cost": a.get("acquisition_cost", 0),
                } for a in assets]

            if report_type == "organization":
                conn = _db()
                orgs = conn.execute("SELECT * FROM organizations WHERE owner_id=?", (owner_id,)).fetchall()
                conn.close()
                report["organizations"] = [dict(o) for o in orgs]

            return report
        except Exception as e:
            logger.error(f"generate_portfolio_report failed: {e}")
            return {"error": str(e)}

    def generate_asset_report(self, asset_id):
        try:
            asset = self.get_asset(asset_id)
            if not asset:
                return {"error": "Asset not found"}
            history = self.get_asset_history(asset_id)
            tags = self.get_asset_tags(asset_id)
            ownership = self.get_ownership(asset_id)

            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "asset": asset,
                "history": history,
                "tags": tags,
                "ownership": ownership,
            }
        except Exception as e:
            logger.error(f"generate_asset_report failed: {e}")
            return {"error": str(e)}

    def generate_audit_report(self, user_id, date_from=None, date_to=None):
        try:
            logs = self.get_audit_logs(user_id, limit=1000, date_from=date_from, date_to=date_to)

            action_counts = {}
            for log in logs:
                a = log["action"]
                action_counts[a] = action_counts.get(a, 0) + 1

            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "total_events": len(logs),
                "action_breakdown": action_counts,
                "logs": logs,
            }
        except Exception as e:
            logger.error(f"generate_audit_report failed: {e}")
            return {"error": str(e)}

    def export_report(self, report_data, format="json"):
        try:
            if format == "csv":
                if "assets" in report_data and report_data["assets"]:
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=report_data["assets"][0].keys())
                    writer.writeheader()
                    writer.writerows(report_data["assets"])
                    return output.getvalue()
                return ""
            return report_data
        except Exception as e:
            logger.error(f"export_report failed: {e}")
            return {} if format != "csv" else ""

    # ═══════════════════════════════════════════════════════════════════════
    #  12. TAGS & NOTES
    # ═══════════════════════════════════════════════════════════════════════

    def create_tag(self, user_id, name, color="#00e5ff"):
        try:
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
                conn2 = _db()
                row = conn2.execute("SELECT * FROM tags WHERE user_id=? AND name=?", (user_id, name.strip())).fetchone()
                conn2.close()
                return dict(row) if row else {"id": tid, "name": name, "color": color}
        except Exception as e:
            logger.error(f"create_tag failed: {e}")
            return {"error": str(e)}

    def list_tags(self, user_id):
        try:
            conn = _db()
            rows = conn.execute("SELECT * FROM tags WHERE user_id=? ORDER BY name", (user_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_tags failed: {e}")
            return []

    def delete_tag(self, tag_id):
        try:
            conn = _db()
            conn.execute("DELETE FROM asset_tags WHERE tag_id=?", (tag_id,))
            conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"delete_tag failed: {e}")
            return False

    def add_tag_to_asset(self, asset_id, tag_id):
        try:
            conn = _db()
            conn.execute("INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?,?)", (asset_id, tag_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"add_tag_to_asset failed: {e}")
            return False

    def remove_tag_from_asset(self, asset_id, tag_id):
        try:
            conn = _db()
            conn.execute("DELETE FROM asset_tags WHERE asset_id=? AND tag_id=?", (asset_id, tag_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"remove_tag_from_asset failed: {e}")
            return False

    def get_asset_tags(self, asset_id):
        try:
            conn = _db()
            rows = conn.execute("""
                SELECT t.* FROM tags t
                JOIN asset_tags at ON t.id = at.tag_id
                WHERE at.asset_id = ?
            """, (asset_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_asset_tags failed: {e}")
            return []

    def get_assets_by_tag(self, user_id, tag_id):
        try:
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
        except Exception as e:
            logger.error(f"get_assets_by_tag failed: {e}")
            return []

    def create_note(self, user_id, resource_type, resource_id,
                    title="", content="", color=""):
        try:
            nid = "nt_" + uuid.uuid4().hex[:12]
            conn = _db()
            conn.execute("""INSERT INTO notes (id, user_id, resource_type, resource_id, title, content, color)
                VALUES (?,?,?,?,?,?,?)""", (nid, user_id, resource_type, resource_id, title, content, color))
            conn.commit()
            note = dict(conn.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone())
            conn.close()
            self._log(user_id, "note_created", resource_type, resource_id, title)
            return note
        except Exception as e:
            logger.error(f"create_note failed: {e}")
            return {"error": str(e)}

    def list_notes(self, user_id, resource_type="", resource_id=""):
        try:
            conn = _db()
            q = "SELECT * FROM notes WHERE user_id=?"
            params = [user_id]
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
        except Exception as e:
            logger.error(f"list_notes failed: {e}")
            return []

    def get_note(self, note_id):
        try:
            conn = _db()
            row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"get_note failed: {e}")
            return None

    def update_note(self, note_id, **kwargs):
        try:
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
        except Exception as e:
            logger.error(f"update_note failed: {e}")
            return None

    def delete_note(self, note_id):
        try:
            conn = _db()
            conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"delete_note failed: {e}")
            return False

    def pin_note(self, note_id, pinned=True):
        try:
            conn = _db()
            conn.execute("UPDATE notes SET pinned=?, updated_at=datetime('now') WHERE id=?",
                         (1 if pinned else 0, note_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"pin_note failed: {e}")
            return False

    def search_notes(self, user_id, query):
        try:
            conn = _db()
            q = "%{}%".format(query)
            rows = conn.execute(
                "SELECT * FROM notes WHERE user_id=? AND (title LIKE ? OR content LIKE ?) ORDER BY updated_at DESC LIMIT 50",
                (user_id, q, q)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"search_notes failed: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════
    #  13. ACCOUNTS
    # ═══════════════════════════════════════════════════════════════════════

    def get_account(self, user_id):
        try:
            conn = _db()
            user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not user:
                conn.close()
                return None
            account = dict(user)

            asset_val = conn.execute(
                "SELECT currency, SUM(current_value) as total FROM assets WHERE owner_id=? AND status='active' GROUP BY currency",
                (user_id,)
            ).fetchall()
            account["balances"] = {r["currency"]: r["total"] for r in asset_val}
            account["total_value_usd"] = 0
            for cur, val in account["balances"].items():
                if cur == "USD":
                    account["total_value_usd"] += val
                elif cur == "ZNT":
                    account["total_value_usd"] += val * 2.47
                elif cur == "BTC":
                    account["total_value_usd"] += val * 67500
                elif cur == "ETH":
                    account["total_value_usd"] += val * 3450
            account["total_value_usd"] = round(account["total_value_usd"], 2)

            conn.close()
            return account
        except Exception as e:
            logger.error(f"get_account failed: {e}")
            return None

    def create_account(self, user_id, znt_balance=0):
        try:
            conn = _db()
            existing = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if existing:
                conn.close()
                return dict(existing)
            conn.execute("INSERT INTO users (id, email) VALUES (?, ?)", (user_id, f"{user_id}@zivault.local"))
            conn.commit()
            user = dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
            conn.close()
            self._log(user_id, "account_created", "user", user_id)
            return user
        except Exception as e:
            logger.error(f"create_account failed: {e}")
            return {"error": str(e)}

    def update_account(self, user_id, **kwargs):
        try:
            conn = _db()
            updates = []
            params = []
            for k in ("name", "email"):
                if k in kwargs:
                    updates.append(f"{k}=?")
                    params.append(kwargs[k])
            if updates:
                params.append(user_id)
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
                conn.commit()
            user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            conn.close()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"update_account failed: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    #  USERS (legacy)
    # ═══════════════════════════════════════════════════════════════════════

    def get_or_create_user(self, email, name=""):
        try:
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
        except Exception as e:
            logger.error(f"get_or_create_user failed: {e}")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    #  CURRENCIES
    # ═══════════════════════════════════════════════════════════════════════

    def list_currencies(self):
        try:
            conn = _db()
            rows = conn.execute("SELECT * FROM currencies ORDER BY code").fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"list_currencies failed: {e}")
            return []

    def get_exchange_rate(self, from_cur, to_cur):
        try:
            conn = _db()
            row = conn.execute(
                "SELECT rate FROM exchange_rates WHERE from_currency=? AND to_currency=?",
                (from_cur, to_cur)
            ).fetchone()
            conn.close()
            return row["rate"] if row else 0
        except Exception as e:
            logger.error(f"get_exchange_rate failed: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════════════
    #  STAKING (backwards compat)
    # ═══════════════════════════════════════════════════════════════════════

    def get_staking(self, owner_id):
        try:
            conn = _db()
            rows = conn.execute("SELECT * FROM staking WHERE user_id=?", (owner_id,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []
