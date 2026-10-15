"""In-memory stand-in for the service API, built on the real catalog, validator and advisor."""
import asyncio
import copy
from types import SimpleNamespace

from soundrec import API_LEVEL, advisor, catalog as cm, config as cfgmod, recommend, settings as st
from custom_components.sound_recognition.api import CannotConnect, InvalidAuth, InvalidConfig, SoundRecClient, SoundRecError

CAT = st.Catalog(cm.load_raw())
STATE = SimpleNamespace(update=None, health_extra={}, cfg=None, down=False, token="tok", handler=None, stop=None, status={}, events=[], feedback={}, pushed={}, clip_calls=[], places={}, storage=None, api_level=None, moved=None, deleted_old=None, conditions=None, noise=None, noise_deleted=None)


def reset(cfg=None):
    STATE.token = "tok"
    STATE.cfg = cfgmod._merge(cfgmod.DEFAULTS, cfg or {})
    STATE.cfg["api"]["token"] = STATE.token
    STATE.down, STATE.handler, STATE.stop, STATE.status, STATE.events, STATE.feedback, STATE.pushed, STATE.clip_calls, STATE.places, STATE.conditions = False, None, asyncio.Event(), {}, [], {}, {}, [], {}, None
    STATE.noise = {"retention_days": 7, "recording": True, "sources": [{"id": "kitchen", "name": "Kitchen", "minutes": 420, "calm_minutes": 400, "bytes": 16800, "since": 1_700_000_000, "until": 1_700_025_200, "level_dbfs": -52.0, "current_gate": -60, "hourly": [-60.0] * 24,
                                                                  "suggestion": {"status": "ready", "gate": -54, "quiet_dbfs": -60.0, "typical_dbfs": -58.0, "loud_dbfs": -40.0, "margin_db": 6.0, "capped": False, "minutes": 400}}]}
    STATE.noise_deleted = None
    STATE.update, STATE.health_extra, STATE.api_level = {"state": "idle", "capable": True}, {}, API_LEVEL
    STATE.storage = {"path": "/var/lib/soundrec/clips", "clips": 69, "bytes": 25_000_000, "free_bytes": 6_000_000_000, "total_bytes": 20_000_000_000, "per_day_bytes": 3_000_000, "days_left": 2000.0,
                     "max_gb": None, "min_free_gb": None, "paused": False, "auto_deleted": 0, "skipped": 0, "moved_skipped": 0,
                     "move": {"capable": True, "roots": ["/mnt", "/media"], "state": "idle", "message": "", "from": "", "to": "", "stalled": False, "log": "",
                              "clean": {"state": "idle", "message": "", "path": "", "stalled": False}, "old": []}}


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
        return {"status": "ok", "version": "0.2.0", "api_level": STATE.api_level, "commit": "abc1234", "release": "v0.2.0", "update": {"capable": STATE.update["capable"]}, **STATE.health_extra}

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
        return advisor.compute(st.fold(copy.deepcopy(STATE.cfg), CAT), lang, overrides=overrides)       # the service advises on the configuration in effect (presets folded in)

    async def catalog(self, lang):
        self._check()
        return cm.load_lang(lang)

    async def get_config(self):
        self._check()
        c = copy.deepcopy(STATE.cfg)
        c["api"]["token"] = "***"
        return c

    async def get_config_effective(self):
        self._check()
        c = st.fold(copy.deepcopy(STATE.cfg), CAT)
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

    async def noise(self):
        self._check()
        return STATE.noise

    async def delete_noise(self, source=None):
        self._check()
        n = sum(x["minutes"] for x in STATE.noise["sources"] if source in (None, x["id"]))
        for x in STATE.noise["sources"]:
            if source in (None, x["id"]):
                x["minutes"] = 0
        STATE.noise_deleted = (source, n)
        return {"deleted": n}

    async def set_conditions(self, states, ttl_s=120):
        self._check()
        STATE.conditions = {"states": dict(states), "ttl_s": ttl_s}
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

    async def storage(self):
        self._check()
        return STATE.storage

    async def storage_move(self, path):
        self._check()
        errors = ["not_found"] if path.endswith("missing") else []
        if errors:
            raise InvalidConfig(errors)
        STATE.storage = {**STATE.storage, "move": {"capable": True, "roots": ["/mnt"], "state": "requested", "message": "", "from": "", "to": "", "stalled": False, "log": ""}}
        STATE.moved = path
        return STATE.storage["move"]

    async def storage_old_delete(self, path):
        self._check()
        if path != "/var/lib/soundrec/clips":
            raise SoundRecError("HTTP 404 on /storage/old/delete")
        STATE.deleted_old = path
        return {"capable": True, "state": "idle", "clean": {"state": "requested", "message": "", "path": path, "stalled": False}}

    async def rotate_token(self):
        self._check()
        STATE.token = "new-" + STATE.token
        STATE.cfg["api"]["token"] = STATE.token
        return STATE.token

    async def clip(self, rel):
        return b"RIFFfake"

    async def listen(self, lang, handler):
        STATE.handler = handler
        await STATE.stop.wait()


# A service behind the integration: methods whose route is newer than STATE.api_level answer 404, like the real service would.
# A route the real client tolerates ('fallback') runs the real client method, so its fallback is the real one.
import json as _json
import pathlib as _pl

for _route, _e in _json.loads((_pl.Path(__file__).parent / "compat_routes.json").read_text())["routes"].items():
    if not _e["client"] or not hasattr(FakeClient, _e["client"]):
        continue

    def _gate(name, route, since, tolerance):
        original = getattr(FakeClient, name)

        async def gated(self, *a, **k):
            if since > STATE.api_level:
                if tolerance == "fallback":
                    return await getattr(SoundRecClient, name)(self, *a, **k)
                raise SoundRecError(f"HTTP 404 on {route.split(' ', 1)[1]}")
            return await original(self, *a, **k)
        setattr(FakeClient, name, gated)
    _gate(_e["client"], _route, _e["since"], _e.get("tolerance"))


async def _no_such_route(self, method, path, **kw):
    raise SoundRecError(f"HTTP 404 on {path}")


FakeClient._request = _no_such_route
