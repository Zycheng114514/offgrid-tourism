"""SQLite storage: hosts, listings, every SMS in and out, and open conversations.

A listing is stored as one JSON document that follows schemas/listing.schema.json.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS hosts (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    publish_phone INTEGER,            -- NULL = not asked yet
    consent_at TEXT,
    created_at TEXT NOT NULL,
    lang TEXT                         -- language the host writes in; replies use it
);
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    region_id TEXT NOT NULL,
    host_id TEXT NOT NULL REFERENCES hosts(id),
    state TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,          -- 'in' or 'out'
    phone TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    gateway_id TEXT UNIQUE,           -- for de-duplicating webhook retries
    meta TEXT
);
CREATE TABLE IF NOT EXISTS conversations (
    phone TEXT PRIMARY KEY,
    listing_id TEXT,
    awaiting TEXT NOT NULL,           -- a field name, 'confirm' or 'consent'
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | pathlib.Path):
        self.path = str(path)
        if self.path != ":memory:":
            pathlib.Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(SCHEMA)
            columns = {row[1] for row in self._db.execute("PRAGMA table_info(hosts)")}
            if "lang" not in columns:  # databases created before languages were added
                self._db.execute("ALTER TABLE hosts ADD COLUMN lang TEXT")
            self._db.commit()

    def _q(self, sql: str, args=()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._db.execute(sql, args)
            rows = cur.fetchall()
            self._db.commit()
            return rows

    # ---- messages ------------------------------------------------------------

    def log_message(self, direction: str, phone: str, text: str, gateway_id: str | None = None,
                    meta: dict | None = None) -> bool:
        """Store one SMS. Returns False if this gateway_id was already stored (a retry)."""
        try:
            self._q("INSERT INTO messages (direction, phone, text, created_at, gateway_id, meta) VALUES (?,?,?,?,?,?)",
                    (direction, phone, text, now(), gateway_id, json.dumps(meta) if meta else None))
            return True
        except sqlite3.IntegrityError:
            return False

    def messages(self, phone: str | None = None, after_id: int = 0, limit: int = 200) -> list[dict]:
        if phone:
            rows = self._q("SELECT * FROM messages WHERE phone=? AND id>? ORDER BY id LIMIT ?", (phone, after_id, limit))
        else:
            rows = self._q("SELECT * FROM messages WHERE id>? ORDER BY id LIMIT ?", (after_id, limit))
        return [{"id": r["id"], "direction": r["direction"], "phone": r["phone"], "text": r["text"],
                 "created_at": r["created_at"]} for r in rows]

    # ---- hosts ---------------------------------------------------------------

    def host_for(self, phone: str) -> dict:
        rows = self._q("SELECT * FROM hosts WHERE phone=?", (phone,))
        if not rows:
            self._q("INSERT INTO hosts (id, phone, created_at) VALUES (?,?,?)", ("h-" + uuid.uuid4().hex[:10], phone, now()))
            rows = self._q("SELECT * FROM hosts WHERE phone=?", (phone,))
        return dict(rows[0])

    def set_host_lang(self, host_id: str, lang: str) -> None:
        self._q("UPDATE hosts SET lang=? WHERE id=?", (lang, host_id))

    def set_consent(self, host_id: str, publish: bool) -> None:
        self._q("UPDATE hosts SET publish_phone=?, consent_at=? WHERE id=?", (int(publish), now(), host_id))

    def host(self, host_id: str) -> dict | None:
        rows = self._q("SELECT * FROM hosts WHERE id=?", (host_id,))
        return dict(rows[0]) if rows else None

    # ---- listings ------------------------------------------------------------

    def next_listing_id(self, region_id: str) -> str:
        n = self._q("SELECT COUNT(*) AS n FROM listings WHERE region_id=?", (region_id,))[0]["n"]
        return f"{region_id}-{n + 1:04d}"

    def save_listing(self, listing: dict) -> None:
        listing["status"]["updated_at"] = now()
        with self._lock:
            self._q("""INSERT INTO listings (id, region_id, host_id, state, data, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET state=excluded.state, data=excluded.data,
                       updated_at=excluded.updated_at""",
                    (listing["id"], listing["region_id"], listing["source"]["host_id"], listing["status"]["state"],
                     json.dumps(listing, ensure_ascii=False), now(), now()))

    def listing(self, listing_id: str) -> dict | None:
        rows = self._q("SELECT data FROM listings WHERE id=?", (listing_id,))
        return json.loads(rows[0]["data"]) if rows else None

    def listings(self, region_id: str | None = None, state: str | None = None, host_id: str | None = None) -> list[dict]:
        sql, args = "SELECT data FROM listings WHERE 1=1", []
        for col, val in (("region_id", region_id), ("state", state), ("host_id", host_id)):
            if val is not None:
                sql += f" AND {col}=?"
                args.append(val)
        return [json.loads(r["data"]) for r in self._q(sql + " ORDER BY id", args)]

    # ---- conversations -------------------------------------------------------

    def conversation(self, phone: str) -> dict | None:
        rows = self._q("SELECT * FROM conversations WHERE phone=?", (phone,))
        return dict(rows[0]) if rows else None

    def set_conversation(self, phone: str, listing_id: str | None, awaiting: str, attempts: int = 0) -> None:
        self._q("""INSERT INTO conversations (phone, listing_id, awaiting, attempts, updated_at) VALUES (?,?,?,?,?)
                   ON CONFLICT(phone) DO UPDATE SET listing_id=excluded.listing_id, awaiting=excluded.awaiting,
                   attempts=excluded.attempts, updated_at=excluded.updated_at""",
                (phone, listing_id, awaiting, attempts, now()))

    def clear_conversation(self, phone: str) -> None:
        self._q("DELETE FROM conversations WHERE phone=?", (phone,))
