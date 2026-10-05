"""Recommendations for the administrator: what to change on each source given the kind of place it is in and what was reported.
Each item may carry an `apply` patch ({"source": id, "source_patch": {...}, "class_patch": {mid: {...}}}) that the panel merges
into the configuration after the administrator confirms. `applied` says the patch is already in place: the item stays in the list so the
administrator sees it took effect (the panel shows « already applied » instead of the button)."""
from . import catalog as cat_mod
from . import settings as st

FALSE_MIN = 2            # false detections of one sound on one source before a threshold change is proposed
FALSE_DAYS = 14

TEXTS = {
    "en": {
        "set_environment": "Tell the panel what kind of place « {source} » is in to get recommendations for it.",
        "enable_contexts": "« {source} » ({environment}): enable {classes}. While they are heard, the thresholds of look-alike sounds are raised.",
        "enable_adaptive": "« {source} » ({environment}): enable the adaptive setting, so a noisy moment raises the thresholds for a while.",
        "raise_threshold": "« {source} »: {count} detections of « {class} » were marked false (highest score {peak}). Raise its threshold to {proposal}.",
    },
    "fr": {
        "set_environment": "Indiquez le type de pièce de « {source} » pour obtenir des recommandations adaptées.",
        "enable_contexts": "« {source} » ({environment}) : activez {classes}. Tant qu'ils sont entendus, les seuils des sons qui leur ressemblent sont relevés.",
        "enable_adaptive": "« {source} » ({environment}) : activez le réglage adaptatif, pour qu'un moment bruyant relève les seuils pendant un temps.",
        "raise_threshold": "« {source} » : {count} détections de « {class} » ont été marquées fausses (score max {peak}). Relevez son seuil à {proposal}.",
    },
}


def compute(cfg, lang="en", root=None, false_rows=(), places=None):
    merged = cat_mod.load_lang(lang, root)
    catalog = st.Catalog(cat_mod.load_raw(root))
    txt = {**TEXTS["en"], **TEXTS.get(lang, {})}
    names = {c["mid"]: c["name"] for c in merged["classes"]}
    envs = {e["id"]: e for e in merged["environments"]}
    out = []
    for src in cfg.get("sources", []):
        if not src.get("enabled", True):
            continue
        sid, sname = src["id"], src.get("name") or src["id"]

        def add(rule, level, classes, message, apply=None, applied=False, _sid=sid):
            out.append({"rule": rule, "level": level, "source": _sid, "classes": list(classes), "message": message, "apply": apply, "applied": applied})

        env = envs.get(src.get("environment") or (places or {}).get(sid))        # the configuration wins over what the integration deduced
        if env is None:
            add("set_environment", "info", [], txt["set_environment"].format(source=sname))
        else:
            missing = [m for m in env["contexts"] if not st.resolve(cfg, catalog, sid, m)["enabled"]]
            if env["contexts"]:
                add("enable_contexts", "warning", env["contexts"] if not missing else missing,
                    txt["enable_contexts"].format(source=sname, environment=env["name"],
                                                  classes=", ".join(names[m] for m in (missing or env["contexts"]))),
                    {"source": sid, "class_patch": {m: {"enabled": True} for m in (missing or env["contexts"])}}, applied=not missing)
            if env["adaptive"]:
                on = bool((src.get("adaptive") or {}).get("enabled"))
                add("enable_adaptive", "info", [], txt["enable_adaptive"].format(source=sname, environment=env["name"]),
                    {"source": sid, "source_patch": {"adaptive": {"enabled": True}}}, applied=on)
        seen = {}
        for r in false_rows:
            if r["source"] == sid:
                seen.setdefault(r["mid"], []).append(r["score"])
        for mid, scores in seen.items():
            if len(scores) < FALSE_MIN or mid not in names:
                continue
            current = st.resolve(cfg, catalog, sid, mid)["threshold"]
            proposal = min(0.95, round(max(scores) + 0.03, 2))
            add("raise_threshold", "warning", [mid],
                txt["raise_threshold"].format(source=sname, count=len(scores), peak=round(max(scores), 2), proposal=proposal, **{"class": names[mid]}),
                {"source": sid, "class_patch": {mid: {"threshold": proposal}}}, applied=proposal <= current)
    return out
