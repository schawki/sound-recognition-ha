"""Configuration file (YAML = single source of truth): load, validate, atomic save."""
import copy
import os
import re
import secrets
import tempfile
import zoneinfo
import yaml

from .settings import DAYS, Catalog

SOURCE_TYPES = ("rtsp", "go2rtc", "alsa_rpi", "esphome", "file")
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
HM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

DEFAULTS = {
    "language": "en",
    "timezone": None,
    "api": {"host": "0.0.0.0", "port": 8765, "token": None},
    "analysis": {"hop_s": 0.48, "context_boost": 0.15, "hold_s": 2.0, "safety_boost_cap": 0.05, "total_boost_cap": 0.30},
    "storage": {"clips_dir": "/data/clips", "db_path": "/data/events.sqlite", "ring_seconds": 30, "events_retention_days": 30},
    "defaults": {"min_volume_dbfs": -60, "schedule": {"mode": "continuous"}, "clips": {"allowed": True, "max_retention_days": 30}},
    "classes": {},
    "advice": {},
    "sources": [],
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    raw.pop("area_links", None)   # rooms are described by the Home Structure integration; the former built-in description is dropped
    return _merge(DEFAULTS, raw)


def save(path, cfg):
    """Atomic write (temp file + rename)."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".config-", suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, width=110)
    os.replace(tmp, path)


def ensure_token(cfg):
    if not cfg["api"].get("token"):
        cfg["api"]["token"] = secrets.token_urlsafe(24)
        return True
    return False


def _num(v, lo, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def _check_schedule(s, where, errs):
    if not isinstance(s, dict) or s.get("mode") not in ("continuous", "scheduled"):
        errs.append(f"{where}: schedule.mode must be 'continuous' or 'scheduled'")
        return
    if s["mode"] == "scheduled":
        w = s.get("windows")
        if not isinstance(w, list) or not w:
            errs.append(f"{where}: scheduled mode needs at least one window")
            return
        for i, win in enumerate(w):
            if not isinstance(win, dict) or not HM.match(str(win.get("from", ""))) or not HM.match(str(win.get("to", ""))):
                errs.append(f"{where}: window {i} needs 'from' and 'to' as HH:MM")
            for d in (win or {}).get("days") or []:
                if d not in DAYS:
                    errs.append(f"{where}: window {i} has unknown day '{d}'")


ADVICE_LEVELS = ("default", "info", "warning", "danger", "ignore")


def advice_entry(v):
    """Normalise an advice override: 'ignore' or {level: ignore, confirm: true} -> (level, confirm)."""
    if isinstance(v, str):
        return v, False
    if isinstance(v, dict):
        return v.get("level"), bool(v.get("confirm", False))
    return None, False


def _check_advice(blk, where, rule_ids, errs):
    if not isinstance(blk, dict):
        errs.append(f"{where}: must be a mapping of rule id -> level")
        return
    for rid, v in blk.items():
        lvl, _ = advice_entry(v)
        if rid not in rule_ids:
            errs.append(f"{where}: unknown advice rule '{rid}'")
        elif lvl not in ADVICE_LEVELS:
            errs.append(f"{where}.{rid}: level must be one of {', '.join(ADVICE_LEVELS)}")
        elif isinstance(v, dict) and (set(v) - {"level", "confirm"} or not isinstance(v.get("confirm", False), bool)):
            errs.append(f"{where}.{rid}: only 'level' and 'confirm' (true/false) are allowed")


def _check_devices(s, w, errs):
    """`area` (a Home Assistant area id) and `devices` are read by the integration; the service only checks their shape."""
    if "area" in s and s["area"] is not None and not isinstance(s["area"], str):
        errs.append(f"{w}.area must be text")
    if "devices" not in s:
        return
    d = s["devices"]
    if not isinstance(d, dict) or set(d) - {"enabled", "max_offset", "exclude", "include"}:
        errs.append(f"{w}.devices: only 'enabled', 'max_offset', 'exclude' and 'include' are allowed")
        return
    if not isinstance(d.get("enabled", False), bool):
        errs.append(f"{w}.devices.enabled must be true or false")
    if "max_offset" in d and not _num(d["max_offset"], 0, 0.4):
        errs.append(f"{w}.devices.max_offset must be between 0 and 0.4")
    for key in ("exclude", "include"):
        if key in d and (not isinstance(d[key], list) or not all(isinstance(x, str) and "." in x for x in d[key])):
            errs.append(f"{w}.devices.{key} must be a list of entity ids")


def advice_rule_ids(catalog):
    raw = catalog.raw
    return {x["id"] for k in ("groups", "rules", "auto_rules") for x in raw.get(k, [])}


def _check_class_block(b, where, errs):
    if not isinstance(b, dict):
        errs.append(f"{where}: must be a mapping")
        return
    rules = {"enabled": lambda v: isinstance(v, bool), "threshold": lambda v: _num(v, 0, 1),
             "min_duration_s": lambda v: _num(v, 0, 600), "cooldown_s": lambda v: _num(v, 0, 86400),
             "pre_roll_s": lambda v: _num(v, 0, 120), "post_roll_s": lambda v: _num(v, 0, 120),
             "clip_retention_days": lambda v: _num(v, 0, 3650), "min_volume_dbfs": lambda v: v is None or _num(v, -90, 0)}
    for k, v in b.items():
        if k == "schedule":
            _check_schedule(v, f"{where}.schedule", errs)
        elif k not in rules:
            errs.append(f"{where}: unknown field '{k}'")
        elif not rules[k](v):
            errs.append(f"{where}.{k}: invalid value {v!r}")


def validate(cfg, catalog: Catalog):
    """Returns a list of human-readable errors (empty = valid)."""
    errs = []
    tz = cfg.get("timezone")
    if tz:
        try:
            zoneinfo.ZoneInfo(tz)
        except Exception:
            errs.append(f"timezone: unknown zone '{tz}'")
    if not _num(cfg["analysis"].get("hop_s"), 0.1, 0.975):
        errs.append("analysis.hop_s must be between 0.1 and 0.975")
    if not _num(cfg["analysis"].get("context_boost"), 0, 1):
        errs.append("analysis.context_boost must be between 0 and 1")
    if not _num(cfg["analysis"].get("safety_boost_cap"), 0, 1):
        errs.append("analysis.safety_boost_cap must be between 0 and 1")
    if not _num(cfg["analysis"].get("total_boost_cap"), 0, 1):
        errs.append("analysis.total_boost_cap must be between 0 and 1")
    d = cfg["defaults"]
    if d.get("min_volume_dbfs") is not None and not _num(d["min_volume_dbfs"], -90, 0):
        errs.append("defaults.min_volume_dbfs must be between -90 and 0 (or null)")
    _check_schedule(d.get("schedule", {"mode": "continuous"}), "defaults.schedule", errs)
    for k, blk in (cfg.get("classes") or {}).items():
        try:
            catalog.get(k)
        except KeyError:
            errs.append(f"classes: unknown class '{k}'")
            continue
        _check_class_block(blk, f"classes.{k}", errs)
    rule_ids = advice_rule_ids(catalog)
    _check_advice(cfg.get("advice") or {}, "advice", rule_ids, errs)
    ids = set()
    for i, s in enumerate(cfg.get("sources") or []):
        sid = s.get("id", "")
        w = f"sources[{i}]({sid})"
        if not SLUG.match(str(sid)):
            errs.append(f"{w}: id must be lowercase letters, digits, '_' or '-'")
        if sid in ids:
            errs.append(f"{w}: duplicate id")
        ids.add(sid)
        if s.get("type") not in SOURCE_TYPES:
            errs.append(f"{w}: type must be one of {', '.join(SOURCE_TYPES)}")
        if not s.get("url"):
            errs.append(f"{w}: url is required")
        if "threshold_offset" in s and not _num(s["threshold_offset"], -1, 1):
            errs.append(f"{w}.threshold_offset must be between -1 and 1")
        if "min_volume_dbfs" in s and s["min_volume_dbfs"] is not None and not _num(s["min_volume_dbfs"], -90, 0):
            errs.append(f"{w}.min_volume_dbfs must be between -90 and 0")
        if "schedule" in s:
            _check_schedule(s["schedule"], f"{w}.schedule", errs)
        if s.get("environment") is not None and s["environment"] not in {e["id"] for e in catalog.raw.get("environments", [])}:
            errs.append(f"{w}.environment: unknown environment '{s['environment']}'")
        if "adaptive" in s:
            ad = s["adaptive"]
            if not isinstance(ad, dict) or set(ad) - {"enabled", "max_offset"} or not isinstance(ad.get("enabled", False), bool) \
                    or ("max_offset" in ad and not _num(ad["max_offset"], 0, 0.4)):
                errs.append(f"{w}.adaptive: only 'enabled' (true/false) and 'max_offset' (0 to 0.4) are allowed")
        _check_devices(s, w, errs)
        if "advice" in s:
            _check_advice(s["advice"], f"{w}.advice", rule_ids, errs)
        clips = s.get("clips") or {}
        if "allowed" in clips and not isinstance(clips["allowed"], bool):
            errs.append(f"{w}.clips.allowed must be true or false")
        for k, blk in (s.get("classes") or {}).items():
            try:
                catalog.get(k)
            except KeyError:
                errs.append(f"{w}.classes: unknown class '{k}'")
                continue
            _check_class_block(blk, f"{w}.classes.{k}", errs)
    return errs
