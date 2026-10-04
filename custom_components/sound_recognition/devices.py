"""Rooms and devices: which appliances make sound near a source, how much each raises its thresholds, and how rooms share sound.

The service only receives the result (one number per source, with the reasons). Everything here is about Home Assistant: the area,
device and entity registries and the states. The functions without a `hass` argument are pure so they can be tested directly."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

AUTO_DOMAINS = ("media_player", "vacuum")                         # found by themselves in the area of a source
MANUAL_DOMAINS = AUTO_DOMAINS + ("switch", "fan", "binary_sensor")  # can be added by hand
MEDIA_ACTIVE = {"playing", "on", "buffering"}
OPENING_CLASSES = {"door", "window", "opening", "garage_door"}
DEFAULT_MAX_OFFSET = 0.15
OPEN_FACTOR, CLOSED_FACTOR = 0.7, 0.15                            # share of the sound that goes through an open / closed door
SHOWN = 8


# ---------------------------------------------------------------------------------------------------- pure
def contribution(domain: str, state: str | None, attrs: dict[str, Any], max_offset: float) -> float:
    """Threshold increase caused by one device, between 0 and max_offset (0 when it makes no sound)."""
    if state is None:
        return 0.0
    if domain == "media_player":
        if state not in MEDIA_ACTIVE or attrs.get("is_volume_muted"):
            return 0.0
        vol = attrs.get("volume_level")
        frac = 0.5 + 0.5 * min(1.0, max(0.0, float(vol))) if isinstance(vol, (int, float)) else 0.6
        return round(max_offset * frac, 3)
    if domain == "vacuum":
        return round(max_offset * 0.8, 3) if state == "cleaning" else 0.0
    if domain in ("switch", "fan", "binary_sensor"):
        return round(max_offset * 0.6, 3) if state == "on" else 0.0
    return 0.0


def edge_factor(link: dict, states: dict[str, str]) -> float:
    """Share of the sound that passes between two linked areas now."""
    if link.get("type") != "door":
        return 1.0
    open_f, closed_f = link.get("open_factor", OPEN_FACTOR), link.get("closed_factor", CLOSED_FACTOR)
    state = states.get(link.get("sensor") or "")
    if state == "on":                                              # a door or window sensor reads "on" when open
        return open_f
    if state == "off":
        return closed_f
    return (open_f + closed_f) / 2                                 # no sensor, or it does not answer


def coupling(a: str | None, b: str | None, links: list[dict], states: dict[str, str]) -> float:
    """How much of the sound of area b reaches area a: 1 inside an area, through up to two links otherwise (factors multiply)."""
    if a is None or b is None or a == b:
        return 1.0
    edges: dict[str, dict[str, float]] = {}
    for link in links:
        f = edge_factor(link, states)
        for x, y in ((link["a"], link["b"]), (link["b"], link["a"])):
            edges.setdefault(x, {})[y] = max(f, edges.get(x, {}).get(y, 0.0))
    best = edges.get(a, {}).get(b, 0.0)
    for mid, f1 in edges.get(a, {}).items():
        if mid != b:
            best = max(best, f1 * edges.get(mid, {}).get(b, 0.0))
    return round(best, 3)


def reachable_areas(a: str | None, links: list[dict]) -> set[str]:
    """The area itself and the areas at most two links away."""
    if a is None:
        return set()
    seen = {a}
    for _ in range(2):
        for link in links:
            if link["a"] in seen or link["b"] in seen:
                seen.update((link["a"], link["b"]))
    return seen


def combine(items: list[dict]) -> tuple[float, list[str], list[dict]]:
    """The strongest cause wins: (offset, reasons, detail of the causes that count, strongest first)."""
    live = sorted((i for i in items if i["value"] > 0), key=lambda i: -i["value"])
    if not live:
        return 0.0, [], []
    return live[0]["value"], sorted({i["kind"] for i in live}), [{"label": i["label"], "value": i["value"]} for i in live[:SHOWN]]


# ---------------------------------------------------------------------------------------------------- Home Assistant side
def entity_area(hass: HomeAssistant, reg: er.RegistryEntry) -> str | None:
    if reg.area_id:
        return reg.area_id
    if reg.device_id and (dev := dr.async_get(hass).async_get(reg.device_id)):
        return dev.area_id
    return None


def _score(hass: HomeAssistant, reg: er.RegistryEntry) -> tuple:
    st = hass.states.get(reg.entity_id)
    attrs = st.attributes if st else {}
    return (st is not None and st.state not in ("unavailable", "unknown"), "volume_level" in attrs,
            attrs.get("device_class") == "tv", attrs.get("supported_features", 0) or 0)


def discover(hass: HomeAssistant, area_id: str, domains: tuple[str, ...] = AUTO_DOMAINS) -> list[dict]:
    """Entities of an area that can make sound. Several entities of one device are folded under the best one (`duplicate_of`)."""
    registry = er.async_get(hass)
    found = [r for r in registry.entities.values() if r.domain in domains and not r.disabled_by and entity_area(hass, r) == area_id]
    best: dict[str, er.RegistryEntry] = {}
    for r in found:
        key = r.device_id or r.entity_id
        if key not in best or _score(hass, r) > _score(hass, best[key]):
            best[key] = r
    out = []
    for r in sorted(found, key=lambda r: r.entity_id):
        st = hass.states.get(r.entity_id)
        keeper = best[r.device_id or r.entity_id]
        out.append({
            "entity_id": r.entity_id, "name": (st.name if st else None) or r.name or r.original_name or r.entity_id, "domain": r.domain,
            "state": st.state if st else "unavailable", "available": st is not None and st.state not in ("unavailable", "unknown"),
            "device_class": st.attributes.get("device_class") if st else None,
            "has_volume": bool(st and "volume_level" in st.attributes),
            "duplicate_of": None if keeper.entity_id == r.entity_id else keeper.entity_id,
        })
    return out


def areas(hass: HomeAssistant) -> list[dict]:
    return sorted(({"area_id": a.id, "name": a.name} for a in ar.async_get(hass).async_list_areas()), key=lambda a: a["name"].casefold())


def openings(hass: HomeAssistant) -> list[dict]:
    """Door, window and opening sensors, to describe how rooms communicate."""
    registry, out = er.async_get(hass), []
    for r in registry.entities.values():
        if r.domain != "binary_sensor" or r.disabled_by:
            continue
        st = hass.states.get(r.entity_id)
        dc = (st.attributes.get("device_class") if st else None) or r.original_device_class or r.device_class
        if dc in OPENING_CLASSES:
            out.append({"entity_id": r.entity_id, "name": (st.name if st else None) or r.name or r.original_name or r.entity_id,
                        "area_id": entity_area(hass, r), "state": st.state if st else "unavailable"})
    return sorted(out, key=lambda o: o["entity_id"])


def selected(hass: HomeAssistant, src: dict, links: list[dict]) -> list[tuple[str, str | None]]:
    """(entity id, area id) of every device that can raise the thresholds of a source: its own area and the areas linked to it,
    minus the exclusions, plus the entities added by hand (taken as being in the room of the source)."""
    cfg = src.get("devices") or {}
    own = src.get("area")
    exclude, out, seen = set(cfg.get("exclude", [])), [], set()
    for area in sorted(reachable_areas(own, links)):
        for d in discover(hass, area):
            if d["entity_id"] not in exclude and d["entity_id"] not in seen:
                seen.add(d["entity_id"])
                out.append((d["entity_id"], area))
    for eid in cfg.get("include", []):
        if eid not in exclude and eid not in seen:
            seen.add(eid)
            out.append((eid, own))
    return out


def compute(hass: HomeAssistant, cfg: dict, src: dict, statuses: dict[str, dict], inhibitors: set[str], names: dict[str, str]) -> tuple[float, list[str], list[dict]]:
    """Threshold increase for one source from the devices around it and from the context sounds heard by the sources linked to it."""
    links = cfg.get("area_links") or []
    dcfg = src.get("devices") or {}
    max_offset = dcfg.get("max_offset", DEFAULT_MAX_OFFSET)
    own = src.get("area")
    area_names = {a["area_id"]: a["name"] for a in areas(hass)}
    states = {l["sensor"]: s.state for l in links if l.get("sensor") and (s := hass.states.get(l["sensor"]))}
    items: list[dict] = []
    for eid, area in selected(hass, src, links):
        st = hass.states.get(eid)
        if st is None:
            continue
        c = coupling(own, area, links, states)
        value = round(contribution(eid.split(".")[0], st.state, st.attributes, max_offset) * c, 3)
        where = area_names.get(area or "", "")
        label = f"{st.name} · {where} · {round(c * 100)} %" if where and area != own else f"{st.name} · {round(c * 100)} %"
        items.append({"kind": "device", "label": label, "value": value})
    boost = (cfg.get("analysis") or {}).get("context_boost", 0.15)
    for other in cfg.get("sources", []):
        if other["id"] == src["id"] or not other.get("enabled", True):
            continue
        heard = [m for m in (statuses.get(other["id"]) or {}).get("active_contexts", []) if m in inhibitors]
        if not heard:
            continue
        c = coupling(own, other.get("area"), links, states) if own and other.get("area") else 0.0
        label = f"{other.get('name') or other['id']}: {', '.join(names.get(m, m) for m in heard)} · {round(c * 100)} %"
        items.append({"kind": "shared", "label": label, "value": round(boost * c, 3)})
    return combine(items)


TEXTS = {
    "en": {
        "set_area": "Assign a Home Assistant room to « {source} » so the devices around it (TV, speakers...) can be taken into account.",
        "enable_devices": "« {source} » ({area}): {devices} found in the room. Enable the device setting, so the thresholds rise while they play.",
    },
    "fr": {
        "set_area": "Attribuez une pièce Home Assistant à « {source} » pour prendre en compte les appareils qui l'entourent (TV, enceintes...).",
        "enable_devices": "« {source} » ({area}) : {devices} dans la pièce. Activez le réglage par appareils, pour que les seuils montent pendant leur lecture.",
    },
}


def recommendations(hass: HomeAssistant, cfg: dict, lang: str) -> list[dict]:
    """What only Home Assistant can see: sources without a room, and rooms with devices that could be used."""
    txt = {**TEXTS["en"], **TEXTS.get(lang, {})}
    area_names = {a["area_id"]: a["name"] for a in areas(hass)}
    out = []
    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        sid, sname = src["id"], src.get("name") or src["id"]
        area = src.get("area")
        if not area or area not in area_names:
            out.append({"rule": "set_area", "level": "info", "source": sid, "classes": [], "message": txt["set_area"].format(source=sname), "apply": None})
            continue
        if (src.get("devices") or {}).get("enabled"):
            continue
        found = [d for d in discover(hass, area) if d["available"] and not d["duplicate_of"]]
        if found:
            names = ", ".join(d["name"] for d in found[:3]) + (f" +{len(found) - 3}" if len(found) > 3 else "")
            out.append({"rule": "enable_devices", "level": "info", "source": sid, "classes": [],
                        "message": txt["enable_devices"].format(source=sname, area=area_names[area], devices=names),
                        "apply": {"source": sid, "source_patch": {"devices": {"enabled": True}}}})
    return out
