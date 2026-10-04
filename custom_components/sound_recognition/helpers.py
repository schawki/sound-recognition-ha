"""Pure helpers on the service configuration and the merged catalog (no Home Assistant objects)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def build_index(catalog: dict) -> dict[str, Any]:
    by_mid = {c["mid"]: c for c in catalog["classes"]}
    by_key = {c["mid"]: c["mid"] for c in catalog["classes"]}
    by_key.update({c["audioset_name"]: c["mid"] for c in catalog["classes"]})
    return {"by_mid": by_mid, "by_key": by_key}


def norm_block(block: dict | None, idx: dict) -> dict[str, dict]:
    """Class block keyed by mid or AudioSet name -> keyed by mid (unknown keys dropped)."""
    return {idx["by_key"][k]: (v or {}) for k, v in (block or {}).items() if k in idx["by_key"]}


def enabled_mids(cfg: dict, source: dict, idx: dict) -> set[str]:
    """Classes effectively enabled on a source (ignores the source's own enabled flag)."""
    glob = norm_block(cfg.get("classes"), idx)
    over = norm_block(source.get("classes"), idx)
    out = {m for m, b in glob.items() if b.get("enabled")}
    for m, b in over.items():
        if "enabled" in b:
            (out.add if b["enabled"] else out.discard)(m)
    return out


def detected_unique_id(entry_id: str, sid: str, mid: str) -> str:
    return f"{entry_id}_{sid}_{mid.strip('/').replace('/', '_')}"


def expected_unique_ids(entry_id: str, cfg: dict, idx: dict) -> set[str]:
    """Unique ids of every entity the current configuration provides (one set per enabled source, plus the service's own)."""
    ids = {f"{entry_id}_advice", f"{entry_id}_service_update"}
    for s in cfg.get("sources", []):
        if not s.get("enabled", True):
            continue
        sid = s["id"]
        ids.update({f"{entry_id}_{sid}_connection", f"{entry_id}_{sid}_event", f"{entry_id}_{sid}_level"})
        ids.update(detected_unique_id(entry_id, sid, mid) for mid in enabled_mids(cfg, s, idx))
    return ids


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40] or "source"


def unique_id(base: str, taken: set[str]) -> str:
    cand, n = base, 2
    while cand in taken:
        cand = f"{base}_{n}"
        n += 1
    return cand


def format_warnings(warnings: list[dict], source_names: dict[str, str]) -> str:
    """Markdown list grouped by level, for flow descriptions."""
    order = ("danger", "warning", "info")
    icons = {"danger": "🛑", "warning": "⚠️", "info": "ℹ️"}
    seen, lines = set(), []
    for level in order:
        for w in warnings:
            if w["level"] != level:
                continue
            key = (w["rule"], tuple(sorted(w["classes"])), w["message"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {icons[level]} **{source_names.get(w['source'], w['source'])}**: {w['message']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------- class selection
def find_key(blocks: dict, mid: str, idx: dict) -> str | None:
    for k in blocks:
        if idx["by_key"].get(k) == mid:
            return k
    return None


def apply_selection(cfg: dict, idx: dict, sid: str | None, selected: set[str], universe: set[str]) -> None:
    """Enable exactly `selected` among `universe` (globally when sid is None, else as overrides on one source)."""
    glob = cfg.setdefault("classes", {})
    if sid is None:
        for mid in universe | set(norm_block(glob, idx)):
            key = find_key(glob, mid, idx) or mid
            blk = glob.get(key)
            if mid in selected:
                glob[key] = {**(blk or {}), "enabled": True}
            elif blk is not None:
                if set(blk) - {"enabled"}:
                    blk["enabled"] = False
                else:
                    del glob[key]
        return
    src = next(s for s in cfg["sources"] if s["id"] == sid)
    blocks = src.setdefault("classes", {})
    global_on = {m for m, b in norm_block(glob, idx).items() if b.get("enabled")}
    for mid in universe | set(norm_block(blocks, idx)):
        key = find_key(blocks, mid, idx) or mid
        blk = dict(blocks.get(key) or {})
        want = mid in selected
        if want == (mid in global_on):
            blk.pop("enabled", None)
        else:
            blk["enabled"] = want
        if blk:
            blocks[key] = blk
        else:
            blocks.pop(key, None)
    if not blocks:
        src.pop("classes")


# ---------------------------------------------------------------------------------------------------- per-class settings
NUMERIC = ("threshold", "min_duration_s", "cooldown_s", "pre_roll_s", "post_roll_s", "clip_retention_days")


def _scope_blocks(cfg: dict, sid: str | None) -> dict:
    if sid is None:
        return cfg.setdefault("classes", {})
    return next(s for s in cfg["sources"] if s["id"] == sid).setdefault("classes", {})


def class_form_defaults(cfg: dict, idx: dict, sid: str | None, mid: str) -> dict:
    sug = idx["by_mid"][mid]["suggestions"]
    glob = norm_block(cfg.get("classes"), idx).get(mid, {})
    own = norm_block(_scope_blocks(cfg, sid), idx).get(mid, {}) if sid else glob
    out = {}
    for f in NUMERIC:
        out[f] = own.get(f, glob.get(f, sug[{"threshold": "threshold", "min_duration_s": "min_duration_s", "cooldown_s": "cooldown_s",
                                              "pre_roll_s": "pre_roll_s", "post_roll_s": "post_roll_s",
                                              "clip_retention_days": "clip_retention_days"}[f]]))
    if "min_volume_dbfs" in own:
        out["min_volume_dbfs"] = own["min_volume_dbfs"]
    out["always_on"] = own.get("schedule") == {"mode": "continuous"}
    return out


def apply_class_form(cfg: dict, idx: dict, sid: str | None, mid: str, values: dict) -> None:
    c = idx["by_mid"][mid]
    sug = c["suggestions"]
    blocks = _scope_blocks(cfg, sid)
    key = find_key(blocks, mid, idx) or mid
    blk = dict(blocks.get(key) or {})
    glob = norm_block(cfg.get("classes"), idx).get(mid, {}) if sid else {}
    for f in NUMERIC:
        if f not in values or values[f] is None or (f == "clip_retention_days" and c["clip_forbidden"]):
            continue
        v = values[f]
        v = round(float(v), 3) if f == "threshold" else (int(v) if float(v).is_integer() else float(v))
        baseline = glob.get(f, sug[f])
        if f in blk or v != baseline:
            blk[f] = v
    if values.get("min_volume_dbfs") is None:
        blk.pop("min_volume_dbfs", None)
    else:
        blk["min_volume_dbfs"] = float(values["min_volume_dbfs"])
    if values.get("always_on"):
        blk["schedule"] = {"mode": "continuous"}
    elif blk.get("schedule") == {"mode": "continuous"}:
        blk.pop("schedule")
    blocks[key] = blk


# ---------------------------------------------------------------------------------------------------- sources
def source_form_defaults(src: dict | None) -> dict:
    src = src or {}
    win = ((src.get("schedule") or {}).get("windows") or [{}])[0]
    sched = src.get("schedule") or {}
    clips = src.get("clips") or {}
    out = {
        "name": src.get("name", ""), "type": src.get("type", "rtsp"), "url": src.get("url", ""), "enabled": src.get("enabled", True),
        "threshold_offset": src.get("threshold_offset", 0.0), "schedule_mode": sched.get("mode", "continuous"),
        "window_days": win.get("days") or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "window_from": win.get("from", "00:00") + ":00", "window_to": win.get("to", "23:59") + ":00",
        "clips_allowed": clips.get("allowed", True),
    }
    if "min_volume_dbfs" in src and src["min_volume_dbfs"] is not None:
        out["min_volume_dbfs"] = src["min_volume_dbfs"]
    if "max_retention_days" in clips:
        out["clips_max_days"] = clips["max_retention_days"]
    return out


def source_from_form(existing: dict | None, ui: dict, sid: str) -> dict:
    src = dict(existing or {})
    src["id"] = sid
    src.update(name=ui["name"].strip(), type=ui["type"], url=ui["url"].strip())
    if ui.get("enabled", True):
        src.pop("enabled", None)
    else:
        src["enabled"] = False
    off = round(float(ui.get("threshold_offset") or 0), 3)
    src.pop("threshold_offset", None) if off == 0 else src.__setitem__("threshold_offset", off)
    if ui.get("min_volume_dbfs") is None:
        src.pop("min_volume_dbfs", None)
    else:
        src["min_volume_dbfs"] = float(ui["min_volume_dbfs"])
    if ui.get("schedule_mode") == "scheduled":
        old = ((existing or {}).get("schedule") or {}).get("windows") or []
        first = {"days": list(ui.get("window_days") or []) or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                 "from": str(ui.get("window_from", "00:00"))[:5], "to": str(ui.get("window_to", "23:59"))[:5]}
        src["schedule"] = {"mode": "scheduled", "windows": [first] + old[1:]}
    else:
        src["schedule"] = {"mode": "continuous"}
    clips: dict = {}
    if not ui.get("clips_allowed", True):
        clips["allowed"] = False
    if ui.get("clips_max_days") is not None:
        clips["max_retention_days"] = int(ui["clips_max_days"])
    src.pop("clips", None) if not clips else src.__setitem__("clips", clips)
    return src
