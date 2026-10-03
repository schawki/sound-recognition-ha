"""Detection history (SQLite)."""
import datetime as dt
import sqlite3
import threading

COLS = ("id", "ts", "source", "mid", "class", "score", "threshold", "duration_s", "level_dbfs", "started_at", "detected_at",
        "clip", "clip_expires")


class EventStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
            id TEXT PRIMARY KEY, ts REAL, source TEXT, mid TEXT, class TEXT, score REAL, threshold REAL, duration_s REAL,
            level_dbfs REAL, started_at TEXT, detected_at TEXT, clip TEXT, clip_expires TEXT)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_ts ON events(ts)")
        self.db.commit()

    def add(self, ev):
        ts = dt.datetime.fromisoformat(ev["detected_at"]).timestamp()
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
                            (ev["id"], ts, ev["source"], ev["mid"], ev["class"], ev["score"], ev["threshold"], ev["duration_s"],
                             ev["level_dbfs"], ev["started_at"], ev["detected_at"]))
            self.db.commit()

    def set_clip(self, event_id, rel, expires):
        with self.lock:
            self.db.execute("UPDATE events SET clip=?, clip_expires=? WHERE id=?", (rel, expires, event_id))
            self.db.commit()

    def query(self, since=None, source=None, mid=None, limit=100):
        q, a = "SELECT * FROM events WHERE 1=1", []
        if since is not None:
            q += " AND ts > ?"; a.append(since)
        if source:
            q += " AND source = ?"; a.append(source)
        if mid:
            q += " AND mid = ?"; a.append(mid)
        q += " ORDER BY ts DESC LIMIT ?"; a.append(max(1, min(int(limit), 1000)))
        with self.lock:
            rows = self.db.execute(q, a).fetchall()
        return [dict(zip(COLS, r)) for r in rows]

    def purge(self, before_ts, now_iso):
        """Deletes old events; drops clip references that have expired."""
        with self.lock:
            self.db.execute("DELETE FROM events WHERE ts < ?", (before_ts,))
            self.db.execute("UPDATE events SET clip=NULL, clip_expires=NULL WHERE clip_expires IS NOT NULL AND clip_expires <= ?", (now_iso,))
            self.db.commit()
