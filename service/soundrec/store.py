"""Detection history (SQLite)."""
import datetime as dt
import sqlite3
import threading

COLS = ("id", "ts", "source", "mid", "class", "score", "threshold", "duration_s", "level_dbfs", "started_at", "detected_at",
        "clip", "clip_expires", "feedback")
HOUR = 3600


class EventStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
            id TEXT PRIMARY KEY, ts REAL, source TEXT, mid TEXT, class TEXT, score REAL, threshold REAL, duration_s REAL,
            level_dbfs REAL, started_at TEXT, detected_at TEXT, clip TEXT, clip_expires TEXT)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_ts ON events(ts)")
        if "feedback" not in {r[1] for r in self.db.execute("PRAGMA table_info(events)")}:
            self.db.execute("ALTER TABLE events ADD COLUMN feedback TEXT")              # 'false' = marked as a false detection
        self.db.execute("""CREATE TABLE IF NOT EXISTS masked(
            id TEXT PRIMARY KEY, ts REAL, source TEXT, mid TEXT, class TEXT, score REAL, base_threshold REAL, threshold REAL,
            reasons TEXT)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_masked_ts ON masked(ts)")
        self.db.commit()

    def add(self, ev):
        ts = dt.datetime.fromisoformat(ev["detected_at"]).timestamp()
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL)",
                            (ev["id"], ts, ev["source"], ev["mid"], ev["class"], ev["score"], ev["threshold"], ev["duration_s"],
                             ev["level_dbfs"], ev["started_at"], ev["detected_at"]))
            self.db.commit()

    def set_clip(self, event_id, rel, expires):
        with self.lock:
            self.db.execute("UPDATE events SET clip=?, clip_expires=? WHERE id=?", (rel, expires, event_id))
            self.db.commit()

    def add_masked(self, ev):
        ts = dt.datetime.fromisoformat(ev["detected_at"]).timestamp()
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO masked VALUES(?,?,?,?,?,?,?,?,?)",
                            (ev["id"], ts, ev["source"], ev["mid"], ev["class"], ev["score"], ev["base_threshold"], ev["threshold"],
                             ",".join(ev["reasons"])))
            self.db.commit()

    def set_feedback(self, event_id, value):
        """value: 'false' or None. Returns False when the event does not exist."""
        with self.lock:
            cur = self.db.execute("UPDATE events SET feedback=? WHERE id=?", (value, event_id))
            self.db.commit()
            return cur.rowcount > 0

    def false_detections(self, since_ts):
        with self.lock:
            rows = self.db.execute("SELECT source, mid, class, score FROM events WHERE feedback='false' AND ts > ?", (since_ts,)).fetchall()
        return [dict(zip(("source", "mid", "class", "score"), r)) for r in rows]

    def stats(self, now_ts, hours=24):
        """Counts over the last `hours` hours: detections, masked detections, false ones, per source / class / hour."""
        since = now_ts - hours * HOUR
        out = {"hours": hours, "since": since}
        with self.lock:
            for key, table, extra in (("detections", "events", ""), ("masked", "masked", ""), ("false", "events", " AND feedback='false'")):
                where = f"ts > ?{extra}"
                total = self.db.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", (since,)).fetchone()[0]
                by_source = dict(self.db.execute(f"SELECT source, COUNT(*) FROM {table} WHERE {where} GROUP BY source", (since,)).fetchall())
                by_class = [{"source": r[0], "mid": r[1], "class": r[2], "count": r[3]} for r in self.db.execute(
                    f"SELECT source, mid, class, COUNT(*) c FROM {table} WHERE {where} GROUP BY source, mid ORDER BY c DESC LIMIT 12", (since,))]
                hourly = [0] * hours
                for (ts,) in self.db.execute(f"SELECT ts FROM {table} WHERE {where}", (since,)):
                    hourly[min(hours - 1, max(0, int((now_ts - ts) // HOUR)))] += 1
                out[key] = {"total": total, "by_source": by_source, "by_class": by_class, "hourly": hourly[::-1]}   # oldest first
        return out

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
            self.db.execute("DELETE FROM masked WHERE ts < ?", (before_ts,))
            self.db.execute("UPDATE events SET clip=NULL, clip_expires=NULL WHERE clip_expires IS NOT NULL AND clip_expires <= ?", (now_iso,))
            self.db.commit()
