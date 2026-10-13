"""Pure helpers on the service configuration and the merged catalog (no Home Assistant objects)."""
from __future__ import annotations

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


# ---------------------------------------------------------------------------------------------------- class selection


# ---------------------------------------------------------------------------------------------------- per-class settings


# ---------------------------------------------------------------------------------------------------- sources


