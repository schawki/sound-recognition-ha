"""Clip management: size of each clip, filters (source, sound, usage, period), deletion one by one, selected, matching, all."""
import datetime as dt
import os

import numpy as np
import pytest
import yaml
from aiohttp.test_utils import TestClient, TestServer

from soundrec import api, catalog as cm, settings as st
from soundrec.engine import Engine

CAT = st.Catalog(cm.load_raw())
BARK, SHOUT = CAT.get("Bark")["mid"], CAT.get("Shout")["mid"]
H = {"Authorization": "Bearer tok"}
NOW = dt.datetime(2026, 6, 20, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
async def client(tmp_path):
    cfgp = tmp_path / "c.yaml"
    yaml.safe_dump({"storage": {"clips_dir": str(tmp_path / "clips"), "db_path": str(tmp_path / "e.sqlite")}, "api": {"token": "tok"},
                    "sources": [{"id": "salon", "type": "file", "url": "x"}, {"id": "jardin", "type": "file", "url": "y"}]}, open(cfgp, "w"))

    class Clf:
        def predict(self, x):
            return np.zeros(521, dtype=np.float32)

    eng = Engine(str(cfgp), "unused", classifier=Clf())
    c = TestClient(TestServer(api.make_app(eng)))
    await c.start_server()
    c.engine = eng
    yield c
    await c.close()


def add_clip(eng, event_id, source, mid, name, days_ago, seconds=1.0):
    when = NOW - dt.timedelta(days=days_ago)
    eng.store.add({"id": event_id, "source": source, "mid": mid, "class": name, "score": 0.7, "threshold": 0.5, "duration_s": 1, "level_dbfs": -30,
                   "started_at": when.isoformat(), "detected_at": when.isoformat()})
    rel, expires = eng.clips.write(event_id, np.zeros(int(16000 * seconds), dtype=np.int16), {"source": source}, 7, when)
    eng.store.set_clip(event_id, rel, expires.isoformat())


@pytest.fixture
def filled(client):
    e = client.engine
    add_clip(e, "a", "salon", BARK, "Bark", 10, 1.0)      # 32 044+ bytes
    add_clip(e, "b", "jardin", BARK, "Bark", 5, 2.0)
    add_clip(e, "c", "jardin", SHOUT, "Shout", 1, 1.0)
    add_clip(e, "d", "salon", SHOUT, "Shout", 0, 0.5)
    return client


async def listing(c, query=""):
    r = await c.get(f"/api/v1/clips{query}", headers=H)
    assert r.status == 200
    return await r.json()


async def test_each_clip_has_a_size_and_the_totals_match_the_disk(filled):
    r = await listing(filled)
    assert [x["id"] for x in r["clips"]] == ["d", "c", "b", "a"] and r["total"] == 4          # newest first
    sizes = {x["id"]: x["size"] for x in r["clips"]}
    assert sizes["b"] > sizes["a"] > sizes["d"] > 16000 and r["clips"][0]["name"] == "Shout"
    assert r["sounds"] == [{"mid": BARK, "name": "Bark", "count": 2}, {"mid": SHOUT, "name": "Shout", "count": 2}]
    assert (await listing(filled, f"?mid={BARK.replace('/', '%2F')}"))["sounds"] == r["sounds"]       # choosing a sound keeps the others on offer
    assert [x["name"] for x in (await listing(filled, "?usage=animals"))["sounds"]] == ["Bark"]
    assert r["total_bytes"] == sum(sizes.values()) == r["disk"]["bytes"] and r["disk"]["clips"] == 4 and r["disk"]["free_bytes"] > 0


async def test_filters_by_source_sound_usage_and_period(filled):
    assert [x["id"] for x in (await listing(filled, "?source=jardin"))["clips"]] == ["c", "b"]
    assert [x["id"] for x in (await listing(filled, f"?mid={SHOUT.replace('/', '%2F')}"))["clips"]] == ["d", "c"]
    animals = await listing(filled, "?usage=animals")
    assert [x["id"] for x in animals["clips"]] == ["b", "a"] and animals["total"] == 2         # only the barks
    since = (NOW - dt.timedelta(days=6)).timestamp()
    until = (NOW - dt.timedelta(days=0.5)).timestamp()
    both = await listing(filled, f"?usage=animals&source=jardin&since={since}&until={until}")
    assert [x["id"] for x in both["clips"]] == ["b"]
    assert [x["id"] for x in (await listing(filled, f"?since={since}&until={until}"))["clips"]] == ["c", "b"]
    assert (await listing(filled, "?usage=animals&mid=" + SHOUT.replace("/", "%2F")))["total"] == 0   # no sound is in both
    assert (await filled.get("/api/v1/clips?usage=nope", headers=H)).status == 400
    assert (await filled.get("/api/v1/clips?since=abc", headers=H)).status == 400


async def test_paging_keeps_the_totals_of_the_whole_selection(filled):
    p1 = await listing(filled, "?limit=3")
    p2 = await listing(filled, "?limit=3&offset=3")
    assert [x["id"] for x in p1["clips"]] == ["d", "c", "b"] and [x["id"] for x in p2["clips"]] == ["a"]
    assert p1["total"] == p2["total"] == 4 and p1["total_bytes"] == p2["total_bytes"]


async def post(c, body):
    r = await c.post("/api/v1/clips/delete", json=body, headers=H)
    return r.status, await r.json()


async def test_dry_run_counts_without_deleting(filled):
    total = (await listing(filled))["total_bytes"]
    assert await post(filled, {"filter": {}, "dry_run": True}) == (200, {"count": 4, "bytes": total, "dry_run": True})
    st_, r = await post(filled, {"filter": {"usage": "animals"}, "dry_run": True})
    assert r["count"] == 2 and 0 < r["bytes"] < total
    assert (await listing(filled))["total"] == 4


async def test_delete_one_selected_matching_and_all(filled):
    e = filled.engine
    one = (await listing(filled))["clips"][0]
    assert await post(filled, {"ids": ["d"]}) == (200, {"count": 1, "bytes": one["size"], "dry_run": False})
    assert e.clips.path(one["clip"]) is None and (await listing(filled))["total"] == 3
    assert e.store.query(limit=10) and len(e.store.query(limit=10)) == 4                        # the detection stays in the history
    assert (await post(filled, {"ids": ["d", "zzz"]}))[1]["count"] == 0                         # already gone / unknown: nothing
    _, r = await post(filled, {"ids": ["c", "a"]})
    assert r["count"] == 2 and [x["id"] for x in (await listing(filled))["clips"]] == ["b"]
    add_clip(e, "e", "salon", BARK, "Bark", 2)
    add_clip(e, "f", "salon", SHOUT, "Shout", 2)
    _, r = await post(filled, {"filter": {"usage": "animals"}})
    assert r["count"] == 2 and [x["id"] for x in (await listing(filled))["clips"]] == ["f"]
    _, r = await post(filled, {"filter": {}})
    assert r["count"] == 1 and (await listing(filled)) ["total"] == 0 and (await listing(filled))["disk"]["clips"] == 0
    assert not os.path.isdir(e.cfg["storage"]["clips_dir"]) or not os.listdir(e.cfg["storage"]["clips_dir"])


async def test_deleting_everything_also_removes_files_without_an_event(filled):
    e = filled.engine
    orphan = os.path.join(e.cfg["storage"]["clips_dir"], "2026-01-01")
    os.makedirs(orphan)
    open(os.path.join(orphan, "old.wav"), "wb").write(b"x" * 100)
    assert (await post(filled, {"filter": {}, "dry_run": True}))[1]["count"] == 5
    assert (await post(filled, {"filter": {}}))[1]["count"] == 5
    assert e.clips.usage()["clips"] == 0


async def test_bad_requests(filled):
    for body in ({}, {"ids": ["a"], "filter": {}}, {"ids": "a"}, {"filter": []}, {"filter": {"colour": "red"}}, {"filter": {"usage": "nope"}}):
        assert (await post(filled, body))[0] == 400, body
    assert (await filled.post("/api/v1/clips/delete", data="nope", headers=H)).status == 400
    assert (await filled.post("/api/v1/clips/delete", json={"filter": {}})).status == 401
    assert (await listing(filled))["total"] == 4
