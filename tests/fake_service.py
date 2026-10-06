"""In-memory stand-in for the service API, built on the real catalog, validator and advisor."""
import asyncio
import copy
from types import SimpleNamespace

from soundrec import advisor, catalog as cm, config as cfgmod, recommend, settings as st
from custom_components.sound_recognition.api import CannotConnect, InvalidAuth, InvalidConfig, SoundRecError

CAT = st.Catalog(cm.load_raw())
STATE = SimpleNamespace(update=None, health_extra={}, cfg=None, down=False, token="tok", handler=None, stop=None, status={}, events=[], feedback={}, pushed={}, clip_calls=[], places={})


def reset(cfg=None):
    STATE.cfg = cfgmod._merge(cfgmod.DEFAULTS, cfg or {})
    STATE.cfg["api"]["token"] = STATE.token
    STATE.down, STATE.handler, STATE.stop, STATE.status, STATE.events, STATE.feedback, STATE.pushed, STATE.clip_calls, STATE.places = False, None, asyncio.Event(), {}, [], {}, {}, [], {}
    STATE.update, STATE.health_extra = {"state": "idle", "capable": True}, {}


class FakeClient:
    def __init__(self, session, host, port, token):
        self.token = token

    def _check(self):
        if STATE.down:
            raise CannotConnect("down")
        if self.token != STATE.token:
            raise InvalidAuth

    async def health(self):
        if STATE.down:
            raise CannotConnect("down")
        return {"status": "ok", "version": "0.2.0", "api_level": 8, "commit": "abc1234", "release": "v0.2.0", "update": {"capable": STATE.update["capable"]}, **STATE.health_extra}

    async def update_status(self):
        self._check()
        return dict(STATE.update)

    async def update_start(self):
        self._check()
        if not STATE.update["capable"]:
            raise SoundRecError("HTTP 501 on /update")
        if STATE.update["state"] in ("requested", "running"):
            raise SoundRecError("HTTP 409 on /update")
        STATE.update = {**STATE.update, "state": "requested"}
        return dict(STATE.update)

    async def sources(self):
        self._check()
        out = []
        for s in STATE.cfg["sources"]:
            base = {"id": s["id"], "name": s.get("name") or s["id"], "type": s["type"], "enabled": s.get("enabled", True),
                    "connected": True, "error": None, "level_dbfs": -42.5, "below_gate": False, "active_classes": [],
                    "last_window": None, "windows": 1, "inferences": 1}
            base.update(STATE.status.get(s["id"], {}))
            out.append(base)
        return out

    async def warnings(self, lang, overrides=True):
        self._check()
        return advisor.compute(STATE.cfg, lang, overrides=overrides)

    async def catalog(self, lang):
        self._check()
        return cm.load_lang(lang)

    async def get_config(self):
        self._check()
        c = copy.deepcopy(STATE.cfg)
        c["api"]["token"] = "***"
        return c

    async def put_config(self, cfg, lang):
        self._check()
        new = cfgmod._merge(cfgmod.DEFAULTS, copy.deepcopy(cfg))
        new["api"]["token"] = STATE.token
        errs = cfgmod.validate(new, CAT)
        if errs:
            raise InvalidConfig(errs)
        STATE.cfg = new
        return {"ok": True}

    async def validate_config(self, cfg, lang):
        self._check()
        cand = cfgmod._merge(cfgmod.DEFAULTS, copy.deepcopy(cfg))
        errs = cfgmod.validate(cand, CAT)
        return {"errors": errs, "warnings": [] if errs else advisor.compute(cand, lang)}

    async def events(self, lang, **query):
        self._check()
        return [dict(e) for e in STATE.events]

    async def recommendations(self, lang):
        self._check()
        return recommend.compute(STATE.cfg, lang)

    async def stats(self, hours=24):
        self._check()
        zeros = [0] * hours
        block = lambda n: {"total": n, "by_source": {"kitchen": n} if n else {}, "by_class": [], "hourly": zeros[:-1] + [n]}
        return {"hours": hours, "since": 0, "detections": block(3), "masked": block(1), "false": block(0)}

    async def set_external(self, sid, offset, reasons, detail, ttl_s=60):
        self._check()
        STATE.pushed[sid] = {"offset": offset, "reasons": reasons, "detail": detail, "ttl_s": ttl_s}
        return {"ok": True}

    async def set_place(self, sid, environment, ttl_s=60):
        self._check()
        STATE.places[sid] = environment
        return {"ok": True}

    async def event_feedback(self, event_id, value, kind="false"):
        self._check()
        STATE.feedback[event_id] = value if kind == "false" else f"{kind}:{value}"
        return {"ok": True}

    async def delete_clipless(self, flt=None, dry_run=False):
        self._check()
        STATE.clip_calls.append(("clipless", {"filter": flt, "dry_run": dry_run}))
        return {"count": 4, "dry_run": dry_run}

    async def resolved(self, source, mid):
        self._check()
        from soundrec import settings as st
        return st.resolve(STATE.cfg, CAT, source, mid)

    async def clips(self, lang, **query):
        self._check()
        STATE.clip_calls.append(("list", query))
        rows = [{"id": "e1", "ts": 1.0, "source": "salon", "mid": "/m/05tny_", "class": "Bark", "name": "Bark", "score": 0.7, "clip": "2026-06-20/e1.wav", "clip_expires": None, "size": 32044}]
        return {"clips": rows, "total": 1, "total_bytes": 32044, "sounds": [{"mid": "/m/05tny_", "name": "Bark", "count": 1}], "disk": {"clips": 1, "bytes": 32044, "free_bytes": 10**9}}

    async def delete_clips(self, ids=None, flt=None, dry_run=False):
        self._check()
        STATE.clip_calls.append(("delete", {"ids": ids, "filter": flt, "dry_run": dry_run}))
        return {"count": 1, "bytes": 32044, "dry_run": dry_run}

    async def clip(self, rel):
        return b"RIFFfake"

    async def listen(self, lang, handler):
        STATE.handler = handler
        await STATE.stop.wait()
