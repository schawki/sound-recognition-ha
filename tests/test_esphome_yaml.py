"""The ESPHome configuration shown in the panel is the one of esphome/example.yaml."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_panel_yaml_matches_the_example():
    ts = open(os.path.join(ROOT, "panel", "src", "esphome-yaml.ts"), encoding="utf-8").read()
    shown = ts.split("`")[1]
    example = open(os.path.join(ROOT, "esphome", "example.yaml"), encoding="utf-8").read()
    assert example.endswith(shown) or shown in example, "esphome/example.yaml must contain the text of panel/src/esphome-yaml.ts"
    assert "!secret sound_recognition_password" in shown and "password: sound" not in shown
