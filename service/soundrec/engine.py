"""Orchestration: sources -> pipelines -> events (store, clips, subscribers); live reload of the configuration."""
import asyncio
import datetime as dt
import logging
import os
import secrets
import time

from . import advisor, catalog as cm, conditions, config as cfgmod, noise as noisemod, recommend, settings as st
from .audio import read_source
from .classifier import YamnetClassifier
from .clips import ClipStore
from .mover import Mover
from .detector import SourcePipeline
from .store import EventStore

log = logging.getLogger("soundrec.engine")


def _now():
    return dt.datetime.now(dt.timezone.utc)


class Engine:
    def __init__(self, config_path, model_path, catalog_root=None, classifier=None):
        self.config_path = config_path
        self.model_path = model_path
        self.catalog_root = catalog_root
        self.cfg = cfgmod.load(config_path)
        if cfgmod.ensure_token(self.cfg):
            cfgmod.save(config_path, self.cfg)
            log.warning("generated an API token and saved it in %s", config_path)
        self.catalog = st.Catalog(cm.load_raw(catalog_root))
        self.auto_gates = {}                  # source id -> automatic minimum volume in use (from the noise measurements)
        self.eff = st.fold(self.cfg, self.catalog)      # the configuration in effect: the presets of each source folded in
        self.places = {}                      # source id -> (environment, expires at), pushed by the integration
        errs = cfgmod.validate(self.cfg, self.catalog)
        if errs:
            raise SystemExit("invalid configuration:\n  " + "\n  ".join(errs))
        self.clf = classifier or YamnetClassifier(model_path)
        s = self.cfg["storage"]
        os.makedirs(s["clips_dir"], exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(s["db_path"])), exist_ok=True)
        self.store = EventStore(s["db_path"])
        self.auto_gates = {k: v[0] for k, v in self.store.auto_state().items() if v[0] is not None}
        self._rebuild()
        self.clips = ClipStore(s["clips_dir"])
        self.mover = Mover.from_env()
        self.facts = conditions.Facts()        # states of Home Assistant entities used by the conditions (pushed by the integration)        # moving the clips to another folder: clips are neither written nor purged meanwhile
        self.pipes, self.tasks, self._src_cfg = {}, {}, {}
        self.subs = set()
        self._maint = None
        self._clip_bytes = None            # running estimate of what the clips take, rebuilt by the maintenance
        self._paused = False               # clips are not kept while the free space is under the limit chosen by the administrator
        self._prev_token = None            # (old token, valid until): a token change must not cut the caller off

    # ---------------------------------------------------------------- lifecycle
    async def start(self):
        self._sync_sources()
        self._maint = asyncio.create_task(self._maintenance())

    async def stop(self):
        for t in list(self.tasks.values()) + ([self._maint] if self._maint else []):
            t.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)

    # ---------------------------------------------------------------- configuration
    def restore_secrets(self, cfg):
        """The API never shows a source password: "***" in a submitted configuration means "unchanged"."""
        old = {x["id"]: x for x in self.cfg.get("sources") or []}
        for src in cfg.get("sources") or []:
            if src.get("password") == "***":
                src["password"] = (old.get(src.get("id")) or {}).get("password")

    def apply_config(self, new_cfg):
        """Validates, saves (atomically) and applies a full configuration. Returns the list of errors (empty = applied)."""
        new_cfg = cfgmod._merge(cfgmod.DEFAULTS, new_cfg)
        if new_cfg["api"].get("token") in (None, "", "***"):
            new_cfg["api"]["token"] = self.cfg["api"]["token"]
        self.restore_secrets(new_cfg)
        errs = cfgmod.validate(new_cfg, self.catalog)
        if errs:
            return errs
        cfgmod.save(self.config_path, new_cfg)
        self.cfg = new_cfg
        self._rebuild()
        self._sync_sources()
        return []

    def _rebuild(self):
        """The configuration in effect: presets folded in, then the automatic minimum volumes of the sources that follow the measurements."""
        self.eff = st.apply_auto_volume(st.fold(self.cfg, self.catalog), self.auto_gates)

    def _sync_sources(self):
        wanted = {s["id"]: s for s in self.eff["sources"] if s.get("enabled", True)}
        for sid in list(self.tasks):
            if sid not in wanted or self._conn_key(wanted[sid]) != self._conn_key(self._src_cfg[sid]):
                self.tasks.pop(sid).cancel()
                self.pipes.pop(sid, None)
                self._src_cfg.pop(sid, None)
        for sid, s in wanted.items():
            if sid in self.pipes:
                self.pipes[sid].source = s
                self.pipes[sid].reload(self.eff)
            else:
                self._start_source(s)

    @staticmethod
    def _conn_key(s):
        return (s["type"], s["url"], s.get("password"))

    def _start_source(self, s):
        pipe = SourcePipeline(s, self.eff, self.catalog, self.clf, tz=self.cfg.get("timezone"))
        pipe.facts = self.facts
        self.pipes[s["id"]] = pipe
        self._src_cfg[s["id"]] = s

        last = {"active": [], "context": None}

        def on_pcm(pcm, pipe=pipe, last=last):
            for ev in pipe.feed(pcm, _now()):
                self._handle(pipe.sid, ev)
            rows = pipe.take_noise()
            if rows and self.cfg["storage"].get("noise_retention_days", 7) > 0:
                self.store.add_noise(pipe.sid, rows)
            active = sorted(pipe.state["active_classes"])
            if active != last["active"]:  # push changes immediately so clients need not wait for the periodic status
                last["active"] = active
                self._publish({"type": "active", "source": pipe.sid, "active_classes": active})
            ctx = (tuple(pipe.state["active_contexts"]), round(pipe.state["adaptive_offset"], 2), round(pipe.state["external_offset"], 2),
                   tuple(pipe.state["held_by_condition"]))
            if ctx != last["context"]:
                last["context"] = ctx
                self._publish({"type": "context", "source": pipe.sid, **self._context(pipe)})

        def on_state(state, err, pipe=pipe):
            pipe.state["connected"] = state == "connected"
            pipe.state["error"] = err
            self._publish({"type": "source_state", "source": pipe.sid, "state": state, "error": err})

        self.tasks[s["id"]] = asyncio.create_task(read_source(s, on_pcm, on_state))

    # ---------------------------------------------------------------- events
    def _handle(self, sid, ev):
        if ev["type"] == "detection":
            self.store.add(ev)
            log.info("detection %s on %s (score %.2f)", ev["class"], sid, ev["score"])
            self._publish(ev)
        elif ev["type"] == "masked":
            self.store.add_masked(ev)
            log.info("masked %s on %s (score %.2f < %.2f, %s)", ev["class"], sid, ev["score"], ev["threshold"], "+".join(ev["reasons"]))
            self._publish(ev)
        elif ev["type"] == "clip":
            if self.mover.active():
                self.store.set_reason(ev["id"], "moving")
                return
            if self._check_free_space():
                self.store.set_reason(ev["id"], "disk_low")
                return
            rel, expires = self.clips.write(ev["id"], ev["pcm"], ev["meta"], ev["retention_days"], _now())
            self.store.set_clip(ev["id"], rel, expires.isoformat())
            if self._clip_bytes is not None:
                self._clip_bytes += self.clips.size(rel)
            self._enforce_quota()
            self._publish({"type": "clip_ready", "id": ev["id"], "source": sid, "mid": ev["mid"], "clip": rel,
                           "expires_at": expires.isoformat()})

    # ---------------------------------------------------------------- disk space chosen by the administrator
    def _check_free_space(self):
        """True while clips must not be kept: the free space fell under `storage.clips_min_free_gb` (and has not come back 10 % above it)."""
        limit = (self.cfg["storage"].get("clips_min_free_gb") or 0) * 1e9
        free = self.clips.free_bytes()
        if not limit or free is None:
            self._paused = False
        elif self._paused:
            self._paused = free < limit * 1.1
        else:
            self._paused = free < limit
        return self._paused

    def _enforce_quota(self):
        """Over `storage.clips_max_gb`: the oldest clips go first (the ones you judged last) until the clips are back to 90 % of the limit."""
        limit = (self.cfg["storage"].get("clips_max_gb") or 0) * 1e9
        if self.mover.active() or not limit or self._clip_bytes is None or self._clip_bytes <= limit:
            return 0
        rows = self.store.clips()                                              # newest first
        order = sorted(rows, key=lambda r: (r["feedback"] is not None, r["ts"]))    # not judged first, oldest first
        removed, target = [], limit * 0.9
        for r in order:
            if self._clip_bytes <= target:
                break
            self._clip_bytes -= self.clips.delete(r["clip"]) or 0
            removed.append(r["id"])
        if removed:
            self.store.forget_clips(removed, "quota")
            log.info("clips over the limit of %.2f GB: %d oldest clips deleted", limit / 1e9, len(removed))
        return len(removed)

    def storage_info(self):
        """What the clips take, what is left, how fast they grow and what the two limits do. Walks the clips folder: call it off the event loop."""
        u = self.clips.usage()
        now = _now().timestamp()
        rows = [r for r in self.store.clips() if r["ts"] >= now - 7 * 86400]
        per_day = None
        if rows:
            span = min(7.0, max(1.0, (now - min(r["ts"] for r in rows)) / 86400))
            per_day = sum(self.clips.size(r["clip"]) for r in rows) / span
        free = u["free_bytes"]
        s = self.cfg["storage"]
        return {**u, "per_day_bytes": per_day, "days_left": (free / per_day) if (free is not None and per_day) else None,
                "max_gb": s.get("clips_max_gb"), "min_free_gb": s.get("clips_min_free_gb"), "paused": self._check_free_space(),
                "auto_deleted": self.store.count_reason("quota"), "skipped": self.store.count_reason("disk_low"),
                "moved_skipped": self.store.count_reason("moving"), "move": {**self.mover.status(), "old": self.mover.old_folders(s["clips_dir"])}}

    # ---------------------------------------------------------------- token
    def rotate_token(self):
        """New API token; the old one still works for a minute so the caller can store the new one."""
        self._prev_token = (self.cfg["api"]["token"], time.time() + 60)
        self.cfg["api"]["token"] = secrets.token_urlsafe(24)
        cfgmod.save(self.config_path, self.cfg)
        return self.cfg["api"]["token"]

    def token_ok(self, given):
        import hmac
        if hmac.compare_digest(given, self.cfg["api"]["token"]):
            return True
        old = self._prev_token
        return bool(old and time.time() < old[1] and hmac.compare_digest(given, old[0]))

    def _publish(self, msg):
        for q in list(self.subs):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                self.subs.discard(q)  # slow consumer: dropped, it can reconnect

    def subscribe(self):
        q = asyncio.Queue(maxsize=500)
        self.subs.add(q)
        return q

    def unsubscribe(self, q):
        self.subs.discard(q)

    # ---------------------------------------------------------------- status
    @staticmethod
    def _context(pipe):
        s = pipe.state
        return {"active_contexts": s["active_contexts"], "ambient_dbfs": s["ambient_dbfs"], "baseline_dbfs": s["baseline_dbfs"],
                "adaptive_enabled": s["adaptive_enabled"], "adaptive_offset": s["adaptive_offset"],
                "external_offset": s["external_offset"], "external_reasons": s["external_reasons"], "external_detail": s["external_detail"],
                "held_by_condition": s["held_by_condition"], "condition_unknown": s["condition_unknown"]}

    def status(self):
        out = []
        for s in self.cfg["sources"]:
            p = self.pipes.get(s["id"])
            base = {"id": s["id"], "name": s.get("name") or s["id"], "type": s["type"], "enabled": s.get("enabled", True)}
            base["min_volume_dbfs"], base["min_volume_origin"] = self._gate_of(s["id"])
            base["min_volume_auto"] = st.auto_enabled(self.cfg, s)
            if p:
                base.update({k: p.state[k] for k in ("connected", "error", "level_dbfs", "below_gate", "active_classes",
                                                     "last_window", "windows", "inferences")})
                base.update(self._context(p))
            else:
                base.update({"connected": False, "error": None if not base["enabled"] else "starting", "level_dbfs": None,
                             "below_gate": False, "active_classes": [], "last_window": None, "windows": 0, "inferences": 0,
                             "active_contexts": [], "ambient_dbfs": None, "baseline_dbfs": None, "adaptive_enabled": False,
                             "adaptive_offset": 0.0, "external_offset": 0.0, "external_reasons": [],
                             "external_detail": [], "held_by_condition": [], "condition_unknown": False})
            out.append(base)
        return out

    def _gate_of(self, sid):
        """(minimum volume, where it comes from) of a source at the level of the source, as in effect."""
        src = next((x for x in self.eff.get("sources", []) if x["id"] == sid), None)
        return st.source_gate(self.eff, src) if src else (None, "none")

    def warnings(self, lang="en", overrides=True):
        seen = self.store.seen([x["id"] for x in self.cfg.get("sources", [])], _now().timestamp())
        now = _now().timestamp()
        return advisor.compute(self.eff, lang, self.catalog_root, overrides, self.active_places(), {k: now - v for k, v in seen.items()})

    def set_external(self, sid, offset, reasons, detail, ttl_s):
        """Offset pushed by the integration for one source. Returns False when the source is not running."""
        pipe = self.pipes.get(sid)
        if pipe is None:
            return False
        pipe.set_external(offset, reasons, detail, ttl_s, _now())
        return True

    def noise(self):
        """What was measured for each source and the minimum volume it suggests (the service only applies it to the sources set to automatic)."""
        days = self.cfg["storage"].get("noise_retention_days", 7)
        tz = self.cfg.get("timezone")
        state = self.store.auto_state()
        out = []
        for s in self.cfg.get("sources", []):
            info = noisemod.summarize([tuple(r) for r in self.store.noise_rows(s["id"])], tz)
            p = self.pipes.get(s["id"])
            gate, origin = self._gate_of(s["id"])
            row = state.get(s["id"]) or (None, None, None)
            info.update({"id": s["id"], "name": s.get("name") or s["id"], "level_dbfs": None if p is None else p.state["level_dbfs"],
                         "current_gate": gate, "gate_origin": origin,
                         "auto": {"enabled": st.auto_enabled(self.cfg, s), "gate": row[0], "since": row[1], "checked": row[2],
                                  "history": self.store.auto_history(s["id"])}})
            out.append(info)
        return {"retention_days": days, "recording": days > 0, "step_db": st.AUTO_STEP_DB, "sources": out}

    def _auto_volume(self, now):
        """Once a day and per source set to automatic: looks at the suggestion and moves the minimum volume if it differs enough from the one in
        use (never when there are not enough calm minutes yet). Returns True when a minimum volume changed."""
        ts = now.timestamp()
        state = self.store.auto_state()
        base = st.fold(self.cfg, self.catalog)
        changed = False
        for s in self.cfg.get("sources", []):
            sid = s["id"]
            if not s.get("enabled", True) or not st.auto_enabled(self.cfg, s):
                continue
            if sid in state and ts - (state[sid][2] or 0) < st.AUTO_EVERY_S:
                continue
            self.store.auto_checked(sid, ts)
            sug = noisemod.summarize([tuple(r) for r in self.store.noise_rows(sid)], self.cfg.get("timezone"))["suggestion"]
            if sug["status"] != "ready":
                continue
            ref = self.auto_gates.get(sid)
            if ref is None:
                src = next(x for x in base["sources"] if x["id"] == sid)
                ref = st.source_gate(base, src)[0]
            if ref is not None and abs(sug["gate"] - ref) < st.AUTO_STEP_DB:
                continue
            self.store.auto_set(sid, sug["gate"], ts, ref)
            self.auto_gates[sid] = sug["gate"]
            log.info("automatic minimum volume of %s: %s -> %s dBFS", sid, ref, sug["gate"])
            changed = True
        return changed

    def delete_noise(self, source=None):
        return self.store.delete_noise(source)

    def set_conditions(self, states, ttl_s):
        """States of the entities the conditions read, pushed by the integration; forgotten after ttl_s seconds."""
        self.facts.set(states, ttl_s, _now().timestamp())

    def set_place(self, sid, environment, ttl_s):
        """Kind of place of a source as deduced by the integration (from Home Structure); used when the configuration names none.
        Forgotten after ttl_s seconds. Returns False for an unknown source or environment."""
        if sid not in {s["id"] for s in self.cfg.get("sources", [])}:
            return False
        if environment is None:
            self.places.pop(sid, None)
            return True
        if environment not in {e["id"] for e in self.catalog.raw.get("environments", [])}:
            return False
        self.places[sid] = (environment, _now().timestamp() + ttl_s)
        return True

    def active_places(self):
        now = _now().timestamp()
        self.places = {k: v for k, v in self.places.items() if v[1] > now}
        return {k: v[0] for k, v in self.places.items()}

    def recommendations(self, lang="en"):
        since = _now().timestamp() - recommend.FALSE_DAYS * 86400
        return recommend.compute(self.eff, lang, self.catalog_root, self.store.false_detections(since), self.active_places())

    def stats(self, hours=24):
        return self.store.stats(_now().timestamp(), hours)

    async def _maintenance(self):
        while True:
            try:
                now = _now()
                removed = [] if self.mover.active() else self.clips.purge(now)
                self._clip_bytes = self.clips.usage()["bytes"]
                self._check_free_space()
                self._enforce_quota()
                days = self.cfg["storage"]["events_retention_days"]
                self.store.purge((now - dt.timedelta(days=days)).timestamp(), now.isoformat())
                self.store.purge_noise(int((now - dt.timedelta(days=self.cfg["storage"].get("noise_retention_days", 7))).timestamp() // 60))
                self.store.auto_forget_except([x["id"] for x in self.cfg.get("sources", [])])
                self.auto_gates = {k: v for k, v in self.auto_gates.items() if any(x["id"] == k for x in self.cfg.get("sources", []))}
                if self._auto_volume(now):
                    self._rebuild()
                    self._sync_sources()
                if removed:
                    log.info("purged %d expired clips", len(removed))
            except Exception:  # noqa: BLE001
                log.exception("maintenance failed")
            await asyncio.sleep(600)
