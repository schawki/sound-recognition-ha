"""Noise measurements: what is kept, the suggestion made from it, and the way to forget it."""
import datetime as dt

import pytest

from soundrec import noise
from soundrec.detector import SourcePipeline
from soundrec.store import EventStore
from test_clips import H, client  # noqa: F401  (fixture)
from test_detector import CAT, Fake, T0, loud, make_cfg, run


def minutes(levels, start=29_000_000, event=()):
    return [(start + i, lv, 1 if i in event else 0) for i, lv in enumerate(levels)]


def test_not_enough_data_gives_no_suggestion():
    out = noise.summarize(minutes([-60.0] * 100))
    assert out["suggestion"] == {"status": "not_enough", "minutes": 100, "needed": noise.MIN_MINUTES}
    assert out["minutes"] == 100 and out["bytes"] == 100 * noise.BYTES_PER_MINUTE
    assert noise.summarize([])["minutes"] == 0 and noise.summarize([])["since"] is None


def test_suggestion_is_the_quiet_level_plus_the_margin():
    rows = minutes([-70.0] * 300 + [-40.0] * 100 + [-70.0] * 100)               # 500 minutes: quiet room, a noisy period
    s = noise.summarize(rows)["suggestion"]
    assert s["status"] == "ready" and s["quiet_dbfs"] == -70.0 and s["gate"] == -64
    assert s["typical_dbfs"] == -70.0 and s["loud_dbfs"] == -40.0 and s["capped"] is False


def test_minutes_with_a_detection_are_left_out():
    quiet = [-70.0] * 400
    noisy_but_detected = [-20.0] * 200
    rows = minutes(quiet + noisy_but_detected, event=range(400, 600))
    out = noise.summarize(rows)
    assert out["calm_minutes"] == 400 and out["suggestion"]["gate"] == -64 and out["minutes"] == 600


def test_the_gate_never_goes_above_the_limit_that_keeps_alarms_audible():
    s = noise.summarize(minutes([-30.0] * 500))["suggestion"]
    assert s["gate"] == -50 and s["capped"] is True                              # a noisy room: capped, and it says so


def test_the_gate_stays_in_the_valid_range():
    assert noise.summarize(minutes([-100.0] * 500))["suggestion"]["gate"] == -90


def test_hourly_profile_follows_the_time_zone():
    start = int(dt.datetime(2026, 10, 5, 0, 0, tzinfo=dt.timezone.utc).timestamp() // 60)
    rows = [(start + i, -70.0 if (i // 60) % 24 < 12 else -60.0, 0) for i in range(24 * 60)]
    h = noise.summarize(rows, "UTC")["hourly"]
    assert h[0] == -70.0 and h[11] == -70.0 and h[12] == -60.0 and h[23] == -60.0
    assert noise.summarize(rows, "Etc/GMT-2")["hourly"][2] == -70.0               # two hours ahead of UTC: the profile shifts


def test_store_keeps_counts_and_forgets(tmp_path):
    st = EventStore(str(tmp_path / "e.sqlite"))
    st.add_noise("a", [(1, -60.0, False), (2, -61.0, True)])
    st.add_noise("a", [(2, -62.0, False)])                                        # same minute: replaced, not duplicated
    st.add_noise("b", [(1, -50.0, False)])
    assert st.noise_counts() == {"a": 2, "b": 1}
    assert st.noise_rows("a") == [(1, -60.0, 0), (2, -62.0, 0)]
    st.purge_noise(2)
    assert st.noise_counts() == {"a": 1}                                          # minute 1 of both sources is older than the cut
    assert st.delete_noise("a") == 1 and st.noise_counts() == {}
    st.add_noise("a", [(1, -60.0, False)]); st.add_noise("b", [(1, -60.0, False)])
    assert st.delete_noise() == 2 and st.noise_counts() == {}


def test_the_pipeline_hands_over_one_record_per_completed_minute():
    cfg = make_cfg({"Bark": {"enabled": True}}, timezone="UTC")
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": 0.0}))
    run(p, 200)
    rows = p.take_noise()
    assert 2 <= len(rows) <= 4 and all(-60 < lv < -10 for _, lv, _ in rows) and not any(ev for *_, ev in rows)
    assert p.take_noise() == []                                                   # handed over once
    assert [r[0] for r in rows] == sorted({r[0] for r in rows})                   # one per minute


def test_a_detection_marks_its_minute():
    cfg = make_cfg({"Bark": {"enabled": True, "min_duration_s": 0}}, timezone="UTC")
    p = SourcePipeline(cfg["sources"][0], cfg, CAT, Fake({"Bark": lambda n: 0.9 if n == 40 else 0.0}))
    run(p, 200)
    assert sum(1 for *_, ev in p.take_noise() if ev) == 1


@pytest.mark.asyncio
async def test_api_lists_what_is_measured_and_forgets_it(client):
    eng = client.engine
    eng.store.add_noise("salon", [(m, -65.0, False) for m in range(1000, 1000 + 400)])
    eng.store.add_noise("jardin", [(m, -45.0, False) for m in range(1000, 1010)])
    body = await (await client.get("/api/v1/noise", headers=H)).json()
    assert body["recording"] is True and body["retention_days"] == 7
    by = {s["id"]: s for s in body["sources"]}
    assert by["salon"]["minutes"] == 400 and by["salon"]["suggestion"]["status"] == "ready" and by["salon"]["suggestion"]["gate"] == -59
    assert by["jardin"]["minutes"] == 10 and by["jardin"]["suggestion"]["status"] == "not_enough"
    assert by["salon"]["current_gate"] == -60                                     # the default gate, shown next to the suggestion
    r = await client.post("/api/v1/noise/delete", headers=H, json={"source": "jardin"})
    assert r.status == 200 and (await r.json()) == {"deleted": 10}
    assert eng.store.noise_counts() == {"salon": 400}
    assert (await client.post("/api/v1/noise/delete", headers=H, json={"source": "nope"})).status == 400
    assert (await (await client.post("/api/v1/noise/delete", headers=H)).json()) == {"deleted": 400}
    assert eng.store.noise_counts() == {}


@pytest.mark.asyncio
async def test_noise_needs_the_token(client):
    assert (await client.get("/api/v1/noise")).status in (401, 403)
    assert (await client.post("/api/v1/noise/delete", json={})).status in (401, 403)


def test_retention_is_validated_and_zero_means_measure_nothing():
    from soundrec import config
    base = {"classes": {"Bark": {"enabled": True}}, "sources": [{"id": "s", "type": "file", "url": "x"}]}
    assert config.validate(config._merge(config.DEFAULTS, base), CAT) == []
    assert config.DEFAULTS["storage"]["noise_retention_days"] == 7
    for ok in (0, 1, 90):
        assert config.validate(config._merge(config.DEFAULTS, {**base, "storage": {"noise_retention_days": ok}}), CAT) == []
    for bad in (-1, 91, "7", None):
        assert any("noise_retention_days" in e for e in config.validate(config._merge(config.DEFAULTS, {**base, "storage": {"noise_retention_days": bad}}), CAT))


@pytest.mark.asyncio
async def test_nothing_is_recorded_when_retention_is_zero(client):
    eng = client.engine
    eng.cfg["storage"]["noise_retention_days"] = 0
    body = await (await client.get("/api/v1/noise", headers=H)).json()
    assert body["recording"] is False and body["retention_days"] == 0
