"""Link with the Home Structure integration (https://github.com/schawki/ha-home-structure), which describes the home: adjacent spaces,
what separates them and the opening sensors. Sound Recognition reads it when it is there and keeps its own, simpler description when not.

The two only talk through Home Structure's public service `home_structure.get_structure` and the entities it creates; nothing is imported."""
from __future__ import annotations

import copy
import logging
import uuid

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
            out.append(link)
    return out


def merge_links(options: dict, links: list[dict], area_ids: set[str]) -> tuple[dict, int]:
    """Home Structure options with our links added (a pair already there gets the missing separations). Returns (options, separations added)."""
    new = copy.deepcopy({"zones": [], "connections": [], **options})
    added = 0
    for l in links:
        if l["a"] not in area_ids or l["b"] not in area_ids or l["a"] == l["b"]:
            continue
        a, b, kind = f"area:{l['a']}", f"area:{l['b']}", devices.link_type(l)
        conn = next((c for c in new["connections"] if {c["a"], c["b"]} == {a, b}), None)
        if conn is None:
            conn = {"id": uuid.uuid4().hex[:8], "a": a, "b": b, "separations": []}
            new["connections"].append(conn)
        sensor = None if kind in ("open_space", "opening", "wall") else l.get("sensor")
        if any(s["type"] == kind and s.get("sensor") == sensor for s in conn["separations"]):
            continue
        sep = {"id": uuid.uuid4().hex[:8], "type": kind}
        if sensor:
            sep["sensor"] = sensor
        conn["separations"].append(sep)
        added += 1
    return new, added


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


async def effective_links(hass: HomeAssistant, cfg: dict) -> tuple[list[dict], str]:
    """The links to use: those of Home Structure when it is ready and describes something, else the ones configured here."""
    st = await structure(hass)
    if st:
        links = links_from_structure(st)
        if links:
            return links, "home_structure"
    return list(cfg.get("area_links") or []), "internal"


async def import_links(hass: HomeAssistant, links: list[dict]) -> int:
    """Copies the links configured here into Home Structure (which must be ready) and reloads it. Returns the separations added."""
    entry = next((e for e in hass.config_entries.async_entries(HS_DOMAIN) if e.state is ConfigEntryState.LOADED), None)
    if entry is None:
        return 0
    new, added = merge_links(entry.options, links, {a["area_id"] for a in devices.areas(hass)})
    if added:
        hass.config_entries.async_update_entry(entry, options=new)
        await hass.config_entries.async_reload(entry.entry_id)
    return added
