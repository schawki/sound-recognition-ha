from custom_components.sound_recognition import helpers as h
from soundrec import catalog as cm
from fake_service import CAT

IDX = h.build_index(cm.load_lang("en"))
MID = lambda n: CAT.get(n)["mid"]


def cfg():
    return {"classes": {"Bark": {"enabled": True, "threshold": 0.6}}, "sources": [{"id": "a", "type": "file", "url": "x"}]}


def test_global_selection_keeps_other_settings_and_names():
    c = cfg()
    h.apply_selection(c, IDX, None, {MID("Doorbell")}, {MID("Bark"), MID("Doorbell")})
    assert c["classes"]["Bark"] == {"enabled": False, "threshold": 0.6}      # settings kept, class off
    assert c["classes"][MID("Doorbell")] == {"enabled": True}
    h.apply_selection(c, IDX, None, set(), {MID("Doorbell")})
    assert MID("Doorbell") not in c["classes"]                                  # nothing left to keep: block removed


def test_source_selection_stores_only_differences():
    c = cfg()
    kitchen = {MID("Bark"), MID("Smoke detector, smoke alarm")}                 # Bark already global, smoke is an addition
    h.apply_selection(c, IDX, "a", kitchen, {MID("Bark"), MID("Smoke detector, smoke alarm"), MID("Doorbell")})
    assert c["sources"][0]["classes"] == {MID("Smoke detector, smoke alarm"): {"enabled": True}}
    h.apply_selection(c, IDX, "a", {MID("Smoke detector, smoke alarm")}, {MID("Bark"), MID("Smoke detector, smoke alarm")})
    assert c["sources"][0]["classes"][MID("Bark")] == {"enabled": False}        # Bark switched off on this source only
    assert h.enabled_mids(c, c["sources"][0], IDX) == {MID("Smoke detector, smoke alarm")}


def test_class_form_writes_only_changes_and_lets_conversations_be_kept():
    c = cfg()
    sug = CAT.get("Doorbell")["suggestions"]
    vals = {"threshold": sug["threshold"], "min_duration_s": sug["min_duration_s"], "cooldown_s": 99, "pre_roll_s": sug["pre_roll_s"],
            "post_roll_s": sug["post_roll_s"], "clip_retention_days": sug["clip_retention_days"], "always_on": True}
    h.apply_class_form(c, IDX, None, MID("Doorbell"), vals)
    assert c["classes"][MID("Doorbell")] == {"cooldown_s": 99, "schedule": {"mode": "continuous"}}
    h.apply_class_form(c, IDX, None, MID("Speech"), dict(vals, clip_retention_days=30))
    assert c["classes"][MID("Speech")]["clip_retention_days"] == 30           # conversations may be kept, knowingly (0 days by default)
    h.apply_class_form(c, IDX, None, MID("Doorbell"), dict(vals, cooldown_s=99, always_on=False, min_volume_dbfs=-40))
    assert c["classes"][MID("Doorbell")] == {"cooldown_s": 99, "min_volume_dbfs": -40.0}


def test_source_form_round_trip_keeps_extra_windows():
    src = {"id": "k", "name": "K", "type": "rtsp", "url": "rtsp://x", "classes": {"Bark": {"enabled": False}},
           "schedule": {"mode": "scheduled", "windows": [{"days": ["mon"], "from": "07:00", "to": "23:00"}, {"days": ["sat"], "from": "09:00", "to": "12:00"}]}}
    ui = h.source_form_defaults(src)
    assert ui["window_from"] == "07:00:00" and ui["schedule_mode"] == "scheduled"
    ui["window_to"] = "22:00:00"
    out = h.source_from_form(src, ui, "k")
    assert out["schedule"]["windows"][0]["to"] == "22:00" and out["schedule"]["windows"][1]["days"] == ["sat"]
    assert out["classes"] == {"Bark": {"enabled": False}}                          # untouched parts preserved
    ui["schedule_mode"] = "continuous"; ui["clips_allowed"] = False; ui["clips_max_days"] = 7
    out = h.source_from_form(src, ui, "k")
    assert out["schedule"] == {"mode": "continuous"} and out["clips"] == {"allowed": False, "max_retention_days": 7}


def test_slugify_and_unique():
    assert h.slugify("Cuisine été !") == "cuisine_ete"
    assert h.unique_id("cuisine", {"cuisine", "cuisine_2"}) == "cuisine_3"
