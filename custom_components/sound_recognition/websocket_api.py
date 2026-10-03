"""WebSocket commands used by the sound recognition panel. Admin only; they relay to the service, whose token never reaches the browser."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .api import InvalidConfig, SoundRecError
from .const import DOMAIN, SIGNAL_LIVE

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


COMMANDS = (ws_overview, ws_catalog, ws_warnings, ws_config, ws_config_validate, ws_config_save, ws_resolved, ws_events, ws_subscribe)


def async_register(hass: HomeAssistant) -> None:
    for command in COMMANDS:
        websocket_api.async_register_command(hass, command)
