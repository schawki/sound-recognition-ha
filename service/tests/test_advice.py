import copy

from soundrec import advisor, catalog as cm, config as cfgmod
from soundrec.settings import Catalog

CAT = Catalog(cm.load_raw())
SPEECH = "/m/09x0r"          # Speech: no safety class


def _cfg(**extra):
    cfg = copy.deepcopy(cfgmod.DEFAULTS)
    cfg["sources"] = [{"id": "a", "type": "rtsp", "url": "rtsp://x", "name": "A", "classes": {SPEECH: {"enabled": True}}},
                      {"id": "b", "type": "rtsp", "url": "rtsp://y", "name": "B", "classes": {SPEECH: {"enabled": True}}}]
    cfg.update(extra)
    return cfg


def _rules(cfg, rule="speech_target"):
    return {(w["source"]): w for w in advisor.compute(cfg) if w["rule"] == rule}


def test_default_level_and_validation():
    cfg = _cfg()
    assert _rules(cfg)["a"]["level"] == "warning"
    assert cfgmod.validate(cfg, CAT) == []


def test_global_and_source_overrides():
    cfg = _cfg(advice={"speech_target": "info"})
    assert _rules(cfg)["a"]["level"] == "info" and _rules(cfg)["b"]["level"] == "info"
    cfg["sources"][1]["advice"] = {"speech_target": "danger"}      # source wins over global
    r = _rules(cfg)
    assert r["a"]["level"] == "info" and r["b"]["level"] == "danger"
    cfg["sources"][0]["advice"] = {"speech_target": "default"}     # back to the catalog level
    assert _rules(cfg)["a"]["level"] == "warning"


def test_ignore_hides_the_warning_for_one_source_only():
    cfg = _cfg()
    cfg["sources"][0]["advice"] = {"speech_target": "ignore"}
    r = _rules(cfg)
    assert "a" not in r and "b" in r
    assert _rules(_cfg(advice={"speech_target": "ignore"})) == {}


def test_safety_warning_needs_confirmation_to_be_ignored():
    fire = [c for c in CAT.raw["classes"] if c["interest"] == "monitor" and c["usages"][:1] == ["fire"]]
    assert fire
    cfg = _cfg()
    cfg["sources"][0]["classes"] = {fire[0]["mid"]: {"enabled": True, "threshold": 0.01, "min_volume_dbfs": None}}
    cfg["sources"][0]["schedule"] = {"mode": "scheduled", "windows": [{"days": ["mon"], "from": "08:00", "to": "09:00"}]}
    base = [w for w in advisor.compute(cfg) if w["source"] == "a" and w["rule"] == "schedule_gap_safety"]
    assert base and base[0]["safety"]
    cfg["advice"] = {"schedule_gap_safety": "ignore"}
    assert [w for w in advisor.compute(cfg) if w["source"] == "a" and w["rule"] == "schedule_gap_safety"]   # protected
    cfg["advice"] = {"schedule_gap_safety": {"level": "ignore", "confirm": True}}
    assert not [w for w in advisor.compute(cfg) if w["source"] == "a" and w["rule"] == "schedule_gap_safety"]


def test_validation_errors():
    errs = cfgmod.validate(_cfg(advice={"nope": "info", "speech_target": "loud", "water_leak": {"level": "info", "x": 1}}), CAT)
    assert any("unknown advice rule 'nope'" in e for e in errs)
    assert any("level must be one of" in e for e in errs)
    assert any("only 'level' and 'confirm'" in e for e in errs)
    cfg = _cfg()
    cfg["sources"][0]["advice"] = {"zzz": "info"}
    assert any("sources[0](a).advice" in e for e in cfgmod.validate(cfg, CAT))


def test_listing_without_overrides_keeps_hidden_advice():
    cfg = _cfg(advice={"speech_target": "ignore"})
    assert _rules(cfg) == {}
    assert {w["source"] for w in advisor.compute(cfg, overrides=False) if w["rule"] == "speech_target"} == {"a", "b"}


def test_environment_and_adaptive_validation():
    cfg = _cfg()
    cfg["sources"][0].update(environment="living_tv", adaptive={"enabled": True, "max_offset": 0.2})
    assert cfgmod.validate(cfg, CAT) == []
    cfg["sources"][0]["environment"] = "moon"
    cfg["sources"][1]["adaptive"] = {"enabled": "yes"}
    errs = cfgmod.validate(cfg, CAT)
    assert any("unknown environment" in e for e in errs) and any("adaptive" in e for e in errs)
    cfg = _cfg(analysis={**cfgmod.DEFAULTS["analysis"], "safety_boost_cap": 2})
    assert any("safety_boost_cap" in e for e in cfgmod.validate(cfg, CAT))


def test_area_devices_and_links_validation():
    cfg = _cfg()
    cfg["sources"][0].update(area="salon", devices={"enabled": True, "max_offset": 0.2, "exclude": ["media_player.old"], "include": ["fan.hood"]})
    cfg["area_links"] = [{"a": "salon", "b": "entree", "type": "open"},
                         {"a": "cuisine", "b": "entree", "type": "door", "sensor": "binary_sensor.porte", "open_factor": 0.8, "closed_factor": 0.1}]
    assert cfgmod.validate(cfg, CAT) == []
    cfg["sources"][0]["devices"] = {"enabled": "yes", "oops": 1}
    cfg["sources"][1]["devices"] = {"exclude": ["nodot"], "max_offset": 3}
    cfg["area_links"] = [{"a": "x", "b": "x", "type": "open"}, {"a": "x", "b": "y", "type": "wall"}, {"a": "x", "b": "y", "type": "open", "sensor": "binary_sensor.d"}]
    errs = cfgmod.validate(cfg, CAT)
    assert sum("devices" in e for e in errs) >= 3 and sum("area_links" in e for e in errs) >= 3
    assert any("total_boost_cap" in e for e in cfgmod.validate(_cfg(analysis={**cfgmod.DEFAULTS["analysis"], "total_boost_cap": 5}), CAT))
