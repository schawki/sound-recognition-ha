"""Rules hassfest enforces on the translations of repair issues, checked here so a failure shows before the release."""
import json
import pathlib

BASE = pathlib.Path(__file__).parent.parent / "custom_components" / "sound_recognition"


def test_an_issue_is_either_fixable_or_has_a_description_never_both():
    for name in ("strings.json", "translations/en.json", "translations/fr.json"):
        issues = json.loads((BASE / name).read_text(encoding="utf-8"))["issues"]
        for key, issue in issues.items():
            assert not ("fix_flow" in issue and "description" in issue), f"{name}: issue {key} has both a fix_flow and a description"


def test_every_language_has_the_same_issues_and_placeholders():
    import re
    ref = json.loads((BASE / "translations/en.json").read_text(encoding="utf-8"))["issues"]
    fr = json.loads((BASE / "translations/fr.json").read_text(encoding="utf-8"))["issues"]
    assert ref.keys() == fr.keys()
    ph = lambda s: set(re.findall(r"\{(\w+)\}", s))
    assert ph(ref["advice_fixable"]["fix_flow"]["step"]["confirm"]["description"]) == ph(fr["advice_fixable"]["fix_flow"]["step"]["confirm"]["description"]) == {"source", "message", "changes"}
