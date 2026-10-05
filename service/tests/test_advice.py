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


def test_area_devices_validation():
    cfg = _cfg()
    cfg["sources"][0].update(area="salon", devices={"enabled": True, "max_offset": 0.2, "exclude": ["media_player.old"], "include": ["fan.hood"]})
    assert cfgmod.validate(cfg, CAT) == []
    cfg["sources"][0]["devices"] = {"enabled": "yes", "oops": 1}
    cfg["sources"][1]["devices"] = {"exclude": ["nodot"], "max_offset": 3}
    errs = cfgmod.validate(cfg, CAT)
    assert sum("devices" in e for e in errs) >= 3
    assert any("total_boost_cap" in e for e in cfgmod.validate(_cfg(analysis={**cfgmod.DEFAULTS["analysis"], "total_boost_cap": 5}), CAT))


def test_the_former_builtin_room_description_is_dropped_on_load(tmp_path):
    import yaml
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump({"area_links": [{"a": "x", "b": "y", "type": "open"}], "sources": []}))
    assert "area_links" not in cfgmod.load(str(p))


FIREWORKS, FIRECRACKER = "/m/0g6b5", "/g/122z_qxw"


def test_the_fireworks_warning_has_a_gesture_and_knows_when_it_is_done():
    cfg = _cfg()
    cfg["sources"][0]["classes"] = {"/m/032s66": {"enabled": True}}                       # gunshots on, the look-alikes not
    w = _rules(cfg, "detonations_fireworks")["a"]
    assert not w["applied"] and set(w["apply"]["class_patch"]) == {FIREWORKS, FIRECRACKER}
    cfg["sources"][0]["classes"] = {FIREWORKS: {"enabled": True}, FIRECRACKER: {"enabled": True}}
    w = _rules(cfg, "detonations_fireworks")["a"]
    assert w["applied"] and set(w["classes"]) == {FIREWORKS, FIRECRACKER}


def test_a_warning_without_a_gesture_has_none():
    w = _rules(_cfg())["a"]
    assert w["apply"] is None and w["applied"] is False


# ---- gestures of the other warnings: what the button does, and when the advice is done
SMOKE, BEEP, FIRE, CRACKLE, BABY, MEOW, TV, RADIO = ("/m/01y3hg", "/m/02fs_r", "/m/02_41", "/m/07pzfmf", "/t/dd00002", "/m/07qrkrw",
                                                      "/m/07c52", "/m/06bz3")


def _on(*mids, **blocks):
    cfg = _cfg()
    cfg["sources"][0]["classes"] = {m: {"enabled": True, **blocks.get(m, {})} for m in mids}
    return cfg


def _apply(cfg, w):
    """What the panel does with a gesture: merge the patch into the class blocks of its source."""
    cfg = copy.deepcopy(cfg)
    src = next(s for s in cfg["sources"] if s["id"] == w["apply"]["source"])
    for mid, block in w["apply"]["class_patch"].items():
        src.setdefault("classes", {}).setdefault(mid, {}).update(block)
    return cfg


def test_beep_and_smoke_gesture_switches_beep_off_and_asks_for_three_seconds():
    cfg = _on(SMOKE, BEEP)
    w = _rules(cfg, "fire_beeps")["a"]
    assert w["apply"]["class_patch"] == {BEEP: {"enabled": False}, SMOKE: {"min_duration_s": 3}} and not w["applied"]
    assert cfgmod.validate(_apply(cfg, w), CAT) == []
    assert "a" not in _rules(_apply(cfg, w), "fire_beeps")                      # the cause is gone: the advice leaves the list


def test_fire_and_crackle_gesture_switches_only_the_ones_that_are_on():
    cfg = _on(FIRE)
    w = _rules(cfg, "fire_only")["a"]
    assert w["apply"]["class_patch"] == {FIRE: {"enabled": False}}
    assert "a" not in _rules(_apply(cfg, w), "fire_only")


def test_baby_cry_gesture_is_already_applied_when_the_duration_is_there():
    cfg = _on(BABY, MEOW)
    w = _rules(cfg, "baby_cat")["a"]
    assert w["apply"]["class_patch"] == {BABY: {"min_duration_s": 2}} and w["applied"]       # the catalog default already asks for 2 s
    cfg = _on(BABY, MEOW, **{BABY: {"min_duration_s": 0.5}})
    w = _rules(cfg, "baby_cat")["a"]
    assert not w["applied"]
    w = _rules(_apply(cfg, w), "baby_cat")["a"]
    assert w["applied"]
    assert _rules(_on(MEOW, "/m/07r81j2"), "baby_cat")["a"]["apply"] is None                  # no baby cry listened to: nothing to set


def test_television_and_radio_gesture_is_kept_as_applied():
    cfg = _on("/m/03qc9zr")
    w = _rules(cfg, "context_recommended")["a"]
    assert w["apply"]["class_patch"] == {TV: {"enabled": True}, RADIO: {"enabled": True}} and not w["applied"]
    w = _rules(_apply(cfg, w), "context_recommended")["a"]
    assert w["applied"]


def test_missing_context_gesture_switches_the_contexts_on():
    cfg = _on(BABY)
    w = _rules(cfg, "missing_context")["a"]
    assert set(w["apply"]["class_patch"]) == set(CAT.get(BABY)["inhibiting_contexts"])
    assert "a" not in _rules(_apply(cfg, w), "missing_context")


def test_low_threshold_gesture_goes_back_to_the_suggested_threshold():
    cfg = _on(SPEECH, **{SPEECH: {"threshold": 0.2}})
    w = _rules(cfg, "low_threshold_high_fp")["a"]
    assert w["apply"]["class_patch"] == {SPEECH: {"threshold": CAT.get(SPEECH)["suggestions"]["threshold"]}}
    assert "a" not in _rules(_apply(cfg, w), "low_threshold_high_fp")


def test_schedule_gap_gesture_gives_the_class_a_continuous_schedule():
    cfg = _on(SMOKE)
    cfg["sources"][0]["schedule"] = {"mode": "scheduled", "windows": [{"from": "08:00", "to": "20:00"}]}
    w = _rules(cfg, "schedule_gap_safety")["a"]
    assert w["apply"]["class_patch"] == {SMOKE: {"schedule": {"mode": "continuous"}}}
    fixed = _apply(cfg, w)
    assert cfgmod.validate(fixed, CAT) == [] and "a" not in _rules(fixed, "schedule_gap_safety")


def test_forbidden_clip_gesture_removes_the_retention_only_when_it_sits_on_the_source():
    cfg = _on(SPEECH, **{SPEECH: {"clip_retention_days": 7}})
    w = _rules(cfg, "clip_forbidden")["a"]
    assert w["apply"]["class_patch"] == {SPEECH: {"clip_retention_days": 0}}
    assert "a" not in _rules(_apply(cfg, w), "clip_forbidden")
    cfg["classes"] = {SPEECH: {"clip_retention_days": 7}}                                       # the global block asks for it too: a source patch cannot answer
    assert _rules(cfg, "clip_forbidden")["a"]["apply"] is None
