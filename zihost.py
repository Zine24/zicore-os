"""
ZiHost - Infinite personal diary with multimedia file storage.
"""
import json, os, sqlite3, uuid, mimetypes
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/zihost", tags=["zihost"])

STORAGE_ROOT = Path("/opt/zihost")
DB_PATH = Path("/opt/zicore-system/data/sso.db")
MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_TYPES = {
    "image": {"image/jpeg","image/png","image/gif","image/webp","image/svg+xml","image/bmp","image/tiff"},
    "video": {"video/mp4","video/webm","video/ogg","video/quicktime","video/x-msvideo","video/x-matroska"},
    "audio": {"audio/mpeg","audio/wav","audio/ogg","audio/flac","audio/aac","audio/mp4","audio/webm"},
    "document": {"application/pdf","application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                 "text/plain","text/csv","text/html","text/css","text/javascript","application/json","application/xml"},
    "code": {"text/x-python","text/x-c","text/x-java","text/x-shellscript","application/x-yaml","text/markdown"},
    "archive": {"application/zip","application/x-tar","application/gzip","application/x-7z-compressed","application/x-rar-compressed"},
}
ALL_MIMES = set()
for mimes in ALLOWED_TYPES.values():
    ALL_MIMES.update(mimes)

def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _init_db():
    conn = _db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS zihost_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            pinned INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_zh_ent_user ON zihost_entries(user_id);
        CREATE INDEX IF NOT EXISTS idx_zh_ent_created ON zihost_entries(created_at DESC);

        CREATE TABLE IF NOT EXISTS zihost_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            mime_type TEXT DEFAULT '',
            category TEXT DEFAULT 'other',
            created_at TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES zihost_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_zh_fil_entry ON zihost_files(entry_id);
        CREATE INDEX IF NOT EXISTS idx_zh_fil_user ON zihost_files(user_id);
    """)
    conn.close()

_init_db()

def _get_user(request: Request):
    import sys
    sso = None
    for mod in sys.modules.values():
        obj = getattr(mod, "sso", None)
        if obj is not None and hasattr(obj, "verify_token") and callable(getattr(obj, "verify_token", None)):
            sso = obj
            break
    if sso is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="SSO not available")

    user = request.scope.get("state", {}).get("sso_user")
    if user:
        return user

    auth = request.headers.get("Authorization", "")
    api_key = request.headers.get("X-API-Key", "")
    token = auth[7:] if auth.startswith("Bearer ") else (api_key or "")

    if not token:
        cookies = request.headers.get("cookie", "")
        for part in cookies.split(";"):
            kv = part.strip().split("=", 1)
            if len(kv) == 2 and kv[0] == "zicore_sso_token":
                token = kv[1]
                break

    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authentication required")

    result = sso.verify_token(token)
    if not (result.get("success") and result.get("user")):
        result = sso.verify_api_token(token)
    if not result.get("success"):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")

    return result["user"]

def _user_dir(user_id):
    d = STORAGE_ROOT / str(user_id) / "entries"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _entry_dir(user_id, entry_id):
    d = _user_dir(user_id) / str(entry_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def _categorize(mime):
    for cat, mimes in ALLOWED_TYPES.items():
        if mime in mimes:
            return cat
    return "other"

def _now():
    return datetime.now(timezone.utc).isoformat()

def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except Exception:
            d["tags"] = []
    return d

def _entry_files(conn, entry_id):
    rows = conn.execute(
        "SELECT * FROM zihost_files WHERE entry_id=? ORDER BY created_at ASC", (entry_id,)
    ).fetchall()
    return [dict(r) for r in rows]

# ── Entries CRUD ─────────────────────────────────────────────────────────────

@router.get("/entries")
async def list_entries(request: Request, page: int = 1, per_page: int = 20, search: str = "", tag: str = "", sort: str = "newest"):
    user = _get_user(request)
    uid = user["id"]

    def _query():
        conn = _db()
        where = ["e.user_id = ?"]
        params = [uid]
        if search:
            where.append("(e.title LIKE ? OR e.description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if tag:
            where.append("e.tags LIKE ?")
            params.append(f"%{tag}%")
        w = " AND ".join(where)
        order = "e.created_at DESC" if sort == "newest" else "e.created_at ASC"
        if sort == "updated":
            order = "e.updated_at DESC"

        total = conn.execute(f"SELECT COUNT(*) FROM zihost_entries e WHERE {w}", params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT e.* FROM zihost_entries e WHERE {w} ORDER BY e.pinned DESC, {order} LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        entries = []
        for r in rows:
            ed = _row_to_dict(r)
            ed["files"] = _entry_files(conn, ed["id"])
            ed["file_count"] = len(ed["files"])
            ed["total_size"] = sum(f["file_size"] for f in ed["files"])
            entries.append(ed)
        conn.close()
        return {"entries": entries, "total": total, "page": page, "per_page": per_page, "pages": max(1, (total + per_page - 1) // per_page)}

    return await run_in_threadpool(_query)

@router.post("/entries")
async def create_entry(request: Request):
    user = _get_user(request)
    data = await request.json()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    tags = json.dumps(data.get("tags", []))
    now = _now()

    def _create():
        conn = _db()
        cur = conn.execute(
            "INSERT INTO zihost_entries (user_id, title, description, tags, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (user["id"], title, description, tags, now, now)
        )
        entry_id = cur.lastrowid
        conn.commit()
        entry = _row_to_dict(conn.execute("SELECT * FROM zihost_entries WHERE id=?", (entry_id,)).fetchone())
        entry["files"] = []
        entry["file_count"] = 0
        entry["total_size"] = 0
        conn.close()
        _entry_dir(user["id"], entry_id)
        return entry

    return await run_in_threadpool(_create)

@router.get("/entries/{entry_id}")
async def get_entry(request: Request, entry_id: int):
    user = _get_user(request)
    def _get():
        conn = _db()
        r = conn.execute("SELECT * FROM zihost_entries WHERE id=? AND user_id=?", (entry_id, user["id"])).fetchone()
        if not r:
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)
        ed = _row_to_dict(r)
        ed["files"] = _entry_files(conn, ed["id"])
        ed["file_count"] = len(ed["files"])
        ed["total_size"] = sum(f["file_size"] for f in ed["files"])
        conn.close()
        return ed
    return await run_in_threadpool(_get)

@router.put("/entries/{entry_id}")
async def update_entry(request: Request, entry_id: int):
    user = _get_user(request)
    data = await request.json()
    now = _now()
    def _update():
        conn = _db()
        r = conn.execute("SELECT * FROM zihost_entries WHERE id=? AND user_id=?", (entry_id, user["id"])).fetchone()
        if not r:
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)
        rd = dict(r)
        title = data.get("title", rd["title"])
        description = data.get("description", rd["description"])
        tags = json.dumps(data.get("tags", json.loads(rd["tags"])))
        pinned = data.get("pinned", rd["pinned"])
        conn.execute(
            "UPDATE zihost_entries SET title=?, description=?, tags=?, pinned=?, updated_at=? WHERE id=? AND user_id=?",
            (title, description, tags, pinned, now, entry_id, user["id"])
        )
        conn.commit()
        entry = _row_to_dict(conn.execute("SELECT * FROM zihost_entries WHERE id=?", (entry_id,)).fetchone())
        entry["files"] = _entry_files(conn, entry_id)
        entry["file_count"] = len(entry["files"])
        entry["total_size"] = sum(f["file_size"] for f in entry["files"])
        conn.close()
        return entry
    return await run_in_threadpool(_update)

@router.delete("/entries/{entry_id}")
async def delete_entry(request: Request, entry_id: int):
    user = _get_user(request)
    def _delete():
        conn = _db()
        r = conn.execute("SELECT * FROM zihost_entries WHERE id=? AND user_id=?", (entry_id, user["id"])).fetchone()
        if not r:
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)
        files = _entry_files(conn, entry_id)
        for f in files:
            fp = STORAGE_ROOT / f["file_path"]
            if fp.exists():
                fp.unlink()
        edir = STORAGE_ROOT / str(user["id"]) / "entries" / str(entry_id)
        if edir.exists():
            import shutil
            shutil.rmtree(edir, ignore_errors=True)
        conn.execute("DELETE FROM zihost_files WHERE entry_id=?", (entry_id,))
        conn.execute("DELETE FROM zihost_entries WHERE id=? AND user_id=?", (entry_id, user["id"]))
        conn.commit()
        conn.close()
        return {"status": "ok", "deleted": entry_id}
    return await run_in_threadpool(_delete)

# ── File Upload / Download / Delete ──────────────────────────────────────────

@router.post("/entries/{entry_id}/upload")
async def upload_files(request: Request, entry_id: int, files: list[UploadFile] = File(...)):
    user = _get_user(request)
    def _upload():
        conn = _db()
        r = conn.execute("SELECT * FROM zihost_entries WHERE id=? AND user_id=?", (entry_id, user["id"])).fetchone()
        if not r:
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)
        edir = _entry_dir(user["id"], entry_id)
        uploaded = []
        for uf in files:
            mime = uf.content_type or "application/octet-stream"
            cat = _categorize(mime)
            ext = Path(uf.filename).suffix if uf.filename else ""
            stored = f"{uuid.uuid4().hex}{ext}"
            rel_path = str(Path(str(user["id"])) / "entries" / str(entry_id) / stored)
            abs_path = STORAGE_ROOT / rel_path
            content = None
            try:
                content = uf.file.read()
            except Exception:
                conn.close()
                return JSONResponse({"error": f"Failed to read {uf.filename}"}, status_code=400)
            if len(content) > MAX_FILE_SIZE:
                conn.close()
                return JSONResponse({"error": f"File {uf.filename} exceeds 50MB limit"}, status_code=400)
            abs_path.write_bytes(content)
            now = _now()
            conn.execute(
                "INSERT INTO zihost_files (entry_id, user_id, original_name, stored_name, file_path, file_size, mime_type, category, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (entry_id, user["id"], uf.filename, stored, str(rel_path), len(content), mime, cat, now)
            )
            uploaded.append({"original_name": uf.filename, "stored_name": stored, "size": len(content), "mime": mime, "category": cat})
        conn.execute("UPDATE zihost_entries SET updated_at=? WHERE id=?", (_now(), entry_id))
        conn.commit()
        conn.close()
        return {"uploaded": uploaded, "count": len(uploaded)}
    return await run_in_threadpool(_upload)

@router.get("/files/{file_id}/download")
async def download_file(request: Request, file_id: int):
    user = _get_user(request)
    def _dl():
        conn = _db()
        r = conn.execute("SELECT * FROM zihost_files WHERE id=? AND user_id=?", (file_id, user["id"])).fetchone()
        conn.close()
        if not r:
            return JSONResponse({"error": "File not found"}, status_code=404)
        d = dict(r)
        fp = STORAGE_ROOT / d["file_path"]
        if not fp.exists():
            return JSONResponse({"error": "File missing from disk"}, status_code=404)
        return FileResponse(str(fp), filename=d["original_name"], media_type=d["mime_type"])
    return await run_in_threadpool(_dl)

@router.delete("/files/{file_id}")
async def delete_file(request: Request, file_id: int):
    user = _get_user(request)
    def _del():
        conn = _db()
        r = conn.execute("SELECT * FROM zihost_files WHERE id=? AND user_id=?", (file_id, user["id"])).fetchone()
        if not r:
            conn.close()
            return JSONResponse({"error": "File not found"}, status_code=404)
        d = dict(r)
        fp = STORAGE_ROOT / d["file_path"]
        if fp.exists():
            fp.unlink()
        conn.execute("DELETE FROM zihost_files WHERE id=?", (file_id,))
        conn.commit()
        conn.close()
        return {"status": "ok", "deleted": file_id}
    return await run_in_threadpool(_del)

# ── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(request: Request):
    user = _get_user(request)
    def _stats():
        conn = _db()
        entry_count = conn.execute("SELECT COUNT(*) FROM zihost_entries WHERE user_id=?", (user["id"],)).fetchone()[0]
        file_count = conn.execute("SELECT COUNT(*) FROM zihost_files WHERE user_id=?", (user["id"],)).fetchone()[0]
        total_size = conn.execute("SELECT COALESCE(SUM(file_size),0) FROM zihost_files WHERE user_id=?", (user["id"],)).fetchone()[0]
        by_cat = conn.execute(
            "SELECT category, COUNT(*) as count, COALESCE(SUM(file_size),0) as size FROM zihost_files WHERE user_id=? GROUP BY category",
            (user["id"],)
        ).fetchall()
        conn.close()
        return {
            "entry_count": entry_count,
            "file_count": file_count,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024*1024), 2),
            "storage_limit_mb": 2048,
            "by_category": [{"category": r["category"], "count": r["count"], "size": r["size"]} for r in by_cat]
        }
    return await run_in_threadpool(_stats)
