"""WebSocket commands used by the sound recognition panel. Admin only; they relay to the service, whose token never reaches the browser."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import devices as dev, structure_link
from .api import InvalidConfig, SoundRecError
from .const import DOMAIN, SIGNAL_LIVE
from .go2rtc import CONF_GO2RTC_URL, Go2RtcError, fetch_streams, normalize_url

ENTRY = {vol.Optional("entry_id"): str}


def _entry(hass: HomeAssistant, entry_id: str | None):
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if hasattr(e, "runtime_data")]
    if entry_id:
        entries = [e for e in entries if e.entry_id == entry_id]
    return entries[0] if entries else None


def _with_entry(func):
    """Resolves the config entry (first loaded one by default) and turns service errors into WebSocket errors."""
    async def wrapper(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
        entry = _entry(hass, msg.get("entry_id"))
        if entry is None:
            connection.send_error(msg["id"], "not_loaded", "Sound Recognition is not set up or not loaded")
            return
        try:
            await func(hass, connection, msg, entry)
        except InvalidConfig as err:
            connection.send_error(msg["id"], "invalid_config", "; ".join(err.errors))
        except SoundRecError as err:
            connection.send_error(msg["id"], "service_error", str(err))
    return wrapper


def _lang(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> str:
    return msg.get("language") or hass.config.language


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/overview", **ENTRY, vol.Optional("language"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_overview(hass, connection, msg, entry):
    """Everything the live view needs in one call."""
    client, lang = entry.runtime_data.client, _lang(hass, connection, msg)
    connection.send_result(msg["id"], {
        "entry_id": entry.entry_id,
        "entries": [{"entry_id": e.entry_id, "title": e.title} for e in hass.config_entries.async_entries(DOMAIN)],
        "version": entry.runtime_data.coordinator.version,
        "language": lang,
        "sources": await client.sources(),
        "warnings": await client.warnings(lang),
        "config": await client.get_config(),
    })


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/update", **ENTRY, vol.Optional("refresh"): bool})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_update(hass, connection, msg, entry):
    """Installed and latest service release, and the progress of an update (the panel polls this while one runs)."""
    up = entry.runtime_data.coordinator.updates
    if msg.get("refresh"):
        await up.async_check(force=True)
    if up.installing:
        try:
            up.status = await entry.runtime_data.client.update_status()
        except SoundRecError:
            pass                                            # restarting
    connection.send_result(msg["id"], up.summary())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/update_install", **ENTRY})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_update_install(hass, connection, msg, entry):
    up = entry.runtime_data.coordinator.updates
    try:
        await up.async_start()
    except SoundRecError as err:
        connection.send_error(msg["id"], "update_failed", str(err))
        return
    connection.send_result(msg["id"], up.summary())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/catalog", **ENTRY, vol.Optional("language"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_catalog(hass, connection, msg, entry):
    connection.send_result(msg["id"], await entry.runtime_data.client.catalog(_lang(hass, connection, msg)))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/warnings", **ENTRY, vol.Optional("language"): str,
                                  vol.Optional("overrides", default=True): bool})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_warnings(hass, connection, msg, entry):
    connection.send_result(msg["id"], {"warnings": await entry.runtime_data.client.warnings(_lang(hass, connection, msg), msg["overrides"])})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/config", **ENTRY})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_config(hass, connection, msg, entry):
    connection.send_result(msg["id"], await entry.runtime_data.client.get_config())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/config_validate", **ENTRY, vol.Optional("language"): str,
                                  vol.Required("config"): dict})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_config_validate(hass, connection, msg, entry):
    connection.send_result(msg["id"], await entry.runtime_data.client.validate_config(msg["config"], _lang(hass, connection, msg)))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/config_save", **ENTRY, vol.Optional("language"): str,
                                  vol.Required("config"): dict})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_config_save(hass, connection, msg, entry):
    """Saves the configuration in the service; the integration reloads so entities follow the sources and classes."""
    result = await entry.runtime_data.client.put_config(msg["config"], _lang(hass, connection, msg))
    hass.config_entries.async_schedule_reload(entry.entry_id)
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/resolved", **ENTRY, vol.Required("source"): str, vol.Required("mid"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_resolved(hass, connection, msg, entry):
    connection.send_result(msg["id"], await entry.runtime_data.client.resolved(msg["source"], msg["mid"]))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/events", **ENTRY, vol.Optional("language"): str,
                                  vol.Optional("source"): str, vol.Optional("mid"): str, vol.Optional("since"): vol.Coerce(float),
                                  vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=1000))})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_events(hass, connection, msg, entry):
    from . import signed_clip_url  # noqa: PLC0415 - circular at import time
    rows = await entry.runtime_data.client.events(
        _lang(hass, connection, msg), source=msg.get("source"), mid=msg.get("mid"), since=msg.get("since"), limit=msg["limit"])
    for r in rows:
        if r.get("clip"):
            r["clip_url"] = signed_clip_url(hass, entry.entry_id, r["clip"])
    connection.send_result(msg["id"], {"events": rows})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/recommendations", **ENTRY, vol.Optional("language"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_recommendations(hass, connection, msg, entry):
    lang = _lang(hass, connection, msg)
    rows = await entry.runtime_data.client.recommendations(lang)
    cfg = entry.runtime_data.coordinator.service_config
    hs = await structure_link.status(hass)
    _, origin = await structure_link.effective_links(hass, cfg)
    connection.send_result(msg["id"], {"recommendations": rows + dev.recommendations(hass, cfg, lang, hs, origin == "home_structure")})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/areas"})
@websocket_api.require_admin
@callback
def ws_areas(hass, connection, msg):
    connection.send_result(msg["id"], {"areas": dev.areas(hass)})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/openings"})
@websocket_api.require_admin
@callback
def ws_openings(hass, connection, msg):
    connection.send_result(msg["id"], {"openings": dev.openings(hass)})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/devices", vol.Required("area_id"): str,
                                  vol.Optional("links"): list, **ENTRY})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_devices(hass, connection, msg, entry):
    """Devices of a room and of the rooms connected to it: through Home Structure when it describes the home, else through the
    connections configured here (those being edited in the panel when it sends them)."""
    links = msg.get("links")
    if links is None:
        links, _ = await structure_link.effective_links(hass, entry.runtime_data.coordinator.service_config)
    names = {a["area_id"]: a["name"] for a in dev.areas(hass)}
    rows = []
    for area in sorted(dev.reachable_areas(msg["area_id"], links)):
        rows += [{**d, "area_id": area, "area": names.get(area, area)} for d in dev.discover(hass, area)]
    connection.send_result(msg["id"], {"devices": rows})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/structure", **ENTRY})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_structure(hass, connection, msg, entry):
    """Where the description of the home comes from: Home Structure (state, links as read) or the connections configured here."""
    status = await structure_link.status(hass)
    cfg = entry.runtime_data.coordinator.service_config
    links, origin = await structure_link.effective_links(hass, cfg)
    plan = structure_link.plan_from_structure(await structure_link.structure(hass)) if origin == "home_structure" else None
    names = {a["area_id"]: a["name"] for a in dev.areas(hass)}
    states = {l["sensor"]: s.state for l in links if l.get("sensor") and (s := hass.states.get(l["sensor"]))}
    rows = [{"a": l["a"], "b": l["b"], "a_name": names.get(l["a"], l["a"]), "b_name": names.get(l["b"], l["b"]), "type": dev.link_type(l),
             "sensor": l.get("sensor"), "state": dev.link_state(l, states), "shutter_state": l.get("shutter_state")} for l in links] if origin == "home_structure" else []
    connection.send_result(msg["id"], {"status": status, "origin": origin, "links": rows, "plan": plan, "url": structure_link.HS_URL})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/import_structure", **ENTRY})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_import_structure(hass, connection, msg, entry):
    """Copies the connections configured here into Home Structure."""
    links = list(entry.runtime_data.coordinator.service_config.get("area_links") or [])
    connection.send_result(msg["id"], {"added": await structure_link.import_links(hass, links)})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/stats", **ENTRY,
                                  vol.Optional("hours", default=24): vol.All(int, vol.Range(min=1, max=720))})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_stats(hass, connection, msg, entry):
    connection.send_result(msg["id"], await entry.runtime_data.client.stats(msg["hours"]))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/event_feedback", **ENTRY, vol.Required("event_id"): str,
                                  vol.Required("false"): bool})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_event_feedback(hass, connection, msg, entry):
    """Marks a detection as false (or clears the mark); the recommendations use it to propose a higher threshold."""
    connection.send_result(msg["id"], await entry.runtime_data.client.event_feedback(msg["event_id"], msg["false"]))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe", **ENTRY, vol.Optional("language"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_subscribe(hass, connection, msg, entry):
    """Live stream of the service messages (status, active classes, detections, clips)."""
    from . import signed_clip_url  # noqa: PLC0415
    names = entry.runtime_data.coordinator.index.get("by_mid", {})

    @callback
    def forward(message: dict) -> None:
        out = dict(message)
        if out.get("type") == "clip_ready":
            out["clip_url"] = signed_clip_url(hass, entry.entry_id, out["clip"])
        if out.get("mid") and not out.get("name") and out["mid"] in names:
            out["name"] = names[out["mid"]]["name"]
        connection.send_message(websocket_api.event_message(msg["id"], out))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_LIVE.format(entry.entry_id), forward)
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/go2rtc_streams", **ENTRY, vol.Optional("url"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_with_entry
async def ws_go2rtc_streams(hass, connection, msg, entry):
    """Streams of the go2rtc server. With `url`, tries that address and remembers it when it answers."""
    try:
        base = normalize_url(msg["url"]) if msg.get("url") is not None else (entry.options.get(CONF_GO2RTC_URL) or "")
    except Go2RtcError as err:
        connection.send_error(msg["id"], "go2rtc_invalid", str(err))
        return
    if not base:
        connection.send_result(msg["id"], {"configured": False, "url": "", "streams": []})
        return
    try:
        streams = await fetch_streams(async_get_clientsession(hass), base)
    except Go2RtcError as err:
        connection.send_error(msg["id"], "go2rtc_unreachable", f"{base}: {err}")
        return
    if msg.get("url") is not None and entry.options.get(CONF_GO2RTC_URL) != base:
        hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_GO2RTC_URL: base})
    connection.send_result(msg["id"], {"configured": True, "url": base, "streams": streams})


COMMANDS = (ws_go2rtc_streams, ws_overview, ws_update, ws_update_install, ws_catalog, ws_warnings, ws_config, ws_config_validate, ws_config_save, ws_resolved, ws_events, ws_recommendations, ws_areas, ws_openings, ws_devices, ws_structure, ws_import_structure, ws_stats, ws_event_feedback, ws_subscribe)


def async_register(hass: HomeAssistant) -> None:
    for command in COMMANDS:
        websocket_api.async_register_command(hass, command)
