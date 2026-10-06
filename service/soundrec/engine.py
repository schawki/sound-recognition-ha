"""Orchestration: sources -> pipelines -> events (store, clips, subscribers); live reload of the configuration."""
import asyncio
import copy
import datetime as dt
import logging
import os

from . import advisor, catalog as cm, config as cfgmod, recommend, settings as st
from .audio import read_source
from .classifier import YamnetClassifier
from .clips import ClipStore
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
        self.places = {}                      # source id -> (environment, expires at), pushed by the integration
        errs = cfgmod.validate(self.cfg, self.catalog)
        if errs:
            raise SystemExit("invalid configuration:\n  " + "\n  ".join(errs))
        self.clf = classifier or YamnetClassifier(model_path)
        s = self.cfg["storage"]
        os.makedirs(s["clips_dir"], exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(s["db_path"])), exist_ok=True)
        self.store = EventStore(s["db_path"])
        self.clips = ClipStore(s["clips_dir"])
        self.pipes, self.tasks, self._src_cfg = {}, {}, {}
        self.subs = set()
        self._maint = None

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
        self._sync_sources()
        return []

    def _sync_sources(self):
        wanted = {s["id"]: s for s in self.cfg["sources"] if s.get("enabled", True)}
        for sid in list(self.tasks):
            if sid not in wanted or self._conn_key(wanted[sid]) != self._conn_key(self._src_cfg[sid]):
                self.tasks.pop(sid).cancel()
                self.pipes.pop(sid, None)
                self._src_cfg.pop(sid, None)
        for sid, s in wanted.items():
            if sid in self.pipes:
                self.pipes[sid].source = s
                self.pipes[sid].reload(self.cfg)
            else:
                self._start_source(s)

    @staticmethod
    def _conn_key(s):
        return (s["type"], s["url"], s.get("password"))

    def _start_source(self, s):
        pipe = SourcePipeline(s, self.cfg, self.catalog, self.clf, tz=self.cfg.get("timezone"))
        self.pipes[s["id"]] = pipe
        self._src_cfg[s["id"]] = s

        last = {"active": [], "context": None}

        def on_pcm(pcm, pipe=pipe, last=last):
            for ev in pipe.feed(pcm, _now()):
                self._handle(pipe.sid, ev)
            active = sorted(pipe.state["active_classes"])
            if active != last["active"]:  # push changes immediately so clients need not wait for the periodic status
                last["active"] = active
                self._publish({"type": "active", "source": pipe.sid, "active_classes": active})
            ctx = (tuple(pipe.state["active_contexts"]), round(pipe.state["adaptive_offset"], 2), round(pipe.state["external_offset"], 2))
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
            rel, expires = self.clips.write(ev["id"], ev["pcm"], ev["meta"], ev["retention_days"], _now())
            self.store.set_clip(ev["id"], rel, expires.isoformat())
            self._publish({"type": "clip_ready", "id": ev["id"], "source": sid, "mid": ev["mid"], "clip": rel,
                           "expires_at": expires.isoformat()})

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
                "external_offset": s["external_offset"], "external_reasons": s["external_reasons"], "external_detail": s["external_detail"]}

    def status(self):
        out = []
        for s in self.cfg["sources"]:
            p = self.pipes.get(s["id"])
            base = {"id": s["id"], "name": s.get("name") or s["id"], "type": s["type"], "enabled": s.get("enabled", True)}
            if p:
                base.update({k: p.state[k] for k in ("connected", "error", "level_dbfs", "below_gate", "active_classes",
                                                     "last_window", "windows", "inferences")})
                base.update(self._context(p))
            else:
                base.update({"connected": False, "error": None if not base["enabled"] else "starting", "level_dbfs": None,
                             "below_gate": False, "active_classes": [], "last_window": None, "windows": 0, "inferences": 0,
                             "active_contexts": [], "ambient_dbfs": None, "baseline_dbfs": None, "adaptive_enabled": False,
                             "adaptive_offset": 0.0, "external_offset": 0.0, "external_reasons": [],
                             "external_detail": []})
            out.append(base)
        return out

    def warnings(self, lang="en", overrides=True):
        return advisor.compute(self.cfg, lang, self.catalog_root, overrides)

    def set_external(self, sid, offset, reasons, detail, ttl_s):
        """Offset pushed by the integration for one source. Returns False when the source is not running."""
        pipe = self.pipes.get(sid)
        if pipe is None:
            return False
        pipe.set_external(offset, reasons, detail, ttl_s, _now())
        return True

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
        return recommend.compute(self.cfg, lang, self.catalog_root, self.store.false_detections(since), self.active_places())

    def stats(self, hours=24):
        return self.store.stats(_now().timestamp(), hours)

    async def _maintenance(self):
        while True:
            try:
                now = _now()
                removed = self.clips.purge(now)
                days = self.cfg["storage"]["events_retention_days"]
                self.store.purge((now - dt.timedelta(days=days)).timestamp(), now.isoformat())
                if removed:
                    log.info("purged %d expired clips", len(removed))
            except Exception:  # noqa: BLE001
                log.exception("maintenance failed")
            await asyncio.sleep(600)
