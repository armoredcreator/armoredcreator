from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import Candidate, ItemState, Verification


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """SQLite-backed source of truth; no external queue is used."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    def initialize(self) -> None:
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS items (
                    content_id TEXT PRIMARY KEY,
                    source_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    source_url TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    state TEXT NOT NULL,
                    affiliate_url TEXT,
                    original_path TEXT,
                    result_path TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, message_id)
                );
                CREATE INDEX IF NOT EXISTS idx_items_state_created
                    ON items(state, created_at);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_media_item
                    ON items((1))
                    WHERE state IN ('DOWNLOADING', 'PROCESSING', 'PUBLISHING');
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL REFERENCES items(content_id),
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    source_id INTEGER PRIMARY KEY,
                    last_message_id INTEGER NOT NULL DEFAULT 0,
                    mode TEXT NOT NULL DEFAULT 'CATCH_UP',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS publications (
                    content_id TEXT PRIMARY KEY REFERENCES items(content_id),
                    destination_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    message_id INTEGER,
                    attempt_started_at TEXT,
                    verified_at TEXT,
                    last_detail TEXT,
                    updated_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def record_candidate(self, candidate: Candidate) -> bool:
        now = utcnow()
        with self.transaction() as con:
            cur = con.execute("""
                INSERT OR IGNORE INTO items
                (content_id, source_id, message_id, source_url, received_at, metadata_json,
                 state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (candidate.content_id, candidate.source_id, candidate.message_id,
                  candidate.source_url, candidate.received_at, candidate.metadata_json,
                  ItemState.RECEIVED.value, now, now))
            if cur.rowcount:
                con.execute("INSERT INTO events(content_id,event_type,detail_json,created_at) VALUES(?,?,?,?)",
                            (candidate.content_id, "DISCOVERED", json.dumps({"source_id": candidate.source_id,
                             "message_id": candidate.message_id}), now))
            return cur.rowcount == 1

    def get_item(self, content_id: str) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM items WHERE content_id=?", (content_id,)).fetchone()
            return dict(row) if row else None

    def items_for_source(self, source_id: int, states: tuple[str, ...] | None = None) -> list[dict]:
        with self.connect() as con:
            if states:
                marks = ",".join("?" for _ in states)
                rows = con.execute(
                    f"SELECT * FROM items WHERE source_id=? AND state IN ({marks}) ORDER BY message_id",
                    (source_id, *states)).fetchall()
            else:
                rows = con.execute("SELECT * FROM items WHERE source_id=? ORDER BY message_id",
                                   (source_id,)).fetchall()
            return [dict(row) for row in rows]

    def next_eligible(self) -> dict | None:
        with self.connect() as con:
            row = con.execute("""
                SELECT * FROM items
                WHERE state IN ('READY','RECEIVED','RECOVERY')
                  AND NOT EXISTS (SELECT 1 FROM items WHERE state IN ('DOWNLOADING','PROCESSING','PUBLISHING'))
                ORDER BY received_at, source_id, message_id LIMIT 1
            """).fetchone()
            return dict(row) if row else None

    def transition(self, content_id: str, state: ItemState, *, detail: dict | None = None,
                   affiliate_url: str | None = None, original_path: str | None = None,
                   result_path: str | None = None, error: str | None = None) -> None:
        now = utcnow()
        with self.transaction() as con:
            row = con.execute("SELECT state FROM items WHERE content_id=?", (content_id,)).fetchone()
            if row is None:
                raise KeyError(f"Item inexistente: {content_id}")
            con.execute("""
                UPDATE items SET state=?, affiliate_url=COALESCE(?,affiliate_url),
                    original_path=COALESCE(?,original_path), result_path=COALESCE(?,result_path),
                    last_error=?, updated_at=? WHERE content_id=?
            """, (state.value, affiliate_url, original_path, result_path, error, now, content_id))
            con.execute("INSERT INTO events(content_id,event_type,detail_json,created_at) VALUES(?,?,?,?)",
                        (content_id, state.value, json.dumps(detail or {}, ensure_ascii=False), now))

    def set_checkpoint(self, source_id: int, message_id: int, mode: str = "CATCH_UP") -> None:
        now = utcnow()
        with self.transaction() as con:
            existing = con.execute("SELECT last_message_id FROM checkpoints WHERE source_id=?", (source_id,)).fetchone()
            if existing and message_id < existing["last_message_id"]:
                raise ValueError("Checkpoint não pode retroceder")
            con.execute("""
                INSERT INTO checkpoints(source_id,last_message_id,mode,updated_at) VALUES(?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET last_message_id=excluded.last_message_id,
                    mode=excluded.mode, updated_at=excluded.updated_at
            """, (source_id, message_id, mode, now))

    def get_checkpoint(self, source_id: int) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM checkpoints WHERE source_id=?", (source_id,)).fetchone()
            return dict(row) if row else None

    def begin_publication(self, content_id: str, destination_id: int, topic_id: int) -> bool:
        now = utcnow()
        with self.transaction() as con:
            cur = con.execute("""
                INSERT OR IGNORE INTO publications
                (content_id,destination_id,topic_id,status,attempt_started_at,updated_at)
                VALUES(?,?,?,'PENDING',?,?)
            """, (content_id, destination_id, topic_id, now, now))
            return cur.rowcount == 1

    def update_publication(self, content_id: str, status: Verification, *,
                           message_id: int | None = None, detail: str | None = None) -> None:
        now = utcnow()
        with self.transaction() as con:
            cur = con.execute("""
                UPDATE publications SET status=?, message_id=COALESCE(?,message_id),
                    verified_at=?, last_detail=?, updated_at=? WHERE content_id=?
            """, (status.value, message_id, now, detail, now, content_id))
            if cur.rowcount == 0:
                raise KeyError(f"Publicação inexistente: {content_id}")

    def get_publication(self, content_id: str) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM publications WHERE content_id=?", (content_id,)).fetchone()
            return dict(row) if row else None

    def events(self, content_id: str) -> list[dict]:
        with self.connect() as con:
            return [dict(row) for row in con.execute(
                "SELECT * FROM events WHERE content_id=? ORDER BY id", (content_id,)).fetchall()]
