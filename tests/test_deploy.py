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


def test_updater_units_match_installer_and_service():
    d = ROOT / "deploy"
    service, install = (d / "soundrec.service").read_text(), (d / "install.sh").read_text()
    path, helper_unit = (d / "soundrec-update.path").read_text(), (d / "soundrec-update.service").read_text()
    assert "PathExists=/var/lib/soundrec/update-request/request" in path
    assert "ExecStart=/usr/local/sbin/soundrec-update" in helper_unit and "/usr/local/sbin/soundrec-update" in install
    for var in ("SOUNDREC_UPDATE_REQUEST", "SOUNDREC_UPDATE_STATUS", "SOUNDREC_BUILD"):
        assert var in service, var
    assert "SOUNDREC_REMOTE_UPDATE" in install and "/etc/soundrec-updater.env" in install
    assert (d / "soundrec-update.sh").stat().st_mode & 0o111


def test_move_units_match_installer_and_service():
    d = ROOT / "deploy"
    install = (d / "install.sh").read_text()
    assert "PathExists=/var/lib/soundrec/update-request/move" in (d / "soundrec-move.path").read_text()
    assert "ExecStart=/usr/local/sbin/soundrec-move" in (d / "soundrec-move.service").read_text() and "/usr/local/sbin/soundrec-move" in install
    for flag in ("move-capable", "move-roots", "SOUNDREC_REMOTE_MOVE", "SOUNDREC_CLIPS", "MOVE_ROOTS"):
        assert flag in install, flag
    assert (d / "soundrec-move.sh").stat().st_mode & 0o111


def test_the_installer_sandbox_follows_a_custom_clips_folder():
    install = (ROOT / "deploy/install.sh").read_text()
    assert "clips-path.conf" in install and "ReadWritePaths=%s" in install
    assert "rm -rf /etc/systemd/system/soundrec.service.d" not in install      # it would drop the drop-in written by the move helper
