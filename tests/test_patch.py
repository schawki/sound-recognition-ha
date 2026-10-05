"""Applying a recommendation patch to a configuration, like the panel does."""
from custom_components.sound_recognition.patch import apply_patch

CFG = {"sources": [{"id": "a", "classes": {"Radio": {"threshold": 0.5}}, "adaptive": {"max_offset": 0.2}}, {"id": "b"}]}


def test_a_key_already_used_is_kept_by_name_or_by_id():
    out = apply_patch(CFG, {"source": "a", "class_patch": {"/m/06bz3": {"enabled": True}}}, {"/m/06bz3": "Radio"})
    assert out["sources"][0]["classes"] == {"Radio": {"threshold": 0.5, "enabled": True}}          # merged under the AudioSet name already there
    out = apply_patch(CFG, {"source": "a", "class_patch": {"/m/07c52": {"enabled": True}}}, {"/m/07c52": "Television"})
    assert out["sources"][0]["classes"]["/m/07c52"] == {"enabled": True} and "Radio" in out["sources"][0]["classes"]


def test_source_settings_are_merged_and_the_input_is_not_changed():
    out = apply_patch(CFG, {"source": "a", "source_patch": {"adaptive": {"enabled": True}}})
    assert out["sources"][0]["adaptive"] == {"max_offset": 0.2, "enabled": True}
    assert "enabled" not in CFG["sources"][0]["adaptive"]
    assert apply_patch(CFG, {"source": "b", "source_patch": {"devices": {"enabled": True}}})["sources"][1]["devices"] == {"enabled": True}


def test_an_unknown_source_changes_nothing():
    assert apply_patch(CFG, {"source": "zzz", "class_patch": {"/m/1": {"enabled": True}}}) == CFG
