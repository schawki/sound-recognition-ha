from custom_components.sound_recognition import helpers as h
from soundrec import catalog as cm
from fake_service import CAT

IDX = h.build_index(cm.load_lang("en"))
MID = lambda n: CAT.get(n)["mid"]


def test_enabled_sounds_follow_the_source_over_the_global_choice():
    cfg = {"classes": {"Bark": {"enabled": True}, "Speech": {"enabled": True}}, "sources": [{"id": "a", "type": "file", "url": "x", "classes": {"Speech": {"enabled": False}}}]}
    assert h.enabled_mids(cfg, cfg["sources"][0], IDX) == {MID("Bark")}
    assert h.enabled_mids(cfg, {"id": "b"}, IDX) == {MID("Bark"), MID("Speech")}


def test_unique_ids_of_the_entities_that_should_exist():
    cfg = {"classes": {"Bark": {"enabled": True}}, "sources": [{"id": "a", "type": "file", "url": "x"}]}
    ids = h.expected_unique_ids("entry", cfg, IDX)
    assert h.detected_unique_id("entry", "a", MID("Bark")) in ids
