"""Per-source pipeline: window loop, volume gate, schedule, thresholds, sustained detection, cooldown, clips.
Pure and synchronous (no I/O, no wall clock of its own) so it can be tested with synthetic audio."""
import datetime as dt
import math
import uuid
import zoneinfo
import numpy as np

from . import settings as st
from .audio import RingBuffer
from .classifier import SAMPLE_RATE, WINDOW

WINDOW_S = WINDOW / SAMPLE_RATE


class SourcePipeline:
    def __init__(self, source, cfg, catalog, classifier, tz=None):
        self.source = source
        self.sid = source["id"]
        self.cat = catalog
        self.clf = classifier
        self.ring = RingBuffer(cfg["storage"]["ring_seconds"])
        self.tz = zoneinfo.ZoneInfo(tz) if tz else None
        self.state = {"connected": False, "error": None, "level_dbfs": None, "below_gate": False,
                      "active_classes": [], "last_window": None, "windows": 0, "inferences": 0}
        self._runs = {}      # mid -> run state
        self._cool = {}      # mid -> abs sample index until which re-emission is blocked
        self._pending = []   # clips waiting for their post-roll
        self._next_end = WINDOW
        self.reload(cfg)

    # ---------------------------------------------------------------- config
    def reload(self, cfg):
        self.cfg = cfg
        a = cfg["analysis"]
        self.hop = max(1, int(a["hop_s"] * SAMPLE_RATE))
        self.boost, self.hold_s = a["context_boost"], a["hold_s"]
        self.resolved = {}
        for c in self.cat.by_mid.values():
            r = st.resolve(cfg, self.cat, self.sid, c["mid"])
            if r["enabled"]:
                self.resolved[c["mid"]] = r
        for mid in list(self._runs):
            if mid not in self.resolved:
                del self._runs[mid]

    # ---------------------------------------------------------------- feed
    def feed(self, pcm, now):
        """pcm: int16 samples; now: aware datetime of the END of this chunk. Returns a list of event dicts."""
        out = []
        self.ring.write(pcm)
        while self.ring.total >= self._next_end:
            end = self._next_end
            self._next_end += self.hop
            t_end = now - dt.timedelta(seconds=(self.ring.total - end) / SAMPLE_RATE)
            out += self._process(end, t_end)
        out += self._flush_clips(now)
        return out

    # ---------------------------------------------------------------- window
    def _local_naive(self, t):
        return (t.astimezone(self.tz) if self.tz else t.astimezone()).replace(tzinfo=None)

    def _process(self, end, t_end):
        st_ = self.state
        st_["windows"] += 1
        st_["last_window"] = t_end.isoformat()
        raw = self.ring.get(end - WINDOW, end)
        if raw is None or len(raw) < WINDOW:
            return []
        x = raw.astype(np.float32) / 32768.0
        level = 20 * math.log10(max(float(np.sqrt(np.mean(x * x))), 1e-9))
        st_["level_dbfs"] = round(level, 1)
        local = self._local_naive(t_end)
        active = {m: r for m, r in self.resolved.items() if st.is_active(r["schedule"], local)}
        passing = {m: r for m, r in active.items() if r["min_volume_dbfs"] is None or level >= r["min_volume_dbfs"]}
        st_["below_gate"] = bool(active) and not passing
        # classes that cannot be heard in this window end their run
        for m in list(self._runs):
            if m not in passing:
                self._miss(m, end)
        if not passing:
            st_["active_classes"] = self._active_now(end)
            return []
        scores = self.clf.predict(x)
        st_["inferences"] += 1
        ctx_on = {m for m, r in active.items()
                  if self.cat.by_mid[m]["interest"] == "context" and scores[self.cat.by_mid[m]["yamnet_index"]] >= r["threshold"]}
        events = []
        for m, r in passing.items():
            c = self.cat.by_mid[m]
            score = float(scores[c["yamnet_index"]])
            thr = r["threshold"]
            if c["interest"] != "context" and any(x_ in ctx_on for x_ in c["inhibiting_contexts"]):
                thr = min(0.99, thr + self.boost)
            if score >= thr:
                ev = self._hit(m, r, c, score, end, t_end)
                if ev:
                    events.append(ev)
            else:
                self._miss(m, end)
        st_["active_classes"] = self._active_now(end)
        return events

    # ---------------------------------------------------------------- run state machine
    def _hit(self, m, r, c, score, end, t_end):
        run = self._runs.get(m)
        if run is None:
            run = self._runs[m] = {"first_end": end, "hits": 0, "misses": 0, "peak": 0.0, "emitted": False, "last_end": end}
        run["hits"] += 1
        run["misses"] = 0
        run["last_end"] = end
        run["peak"] = max(run["peak"], score)
        covered = WINDOW_S + (run["hits"] - 1) * self.hop / SAMPLE_RATE
        if run["emitted"] or covered + 1e-9 < r["min_duration_s"] or end < self._cool.get(m, 0):
            return None
        run["emitted"] = True
        self._cool[m] = end + int(r["cooldown_s"] * SAMPLE_RATE)
        onset_abs = run["first_end"] - WINDOW
        started = t_end - dt.timedelta(seconds=(end - onset_abs) / SAMPLE_RATE)
        ev = {"type": "detection", "id": uuid.uuid4().hex[:12], "source": self.sid, "mid": m, "class": c["audioset_name"],
              "score": round(run["peak"], 3), "threshold": r["threshold"], "duration_s": round(covered, 2),
              "level_dbfs": self.state["level_dbfs"], "started_at": started.isoformat(), "detected_at": t_end.isoformat(),
              "clip_retention_days": r["clip_retention_days"]}
        if r["clip_retention_days"] > 0:
            self._pending.append({"id": ev["id"], "mid": m, "from": onset_abs - int(r["pre_roll_s"] * SAMPLE_RATE),
                                  "to": end + int(r["post_roll_s"] * SAMPLE_RATE), "retention": r["clip_retention_days"],
                                  "meta": {k: ev[k] for k in ("source", "mid", "class", "score", "started_at")}})
        return ev

    def _miss(self, m, end):
        run = self._runs.get(m)
        if run is None:
            return
        run["misses"] += 1
        if run["misses"] > 1 or (end - run["last_end"]) > 3 * self.hop:  # one missed window is tolerated (pulsed alarms)
            del self._runs[m]

    def _active_now(self, end):
        horizon = int(self.hold_s * SAMPLE_RATE)
        return [m for m, run in self._runs.items() if run["emitted"] and end - run["last_end"] <= horizon]

    # ---------------------------------------------------------------- clips
    def _flush_clips(self, now):
        out, keep = [], []
        for p in self._pending:
            if self.ring.total >= p["to"]:
                pcm = self.ring.get(p["from"], p["to"])
                if pcm is not None and len(pcm):
                    out.append({"type": "clip", "id": p["id"], "mid": p["mid"], "pcm": pcm, "retention_days": p["retention"],
                                "meta": p["meta"]})
            else:
                keep.append(p)
        self._pending = keep
        return out
