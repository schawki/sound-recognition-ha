"""Loads the language-neutral catalog and merges it with a language file (fallback: lang -> en -> AudioSet name)."""
import os
import threading
import yaml

_lock = threading.Lock()
_cache = {}


def default_root():
    return os.environ.get("SOUNDREC_CATALOG") or os.path.join(os.path.dirname(__file__), "..", "..", "catalog")


def _y(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_raw(root=None):
    root = os.path.abspath(root or default_root())
    with _lock:
        if ("raw", root) not in _cache:
            _cache[("raw", root)] = _y(os.path.join(root, "catalog.yaml"))
        return _cache[("raw", root)]


def available_languages(root=None):
    root = os.path.abspath(root or default_root())
    d = os.path.join(root, "i18n")
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".yaml"))


def _lang_file(root, lang):
    key = ("lang", root, lang)
    with _lock:
        if key not in _cache:
            p = os.path.join(root, "i18n", f"{lang}.yaml")
            _cache[key] = _y(p) if os.path.exists(p) else {}
        return _cache[key]


def load_lang(lang, root=None):
    """Merged catalog for one language (JSON-serialisable)."""
    root = os.path.abspath(root or default_root())
    key = ("merged", root, lang)
    with _lock:
        if key in _cache:
            return _cache[key]
    cat = load_raw(root)
    fb = _lang_file(root, "en")
    L = _lang_file(root, lang)

    def g(sec, k, default=None):
        return (L.get(sec) or {}).get(k) or (fb.get(sec) or {}).get(k) or default

    out = {"language": lang if L else "en", "meta": cat["meta"], "enums": cat["enums"]}
    out["categories"] = {k: g("categories", k, k) for k in cat["categories"]}
    out["usages"] = {k: g("usages", k, k) for k in cat["usages"]}
    out["causes"] = {k: g("causes", k, k) for k in cat["causes"]}
    out["enum_help"] = {e: {v: (L.get("enum_help") or {}).get(e, {}).get(v) or fb["enum_help"][e][v] for v in vals}
                        for e, vals in cat["enums"].items() if e in fb["enum_help"]}
    out["setting_help"] = {k: (L.get("setting_help") or {}).get(k) or v for k, v in fb["setting_help"].items()}
    out["groups"] = [dict(id=x["id"], members=x["members"],
                          **{k: g("groups", x["id"], {}).get(k) for k in ("name", "risk", "advice")}) for x in cat["groups"]]
    out["rules"] = [dict(x, message=g("rules", x["id"])) for x in cat["rules"]]
    out["auto_rules"] = [dict(x, **{k: g("auto_rules", x["id"], {}).get(k) for k in ("condition", "message")})
                         for x in cat["auto_rules"]]
    classes = []
    for c in cat["classes"]:
        d = dict(c)
        d["name"] = g("classes", c["mid"], c["audioset_name"])
        d["note_text"] = g("notes", c["note"]) if c["note"] else None
        d["false_positives"] = dict(c["false_positives"], cause_labels=[out["causes"][x] for x in c["false_positives"]["causes"]])
        classes.append(d)
    out["classes"] = classes
    with _lock:
        _cache[key] = out
    return out


def class_names(lang, root=None):
    return {c["mid"]: c["name"] for c in load_lang(lang, root)["classes"]}
