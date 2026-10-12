"""Small per-user SQLite store for game events, metadata and narration history."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


class NiaStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=3)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, game_id TEXT NOT NULL, event_type TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS narrations (
                id INTEGER PRIMARY KEY, game_id TEXT NOT NULL, event_type TEXT NOT NULL,
                text TEXT NOT NULL, fingerprint TEXT NOT NULL, created_at REAL NOT NULL,
                UNIQUE(game_id, fingerprint)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS game_metadata (
                game_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at REAL NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS events_by_game ON events(game_id, created_at DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS narrations_by_game ON narrations(game_id, created_at DESC)")

    def record_event(self, game_id: str, event_type: str, detail: str = "", created_at: Optional[float] = None) -> int:
        import time
        with self._connection() as db:
            cursor = db.execute(
                "INSERT INTO events(game_id,event_type,detail,created_at) VALUES(?,?,?,?)",
                (game_id, event_type, detail[:500], created_at or time.time()),
            )
            return int(cursor.lastrowid)

    def add_narration(self, game_id: str, event_type: str, text: str, created_at: Optional[float] = None) -> bool:
        import time
        normalized = " ".join(text.casefold().split())
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        with self._connection() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO narrations(game_id,event_type,text,fingerprint,created_at) VALUES(?,?,?,?,?)",
                (game_id, event_type, text[:6000], fingerprint, created_at or time.time()),
            )
            return cursor.rowcount > 0

    def recent_narrations(self, game_id: str, limit: int = 8) -> List[str]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT text FROM narrations WHERE game_id=? ORDER BY created_at DESC LIMIT ?",
                (game_id, max(1, min(30, int(limit)))),
            ).fetchall()
            return [str(row["text"]) for row in rows]

    def latest_narration(self, game_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as db:
            row = db.execute(
                "SELECT event_type,text,created_at FROM narrations WHERE game_id=? ORDER BY created_at DESC LIMIT 1",
                (game_id,),
            ).fetchone()
            return dict(row) if row else None

    def game_stats(self, game_id: str) -> Dict[str, int]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT event_type, COUNT(*) AS total FROM events WHERE game_id=? GROUP BY event_type",
                (game_id,),
            ).fetchall()
        counts = {str(row["event_type"]): int(row["total"]) for row in rows}
        return {
            "deaths": counts.get("death", 0),
            "checkpoints": counts.get("checkpoint", 0),
            "objectives": counts.get("objective", 0),
            "victories": counts.get("victory", 0),
            "sessions": counts.get("session_start", 0),
        }

    def put_metadata(self, game_id: str, payload: Dict[str, Any]) -> None:
        import time
        encoded = json.dumps(payload, ensure_ascii=False)
        with self._connection() as db:
            db.execute(
                "INSERT INTO game_metadata(game_id,payload,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(game_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
                (game_id, encoded, time.time()),
            )

    def get_metadata(self, game_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as db:
            row = db.execute("SELECT payload FROM game_metadata WHERE game_id=?", (game_id,)).fetchone()
            if not row:
                return None
            try:
                value = json.loads(row["payload"])
                return value if isinstance(value, dict) else None
            except (TypeError, json.JSONDecodeError):
                return None
