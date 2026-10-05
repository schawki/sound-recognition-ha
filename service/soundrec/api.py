"""Local HTTP + WebSocket API (aiohttp). Every route except /health needs 'Authorization: Bearer <token>'."""
import asyncio
import datetime as dt
import hmac
import json

from aiohttp import web, WSMsgType

from .updater import Updater
from . import API_LEVEL, __version__, catalog as cm, config as cfgmod, settings as st, advisor

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
    up = req.app["updater"]
    build = up.build()
    return web.json_response({"status": "ok", "version": __version__, "api_level": API_LEVEL, "commit": build.get("commit", "")[:7],
                              "release": build.get("release", ""), "update": {"capable": up.capable}})


async def update_status(req):
    return web.json_response(req.app["updater"].status())


async def update_start(req):
    """Asks the root helper to move the installation to the latest tagged release (202), if it is there (501) and idle (409)."""
    result = req.app["updater"].request()
    if result == "unavailable":
        return web.json_response({"error": "updates from Home Assistant are not enabled on this installation (see deploy/DEPLOY.md)"}, status=501)
    if result == "busy":
        return web.json_response({"error": "an update is already requested or running", **req.app["updater"].status()}, status=409)
    return web.json_response(req.app["updater"].status(), status=202)


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


async def set_external(req):
    """The integration pushes the threshold increase it computed for a source: {offset, reasons, detail, ttl_s}."""
    try:
        body = await req.json()
        offset = float(body["offset"])
        ttl = float(body.get("ttl_s", 60))
        reasons = [str(r) for r in body.get("reasons", [])][:5]
        detail = [{"label": str(d["label"])[:80], "value": float(d["value"])} for d in body.get("detail", [])][:20]
        if not 0 <= offset <= 1 or not 5 <= ttl <= 600:
            raise ValueError
    except Exception:
        return web.json_response({"error": "body must be {offset: 0..1, reasons?, detail?: [{label, value}], ttl_s?: 5..600}"}, status=400)
    if not req.app["engine"].set_external(req.match_info["sid"], offset, reasons, detail, ttl):
        return web.json_response({"error": "unknown or stopped source"}, status=404)
    return web.json_response({"ok": True})


async def recommendations(req):
    return web.json_response({"recommendations": req.app["engine"].recommendations(_lang(req))})


async def stats(req):
    try:
        hours = max(1, min(int(req.query.get("hours", 24)), 24 * 30))
    except ValueError:
        return web.json_response({"error": "hours must be a number"}, status=400)
    return web.json_response(req.app["engine"].stats(hours))


async def feedback(req):
    """Marks a detection as false (or clears the mark): {"false": true|false}."""
    try:
        body = await req.json()
        value = "false" if body["false"] is True else None
        if body["false"] not in (True, False):
            raise ValueError
    except Exception:
        return web.json_response({"error": 'body must be {"false": true|false}'}, status=400)
    if not req.app["engine"].store.set_feedback(req.match_info["id"], value):
        return web.json_response({"error": "unknown event"}, status=404)
    return web.json_response({"ok": True})


CLIP_FILTERS = {"source", "mid", "usage", "since", "until"}


def _clip_filter(eng, data):
    """Filters on clips (source, sound, usage category, period) -> keyword arguments for the store; ValueError when invalid."""
    unknown = set(data) - CLIP_FILTERS
    if unknown:
        raise ValueError(f"unknown filter: {', '.join(sorted(unknown))}")
    flt = {}
    if data.get("source"):
        flt["source"] = str(data["source"])
    mids = None
    if data.get("usage"):
        raw = cm.load_raw(eng.catalog_root)
        if data["usage"] not in raw["usages"]:
            raise ValueError(f"unknown usage '{data['usage']}'")
        mids = {c["mid"] for c in raw["classes"] if data["usage"] in c["usages"]}
    if data.get("mid"):
        mids = {str(data["mid"])} if mids is None else mids & {str(data["mid"])}
    if mids is not None:
        flt["mids"] = sorted(mids)
    for k in ("since", "until"):
        if data.get(k) not in (None, ""):
            flt[k] = float(data[k])
    return flt


def _clip_rows(eng, rows, names):
    return [dict(r, name=names.get(r["mid"], r["class"]), size=eng.clips.size(r["clip"])) for r in rows]


async def clips_list(req):
    """Clips kept, with their size: filters source, mid, usage, since, until (epoch seconds); paging with limit/offset.
    Also the total count and size of what matches, and what the clips take on disk."""
    eng = req.app["engine"]
    try:
        flt = _clip_filter(eng, {k: v for k, v in req.query.items() if k in CLIP_FILTERS})
        limit, offset = max(1, min(int(req.query.get("limit", 100)), 500)), max(0, int(req.query.get("offset", 0)))
    except ValueError as err:
        return web.json_response({"error": str(err)}, status=400)
    names = cm.class_names(_lang(req), eng.catalog_root)
    loop = asyncio.get_running_loop()

    def work():
        every = eng.store.clips(**flt)
        # the sounds to choose from: those of the selection, whatever sound is already chosen
        pool = eng.store.clips(**_clip_filter(eng, {k: v for k, v in req.query.items() if k in CLIP_FILTERS and k != "mid"}))
        counts = {}
        for r in pool:
            counts[r["mid"]] = counts.get(r["mid"], 0) + 1
        sounds = sorted(({"mid": m, "name": names.get(m, m), "count": n} for m, n in counts.items()), key=lambda x: x["name"].lower())
        return every, _clip_rows(eng, every[offset:offset + limit], names), sum(eng.clips.size(r["clip"]) for r in every), eng.clips.usage(), sounds
    every, page, total_bytes, usage, sounds = await loop.run_in_executor(None, work)
    return web.json_response({"clips": page, "total": len(every), "total_bytes": total_bytes, "disk": usage, "sounds": sounds})


async def clips_delete(req):
    """Deletes clips: {"ids": [event ids]} or {"filter": {...}} (an empty filter means every clip, referenced or not);
    "dry_run": true only counts. Detections stay in the history, only their audio goes."""
    eng = req.app["engine"]
    try:
        body = await req.json()
        dry = body.get("dry_run", False) is True
        if ("ids" in body) == ("filter" in body):
            raise ValueError("give either ids or filter")
        if "ids" in body:
            if not isinstance(body["ids"], list) or not all(isinstance(i, str) for i in body["ids"]):
                raise ValueError("ids must be a list of event ids")
            flt = None
        else:
            if not isinstance(body["filter"], dict):
                raise ValueError("filter must be an object")
            flt = _clip_filter(eng, body["filter"])
    except (ValueError, TypeError, json.JSONDecodeError) as err:
        return web.json_response({"error": str(err) or "invalid body"}, status=400)
    loop = asyncio.get_running_loop()

    def work():
        everything = flt == {}
        if everything:
            usage = eng.clips.usage()
            if dry:
                return usage["clips"], usage["bytes"]
            count, freed = eng.clips.delete_all()
            eng.store.forget_clips()
            return count, freed
        rows = eng.store.clips_by_ids(body["ids"]) if flt is None else eng.store.clips(**flt)
        freed = 0
        for r in rows:
            freed += eng.clips.size(r["clip"]) if dry else eng.clips.delete(r["clip"])
        if not dry:
            eng.store.forget_clips([r["id"] for r in rows])
        return len(rows), freed
    count, freed = await loop.run_in_executor(None, work)
    return web.json_response({"count": count, "bytes": freed, "dry_run": dry})


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


def make_app(engine, updater=None):
    app = web.Application(middlewares=[auth], client_max_size=2 * 1024 * 1024)
    app["engine"] = engine
    app["updater"] = updater or Updater.from_env()
    p = VERSION_PREFIX
    app.add_routes([
        web.get(f"{p}/health", health), web.get(f"{p}/update", update_status), web.post(f"{p}/update", update_start), web.get(f"{p}/languages", languages), web.get(f"{p}/catalog", catalog),
        web.get(f"{p}/config", get_config), web.put(f"{p}/config", put_config), web.post(f"{p}/config/validate", validate_config),
        web.get(f"{p}/warnings", warnings), web.get(f"{p}/sources", sources), web.get(f"{p}/resolved", resolved),
        web.get(f"{p}/events", events), web.get(f"{p}/recommendations", recommendations), web.put(f"{p}/sources/{{sid}}/external", set_external), web.get(f"{p}/stats", stats),
        web.post(f"{p}/events/{{id}}/feedback", feedback), web.get(f"{p}/clips", clips_list), web.post(f"{p}/clips/delete", clips_delete), web.get(f"{p}/clips/{{rel:.+}}", clip), web.get(f"{p}/ws", ws),
    ])
    return app
