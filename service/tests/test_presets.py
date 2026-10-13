import copy

from soundrec import catalog as cm
from soundrec import config as cfgmod
from soundrec.settings import Catalog, fold, fold_source, resolve

CAT = Catalog(cm.load_raw())


def base():
    return {"defaults": {"min_volume_dbfs": -60, "clips": {"allowed": True}}, "classes": {},
            "sources": [{"id": "a", "name": "A", "type": "file", "url": "x"}]}


def R(cfg, cls, sid="a"):
    return resolve(fold(cfg, CAT), CAT, sid, cls)


def validate(cfg):
    return cfgmod.validate(cfgmod._merge(cfgmod.DEFAULTS, cfg), CAT)


def test_catalog_presets_only_name_known_sounds_and_are_valid():
    raw = CAT.raw["presets"]
    assert len(raw) >= 18 and len({p["id"] for p in raw}) == len(raw)
    for p in raw:
        for name in p["sounds"]:
            CAT.get(name)                                              # an unknown sound would raise
        errs = []
        cfgmod._check_preset({"id": p["id"], "name": p["en"]["name"], "sounds": p["sounds"], "source": p.get("source", {})}, p["id"], set(), CAT, errs)
        assert not errs, errs
        assert p["fr"]["name"] and p["fr"]["why"] and p["en"]["why"]
    assert {p["place"] for p in raw if p["kind"] == "place"} == {e["id"] for e in CAT.raw["environments"]}   # one preset per kind of place


def test_a_preset_enables_its_sounds_and_says_where_they_come_from():
    cfg = base()
    assert R(cfg, "Baby cry, infant cry")["enabled"] is False
    cfg["sources"][0]["presets"] = ["room_nursery"]
    r = R(cfg, "Baby cry, infant cry")
    assert r["enabled"] is True and r["threshold"] == 0.45 and r["provenance"]["enabled"] == "preset" and r["provenance"]["threshold"] == "preset"
    assert cfg["sources"][0].get("classes") is None                    # the stored configuration is not touched


def test_presets_add_up_and_the_last_one_wins():
    cfg = base()
    cfg["presets"] = [{"id": "mine", "name": "Mine", "sounds": {"Bark": {"enabled": True, "threshold": 0.8}}},
                      {"id": "other", "name": "Other", "sounds": {"Bark": {"threshold": 0.65}, "Cat": {"enabled": True}}}]
    cfg["sources"][0]["presets"] = ["situation_pets", "mine", "other"]
    assert not validate(cfg)
    r = R(cfg, "Bark")
    assert r["enabled"] is True and r["threshold"] == 0.65                # `other` is listed last
    assert R(cfg, "Cat")["enabled"] is True and R(cfg, "Meow")["enabled"] is True      # sounds of every preset
    cfg["sources"][0]["presets"] = ["other", "mine"]
    assert R(cfg, "Bark")["threshold"] == 0.8                          # the order is the priority


def test_what_the_source_sets_itself_beats_a_preset():
    cfg = base()
    cfg["sources"][0].update({"presets": ["room_nursery"], "min_volume_dbfs": -40, "clips": {"allowed": True},
                              "classes": {"Baby cry, infant cry": {"threshold": 0.7}, "Whimper": {"enabled": False}}})
    r = R(cfg, "Baby cry, infant cry")
    assert r["threshold"] == 0.7 and r["provenance"]["threshold"] == "source_class" and r["enabled"] is True
    assert R(cfg, "Whimper")["enabled"] is False
    assert r["min_volume_dbfs"] == -40 and r["provenance"]["min_volume_dbfs"] == "source"
    assert R(cfg, "Bark")["provenance"]["clip_retention_days"] != "source_clips_disallowed"     # clips explicitly allowed: the preset's "no clips" is ignored
    eff = fold_source(cfg, CAT, cfg["sources"][0])
    assert eff["clips"]["allowed"] is True


def test_source_level_values_of_a_preset():
    cfg = base()
    cfg["sources"][0]["presets"] = ["room_bedroom"]
    eff = fold(cfg, CAT)["sources"][0]
    assert eff["min_volume_dbfs"] == -65 and eff["clips"]["allowed"] is False
    r = R(cfg, "Bark")
    assert r["min_volume_dbfs"] == -65 and r["provenance"]["min_volume_dbfs"] == "preset"
    assert r["clip_retention_days"] == 0                               # the preset turns clips off
    cfg["sources"][0]["presets"] = ["room_kitchen"]
    assert fold(cfg, CAT)["sources"][0]["adaptive"]["enabled"] is True


def test_a_preset_never_makes_a_safety_sound_harder_to_detect():
    cfg = base()
    cfg["presets"] = [{"id": "strict", "name": "Strict", "sounds": {
        "Smoke detector, smoke alarm": {"enabled": False, "threshold": 0.9, "min_duration_s": 30, "cooldown_s": 3000},
        "Baby cry, infant cry": {"enabled": True, "threshold": 0.3},
        "Bark": {"enabled": True, "threshold": 0.9}}}]
    cfg["sources"][0]["presets"] = ["strict"]
    smoke = R(cfg, "Smoke detector, smoke alarm")
    plain = resolve(cfg, CAT, "a", "Smoke detector, smoke alarm")
    assert smoke["enabled"] is False                                   # not enabled by anything else, and the preset does not switch it off
    assert smoke["threshold"] == plain["threshold"] and smoke["min_duration_s"] == plain["min_duration_s"] and smoke["cooldown_s"] == plain["cooldown_s"]
    assert R(cfg, "Baby cry, infant cry")["threshold"] == 0.3          # easier is accepted
    assert R(cfg, "Bark")["threshold"] == 0.9                          # an ordinary sound may be made stricter
    cfg["classes"] = {"Smoke detector, smoke alarm": {"enabled": True}}
    assert R(cfg, "Smoke detector, smoke alarm")["enabled"] is True    # `enabled: false` of a preset is ignored


def test_validation_of_presets():
    cfg = base()
    cfg["sources"][0]["presets"] = ["nope"]
    assert any("unknown preset 'nope'" in e for e in validate(cfg))
    cfg["sources"][0]["presets"] = ["room_kitchen"]
    assert not validate(cfg)
    cfg["presets"] = [{"id": "room_kitchen", "name": "x"}]
    assert any("already used by a preset of the catalog" in e for e in validate(cfg))
    cfg["presets"] = [{"id": "p", "name": "x", "source": {"min_volume_dbfs": -30}}]
    assert any("min_volume_dbfs must be between -90 and -50" in e for e in validate(cfg))
    cfg["presets"] = [{"id": "p", "name": "x", "sounds": {"Not a sound": {}}}]
    assert any("unknown class" in e for e in validate(cfg))
    cfg["presets"] = [{"id": "p", "name": "x", "sounds": {"Bark": {"schedule": {"mode": "continuous"}}}}]
    assert any("only enabled" in e for e in validate(cfg))
    cfg["presets"] = [{"id": "p", "name": ""}, {"id": "p", "name": "y"}]
    errs = validate(cfg)
    assert any("a name is required" in e for e in errs) and any("duplicate id" in e for e in errs)


def test_the_unfolded_configuration_is_never_modified():
    cfg = base()
    cfg["sources"][0]["presets"] = ["room_nursery", "situation_baby"]
    before = copy.deepcopy(cfg)
    fold(cfg, CAT)
    assert cfg == before


# ---------------------------------------------------------------------------------------------------------- through the service
from test_clips import H, client  # noqa: E402,F401  (fixtures)


async def test_the_service_applies_presets_and_serves_both_views(client):
    cfg = await (await client.get("/api/v1/config", headers=H)).json()
    cfg["presets"] = [{"id": "mine", "name": "Mine", "sounds": {"Cat": {"enabled": True}}}]
    cfg["sources"][0]["presets"] = ["room_nursery", "mine"]
    r = await client.put("/api/v1/config", json=cfg, headers=H)
    assert r.status == 200, await r.text()
    raw = await (await client.get("/api/v1/config", headers=H)).json()
    assert raw["sources"][0]["presets"] == ["room_nursery", "mine"] and "Baby cry, infant cry" not in raw["sources"][0].get("classes", {})
    eff = await (await client.get("/api/v1/config/effective", headers=H)).json()
    assert eff["sources"][0]["clips"]["allowed"] is False and eff["api"]["token"] == "***"
    sid = cfg["sources"][0]["id"]
    res = await (await client.get(f"/api/v1/resolved?source={sid}&class=Baby cry, infant cry", headers=H)).json()
    assert res["enabled"] is True and res["provenance"]["enabled"] == "preset"
    cfg["sources"][0]["presets"] = ["ghost"]
    r = await client.put("/api/v1/config", json=cfg, headers=H)
    assert r.status == 422 and "unknown preset 'ghost'" in (await r.text())
