"""Recommendations drawn from the description of the home kept by Home Structure: the place of a source from the type of its room,
and what to enable when its room is linked to a street, a garden, a living room... The rules are data (home_rules.yaml)."""
from __future__ import annotations

import os

import yaml

_RULES_FILE = os.path.join(os.path.dirname(__file__), "home_rules.yaml")
_cache: dict | None = None


def load_rules() -> dict:
    """Blocking read of the data file: call it in an executor (or at startup)."""
    global _cache
    if _cache is None:
        with open(_RULES_FILE, encoding="utf-8") as f:
            _cache = yaml.safe_load(f)
    return _cache


def _kind_of(space: dict) -> str | None:
    """Type of a room, or kind of an outside / shared space, as chosen in Home Structure (None when nothing was chosen)."""
    return space.get("room_type") if space.get("kind") == "room" else space.get("kind")


def _label(rules: dict, lang: str, space: dict) -> str:
    txt = {**rules["texts"]["en"], **rules["texts"].get(lang, {})}
    key = _kind_of(space)
    table = txt["room_types"] if space.get("kind") == "room" else txt["kinds"]
    return table.get(key, key or "")


def space_label(rules: dict, lang: str, space: dict) -> str:
    """Name of the type of a space in the language asked (empty when none was chosen)."""
    return _label(rules, lang, space)


def place_for(rules: dict, space: dict) -> str | None:
    return rules["places"].get(_kind_of(space) or "")


def _enabled(cfg: dict, src: dict, mid: str) -> bool:
    for block in (src.get("classes") or {}, cfg.get("classes") or {}):
        if (block.get(mid) or {}).get("enabled") is True:
            return True
    return False


def neighbours(structure: dict, space_id: str, blocking=("wall",)) -> list[tuple[dict, list[str]]]:
    """Spaces linked to `space_id` by at least one separation that is not a wall, with the types of those separations."""
    spaces = {s["id"]: s for s in structure.get("spaces", [])}
    out = []
    for c in structure.get("connections", []):
        if space_id not in (c["a"], c["b"]):
            continue
        other = spaces.get(c["b"] if c["a"] == space_id else c["a"])
        seps = [x["type"] for x in c.get("separations", []) if x["type"] not in blocking]
        if other and seps:
            out.append((other, seps))
    return out


def places_for(cfg: dict, structure: dict | None, rules: dict) -> dict[str, tuple[str | None, dict | None]]:
    """For every enabled source that has a room and names no place itself: (place deduced, the space of its room in Home Structure).
    The place is None when Home Structure gives none (no type chosen, or a type without a place); the space is None when it does not know the room."""
    spaces = {s["id"]: s for s in (structure or {}).get("spaces", [])}
    out = {}
    for src in cfg.get("sources", []):
        if not src.get("enabled", True) or src.get("environment") or not src.get("area"):
            continue
        space = spaces.get(f"area:{src['area']}")
        out[src["id"]] = (place_for(rules, space) if space else None, space)
    return out


def set_room_type_rows(cfg: dict, structure: dict | None, lang: str, rules: dict) -> list[dict]:
    """Asks to choose the type of the room in Home Structure, for the sources whose room it describes without a usable type."""
    txt = {**rules["texts"]["en"], **rules["texts"].get(lang, {})}
    out = []
    for src in cfg.get("sources", []):
        place, space = places_for(cfg, structure, rules).get(src["id"], (None, None))
        if space and not place and not _kind_of(space):
            out.append({"rule": "set_room_type", "level": "info", "source": src["id"], "classes": [],
                        "message": txt["set_room_type"].format(source=src.get("name") or src["id"], room=space["name"]), "apply": None})
    return out


def compute(cfg: dict, structure: dict | None, lang: str, rules: dict, class_names: dict[str, str] | None = None) -> list[dict]:
    """Recommendation rows (same shape as the others) for the sources whose room is described in Home Structure.

    `class_names` (catalog id -> name) come from the catalog of the service, in the language asked."""
    if not structure:
        return []
    class_names = class_names or {}
    spaces = {s["id"]: s for s in structure.get("spaces", [])}
    txt = {**rules["texts"]["en"], **rules["texts"].get(lang, {})}
    blocking = tuple(rules.get("blocking", ["wall"]))
    out = []
    for src in cfg.get("sources", []):
        area = src.get("area")
        space = spaces.get(f"area:{area}") if area and src.get("enabled", True) else None
        if not space or space.get("kind") != "room":
            continue                                                  # only a room of Home Assistant that was typed in Home Structure
        sid, sname = src["id"], src.get("name") or src["id"]
        room_label = _label(rules, lang, space) or txt["room"]
        links = neighbours(structure, space["id"], blocking)
        for rule in rules["rules"]:
            if rule.get("in") and _kind_of(space) not in rule["in"]:
                continue
            near = [o for o, _ in links if _kind_of(o) in rule["next_to"]]
            if not near:
                continue
            contexts = [m for m in rule.get("contexts", []) if not _enabled(cfg, src, m)]
            adaptive = bool(rule.get("adaptive")) and not (src.get("adaptive") or {}).get("enabled")
            if not contexts and not adaptive:
                continue
            patch: dict = {"source": sid}
            if contexts:
                patch["class_patch"] = {m: {"enabled": True} for m in contexts}
            if adaptive:
                patch["source_patch"] = {"adaptive": {"enabled": True}}
            names = ", ".join(f"{o['name']} ({_label(rules, lang, o)})" if _label(rules, lang, o) else o["name"] for o in near)
            text = rule.get(lang) or rule["en"]
            out.append({"rule": f"home_{rule['id']}", "level": "info", "source": sid, "classes": contexts,
                        "message": text.format(source=sname, room=room_label, neighbours=names, classes=", ".join(class_names.get(m, m) for m in contexts)),
                        "apply": patch})
    return out
