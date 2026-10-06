"""Finds the ESPHome devices that run the Sound Recognition microphone component (esphome/ in the repository).

The component adds a diagnostic text sensor whose state is "sound-recognition-stream/1 port=6055"; Home Assistant already knows
the address of every ESPHome device, so the panel can offer them with one click.
"""
from __future__ import annotations

import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

MARK = "sound-recognition-stream/1"
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
        if entry.platform != "esphome" or entry.domain != "text_sensor" or entry.disabled:
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
            "device_id": entry.device_id or "",
            "name": (device.name_by_user or device.name) if device else entry.entity_id,
            "host": host,
            "port": port,
            "url": f"tcp://{host}:{port}",
            "area_id": entry.area_id or (device.area_id if device else None) or "",
        }
    return sorted(found.values(), key=lambda d: d["name"].lower())
