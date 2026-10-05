"""Applies a recommendation patch ({"source": id, "source_patch": {...}, "class_patch": {mid: {...}}}) to a configuration.
Same rules as the panel: the blocks of a source may be keyed by sound id or by AudioSet name; a key already used is kept."""
from __future__ import annotations

import copy


def apply_patch(cfg: dict, patch: dict, audio_names: dict[str, str] | None = None) -> dict:
    new = copy.deepcopy(cfg)
    src = next((s for s in new.get("sources", []) if s.get("id") == patch.get("source")), None)
    if src is None:
        return new
    for key, value in (patch.get("source_patch") or {}).items():
        cur = src.get(key)
        src[key] = {**cur, **value} if isinstance(value, dict) and isinstance(cur, dict) else value
    classes = dict(src.get("classes") or {})
    for mid, block in (patch.get("class_patch") or {}).items():
        name = (audio_names or {}).get(mid)
        key = next((k for k in classes if k in (mid, name)), mid)
        classes[key] = {**(classes.get(key) or {}), **block}
    if classes:
        src["classes"] = classes
    return new
