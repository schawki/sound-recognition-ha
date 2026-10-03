"""In-memory stand-in for the service API, built on the real catalog, validator and advisor."""
import asyncio
import copy
from types import SimpleNamespace

from soundrec import advisor, catalog as cm, config as cfgmod, settings as st
from custom_components.sound_recognition.api import CannotConnect, InvalidAuth, InvalidConfig

CAT = st.Catalog(cm.load_raw())
STATE = SimpleNamespace(cfg=None, down=False, token="tok", handler=None, stop=None, status={}, events=[])


def reset(cfg=None):
    STATE.cfg = cfgmod._merge(cfgmod.DEFAULTS, cfg or {})
    STATE.cfg["api"]["token"] = STATE.token
    STATE.down, STATE.handler, STATE.stop, STATE.status, STATE.events = False, None, asyncio.Event(), {}, []


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
        return {"status": "ok", "version": "0.1.0"}

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

    async def resolved(self, source, mid):
        self._check()
        from soundrec import settings as st
        return st.resolve(STATE.cfg, CAT, source, mid)

    async def clip(self, rel):
        return b"RIFFfake"

    async def listen(self, lang, handler):
        STATE.handler = handler
        await STATE.stop.wait()
