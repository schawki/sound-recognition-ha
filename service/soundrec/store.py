"""Detection history (SQLite)."""
import datetime as dt
import sqlite3
import threading

COLS = ("id", "ts", "source", "mid", "class", "score", "threshold", "duration_s", "level_dbfs", "started_at", "detected_at",
        "clip", "clip_expires", "feedback", "clip_reason")
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
        if "clip_reason" not in {r[1] for r in self.db.execute("PRAGMA table_info(events)")}:
            self.db.execute("ALTER TABLE events ADD COLUMN clip_reason TEXT")           # why there is no clip (resolution provenance, 'expired', 'deleted')
        self.db.execute("""CREATE TABLE IF NOT EXISTS masked(
            id TEXT PRIMARY KEY, ts REAL, source TEXT, mid TEXT, class TEXT, score REAL, base_threshold REAL, threshold REAL,
            reasons TEXT)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_masked_ts ON masked(ts)")
        self.db.commit()

    def add(self, ev):
        ts = dt.datetime.fromisoformat(ev["detected_at"]).timestamp()
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO events(id, ts, source, mid, class, score, threshold, duration_s, level_dbfs, started_at, detected_at, clip_reason) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (ev["id"], ts, ev["source"], ev["mid"], ev["class"], ev["score"], ev["threshold"], ev["duration_s"],
                             ev["level_dbfs"], ev["started_at"], ev["detected_at"], ev.get("clip_reason")))
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
        """value: 'false' (wrong detection), 'good' (confirmed) or None. Returns False when the event does not exist."""
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
            for key, table, extra in (("detections", "events", ""), ("masked", "masked", ""), ("false", "events", " AND feedback='false'"), ("good", "events", " AND feedback='good'")):
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

    # ------------------------------------------------------------------ clip management
    @staticmethod
    def _clip_where(source=None, mids=None, since=None, until=None, feedback=None, with_clip=True):
        q, a = (" FROM events WHERE clip IS NOT NULL" if with_clip else " FROM events WHERE clip IS NULL"), []
        if feedback in ("false", "good"):
            q += " AND feedback = ?"; a.append(feedback)
        elif feedback == "unjudged":
            q += " AND feedback IS NULL"
        if source:
            q += " AND source = ?"; a.append(source)
        if mids is not None:
            q += f" AND mid IN ({','.join('?' * len(mids))})" if mids else " AND 0"; a += list(mids)
        if since is not None:
            q += " AND ts >= ?"; a.append(since)
        if until is not None:
            q += " AND ts <= ?"; a.append(until)
        return q, a

    def clips(self, limit=None, offset=0, **flt):
        """Events that still have a clip, newest first, matching the filters (source, mids, since, until). limit=None: all of them."""
        q, a = self._clip_where(**flt)
        q = "SELECT id, ts, source, mid, class, score, threshold, feedback, clip, clip_expires" + q + " ORDER BY ts DESC"
        if limit is not None:
            q += " LIMIT ? OFFSET ?"; a += [max(0, int(limit)), max(0, int(offset))]
        with self.lock:
            rows = self.db.execute(q, a).fetchall()
        return [dict(zip(("id", "ts", "source", "mid", "class", "score", "threshold", "feedback", "clip", "clip_expires"), r)) for r in rows]

    def delete_clipless(self, dry_run=False, **flt):
        """Deletes the detections that have no clip (they cannot be checked) and that nobody judged: the ones marked false or good stay.
        Same filters as clips (source, mids, since, until). Returns how many."""
        flt = {k: v for k, v in flt.items() if k in ("source", "mids", "since", "until")}
        q, a = self._clip_where(with_clip=False, feedback="unjudged", **flt)
        with self.lock:
            if dry_run:
                return self.db.execute("SELECT COUNT(*)" + q, a).fetchone()[0]
            n = self.db.execute("DELETE" + q, a).rowcount
            self.db.commit()
            return n

    def count_clipless(self, **flt):
        return self.delete_clipless(dry_run=True, **flt)

    def clips_by_ids(self, ids):
        out = []
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            with self.lock:
                rows = self.db.execute(f"SELECT id, clip FROM events WHERE clip IS NOT NULL AND id IN ({','.join('?' * len(chunk))})", chunk).fetchall()
            out += [{"id": r[0], "clip": r[1]} for r in rows]
        return out

    def forget_clips(self, ids=None):
        """Drops the clip reference of these events (all of them when ids is None); the detections themselves stay."""
        with self.lock:
            if ids is None:
                self.db.execute("UPDATE events SET clip=NULL, clip_expires=NULL, clip_reason='deleted' WHERE clip IS NOT NULL")
            for i in range(0, len(ids or []), 500):
                chunk = ids[i:i + 500]
                self.db.execute(f"UPDATE events SET clip=NULL, clip_expires=NULL, clip_reason='deleted' WHERE id IN ({','.join('?' * len(chunk))})", chunk)
            self.db.commit()

    def purge(self, before_ts, now_iso):
        """Deletes old events; drops clip references that have expired."""
        with self.lock:
            self.db.execute("DELETE FROM events WHERE ts < ?", (before_ts,))
            self.db.execute("DELETE FROM masked WHERE ts < ?", (before_ts,))
            self.db.execute("UPDATE events SET clip=NULL, clip_expires=NULL, clip_reason='expired' WHERE clip_expires IS NOT NULL AND clip_expires <= ?", (now_iso,))
            self.db.commit()
