"""Consistency checks for the deployment files."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _const(text, name):
    m = re.search(rf'{name}[^\n]*?(https://[^"}}\s]+|[0-9a-f]{{64}})', text)
    return m.group(1) if m else None


def test_model_constants_match_dockerfile():
    install = (ROOT / "deploy/install.sh").read_text()
    docker_path = next(ROOT.glob("**/Dockerfile"), None)
    assert docker_path is not None
    docker = docker_path.read_text()
    for name in ("MODEL_URL", "MODEL_SHA256"):
        assert _const(install, name) and _const(install, name) == _const(docker, name), name


def test_unit_matches_installer_paths():
    unit = (ROOT / "deploy/soundrec.service").read_text()
    assert "ExecStart=/opt/soundrec/venv/bin/python -m soundrec" in unit
    assert "/etc/soundrec/config.yaml" in unit
