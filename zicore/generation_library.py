"""
ZICORE Generation Library — Metadata, thumbnails, and search for all generated content.

Manages a SQLite database of generations with full-text search,
auto-thumbnail generation, folder organization, and tagging.

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import os
import json
import sqlite3
import shutil
import struct
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Union
from enum import Enum

logger = logging.getLogger("zicore.generation_library")

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "generation_library.db"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# MEDIA TYPE HELPERS
# =============================================================================

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp"}
MESH_EXTS = {".stl", ".obj", ".glb", ".gltf", ".ply", ".3ds"}
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".webm", ".mkv"}
DOC_EXTS = {".txt", ".json", ".csv", ".xml", ".md", ".pdf"}


def get_media_type(file_path: str) -> str:
    """Return the media category for a file based on extension.

    Returns one of: 'image', '3d', 'audio', 'video', 'document', 'unknown'.
    """
    ext = Path(file_path).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in MESH_EXTS:
        return "3d"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in DOC_EXTS:
        return "document"
    return "unknown"


def get_file_size(file_path: Union[str, Path]) -> str:
    """Return a human-readable file size string."""
    path = Path(file_path)
    if not path.exists():
        return "0 B"
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return f"{size:.1f} PB"


def validate_file(file_path: Union[str, Path]) -> bool:
    """Check if a file exists and is a regular file with non-zero size."""
    path = Path(file_path)
    return path.is_file() and path.stat().st_size > 0


# =============================================================================
# THUMBNAIL GENERATION
# =============================================================================

def _make_thumbnail_name(file_path: str) -> str:
    """Generate a deterministic thumbnail filename from the source file path."""
    h = hashlib.md5(file_path.encode()).hexdigest()[:12]
    return f"{h}.png"


def _generate_image_thumbnail(src: Path, dst: Path) -> bool:
    """Resize an image to 200x200 for thumbnail use."""
    try:
        from PIL import Image
        img = Image.open(src)
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(dst, "PNG")
        return True
    except Exception as e:
        logger.warning(f"Image thumbnail failed for {src}: {e}")
        return False


def _generate_mesh_thumbnail(src: Path, dst: Path) -> bool:
    """Generate a wireframe preview PNG from a 3D mesh using trimesh."""
    try:
        import trimesh
        import numpy as np
        mesh = trimesh.load(str(src), force="mesh", process=False)
        scene_or_mesh = mesh

        try:
            if hasattr(scene_or_mesh, "geometry"):
                geoms = list(scene_or_mesh.geometry.values())
                if geoms:
                    mesh = geoms[0]
        except Exception:
            pass

        vertices = np.array(mesh.vertices)
        faces = np.array(mesh.faces)

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection

            fig = plt.figure(figsize=(2, 2), dpi=100)
            ax = fig.add_subplot(111, projection="3d")

            mean = vertices.mean(axis=0)
            vertices = vertices - mean
            scale = max(np.ptp(vertices, axis=0)) or 1.0
            vertices = vertices / scale * 1.6

            polys = vertices[faces]
            collection = Poly3DCollection(polys, alpha=0.15, linewidths=0.3,
                                          edgecolors="#00e5ff", facecolors="none")
            ax.add_collection3d(collection)

            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            ax.set_zlim(-1, 1)
            ax.set_axis_off()
            ax.set_facecolor("#0a0e1a")
            fig.patch.set_facecolor("#0a0e1a")

            plt.savefig(dst, dpi=100, bbox_inches="tight",
                        pad_inches=0.05, facecolor="#0a0e1a")
            plt.close(fig)
            return True
        except ImportError:
            logger.warning("matplotlib not available for mesh thumbnail")
            return False
    except Exception as e:
        logger.warning(f"Mesh thumbnail failed for {src}: {e}")
        return False


def _generate_audio_thumbnail(src: Path, dst: Path) -> bool:
    """Generate a waveform PNG from an audio file."""
    try:
        import wave
        import numpy as np

        with wave.open(str(src), "rb") as wf:
            n_frames = wf.getnframes()
            sample_width = wf.getsampwidth()
            channels = wf.getnchannels()
            raw = wf.readframes(min(n_frames, 44100 * 10))

        if sample_width == 2:
            samples = np.frombuffer(raw, dtype=np.int16)
        elif sample_width == 4:
            samples = np.frombuffer(raw, dtype=np.int32)
        else:
            samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128

        if channels > 1:
            samples = samples[::channels]

        samples = samples.astype(np.float32)
        peak = np.max(np.abs(samples)) or 1.0
        samples = samples / peak

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(3, 1.2), dpi=100)
        ax.fill_between(range(len(samples)), samples, alpha=0.7, color="#00e5ff")
        ax.set_xlim(0, len(samples))
        ax.set_ylim(-1, 1)
        ax.axis("off")
        ax.set_facecolor("#0a0e1a")
        fig.patch.set_facecolor("#0a0e1a")
        plt.savefig(dst, dpi=100, bbox_inches="tight",
                    pad_inches=0.02, facecolor="#0a0e1a")
        plt.close(fig)
        return True
    except Exception as e:
        logger.warning(f"Audio thumbnail failed for {src}: {e}")
        return False


_PLACEHOLDER_PNG = None


def _placeholder_thumbnail(dst: Path) -> bool:
    """Create a minimal placeholder thumbnail."""
    global _PLACEHOLDER_PNG
    if _PLACEHOLDER_PNG is not None:
        shutil.copy(_PLACEHOLDER_PNG, dst)
        return True
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(2, 2), dpi=100)
        ax.text(0.5, 0.5, "?", fontsize=48, ha="center", va="center",
                color="#00e5ff", fontweight="bold")
        ax.set_facecolor("#0a0e1a")
        fig.patch.set_facecolor("#0a0e1a")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        plt.savefig(dst, dpi=100, bbox_inches="tight",
                    pad_inches=0.02, facecolor="#0a0e1a")
        plt.close(fig)
        return True
    except Exception:
        return False


def generate_thumbnail(file_path: Union[str, Path]) -> Optional[str]:
    """Generate a thumbnail for the given file and return its relative path.

    Returns the path relative to the project root, or None on failure.
    """
    src = Path(file_path)
    if not src.is_file():
        return None

    thumb_name = _make_thumbnail_name(str(src))
    thumb_path = THUMBNAILS_DIR / thumb_name
    media = get_media_type(str(src))

    generated = False
    if media == "image":
        generated = _generate_image_thumbnail(src, thumb_path)
    elif media == "3d":
        generated = _generate_mesh_thumbnail(src, thumb_path)
    elif media == "audio":
        generated = _generate_audio_thumbnail(src, thumb_path)

    if not generated:
        _placeholder_thumbnail(thumb_path)

    return f"data/thumbnails/{thumb_name}"


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL DEFAULT '',
    output_type TEXT NOT NULL,
    engine TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL,
    file_format TEXT NOT NULL DEFAULT '',
    thumbnail_path TEXT DEFAULT NULL,
    tags TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    is_favorite BOOLEAN DEFAULT 0,
    folder_id INTEGER DEFAULT NULL,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#00e5ff'
);

CREATE INDEX IF NOT EXISTS idx_gen_type ON generations(output_type);
CREATE INDEX IF NOT EXISTS idx_gen_engine ON generations(engine);
CREATE INDEX IF NOT EXISTS idx_gen_folder ON generations(folder_id);
CREATE INDEX IF NOT EXISTS idx_gen_created ON generations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gen_favorite ON generations(is_favorite);
"""


# =============================================================================
# GenerationDB — low-level SQLite wrapper
# =============================================================================

class GenerationDB:
    """Low-level SQLite database for generation records."""

    def __init__(self, db_path: Union[str, Path] = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self):
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        return self._conn.executemany(sql, params_list)

    def commit(self):
        self._conn.commit()

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        return self.execute(sql, params).fetchall()


# =============================================================================
# GenerationLibrary — high-level API
# =============================================================================

class GenerationLibrary:
    """High-level API for managing all generated content.

    Usage:
        lib = GenerationLibrary()
        gen_id = lib.add("Moon base concept", "image", "sd", "output/moon.png", "png")
        lib.add_tag(gen_id, "lunar")
        lib.update(gen_id, is_favorite=True)
        results = lib.search("moon")
    """

    def __init__(self, db_path: Union[str, Path] = DB_PATH):
        self.db = GenerationDB(db_path)

    def close(self):
        self.db.close()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        prompt: str,
        output_type: str,
        engine: str,
        file_path: str,
        file_format: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        folder_id: Optional[int] = None,
        is_favorite: bool = False,
    ) -> int:
        """Add a new generation record. Returns the new record ID."""
        thumb = generate_thumbnail(file_path)
        now = datetime.utcnow().isoformat()

        cur = self.db.execute(
            """INSERT INTO generations
               (prompt, output_type, engine, file_path, file_format,
                thumbnail_path, tags, metadata, created_at, updated_at,
                is_favorite, folder_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prompt,
                output_type,
                engine,
                file_path,
                file_format,
                thumb,
                json.dumps(tags or []),
                json.dumps(metadata or {}),
                now,
                now,
                int(is_favorite),
                folder_id,
            ),
        )
        self.db.commit()
        gen_id = cur.lastrowid

        for tag in (tags or []):
            self._ensure_tag(tag)
            self._link_tag(gen_id, tag)

        logger.info(f"Generation added: id={gen_id} type={output_type} engine={engine}")
        return gen_id

    def get(self, gen_id: int) -> Optional[Dict]:
        """Get a single generation by ID."""
        row = self.db.fetchone(
            "SELECT * FROM generations WHERE id = ?", (gen_id,)
        )
        return self._row_to_dict(row) if row else None

    def list(
        self,
        output_type: Optional[str] = None,
        folder_id: Optional[int] = None,
        favorite: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """List generations with optional filters."""
        clauses = []
        params: list = []

        if output_type:
            clauses.append("output_type = ?")
            params.append(output_type)
        if folder_id is not None:
            clauses.append("folder_id = ?")
            params.append(folder_id)
        if favorite:
            clauses.append("is_favorite = 1")
        if search:
            like = f"%{search}%"
            clauses.append(
                "(prompt LIKE ? OR tags LIKE ? OR metadata LIKE ?)"
            )
            params.extend([like, like, like])

        where = " AND ".join(clauses) if clauses else "1=1"
        params.extend([limit, offset])

        rows = self.db.fetchall(
            f"SELECT * FROM generations WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params),
        )
        return [self._row_to_dict(r) for r in rows]

    def update(self, gen_id: int, **kwargs) -> bool:
        """Update fields on an existing generation.

        Supported kwargs: prompt, output_type, engine, file_path, file_format,
        tags, metadata, is_favorite, folder_id, thumbnail_path.
        Returns True if a row was updated.
        """
        allowed = {
            "prompt", "output_type", "engine", "file_path", "file_format",
            "tags", "metadata", "is_favorite", "folder_id", "thumbnail_path",
        }
        updates = []
        params: list = []
        for key, val in kwargs.items():
            if key not in allowed:
                continue
            if key in ("tags", "metadata"):
                val = json.dumps(val) if isinstance(val, (list, dict)) else val
            if key == "is_favorite":
                val = int(val)
            updates.append(f"{key} = ?")
            params.append(val)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(gen_id)

        cur = self.db.execute(
            f"UPDATE generations SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self.db.commit()

        if "tags" in kwargs:
            self.db.execute(
                "DELETE FROM generation_tags WHERE generation_id = ?", (gen_id,)
            )
            for tag in (kwargs["tags"] if isinstance(kwargs["tags"], list) else []):
                self._ensure_tag(tag)
                self._link_tag(gen_id, tag)
            self.db.commit()

        return cur.rowcount > 0

    def delete(self, gen_id: int) -> bool:
        """Delete a generation record and its file/thumbnail.

        Returns True if the record was deleted.
        """
        row = self.db.fetchone(
            "SELECT file_path, thumbnail_path FROM generations WHERE id = ?",
            (gen_id,),
        )
        if not row:
            return False

        self.db.execute(
            "DELETE FROM generation_tags WHERE generation_id = ?", (gen_id,)
        )
        self.db.execute("DELETE FROM generations WHERE id = ?", (gen_id,))
        self.db.commit()

        self._safe_delete(row["file_path"])
        self._safe_delete(row["thumbnail_path"])

        logger.info(f"Generation deleted: id={gen_id}")
        return True

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Full-text search across prompt, tags, and metadata."""
        like = f"%{query}%"
        rows = self.db.fetchall(
            """SELECT * FROM generations
               WHERE prompt LIKE ? OR tags LIKE ? OR metadata LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (like, like, like, limit),
        )
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # STATS
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return library statistics: counts by type, total size, recent activity."""
        total = self.db.fetchone("SELECT COUNT(*) as c FROM generations")
        by_type = self.db.fetchall(
            "SELECT output_type, COUNT(*) as c FROM generations GROUP BY output_type"
        )
        by_engine = self.db.fetchall(
            "SELECT engine, COUNT(*) as c FROM generations GROUP BY engine"
        )
        favorites = self.db.fetchone(
            "SELECT COUNT(*) as c FROM generations WHERE is_favorite = 1"
        )
        recent = self.db.fetchall(
            "SELECT * FROM generations ORDER BY created_at DESC LIMIT 5"
        )

        total_size = 0
        for row in recent:
            p = PROJECT_ROOT / row["file_path"]
            if p.is_file():
                total_size += p.stat().st_size

        return {
            "total": total["c"] if total else 0,
            "by_type": {r["output_type"]: r["c"] for r in by_type},
            "by_engine": {r["engine"]: r["c"] for r in by_engine},
            "favorites": favorites["c"] if favorites else 0,
            "recent_activity": [self._row_to_dict(r) for r in recent],
            "sample_size": get_file_size(total_size) if total_size else "0 B",
        }

    # ------------------------------------------------------------------
    # FOLDERS
    # ------------------------------------------------------------------

    def create_folder(self, name: str, parent_id: Optional[int] = None) -> int:
        """Create a folder. Returns the new folder ID."""
        cur = self.db.execute(
            "INSERT INTO folders (name, parent_id) VALUES (?, ?)",
            (name, parent_id),
        )
        self.db.commit()
        return cur.lastrowid

    def move_to_folder(self, gen_id: int, folder_id: Optional[int]) -> bool:
        """Move a generation to a folder (or None to unfile)."""
        cur = self.db.execute(
            "UPDATE generations SET folder_id = ?, updated_at = ? WHERE id = ?",
            (folder_id, datetime.utcnow().isoformat(), gen_id),
        )
        self.db.commit()
        return cur.rowcount > 0

    def list_folders(self) -> List[Dict]:
        """List all folders."""
        rows = self.db.fetchall("SELECT * FROM folders ORDER BY name")
        return [dict(r) for r in rows]

    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder. Contents move to unfiled (folder_id=NULL)."""
        self.db.execute(
            "UPDATE generations SET folder_id = NULL WHERE folder_id = ?",
            (folder_id,),
        )
        cur = self.db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # QUICK QUERIES
    # ------------------------------------------------------------------

    def get_latest(self, output_type: Optional[str] = None) -> Optional[Dict]:
        """Get the most recently added generation."""
        if output_type:
            row = self.db.fetchone(
                "SELECT * FROM generations WHERE output_type = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (output_type,),
            )
        else:
            row = self.db.fetchone(
                "SELECT * FROM generations ORDER BY created_at DESC LIMIT 1"
            )
        return self._row_to_dict(row) if row else None

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent generations."""
        rows = self.db.fetchall(
            "SELECT * FROM generations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_dict(r) for r in rows]

    def get_by_engine(self, engine: str, limit: int = 100) -> List[Dict]:
        """Get all generations from a specific engine."""
        rows = self.db.fetchall(
            "SELECT * FROM generations WHERE engine = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (engine, limit),
        )
        return [self._row_to_dict(r) for r in rows]

    def get_favorites(self, limit: int = 50) -> List[Dict]:
        """Get all favorite generations."""
        rows = self.db.fetchall(
            "SELECT * FROM generations WHERE is_favorite = 1 "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_dict(r) for r in rows]

    def get_by_type(self, output_type: str, limit: int = 50) -> List[Dict]:
        """Get generations filtered by output type."""
        rows = self.db.fetchall(
            "SELECT * FROM generations WHERE output_type = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (output_type, limit),
        )
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # TAGS
    # ------------------------------------------------------------------

    def add_tag(self, gen_id: int, tag: str) -> bool:
        """Add a tag to a generation."""
        gen = self.get(gen_id)
        if not gen:
            return False
        current = json.loads(gen["tags"]) if isinstance(gen["tags"], str) else gen["tags"]
        if tag not in current:
            current.append(tag)
            self.update(gen_id, tags=current)
            self._ensure_tag(tag)
            self._link_tag(gen_id, tag)
        return True

    def remove_tag(self, gen_id: int, tag: str) -> bool:
        """Remove a tag from a generation."""
        gen = self.get(gen_id)
        if not gen:
            return False
        current = json.loads(gen["tags"]) if isinstance(gen["tags"], str) else gen["tags"]
        if tag in current:
            current.remove(tag)
            self.update(gen_id, tags=current)
            self.db.execute(
                """DELETE FROM generation_tags
                   WHERE generation_id = ? AND tag_id = (
                       SELECT id FROM tags WHERE name = ?
                   )""",
                (gen_id, tag),
            )
            self.db.commit()
        return True

    def get_tags(self) -> List[Dict]:
        """List all tags with generation counts."""
        rows = self.db.fetchall(
            """SELECT t.*, COUNT(gt.generation_id) as usage_count
               FROM tags t
               LEFT JOIN generation_tags gt ON t.id = gt.tag_id
               GROUP BY t.id ORDER BY usage_count DESC"""
        )
        return [dict(r) for r in rows]

    def search_by_tag(self, tag: str, limit: int = 50) -> List[Dict]:
        """Find all generations with a specific tag."""
        like = f"%{tag}%"
        rows = self.db.fetchall(
            "SELECT * FROM generations WHERE tags LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (like, limit),
        )
        return [self._row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------------

    def export_library(self, format: str = "json") -> str:
        """Export all generation metadata.

        Returns a JSON string. Future formats can be added.
        """
        rows = self.db.fetchall(
            "SELECT * FROM generations ORDER BY created_at DESC"
        )
        data = [self._row_to_dict(r) for r in rows]

        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        return json.dumps(data, indent=2, ensure_ascii=False)

    def import_library(self, json_str: str) -> int:
        """Import generations from a JSON export string.

        Returns the number of imported records. Skips duplicates by file_path.
        """
        data = json.loads(json_str)
        imported = 0
        for item in data:
            existing = self.db.fetchone(
                "SELECT id FROM generations WHERE file_path = ?",
                (item["file_path"],),
            )
            if existing:
                continue
            self.add(
                prompt=item.get("prompt", ""),
                output_type=item.get("output_type", "unknown"),
                engine=item.get("engine", ""),
                file_path=item["file_path"],
                file_format=item.get("file_format", ""),
                metadata=json.loads(item["metadata"]) if isinstance(item.get("metadata"), str) else item.get("metadata", {}),
                tags=json.loads(item["tags"]) if isinstance(item.get("tags"), str) else item.get("tags", []),
                folder_id=item.get("folder_id"),
                is_favorite=bool(item.get("is_favorite")),
            )
            imported += 1
        return imported

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a plain dictionary with parsed JSON fields."""
        d = dict(row)
        for field in ("tags", "metadata"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except json.JSONDecodeError:
                    pass
        if "is_favorite" in d:
            d["is_favorite"] = bool(d["is_favorite"])
        return d

    def _ensure_tag(self, tag_name: str, color: str = "#00e5ff"):
        """Create a tag record if it doesn't exist."""
        existing = self.db.fetchone(
            "SELECT id FROM tags WHERE name = ?", (tag_name,)
        )
        if not existing:
            self.db.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)",
                (tag_name, color),
            )
            self.db.commit()

    def _link_tag(self, gen_id: int, tag_name: str):
        """Link a generation to a tag."""
        row = self.db.fetchone(
            "SELECT id FROM tags WHERE name = ?", (tag_name,)
        )
        if row:
            self.db.execute(
                "INSERT OR IGNORE INTO generation_tags (generation_id, tag_id) VALUES (?, ?)",
                (gen_id, row["id"]),
            )

    @staticmethod
    def _safe_delete(path_str: Optional[str]):
        """Delete a file if it exists, without raising."""
        if not path_str:
            return
        full = PROJECT_ROOT / path_str
        if full.is_file():
            try:
                full.unlink()
            except OSError as e:
                logger.warning(f"Failed to delete {full}: {e}")


# Ensure the generation_tags junction table exists (created lazily)
def _init_junction_table():
    db = GenerationDB()
    db.execute(
        """CREATE TABLE IF NOT EXISTS generation_tags (
            generation_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (generation_id, tag_id),
            FOREIGN KEY (generation_id) REFERENCES generations(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )"""
    )
    db.commit()
    db.close()

_init_junction_table()


# =============================================================================
# MODULE-LEVEL CONVENIENCE INSTANCE
# =============================================================================

generation_library = GenerationLibrary()


if __name__ == "__main__":
    lib = GenerationLibrary()

    sample_id = lib.add(
        prompt="Lunar crater habitat concept",
        output_type="image",
        engine="sd",
        file_path="output/lunar_habitat.png",
        file_format="png",
        metadata={"width": 1024, "height": 1024, "steps": 30},
        tags=["lunar", "habitat", "concept"],
    )
    print(f"Added generation: {sample_id}")

    lib.add_tag(sample_id, "aerospace")
    lib.update(sample_id, is_favorite=True)

    stats = lib.get_stats()
    print(f"Library stats: {json.dumps(stats, indent=2)}")

    results = lib.search("lunar")
    print(f"Search results: {len(results)}")

    lib.close()
    print("Generation Library ready.")
