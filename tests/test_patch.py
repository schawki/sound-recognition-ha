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


def test_describe_patch_in_words():
    from custom_components.sound_recognition.patch import describe_patch
    patch = {"source": "a", "class_patch": {"x": {"enabled": False}, "y": {"min_duration_s": 3}, "z": {"schedule": {"mode": "continuous"}}}}
    names = {"x": "Beep", "y": "Smoke detector", "z": "Fire alarm"}
    assert describe_patch(patch, names) == "- Beep: switched off\n- Smoke detector: minimum duration 3 s\n- Fire alarm: continuous schedule"
    assert describe_patch(patch, names, "fr").splitlines()[0] == "- Beep: désactivé"
    assert describe_patch(patch, names, "de").splitlines()[0] == "- Beep: switched off"


def test_a_patch_that_answers_an_advice_leaves_a_trace_replaced_when_applied_again():
    patch = {"source": "a", "class_patch": {"/m/06bz3": {"enabled": True}}, "rule": "context_recommended", "message": "Add contexts", "level": "info", "classes": ["/m/03qc9zr"]}
    out = apply_patch(CFG, patch)
    (trace,) = out["sources"][0]["applied_advice"]
    assert trace["rule"] == "context_recommended" and trace["classes"] == ["/m/03qc9zr"] and trace["level"] == "info"
    assert trace["patch"] == {"class_patch": {"/m/06bz3": {"enabled": True}}} and trace["at"]
    again = apply_patch(out, patch)
    assert len(again["sources"][0]["applied_advice"]) == 1                                          # same advice: replaced, not added
    other = apply_patch(again, {**patch, "rule": "other_rule"})
    assert len(other["sources"][0]["applied_advice"]) == 2
    assert "applied_advice" not in apply_patch(CFG, {"source": "a", "class_patch": {"/m/06bz3": {"enabled": True}}})["sources"][0]   # no rule, no trace
