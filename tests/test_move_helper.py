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
    (bin_ / "mountpoint").write_text(f'#!/bin/sh\n[ -f {tmp_path}/ismount ] && exit 0\nexit 1\n')
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

    def run_delete(old):
        (tmp_path / "req/move-delete").write_text(json.dumps({"old": str(old)}))
        env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "SOUNDREC_UPDATER_ENV": str(env_file), "DROPIN_DIR": str(tmp_path / "dropin"), "HEALTH_TRIES": "2"}
        subprocess.run(["bash", str(HELPER)], env=env, capture_output=True, text=True, timeout=60)
        return json.loads((tmp_path / "status/clean.json").read_text())
    b.run_delete = run_delete
    b.kept = lambda: (tmp_path / "status/move-old").read_text().split() if (tmp_path / "status/move-old").exists() else []
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


def moved(box):
    assert box.run(box.mnt / "disk")["state"] == "done"
    return box.old


def test_the_old_folder_is_remembered_by_the_helper_itself(box):
    assert box.kept() == []
    moved(box)
    assert box.kept() == [str(box.old)]


def test_deleting_the_old_clips_removes_them_then_the_empty_folder(box):
    old = moved(box)
    st = box.run_delete(old)
    assert st["state"] == "done" and "removed" in st["message"], st
    assert not old.exists() and box.kept() == []
    assert (box.mnt / "disk/2026-10-01/a.wav").exists(), "the new folder is untouched"
    assert not (box.path / "req/move-delete").exists()


def test_files_that_are_not_clips_are_kept_with_their_folder(box):
    old = moved(box)
    (old / "notes.txt").write_text("mine")
    (old / "2026-10-01/readme").write_text("mine too")
    st = box.run_delete(old)
    assert st["state"] == "done" and "kept" in st["message"] and "other files" in st["message"], st
    assert (old / "notes.txt").exists() and (old / "2026-10-01/readme").exists()
    assert not (old / "2026-10-01/a.wav").exists() and not (old / "2026-10-01/a.json").exists()
    assert box.kept() == [str(old)], "still listed: the panel tells what to do by hand"


def test_a_mounted_old_folder_loses_its_clips_but_stays(box):
    old = moved(box)
    (box.path / "ismount").write_text("")
    st = box.run_delete(old)
    assert st["state"] == "done" and "mounted" in st["message"], st
    assert old.exists() and not (old / "2026-10-01/a.wav").exists()


def test_only_a_folder_the_helper_listed_can_be_deleted(box):
    moved(box)
    victim = box.path / "other"
    victim.mkdir()
    (victim / "2026-10-01").mkdir()
    (victim / "2026-10-01/x.wav").write_text("x")
    st = box.run_delete(victim)
    assert st["state"] == "failed" and "not a folder kept" in st["message"] and (victim / "2026-10-01/x.wav").exists()


def test_the_current_folder_is_never_deleted_even_if_listed(box):
    moved(box)
    with open(box.path / "status/move-old", "a") as f:
        f.write(f"{box.mnt / 'disk'}\n")
    st = box.run_delete(box.mnt / "disk")
    assert st["state"] == "failed" and "now" in st["message"] and (box.mnt / "disk/2026-10-01/a.wav").exists()


def test_an_empty_new_folder_blocks_the_deletion_of_the_only_copy(box):
    old = moved(box)
    for f in (box.mnt / "disk/2026-10-01").iterdir():
        f.unlink()
    st = box.run_delete(old)
    assert st["state"] == "failed" and "holds no clip" in st["message"] and (old / "2026-10-01/a.wav").exists()


def test_an_old_folder_already_gone_is_just_forgotten(box):
    old = moved(box)
    import shutil
    shutil.rmtree(old)
    st = box.run_delete(old)
    assert st["state"] == "done" and "already gone" in st["message"] and box.kept() == []
