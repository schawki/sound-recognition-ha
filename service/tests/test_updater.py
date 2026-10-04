"""Updater (service side), its API routes, and the root helper script run against a throw-away git repository."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from aiohttp.test_utils import TestClient, TestServer

from soundrec import api
from soundrec.engine import Engine
from soundrec.updater import STALLED_REQUEST_S, STALLED_RUN_S, Updater

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "deploy" / "soundrec-update.sh"
H = {"Authorization": "Bearer tok"}


def _dirs(tmp_path, capable=True):
    req, st = tmp_path / "req", tmp_path / "status"
    req.mkdir(), st.mkdir()
    if capable:
        (st / "capable").touch()
    (tmp_path / "BUILD").write_text("commit=abc1234\nrelease=v0.1.0\nbuilt=2026-10-01\n")
    return req, st, tmp_path / "BUILD"


def test_updater_not_capable_without_flag(tmp_path):
    req, st, b = _dirs(tmp_path, capable=False)
    u = Updater(str(req), str(st), str(b))
    assert not u.capable and u.request() == "unavailable"
    assert not Updater(None, None, None).capable
    assert u.status()["state"] == "idle" and u.status()["release"] == "v0.1.0"


def test_updater_request_busy_and_states(tmp_path):
    req, st, b = _dirs(tmp_path)
    u = Updater(str(req), str(st), str(b))
    assert u.capable and u.status()["state"] == "idle"
    assert u.request() == "requested" and u.request() == "busy"
    s = u.status()
    assert s["state"] == "requested" and not s["stalled"]
    assert u.status(now=time.time() + STALLED_REQUEST_S + 5)["stalled"]
    (req / "request").unlink()
    (st / "status.json").write_text(json.dumps({"state": "running", "message": "x", "updated": 1000, "from": "v0.1.0", "to": "v0.2.0"}))
    (st / "update.log").write_text("\n".join(f"l{i}" for i in range(30)))
    s = u.status(now=1010)
    assert s["state"] == "running" and not s["stalled"] and s["to"] == "v0.2.0" and s["log"].endswith("l29")
    assert u.status(now=1000 + STALLED_RUN_S + 1)["stalled"] and u.request() == "busy"
    (st / "status.json").write_text(json.dumps({"state": "done", "message": "ok"}))
    assert u.status()["state"] == "done" and u.request() == "requested"


def test_updater_ignores_garbage(tmp_path):
    req, st, b = _dirs(tmp_path)
    (st / "status.json").write_text("not json")
    assert Updater(str(req), str(st), str(b)).status()["state"] == "idle"
    (st / "status.json").write_text(json.dumps({"state": "exploded"}))
    assert Updater(str(req), str(st), str(b)).status()["state"] == "idle"


@pytest.fixture
async def client(tmp_path):
    cfgp = tmp_path / "c.yaml"
    yaml.safe_dump({"storage": {"clips_dir": str(tmp_path / "clips"), "db_path": str(tmp_path / "e.sqlite")}, "api": {"token": "tok"},
                    "sources": []}, open(cfgp, "w"))

    class Clf:
        def predict(self, x):
            return np.zeros(521, dtype=np.float32)

    (tmp_path / "u").mkdir()
    req, st, b = _dirs(tmp_path / "u")
    c = TestClient(TestServer(api.make_app(Engine(str(cfgp), "unused", classifier=Clf()), Updater(str(req), str(st), str(b)))))
    await c.start_server()
    c.req_dir = req
    yield c
    await c.close()


async def test_api_health_and_update_routes(client):
    h = await (await client.get("/api/v1/health")).json()
    assert h["api_level"] >= 2 and h["update"] == {"capable": True} and h["commit"] == "abc1234" and h["release"] == "v0.1.0"
    assert (await client.get("/api/v1/update")).status == 401 and (await client.post("/api/v1/update")).status == 401
    assert (await (await client.get("/api/v1/update", headers=H)).json())["state"] == "idle"
    r = await client.post("/api/v1/update", headers=H)
    assert r.status == 202 and (await r.json())["state"] == "requested" and (client.req_dir / "request").exists()
    assert (await client.post("/api/v1/update", headers=H)).status == 409


async def test_api_update_unavailable(tmp_path):
    cfgp = tmp_path / "c.yaml"
    yaml.safe_dump({"storage": {"clips_dir": str(tmp_path / "c"), "db_path": str(tmp_path / "e.sqlite")}, "api": {"token": "tok"}, "sources": []}, open(cfgp, "w"))

    class Clf:
        def predict(self, x):
            return np.zeros(521, dtype=np.float32)

    c = TestClient(TestServer(api.make_app(Engine(str(cfgp), "unused", classifier=Clf()), Updater(None, None, None))))
    await c.start_server()
    try:
        assert (await (await c.get("/api/v1/health")).json())["update"] == {"capable": False}
        assert (await c.post("/api/v1/update", headers=H)).status == 501
    finally:
        await c.close()


# ---------------------------------------------------------------- the root helper
def _git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)


@pytest.fixture
def world(tmp_path):
    if not shutil.which("git"):
        pytest.skip("git missing")
    origin, clone = tmp_path / "origin", tmp_path / "clone"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    (origin / "VERSION").write_text("1")
    _git(origin, "add", "."), _git(origin, "commit", "-qm", "one"), _git(origin, "tag", "v0.1.0")
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    req, st = tmp_path / "req", tmp_path / "st"
    req.mkdir(), st.mkdir()
    install = tmp_path / "install.sh"
    install.write_text(f'#!/bin/bash\ncat "{clone}/VERSION" >> "{tmp_path}/installed"\n[ -f "{tmp_path}/fail" ] && [ "$(cat {clone}/VERSION)" = 2 ] && exit 1\nexit 0\n')
    env = tmp_path / "updater.env"
    env.write_text(f'REPO={clone}\nREQUEST_DIR={req}\nSTATUS_DIR={st}\nINSTALL={install}\n')

    def run():
        (req / "request").write_text("whatever; rm -rf /")
        subprocess.run(["bash", str(HELPER)], env={**os.environ, "SOUNDREC_UPDATER_ENV": str(env)}, check=False, capture_output=True)
        return json.loads((st / "status.json").read_text())

    def release(n, tag):
        (origin / "VERSION").write_text(str(n))
        _git(origin, "commit", "-qam", f"v{n}"), _git(origin, "tag", tag)

    return SimpleNamespace(run=run, release=release, clone=clone, req=req, tmp=tmp_path)


def test_helper_already_up_to_date(world):
    s = world.run()
    assert s["state"] == "done" and "Already" in s["message"] and not (world.req / "request").exists()
    assert not (world.tmp / "installed").exists()


def test_helper_updates_to_latest_tag_only(world):
    world.release(2, "v0.2.0")
    world.release(3, "v0.10.0")
    (world.tmp / "origin" / "VERSION").write_text("4")
    _git(world.tmp / "origin", "commit", "-qam", "untagged work on main")
    s = world.run()
    assert s["state"] == "done" and s["to"] == "v0.10.0" and (world.clone / "VERSION").read_text() == "3"
    assert (world.tmp / "installed").read_text() == "3"


def test_helper_rolls_back_on_install_failure(world):
    world.release(2, "v0.2.0")
    (world.tmp / "fail").touch()
    s = world.run()
    assert s["state"] == "failed" and "restored" in s["message"]
    assert (world.clone / "VERSION").read_text() == "1"
    assert (world.tmp / "installed").read_text() == "21"      # failed install of 2, then reinstall of 1


def test_helper_fails_cleanly_without_network(world):
    shutil.rmtree(world.tmp / "origin")
    s = world.run()
    assert s["state"] == "failed" and "fetch" in s["message"]
