"""Orchestration: sources -> pipelines -> events (store, clips, subscribers); live reload of the configuration."""
import asyncio
import copy
import datetime as dt
import logging
import os

from . import advisor, catalog as cm, config as cfgmod, settings as st
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
    def apply_config(self, new_cfg):
        """Validates, saves (atomically) and applies a full configuration. Returns the list of errors (empty = applied)."""
        new_cfg = cfgmod._merge(cfgmod.DEFAULTS, new_cfg)
        if new_cfg["api"].get("token") in (None, "", "***"):
            new_cfg["api"]["token"] = self.cfg["api"]["token"]
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
        return (s["type"], s["url"])

    def _start_source(self, s):
        pipe = SourcePipeline(s, self.cfg, self.catalog, self.clf, tz=self.cfg.get("timezone"))
        self.pipes[s["id"]] = pipe
        self._src_cfg[s["id"]] = s

        last = {"active": []}

        def on_pcm(pcm, pipe=pipe, last=last):
            for ev in pipe.feed(pcm, _now()):
                self._handle(pipe.sid, ev)
            active = sorted(pipe.state["active_classes"])
            if active != last["active"]:  # push changes immediately so clients need not wait for the periodic status
                last["active"] = active
                self._publish({"type": "active", "source": pipe.sid, "active_classes": active})

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
    def status(self):
        out = []
        for s in self.cfg["sources"]:
            p = self.pipes.get(s["id"])
            base = {"id": s["id"], "name": s.get("name") or s["id"], "type": s["type"], "enabled": s.get("enabled", True)}
            if p:
                base.update({k: p.state[k] for k in ("connected", "error", "level_dbfs", "below_gate", "active_classes",
                                                     "last_window", "windows", "inferences")})
            else:
                base.update({"connected": False, "error": None if not base["enabled"] else "starting", "level_dbfs": None,
                             "below_gate": False, "active_classes": [], "last_window": None, "windows": 0, "inferences": 0})
            out.append(base)
        return out

    def warnings(self, lang="en", overrides=True):
        return advisor.compute(self.cfg, lang, self.catalog_root, overrides)

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
