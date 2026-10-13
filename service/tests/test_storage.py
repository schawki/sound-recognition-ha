"""Storage of the clips: figures, the two limits chosen by the administrator, and the change of API token."""
import time

import numpy as np

from test_clips import BARK, H, NOW, add_clip, client, filled  # noqa: F401  (fixtures)


async def test_storage_reports_size_growth_and_limits(filled):
    r = await filled.get("/api/v1/storage", headers=H)
    assert r.status == 200
    s = await r.json()
    assert s["clips"] == 4 and s["bytes"] > 100000 and s["free_bytes"] > 0 and s["total_bytes"] >= s["free_bytes"]
    assert s["path"].endswith("clips") and s["max_gb"] is None and s["min_free_gb"] is None and s["paused"] is False
    assert s["auto_deleted"] == 0 and s["skipped"] == 0


async def test_the_token_can_be_changed_and_the_old_one_lives_a_minute(client):
    r = await client.post("/api/v1/token/rotate", headers=H)
    new = (await r.json())["token"]
    assert new != "tok" and len(new) >= 24
    assert (await client.get("/api/v1/sources", headers={"Authorization": f"Bearer {new}"})).status == 200
    assert (await client.get("/api/v1/sources", headers=H)).status == 200                  # grace period
    client.engine._prev_token = ("tok", time.time() - 1)                                   # the minute is over
    assert (await client.get("/api/v1/sources", headers=H)).status == 401
    assert new in open(client.engine.config_path).read()                                   # kept for the next start


async def test_over_the_limit_the_oldest_clips_go_first_and_judged_ones_last(filled):
    e = filled.engine
    e.store.set_feedback("b", "good")                                                      # judged
    e.cfg["storage"]["clips_max_gb"] = 100000 / 1e9
    e._clip_bytes = e.clips.usage()["bytes"]
    assert e._enforce_quota() == 2
    left = {r["id"] for r in e.store.clips()}
    assert left == {"b", "d"}                                                              # a (oldest) and c went; b was judged, d is the newest
    assert e._clip_bytes <= 100000 * 0.9
    assert e.store.count_reason("quota") == 2


async def test_without_a_limit_nothing_is_deleted(filled):
    e = filled.engine
    e._clip_bytes = e.clips.usage()["bytes"]
    assert e._enforce_quota() == 0 and len(e.store.clips()) == 4


async def test_clips_are_not_kept_while_the_free_space_is_low(client):
    e = client.engine
    e.cfg["storage"]["clips_min_free_gb"] = 1.0
    ev = {"type": "clip", "id": "z", "mid": BARK, "pcm": np.zeros(16000, dtype=np.int16), "meta": {}, "retention_days": 7}

    def detect(event_id):
        e.store.add({"id": event_id, "source": "salon", "mid": BARK, "class": "Bark", "score": 0.7, "threshold": 0.5, "duration_s": 1, "level_dbfs": -30,
                     "started_at": NOW.isoformat(), "detected_at": NOW.isoformat()})
    detect("z")
    e.clips.free_bytes = lambda: 0.5e9                                                     # under the limit
    e._handle("salon", ev)
    assert e.clips.usage()["clips"] == 0 and e.store.count_reason("disk_low") == 1
    e.clips.free_bytes = lambda: 1.05e9                                                    # above, but not 10 % above: still paused
    detect("y"); e._handle("salon", dict(ev, id="y"))
    assert e.clips.usage()["clips"] == 0 and e._paused is True
    e.clips.free_bytes = lambda: 1.2e9                                                     # back
    detect("x"); e._handle("salon", dict(ev, id="x"))
    assert e.clips.usage()["clips"] == 1 and e._paused is False


async def test_the_limits_are_checked_when_the_configuration_is_saved(client):
    cfg = dict(client.engine.cfg)
    cfg["storage"] = dict(cfg["storage"], clips_max_gb=-3)
    r = await client.put("/api/v1/config", json=cfg, headers=H)
    assert r.status == 422 and "clips_max_gb" in "".join((await r.json())["errors"])
    cfg["storage"] = dict(cfg["storage"], clips_max_gb=5, clips_min_free_gb=2)
    assert (await client.put("/api/v1/config", json=cfg, headers=H)).status == 200
