"""Local HTTP + WebSocket API (aiohttp). Every route except /health needs 'Authorization: Bearer <token>'."""
import asyncio
import datetime as dt
import hmac
import json

from aiohttp import web, WSMsgType

from . import __version__, catalog as cm, config as cfgmod, settings as st, advisor

VERSION_PREFIX = "/api/v1"


def _lang(req):
    lang = req.query.get("lang") or req.headers.get("Accept-Language", "en")[:2] or "en"
    return lang.lower()


@web.middleware
async def auth(req, handler):
    if req.path == f"{VERSION_PREFIX}/health":
        return await handler(req)
    token = req.app["engine"].cfg["api"]["token"]
    header = req.headers.get("Authorization", "")
    given = header[7:] if header.startswith("Bearer ") else req.query.get("token", "")
    if not given or not hmac.compare_digest(given, token):
        return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(req)


def _masked(cfg):
    out = json.loads(json.dumps(cfg))
    out["api"]["token"] = "***"
    return out


async def health(req):
    return web.json_response({"status": "ok", "version": __version__})


async def languages(req):
    return web.json_response({"languages": cm.available_languages(req.app["engine"].catalog_root)})


async def catalog(req):
    return web.json_response(cm.load_lang(_lang(req), req.app["engine"].catalog_root))


async def get_config(req):
    return web.json_response(_masked(req.app["engine"].cfg))


async def put_config(req):
    eng = req.app["engine"]
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"errors": ["body must be JSON"]}, status=400)
    errs = eng.apply_config(body)
    if errs:
        return web.json_response({"errors": errs}, status=422)
    return web.json_response({"ok": True, "warnings": eng.warnings(_lang(req))})


async def validate_config(req):
    """Dry run: errors and warnings for a candidate configuration, nothing is saved."""
    eng = req.app["engine"]
    try:
        body = await req.json()
    except Exception:
        return web.json_response({"errors": ["body must be JSON"]}, status=400)
    cand = cfgmod._merge(cfgmod.DEFAULTS, body)
    errs = cfgmod.validate(cand, eng.catalog)
    return web.json_response({"errors": errs, "warnings": [] if errs else advisor.compute(cand, _lang(req), eng.catalog_root)})


async def warnings(req):
    """?overrides=0 returns the catalog levels, ignoring the `advice` settings (to list what can be adjusted)."""
    return web.json_response({"warnings": req.app["engine"].warnings(_lang(req), req.query.get("overrides", "1") != "0")})


async def sources(req):
    return web.json_response({"sources": req.app["engine"].status()})


async def resolved(req):
    eng = req.app["engine"]
    sid, cls = req.query.get("source"), req.query.get("class")
    try:
        r = st.resolve(eng.cfg, eng.catalog, sid, cls)
    except (KeyError, StopIteration):
        return web.json_response({"error": "unknown source or class"}, status=404)
    return web.json_response(r)


async def events(req):
    eng = req.app["engine"]
    names = cm.class_names(_lang(req), eng.catalog_root)
    since = float(req.query["since"]) if "since" in req.query else None
    rows = eng.store.query(since, req.query.get("source"), req.query.get("mid"), req.query.get("limit", 100))
    for r in rows:
        r["name"] = names.get(r["mid"], r["class"])
    return web.json_response({"events": rows})


async def clip(req):
    p = req.app["engine"].clips.path(req.match_info["rel"])
    if not p:
        return web.json_response({"error": "not found"}, status=404)
    return web.FileResponse(p, headers={"Content-Type": "audio/wav"})


async def ws(req):
    eng = req.app["engine"]
    sock = web.WebSocketResponse(heartbeat=20)
    await sock.prepare(req)
    names = cm.class_names(_lang(req), eng.catalog_root)
    q = eng.subscribe()
    await sock.send_json({"type": "hello", "version": __version__, "sources": eng.status()})

    async def pump():
        last = 0.0
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=5.0)
                if "mid" in msg:
                    msg = dict(msg, name=names.get(msg["mid"], msg.get("class")))
                await sock.send_json(msg)
            except asyncio.TimeoutError:
                await sock.send_json({"type": "status", "sources": eng.status()})

    task = asyncio.create_task(pump())
    try:
        async for m in sock:
            if m.type == WSMsgType.ERROR:
                break
    finally:
        task.cancel()
        eng.unsubscribe(q)
    return sock


def make_app(engine):
    app = web.Application(middlewares=[auth], client_max_size=2 * 1024 * 1024)
    app["engine"] = engine
    p = VERSION_PREFIX
    app.add_routes([
        web.get(f"{p}/health", health), web.get(f"{p}/languages", languages), web.get(f"{p}/catalog", catalog),
        web.get(f"{p}/config", get_config), web.put(f"{p}/config", put_config), web.post(f"{p}/config/validate", validate_config),
        web.get(f"{p}/warnings", warnings), web.get(f"{p}/sources", sources), web.get(f"{p}/resolved", resolved),
        web.get(f"{p}/events", events), web.get(f"{p}/clips/{{rel:.+}}", clip), web.get(f"{p}/ws", ws),
    ])
    return app
