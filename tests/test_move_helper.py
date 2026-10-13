"""The root helper that moves the clips: run for real in a sandbox (runuser, systemctl and curl are stubs), on temporary folders."""
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "deploy/soundrec-move.sh"


@pytest.fixture
def box(tmp_path):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.txt"
    (bin_ / "runuser").write_text('#!/bin/sh\nshift 2; [ "$1" = "--" ] && shift; exec "$@"\n')
    (bin_ / "systemctl").write_text(f'#!/bin/sh\necho "systemctl $*" >> {calls}\n')
    (bin_ / "curl").write_text(f'#!/bin/sh\n[ -f {tmp_path}/unhealthy ] && exit 22\nexit 0\n')
    for f in bin_.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    old, mnt = tmp_path / "var/clips", tmp_path / "mnt"
    for d in (old / "2026-10-01", mnt / "disk", tmp_path / "req", tmp_path / "status", tmp_path / "dropin"):
        d.mkdir(parents=True)
    (old / "2026-10-01/a.wav").write_bytes(b"RIFF" * 1000)
    (old / "2026-10-01/a.json").write_text("{}")
    config = tmp_path / "config.yaml"
    config.write_text(f"api:\n  port: 8765\nstorage:\n  clips_dir: {old}\n  db_path: {tmp_path}/events.sqlite\nsources: []\n")
    env_file = tmp_path / "updater.env"
    env_file.write_text(f"REQUEST_DIR='{tmp_path}/req'\nSTATUS_DIR='{tmp_path}/status'\nCONFIG='{config}'\nSERVICE_USER='nobody'\nMOVE_ROOTS='{mnt}:{tmp_path}/var'\n")

    class Box:
        pass
    b = Box()
    b.path, b.old, b.mnt, b.config, b.calls = tmp_path, old, mnt, config, calls

    def run(dest):
        (tmp_path / "req/move").write_text(json.dumps({"dest": str(dest)}))
        env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "SOUNDREC_UPDATER_ENV": str(env_file), "DROPIN_DIR": str(tmp_path / "dropin"), "HEALTH_TRIES": "2"}
        subprocess.run(["bash", str(HELPER)], env=env, capture_output=True, text=True, timeout=60)
        return json.loads((tmp_path / "status/move.json").read_text())
    b.run = run
    return b


def test_a_move_copies_verifies_switches_and_keeps_the_old_folder(box):
    dest = box.mnt / "disk"
    st = box.run(dest)
    assert st["state"] == "done", st
    assert (dest / "2026-10-01/a.wav").read_bytes() == b"RIFF" * 1000 and (dest / "2026-10-01/a.json").exists()
    assert f'clips_dir: "{dest}"' in box.config.read_text()
    assert (box.path / "dropin/clips-path.conf").read_text() == f"[Service]\nReadWritePaths={dest}\n"
    assert (box.old / "2026-10-01/a.wav").exists(), "the old folder is never deleted"
    assert "systemctl restart soundrec.service" in box.calls.read_text()
    assert not (box.path / "req/move").exists(), "the request is consumed"


@pytest.mark.parametrize("make,why", [
    (lambda b: "relative/path", "absolute"),
    (lambda b: "/etc", "not under"),
    (lambda b: str(b.mnt / "missing"), "does not exist"),
    (lambda b: str(b.mnt / "bad name"), "characters"),
    (lambda b: str(b.mnt / "disk/../disk"), "contain"),
    (lambda b: str(b.old), "already"),
])
def test_a_wrong_destination_is_refused_and_nothing_changes(box, make, why):
    before = box.config.read_text()
    (box.mnt / "bad name").mkdir()
    st = box.run(make(box))
    assert st["state"] == "failed" and why in st["message"], st
    assert box.config.read_text() == before
    assert not (box.path / "dropin/clips-path.conf").exists()


def test_a_destination_with_files_a_link_or_inside_the_old_folder_is_refused(box):
    (box.mnt / "disk/x").write_text("x")
    assert "not empty" in box.run(box.mnt / "disk")["message"]
    (box.mnt / "link").symlink_to(box.mnt / "disk")
    assert "link" in box.run(box.mnt / "link")["message"]
    inside = box.old / "sub"
    inside.mkdir()
    assert "inside the current" in box.run(inside)["message"]


def test_a_service_that_does_not_start_gets_its_old_configuration_back(box):
    (box.path / "unhealthy").write_text("")
    before = box.config.read_text()
    st = box.run(box.mnt / "disk")
    assert st["state"] == "failed" and "restored" in st["message"]
    assert box.config.read_text() == before and not (box.path / "dropin/clips-path.conf").exists()
    assert (box.old / "2026-10-01/a.wav").exists()
