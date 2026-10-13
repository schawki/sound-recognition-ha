"""Moving the clips: what the service checks, what it asks of the root helper, and how clips are held back meanwhile."""
import json
import os
import time

import numpy as np

from soundrec.mover import Mover
from test_clips import BARK, H, NOW, client  # noqa: F401  (fixtures)


def make(tmp_path, capable=True):
    req, status, mnt = tmp_path / "req", tmp_path / "status", tmp_path / "mnt"
    for d in (req, status, mnt / "disk"):
        d.mkdir(parents=True)
    if capable:
        (status / "move-capable").write_text("")
    (status / "move-roots").write_text(f"{mnt}\n")
    return Mover(str(req), str(status)), req, status, mnt


def test_a_good_destination_is_accepted(tmp_path):
    m, _, _, mnt = make(tmp_path)
    cur = tmp_path / "cur"
    cur.mkdir()
    assert m.check(str(mnt / "disk"), str(cur), 1000) == []


def test_every_reason_to_refuse_has_its_code(tmp_path):
    m, _, _, mnt = make(tmp_path)
    cur = tmp_path / "mnt" / "cur"
    cur.mkdir()
    (mnt / "full").mkdir(); (mnt / "full/x").write_text("x")
    (mnt / "file").write_text("x")
    (mnt / "link").symlink_to(mnt / "disk")
    (cur / "sub").mkdir()
    cases = {"relative": "not_absolute", str(mnt / "a b"): "bad_characters", str(mnt / "disk/../disk"): "bad_characters", str(mnt / "none"): "not_found",
             str(mnt / "file"): "not_directory", str(mnt / "link"): "symlink", str(cur): "same_folder", str(cur / "sub"): "nested", "/usr": "outside_roots",
             str(mnt / "full"): "not_empty"}
    for dest, code in cases.items():
        assert m.check(dest, str(cur), 1000) == [code], dest
    assert m.check(str(mnt / "disk"), str(cur), 10 ** 18) == ["not_enough_space"]


def test_a_request_is_dropped_once_and_the_status_follows_the_helper(tmp_path):
    m, req, status, mnt = make(tmp_path)
    assert m.capable and m.request(str(mnt / "disk")) == "requested"
    assert json.loads((req / "move").read_text()) == {"dest": str(mnt / "disk")}
    assert m.request(str(mnt / "disk")) == "busy" and m.status()["state"] == "requested"
    (req / "move").unlink()                                                            # the helper took it
    (status / "move.json").write_text(json.dumps({"state": "running", "message": "Copying the clips", "from": "/a", "to": "/b"}))
    s = m.status()
    assert s["state"] == "running" and s["message"] == "Copying the clips" and s["to"] == "/b" and not s["stalled"]
    (status / "move.json").write_text(json.dumps({"state": "done", "message": "ok"}))
    assert m.status()["state"] == "done" and m.request(str(mnt / "disk")) == "requested"


def test_without_the_helper_nothing_can_be_requested(tmp_path):
    m, *_ = make(tmp_path, capable=False)
    assert not m.capable and m.request("/mnt/x") == "unavailable"
    assert Mover(None, None).status()["state"] == "idle" and not Mover(None, None).active()


def test_a_move_holds_clips_back_only_while_its_helper_is_alive(tmp_path):
    m, req, status, _ = make(tmp_path)
    (req / "move").write_text("{}")
    assert m.active(now=time.time())
    old = time.time() - 3600
    os.utime(req / "move", (old, old))                                                  # nobody picked it up for an hour
    m._cache = (0.0, False)
    assert not m.active(now=time.time())
    (req / "move").unlink()
    (status / "move.json").write_text(json.dumps({"state": "running"}))
    m._cache = (0.0, False)
    assert m.active(now=time.time())
    os.utime(status / "move.json", (old, old))                                          # the helper stopped reporting
    m._cache = (0.0, False)
    assert not m.active(now=time.time()) and m.status()["stalled"]


async def test_clips_are_not_kept_nor_purged_during_a_move(client, tmp_path):
    e = client.engine
    e.mover, req, status, _ = make(tmp_path)
    (req / "move").write_text("{}")
    e.store.add({"id": "m", "source": "salon", "mid": BARK, "class": "Bark", "score": 0.7, "threshold": 0.5, "duration_s": 1, "level_dbfs": -30,
                 "started_at": NOW.isoformat(), "detected_at": NOW.isoformat()})
    e._handle("salon", {"type": "clip", "id": "m", "mid": BARK, "pcm": np.zeros(16000, dtype=np.int16), "meta": {}, "retention_days": 7})
    assert e.clips.usage()["clips"] == 0 and e.store.count_reason("moving") == 1
    e.cfg["storage"]["clips_max_gb"] = 1e-9
    e._clip_bytes = 10 ** 9
    assert e._enforce_quota() == 0, "the quota does not delete while the clips are being copied"


async def test_the_api_checks_then_asks_the_helper(client, tmp_path):
    e = client.engine
    e.mover, req, status, mnt = make(tmp_path)
    r = await client.post("/api/v1/storage/move", headers=H, json={"path": "relative"})
    assert r.status == 422 and (await r.json())["errors"] == ["not_absolute"]
    r = await client.post("/api/v1/storage/move", headers=H, json={"path": str(mnt / "disk")})
    assert r.status == 202 and (await r.json())["state"] == "requested"
    assert json.loads((req / "move").read_text())["dest"] == str(mnt / "disk")
    assert (await client.post("/api/v1/storage/move", headers=H, json={"path": str(mnt / "disk")})).status == 409
    s = await (await client.get("/api/v1/storage", headers=H)).json()
    assert s["move"]["state"] == "requested" and s["move"]["capable"] and s["move"]["roots"] == [str(mnt)]


async def test_the_api_says_when_the_installation_cannot_move_the_clips(client, tmp_path):
    client.engine.mover, *_ = make(tmp_path, capable=False)
    assert (await client.post("/api/v1/storage/move", headers=H, json={"path": "/mnt/x"})).status == 501
    assert (await client.post("/api/v1/storage/move", json={"path": "/mnt/x"})).status == 401


def keep(status, *paths):
    (status / "move-old").write_text("\n".join(str(p) for p in paths) + "\n")


def old_folder(tmp_path, name="old", extra=False):
    old = tmp_path / name
    (old / "2026-10-01").mkdir(parents=True)
    (old / "2026-10-01/a.wav").write_bytes(b"x" * 1000)
    (old / "2026-10-01/a.json").write_text("{}")
    if extra:
        (old / "notes.txt").write_text("mine")
    return old


def test_old_folders_say_what_they_hold_and_what_the_helper_cannot_do(tmp_path):
    m, _, status, _ = make(tmp_path)
    plain, mixed = old_folder(tmp_path, "plain"), old_folder(tmp_path, "mixed", extra=True)
    keep(status, plain, mixed, tmp_path / "gone")
    rows = {r["path"]: r for r in m.old_folders()}
    assert set(rows) == {str(plain), str(mixed)}, "a folder that no longer exists is not offered"
    assert rows[str(plain)]["clips"] == 1 and rows[str(plain)]["bytes"] == 1002 and rows[str(plain)]["notes"] == []
    assert rows[str(mixed)]["other"] == 1 and rows[str(mixed)]["notes"] == ["other_files"]
    helperless = Mover(str(tmp_path / "req"), str(status))
    (status / "move-capable").unlink()
    assert "no_helper" in helperless.old_folders()[0]["notes"]


def test_the_current_folder_is_never_offered_for_deletion(tmp_path):
    m, _, status, _ = make(tmp_path)
    cur, other = old_folder(tmp_path, "cur"), old_folder(tmp_path, "other")
    keep(status, cur, other)
    assert [r["path"] for r in m.old_folders(str(cur))] == [str(other)]


def test_a_deletion_can_only_be_asked_for_a_folder_the_helper_listed(tmp_path):
    m, req, status, _ = make(tmp_path)
    old = old_folder(tmp_path)
    keep(status, old)
    assert m.request_delete(str(tmp_path / "elsewhere")) == "unknown"
    assert m.request_delete(str(old)) == "requested" and json.loads((req / "move-delete").read_text()) == {"old": str(old)}
    assert m.clean_status()["state"] == "requested" and m.request_delete(str(old)) == "busy"
    (req / "move-delete").unlink()
    (status / "clean.json").write_text(json.dumps({"state": "done", "message": "ok", "path": str(old)}))
    s = m.clean_status()
    assert s["state"] == "done" and s["message"] == "ok" and s["path"] == str(old)


async def test_the_api_lists_old_folders_and_deletes_only_listed_ones(client, tmp_path):
    e = client.engine
    e.mover, req, status, _ = make(tmp_path)
    old = old_folder(tmp_path)
    keep(status, old)
    s = await (await client.get("/api/v1/storage", headers=H)).json()
    assert s["move"]["old"][0]["path"] == str(old) and s["move"]["old"][0]["clips"] == 1 and s["move"]["clean"]["state"] == "idle"
    assert (await client.post("/api/v1/storage/old/delete", headers=H, json={"path": "/etc"})).status == 404
    r = await client.post("/api/v1/storage/old/delete", headers=H, json={"path": str(old)})
    assert r.status == 202 and json.loads((req / "move-delete").read_text()) == {"old": str(old)}
    assert (await client.post("/api/v1/storage/old/delete", headers=H, json={"path": str(old)})).status == 409
    assert (await client.post("/api/v1/storage/old/delete", json={"path": str(old)})).status == 401


async def test_the_api_says_when_nothing_can_delete(client, tmp_path):
    client.engine.mover, *_ = make(tmp_path, capable=False)
    assert (await client.post("/api/v1/storage/old/delete", headers=H, json={"path": "/x"})).status == 501
