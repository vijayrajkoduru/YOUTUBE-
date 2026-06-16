"""SQLite persistence layer (stdlib sqlite3, no ORM).

Single table `assets` holds both video and blog items as they move through
draft -> approved -> posted (or rejected / failed). All access goes through
the helper functions below so the schema stays in one place.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "engine.db")

VALID_KINDS = ("video", "blog")
VALID_STATUSES = ("draft", "approved", "rejected", "posted", "failed")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the data dir + assets table if they do not exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                kind        TEXT NOT NULL,
                topic       TEXT,
                title       TEXT,
                status      TEXT NOT NULL DEFAULT 'draft',
                detail      TEXT,
                video_path  TEXT,
                blog_html   TEXT,
                targets     TEXT,
                cost        REAL NOT NULL DEFAULT 0,
                error       TEXT,
                created_at  TEXT,
                updated_at  TEXT
            )
            """
        )
        conn.commit()


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    # Decode JSON columns into Python objects for convenience.
    for col in ("detail", "targets"):
        raw = d.get(col)
        if raw:
            try:
                d[col] = json.loads(raw)
            except (ValueError, TypeError):
                d[col] = raw
    return d


def create_asset(kind, topic, title, detail=None):
    """Insert a new asset in 'draft' status and return its id."""
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid kind: {kind}")
    now = _now()
    detail_json = json.dumps(detail) if detail is not None else None
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO assets (kind, topic, title, status, detail, cost, created_at, updated_at)
            VALUES (?, ?, ?, 'draft', ?, 0, ?, ?)
            """,
            (kind, topic, title, detail_json, now, now),
        )
        conn.commit()
        return cur.lastrowid


def get_asset(asset_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM assets WHERE id = ?", (asset_id,)
        ).fetchone()
    return _row_to_dict(row)


def list_assets(status=None, kind=None):
    query = "SELECT * FROM assets"
    clauses = []
    params = []
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if kind is not None:
        clauses.append("kind = ?")
        params.append(kind)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def set_status(asset_id, status, error=None):
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    with _connect() as conn:
        conn.execute(
            "UPDATE assets SET status = ?, error = ?, updated_at = ? WHERE id = ?",
            (status, error, _now(), asset_id),
        )
        conn.commit()


def set_video(asset_id, path, cost):
    with _connect() as conn:
        conn.execute(
            "UPDATE assets SET video_path = ?, cost = ?, updated_at = ? WHERE id = ?",
            (path, float(cost or 0), _now(), asset_id),
        )
        conn.commit()


def set_blog(asset_id, html, title):
    with _connect() as conn:
        conn.execute(
            "UPDATE assets SET blog_html = ?, title = ?, updated_at = ? WHERE id = ?",
            (html, title, _now(), asset_id),
        )
        conn.commit()


def update_detail(asset_id, detail):
    """Overwrite the detail JSON blob (used by the worker to store results)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE assets SET detail = ?, updated_at = ? WHERE id = ?",
            (json.dumps(detail), _now(), asset_id),
        )
        conn.commit()


def _month_prefix():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _day_prefix():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def month_cost_usd():
    """Total Veo cost recorded in the current UTC month."""
    prefix = _month_prefix() + "%"
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost), 0) AS total FROM assets "
            "WHERE kind = 'video' AND created_at LIKE ?",
            (prefix,),
        ).fetchone()
    return float(row["total"] or 0)


def day_clip_count():
    """Number of video clips created in the current UTC day."""
    prefix = _day_prefix() + "%"
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM assets "
            "WHERE kind = 'video' AND video_path IS NOT NULL AND created_at LIKE ?",
            (prefix,),
        ).fetchone()
    return int(row["cnt"] or 0)
