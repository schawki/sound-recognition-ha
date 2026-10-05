"""Warnings about the selected classes: close classes, risky combinations, per-source settings."""
from . import catalog as cat_mod
from . import settings as st
from .config import advice_entry


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def _fmt(text, **kw):
    return (text or "").format_map(_Safe(**kw))


def _apply_overrides(cfg, catalog, out):
    """Apply `advice` overrides (source level wins over global). `ignore` on a safety warning needs confirm: true."""
    srcs = {s["id"]: s for s in cfg.get("sources", [])}
    final = []
    for w in out:
        w["safety"] = any(st.is_safety(catalog.get(m)) for m in w["classes"])
        entry = (srcs[w["source"]].get("advice") or {}).get(w["rule"])
        if entry is None:
            entry = (cfg.get("advice") or {}).get(w["rule"])
        lvl, confirm = advice_entry(entry)
        if lvl in (None, "default"):
            final.append(w)
        elif lvl == "ignore":
            if w["safety"] and not confirm:
                final.append(w)  # protected: a safety warning is only hidden when explicitly confirmed
            continue
        else:
            w["level"] = lvl
            final.append(w)
    return final


def compute(cfg, lang="en", root=None, overrides=True):
    """List of warnings: {rule, kind, level, source, classes (mids), safety, message}."""
    merged = cat_mod.load_lang(lang, root)
    raw = cat_mod.load_raw(root)
    catalog = st.Catalog(raw)
    by = {c["mid"]: c for c in merged["classes"]}
    rules = {r["id"]: r for r in merged["rules"]}
    autos = {r["id"]: r for r in merged["auto_rules"]}
    out = []
    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        sid = src["id"]
        sname = src.get("name") or sid
        res = {}
        for mid in by:
            r = st.resolve(cfg, catalog, sid, mid)
            if r["enabled"]:
                res[mid] = r
        enabled = set(res)

        def add(rule, kind, level, classes, message, fix=None):
            row = {"rule": rule, "kind": kind, "level": level, "source": sid, "classes": list(classes), "message": message,
                   "apply": None, "applied": False}
            if fix:                       # a warning that has a gesture: the patch the panel applies, and whether it is already in place
                row["apply"] = {"source": sid, "class_patch": {m: {"enabled": True} for m in fix}}
                row["applied"] = all(m in enabled for m in fix)
            out.append(row)

        # catalog groups: several members enabled on the same source
        for g in merged["groups"]:
            hit = [m for m in g["members"] if m in enabled]
            if len(hit) >= 2:
                add(g["id"], "group", "info", hit, f"{g['name']}: {g['risk']} {g['advice']}")
        # specific combination rules
        for r in rules.values():
            hit = [m for m in r["classes"] if m in enabled]
            ok = {"all": len(hit) == len(r["classes"]), "at_least_two": len(hit) >= 2, "any": len(hit) >= 1}[r["match"]]
            if ok:
                add(r["id"], "rule", r["level"], hit, r["message"], (r.get("fix") or {}).get("enable"))
        # automatic rules
        for mid in enabled:
            c, r = by[mid], res[mid]
            name = c["name"]
            for other in c["descendants"]:
                if other in enabled:
                    add("parent_child", "auto", autos["parent_child"]["level"], [mid, other],
                        _fmt(autos["parent_child"]["message"], parent=name, child=by[other]["name"]))
            if c["clip_forbidden"] and _explicit_retention(cfg, src, mid):
                add("clip_forbidden", "auto", "danger", [mid], _fmt(autos["clip_forbidden"]["message"], **{"class": name}))
            if c["false_positives"]["level"] == "high" and r["threshold"] < c["suggestions"]["threshold"]:
                add("low_threshold_high_fp", "auto", autos["low_threshold_high_fp"]["level"], [mid],
                    _fmt(autos["low_threshold_high_fp"]["message"], **{"class": name}))
            if c["role"] == "generic":
                ex = ", ".join(by[d]["name"] for d in c["descendants"][:3])
                add("generic_class", "auto", autos["generic_class"]["level"], [mid],
                    _fmt(autos["generic_class"]["message"], **{"class": name}, examples=ex))
            if c["inhibiting_contexts"] and not any(x in enabled for x in c["inhibiting_contexts"]):
                add("missing_context", "auto", autos["missing_context"]["level"], [mid],
                    _fmt(autos["missing_context"]["message"], **{"class": name}))
    # per-source settings rules (schedule gaps, volume gate, clips)
    srcname = {s["id"]: (s.get("name") or s["id"]) for s in cfg.get("sources", [])}
    for rule, sid, cname, params in st.warnings(cfg, catalog):
        c = catalog.get(cname)
        a = autos[rule]
        out.append({"rule": rule, "kind": "auto", "level": a["level"], "source": sid, "classes": [c["mid"]],
                    "message": _fmt(a["message"], **{"class": by[c["mid"]]["name"]}, source=srcname[sid], **params), "apply": None, "applied": False})
    return _apply_overrides(cfg, catalog, out) if overrides else _apply_overrides({**cfg, "advice": {}, "sources": [{**s, "advice": {}} for s in cfg.get("sources", [])]}, catalog, out)


def _explicit_retention(cfg, src, mid):
    """True if the user explicitly asked to keep clips of a class whose catalog forbids it (the service forces 0 anyway)."""
    catalog = st.Catalog(cat_mod.load_raw())
    for blk in ((src.get("classes") or {}), (cfg.get("classes") or {})):
        for k, v in blk.items():
            if catalog.get(k)["mid"] == mid and (v or {}).get("clip_retention_days", 0) > 0:
                return True
    return False
