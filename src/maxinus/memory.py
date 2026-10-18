from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class Memory:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content, content='memories', content_rowid='id'
            );
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
              INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
            END;
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    def remember(self, content: str) -> str:
        content = content.strip()[:4000]
        self.db.execute(
            "INSERT INTO memories(created_at, content) VALUES (?, ?)",
            (datetime.now().isoformat(timespec="seconds"), content),
        )
        self.db.commit()
        return "Souvenir enregistré dans la mémoire locale."

    def search(self, query: str, limit: int = 5) -> list[str]:
        tokens = [t.replace('"', "") for t in query.split() if len(t) > 1]
        if not tokens:
            return []
        expression = " OR ".join(f'"{t}"' for t in tokens[:8])
        rows = self.db.execute(
            "SELECT m.content FROM memories_fts f JOIN memories m ON m.id=f.rowid "
            "WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
            (expression, max(1, min(limit, 10))),
        ).fetchall()
        return [row[0] for row in rows]

    def add_message(self, role: str, content: str) -> None:
        self.db.execute(
            "INSERT INTO messages(created_at, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), role, content[:16000]),
        )
        self.db.commit()

    def recent_messages(self, limit: int) -> list[dict[str, str]]:
        rows = self.db.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    def clear_conversation(self) -> None:
        self.db.execute("DELETE FROM messages")
        self.db.commit()
