"""Link with the Home Structure integration (https://github.com/schawki/ha-home-structure), which describes the home: adjacent spaces,
what separates them, the opening sensors and the type of each room. Sound Recognition reads it and describes no rooms of its own.

The two only talk through Home Structure's public service `home_structure.get_structure` and the entities it creates; nothing is imported."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_custom_components

from . import devices

_LOGGER = logging.getLogger(__name__)
HS_DOMAIN, HS_SERVICE = "home_structure", "get_structure"
HS_URL = "https://github.com/schawki/ha-home-structure"
NOT_INSTALLED, NOT_CONFIGURED, READY = "not_installed", "not_configured", "ready"


def links_from_structure(structure: dict) -> list[dict]:
    """The links between rooms (Home Assistant areas) of a structure returned by Home Structure, in the form used here.

    Each separation becomes a link; its state is read from the Home Structure entity (open, closed, partial) rather than from the raw sensor."""
    out = []
    for c in structure.get("connections", []):
        if not (c["a"].startswith("area:") and c["b"].startswith("area:")):
            continue                                                  # a street or a neighbour has no sensor of ours to take into account
        for s in c.get("separations", []):
            link = {"a": c["a"][5:], "b": c["b"][5:], "type": s["type"]}
            sensor = s.get("entity_id") or s.get("sensor")
            if sensor and s["type"] not in ("open_space", "opening", "wall"):
                link["sensor"] = sensor
            if s.get("shutter"):
                link["shutter_state"] = s.get("shutter_state") or "unknown"   # the shutter in front of this very separation
            out.append(link)
    return out


def plan_from_structure(structure: dict | None) -> dict | None:
    """The home as Home Structure draws it, to show it read-only: spaces with their position and the separations between them.

    None when there is nothing to draw (Home Structure absent, an older version that does not return positions, or an empty plan)."""
    layout = (structure or {}).get("layout") or {}
    spaces = [{"id": s["id"], "name": s["name"], "kind": s["kind"], "in_home": s["in_home"], "room_type": s.get("room_type"), "x": layout[s["id"]]["x"], "y": layout[s["id"]]["y"]}
              for s in (structure or {}).get("spaces", []) if s["id"] in layout]
    if not spaces:
        return None
    shown = {s["id"] for s in spaces}
    conns = [{"a": c["a"], "b": c["b"], "separations": [{"type": x["type"], "state": x["state"], "shutter_state": x.get("shutter_state")} for x in c["separations"]]}
             for c in structure["connections"] if c["a"] in shown and c["b"] in shown]
    return {"spaces": spaces, "connections": conns}


async def status(hass: HomeAssistant) -> str:
    entries = hass.config_entries.async_entries(HS_DOMAIN)
    if any(e.state is ConfigEntryState.LOADED for e in entries) and hass.services.has_service(HS_DOMAIN, HS_SERVICE):
        return READY
    if entries:
        return NOT_CONFIGURED                                          # set up but not running (starting, failing)
    return NOT_CONFIGURED if HS_DOMAIN in await async_get_custom_components(hass) else NOT_INSTALLED


async def structure(hass: HomeAssistant) -> dict | None:
    if await status(hass) != READY:
        return None
    try:
        return await hass.services.async_call(HS_DOMAIN, HS_SERVICE, {}, blocking=True, return_response=True)
    except Exception as err:  # noqa: BLE001 - another integration: whatever goes wrong there must not stop this one
        _LOGGER.debug("Home Structure did not answer: %s", err)
        return None


async def effective_links(hass: HomeAssistant, cfg: dict | None = None) -> tuple[list[dict], str]:
    """The links between rooms, read from Home Structure: (links, "home_structure"), or ([], "none") when it is absent or describes nothing."""
    st = await structure(hass)
    if st:
        links = links_from_structure(st)
        if links:
            return links, "home_structure"
    return [], "none"
