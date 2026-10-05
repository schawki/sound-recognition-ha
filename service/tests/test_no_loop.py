"""Applying the gestures of the advice, one after the other, always ends: no advice undoes what another one asks for.
Starts from the sounds of each catalog rule (and of pairs of rules), follows either the first or the last gesture on offer, and includes
the recommendations of the home that switch contexts on (the home rules of the integration)."""
import copy
import itertools
import pathlib

import yaml

from soundrec import advisor, catalog as cm, config as cfgmod

HOME_RULES = pathlib.Path(__file__).parent.parent.parent / "custom_components" / "sound_recognition" / "home_rules.yaml"
CONTEXTS = [r["contexts"] for r in yaml.safe_load(HOME_RULES.read_text(encoding="utf-8")).get("rules", []) if r.get("contexts")]


def _cfg(classes):
    cfg = copy.deepcopy(cfgmod.DEFAULTS)
    cfg["sources"] = [{"id": "a", "type": "rtsp", "url": "rtsp://x", "name": "A", "classes": {m: {"enabled": True} for m in classes}}]
    return cfg


def _apply(cfg, patch):
    cfg = copy.deepcopy(cfg)
    for mid, block in patch["class_patch"].items():
        cfg["sources"][0].setdefault("classes", {}).setdefault(mid, {}).update(block)
    return cfg


def _state(cfg):
    return repr(sorted((m, sorted(b.items())) for m, b in cfg["sources"][0].get("classes", {}).items()))


def _gestures(cfg):
    out = []
    for w in advisor.compute(cfg):
        if w["source"] != "a" or w["applied"]:
            continue
        if w.get("apply"):
            out.append((w["rule"], w["apply"]))
        else:
            out += [(f"{w['rule']}/{c['keep']}", c["apply"]) for c in w.get("choices", [])]
    on = {m for m, b in cfg["sources"][0].get("classes", {}).items() if b.get("enabled")}
    for ctx in CONTEXTS:                                              # the home asks for its contexts to be switched on
        missing = [m for m in ctx if m not in on]
        if missing:
            out.append(("home", {"class_patch": {m: {"enabled": True} for m in missing}}))
    return out


def test_following_the_advice_always_ends():
    rules = cm.load_raw()["rules"]
    starts = [r["classes"] for r in rules] + [a["classes"] + b["classes"] for a, b in itertools.combinations(rules, 2)]
    loops = []
    for classes in starts:
        for pick in (0, -1):
            cfg = _cfg(classes)
            seen, trail = {_state(cfg)}, []
            for _ in range(25):
                gestures = _gestures(cfg)
                if not gestures:
                    break
                name, patch = gestures[pick]
                trail.append(name)
                cfg = _apply(cfg, patch)
                if _state(cfg) in seen:
                    loops.append(trail)
                    break
                seen.add(_state(cfg))
    assert not loops, loops[:3]
