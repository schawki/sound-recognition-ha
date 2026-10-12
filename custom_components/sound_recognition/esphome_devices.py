"""Finds the ESPHome devices that run the Sound Recognition microphone component (esphome/ in the repository).

The component adds a diagnostic text sensor (Home Assistant files the text sensors of ESPHome under the `sensor` domain) whose state is "sound-recognition-stream/1 port=6055"; Home Assistant already knows
the address of every ESPHome device, so the panel can offer them with one click.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

MARK = "sound-recognition-stream/1"
CONF_IGNORED = "ignored_esp_devices"      # config entry option: ids of the devices the administrator does not want as microphones
_PORT = re.compile(r"\bport=(\d{1,5})\b")


def parse_state(state: str | None) -> int | None:
    """Port announced by the device, or None when this is not a Sound Recognition stream."""
    if not state or not state.startswith(MARK):
        return None
    m = _PORT.search(state)
    port = int(m.group(1)) if m else 6055
    return port if 0 < port < 65536 else None


def find_devices(hass: HomeAssistant) -> list[dict[str, Any]]:
    entities, devices = er.async_get(hass), dr.async_get(hass)
    found: dict[str, dict[str, Any]] = {}
    for entry in entities.entities.values():
        if entry.platform != "esphome" or entry.domain != "sensor" or entry.disabled:
            continue
        st = hass.states.get(entry.entity_id)
        port = parse_state(st.state if st else None)
        if port is None:
            continue
        device = devices.async_get(entry.device_id) if entry.device_id else None
        config_entry = hass.config_entries.async_get_entry(entry.config_entry_id) if entry.config_entry_id else None
        host = (config_entry.data.get("host") if config_entry else None) or ""
        if not host:
            continue
        host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        key = entry.device_id or entry.entity_id
        found[key] = {
            "id": entry.device_id or "url-" + hashlib.sha1(f"{host}:{port}".encode()).hexdigest()[:10],   # stable, safe in an issue id
            "device_id": entry.device_id or "",
            "name": (device.name_by_user or device.name) if device else entry.entity_id,
            "host": host,
            "port": port,
            "url": f"tcp://{host}:{port}",
            "area_id": entry.area_id or (device.area_id if device else None) or "",
        }
    return sorted(found.values(), key=lambda d: d["name"].lower())


def host_of(url: str | None) -> str:
    """Host of a `tcp://host:port` address, lower case and without the IPv6 brackets; empty when there is none."""
    m = re.match(r"^\w+://(\[[^\]]+\]|[^/:]+)", (url or "").strip())
    return m.group(1).strip("[]").lower() if m else ""


def annotate(devices: list[dict[str, Any]], cfg: dict, ignored: set[str]) -> list[dict[str, Any]]:
    """The devices with `added` (a source of the configuration already uses this address) and `ignored` (the administrator said no)."""
    used = {host_of(s.get("url")) for s in cfg.get("sources", []) if s.get("type") == "esphome"}
    return [{**d, "added": host_of(d["url"]) in used, "ignored": d["id"] in ignored} for d in devices]


def pending(devices: list[dict[str, Any]], cfg: dict, ignored: set[str]) -> list[dict[str, Any]]:
    """The devices that could be added as a microphone and are not yet: not a source, not ignored."""
    return [d for d in annotate(devices, cfg, ignored) if not d["added"] and not d["ignored"]]


def area_name(hass: HomeAssistant, area_id: str) -> str:
    from homeassistant.helpers import area_registry as ar
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    return area.name if area else ""
