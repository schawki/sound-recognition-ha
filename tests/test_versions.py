"""The integration and the service carry the same version: the service reports its own, and Home Assistant offers an update while it is older than the latest tag."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_service_and_integration_have_the_same_version():
    manifest = json.loads((ROOT / "custom_components" / "sound_recognition" / "manifest.json").read_text())["version"]
    service = re.search(r'__version__ = "([^"]+)"', (ROOT / "service" / "soundrec" / "__init__.py").read_text()).group(1)
    assert manifest == service
