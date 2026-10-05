"""Applies a recommendation patch ({"source": id, "source_patch": {...}, "class_patch": {mid: {...}}}) to a configuration.
Same rules as the panel: the blocks of a source may be keyed by sound id or by AudioSet name; a key already used is kept."""
from __future__ import annotations

import copy
from datetime import datetime, timezone


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
    if patch.get("rule"):             # a patch that answers an advice leaves a trace on the source, so the panel can show it and undo it
        changes = {k: patch[k] for k in ("source_patch", "class_patch") if patch.get(k)}
        ident = advice_id(patch["rule"], changes)
        trace = {"rule": patch["rule"], "classes": list(patch.get("classes") or (patch.get("class_patch") or {})), "at": datetime.now(timezone.utc).isoformat(),
                 "level": patch.get("level") or "info", "message": patch.get("message") or "", "patch": changes}
        src["applied_advice"] = [a for a in src.get("applied_advice") or [] if advice_id(a.get("rule"), a.get("patch") or {}) != ident] + [trace]
    return new


def advice_id(rule: str, patch: dict) -> str:
    """Same identity as the panel: the rule and what it touches."""
    return f"{rule}|{','.join(sorted(patch.get('class_patch') or {}))}|{','.join(sorted(patch.get('source_patch') or {}))}"


# What a patch changes, in words (the confirmation of the Repairs fix). English first, French as the translation; other languages fall back to English.
_WORDS = {
    "en": {"on": "switched on", "off": "switched off", "min_duration_s": "minimum duration {v} s", "threshold": "threshold {v}",
           "cooldown_s": "cooldown {v} s", "clip_retention_days": "clip retention {v} days", "schedule": "continuous schedule"},
    "fr": {"on": "activé", "off": "désactivé", "min_duration_s": "durée minimale {v} s", "threshold": "seuil {v}",
           "cooldown_s": "délai {v} s", "clip_retention_days": "rétention des clips {v} jours", "schedule": "horaire continu"},
}


def describe_patch(patch: dict, names: dict[str, str], lang: str = "en") -> str:
    """One line per sound: `- Beep: switched off`."""
    words = _WORDS.get((lang or "en").split("-")[0], _WORDS["en"])
    lines = []
    for mid, block in (patch.get("class_patch") or {}).items():
        parts = []
        for key, value in block.items():
            if key == "enabled":
                parts.append(words["on" if value else "off"])
            elif key == "schedule":
                parts.append(words["schedule"] if (value or {}).get("mode") == "continuous" else key)
            elif key in words:
                parts.append(words[key].format(v=value))
        lines.append(f"- {names.get(mid, mid)}: {', '.join(parts)}")
    return "\n".join(lines) or "—"
