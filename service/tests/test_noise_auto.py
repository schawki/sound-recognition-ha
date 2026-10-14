"""Automatic minimum volume: a source set to automatic follows the noise measurements, once a day, and only for a real change."""
import datetime as dt

import pytest

from soundrec import config, settings as st
from test_clips import H, client  # noqa: F401  (fixture)
from test_detector import CAT

NOW = dt.datetime(2026, 10, 14, 12, 0, tzinfo=dt.timezone.utc)
M0 = int(NOW.timestamp() // 60) - 500


def measure(eng, sid, level, n=500):
    eng.store.add_noise(sid, [(M0 + i, level, False) for i in range(n)])


def set_auto(eng, sid="salon", value=True, defaults=None):
    for s in eng.cfg["sources"]:
        if s["id"] == sid:
            s["min_volume_auto"] = value
    if defaults is not None:
        eng.cfg["defaults"]["min_volume_auto"] = defaults
    eng._rebuild()


def gate(eng, sid="salon"):
    return eng._gate_of(sid)


def test_manual_is_the_default_and_nothing_moves(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    assert eng._auto_volume(NOW) is False and gate(eng) == (-60, "defaults")


def test_a_source_set_to_automatic_follows_the_suggestion(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    set_auto(eng)
    assert eng._auto_volume(NOW) is True
    eng._rebuild()
    assert gate(eng) == (-69, "auto")                                  # -75 + 6 dB margin
    assert eng.store.auto_history("salon") == [{"ts": NOW.timestamp(), "old": -60, "new": -69}]
    assert gate(eng, "jardin") == (-60, "defaults")                    # the other source stays manual


def test_the_defaults_make_every_source_automatic_and_a_source_can_opt_out(client):
    eng = client.engine
    for sid in ("salon", "jardin"):
        measure(eng, sid, -75.0)
    set_auto(eng, "jardin", False, defaults=True)
    assert eng._auto_volume(NOW) is True
    eng._rebuild()
    assert gate(eng, "salon")[1] == "auto" and gate(eng, "jardin") == (-60, "defaults")


def test_not_enough_calm_minutes_changes_nothing_but_is_not_asked_again_today(client):
    eng = client.engine
    measure(eng, "salon", -75.0, n=100)
    set_auto(eng)
    assert eng._auto_volume(NOW) is False and gate(eng) == (-60, "defaults")
    measure(eng, "salon", -75.0, n=500)
    assert eng._auto_volume(NOW + dt.timedelta(hours=3)) is False       # looked at once a day
    assert eng._auto_volume(NOW + dt.timedelta(hours=25)) is True


def test_a_small_difference_does_not_move_the_gate(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    set_auto(eng)
    eng._auto_volume(NOW)
    eng._rebuild()
    eng.store.delete_noise("salon")
    measure(eng, "salon", -73.0)                                       # suggestion -67, in use -69: under 3 dB apart
    assert eng._auto_volume(NOW + dt.timedelta(days=1, minutes=1)) is False
    assert gate(eng) == (-69, "auto")
    eng.store.delete_noise("salon")
    measure(eng, "salon", -65.0)                                       # suggestion -59: 10 dB apart
    assert eng._auto_volume(NOW + dt.timedelta(days=2, minutes=2)) is True
    eng._rebuild()
    assert gate(eng) == (-59, "auto") and [h["new"] for h in eng.store.auto_history("salon")] == [-59, -69]


def test_the_gate_of_a_source_that_is_set_back_to_manual_is_the_configured_one(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    set_auto(eng)
    eng._auto_volume(NOW)
    eng._rebuild()
    set_auto(eng, value=False)
    assert gate(eng) == (-60, "defaults")


def test_erasing_the_measurements_keeps_the_gate_in_use(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    set_auto(eng)
    eng._auto_volume(NOW)
    eng._rebuild()
    eng.store.delete_noise()
    assert gate(eng) == (-69, "auto")


def test_the_gate_survives_a_restart(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    set_auto(eng)
    eng._auto_volume(NOW)
    assert {k: v[0] for k, v in eng.store.auto_state().items()} == {"salon": -69}


def test_a_gate_set_for_one_sound_on_a_source_still_wins():
    cfg = {"sources": [{"id": "s", "type": "file", "url": "x", "min_volume_auto": True, "classes": {"Bark": {"min_volume_dbfs": -80}}}],
           "classes": {}, "defaults": {"min_volume_dbfs": -60}}
    eff = st.apply_auto_volume(cfg, {"s": -69})
    r = st.resolve(eff, CAT, "s", "Bark")
    assert r["min_volume_dbfs"] == -80 and r["provenance"]["min_volume_dbfs"] == "source_class"


def test_the_origin_is_auto_for_the_sounds_that_follow_the_source():
    cfg = {"sources": [{"id": "s", "type": "file", "url": "x", "min_volume_auto": True}], "classes": {}, "defaults": {"min_volume_dbfs": -60}}
    eff = st.apply_auto_volume(cfg, {"s": -69})
    r = st.resolve(eff, CAT, "s", "Bark")
    assert r["min_volume_dbfs"] == -69 and r["provenance"]["min_volume_dbfs"] == "auto"
    assert cfg["sources"][0].get("min_volume_dbfs") is None             # the stored configuration is never changed


def test_validation():
    base = {"classes": {"Bark": {"enabled": True}}, "sources": [{"id": "s", "type": "file", "url": "x"}]}
    ok = config._merge(config.DEFAULTS, {**base, "defaults": {"min_volume_auto": True}})
    ok["sources"][0]["min_volume_auto"] = False
    assert config.validate(ok, CAT) == []
    bad = config._merge(config.DEFAULTS, {**base, "defaults": {"min_volume_auto": "yes"}})
    bad["sources"][0]["min_volume_auto"] = 1
    errs = config.validate(bad, CAT)
    assert any("defaults.min_volume_auto" in e for e in errs) and any("sources[0](s).min_volume_auto" in e for e in errs)


@pytest.mark.asyncio
async def test_the_api_shows_the_gate_its_origin_and_the_history(client):
    eng = client.engine
    measure(eng, "salon", -75.0)
    set_auto(eng)
    eng._auto_volume(NOW)
    eng._rebuild()
    body = await (await client.get("/api/v1/noise", headers=H)).json()
    by = {s["id"]: s for s in body["sources"]}
    assert body["step_db"] == 3
    assert by["salon"]["current_gate"] == -69 and by["salon"]["gate_origin"] == "auto"
    assert by["salon"]["auto"]["enabled"] is True and by["salon"]["auto"]["gate"] == -69 and by["salon"]["auto"]["history"][0]["old"] == -60
    assert by["jardin"]["gate_origin"] == "defaults" and by["jardin"]["auto"]["enabled"] is False
    status = {s["id"]: s for s in eng.status()}
    assert status["salon"]["min_volume_dbfs"] == -69 and status["salon"]["min_volume_origin"] == "auto" and status["salon"]["min_volume_auto"] is True
    assert status["jardin"]["min_volume_origin"] == "defaults" and status["jardin"]["min_volume_auto"] is False
