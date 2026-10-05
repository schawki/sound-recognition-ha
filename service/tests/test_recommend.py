import datetime as dt

import numpy as np
import pytest
import yaml
from aiohttp.test_utils import TestClient, TestServer

from soundrec import api, catalog as cm, config as cfgmod, recommend, settings as st
from soundrec.engine import Engine
from soundrec.store import EventStore

CAT = st.Catalog(cm.load_raw())
TV, RADIO, MUSIC = CAT.get("Television")["mid"], CAT.get("Radio")["mid"], CAT.get("Music")["mid"]
BARK = CAT.get("Bark")["mid"]


def cfg_with(**source):
    cfg = cfgmod._merge(cfgmod.DEFAULTS, {"classes": {"Bark": {"enabled": True}},
                                          "sources": [dict({"id": "salon", "name": "Salon", "type": "file", "url": "x"}, **source)]})
    assert cfgmod.validate(cfg, CAT) == []
    return cfg


def rules(recs):
    return {r["rule"]: r for r in recs}


def test_environments_are_in_the_catalog_in_both_languages():
    for lang in ("en", "fr"):
        envs = {e["id"]: e for e in cm.load_lang(lang)["environments"]}
        assert {"living_tv", "kitchen", "bedroom", "nursery", "office", "entrance", "outdoor", "garage", "dining_room", "bathroom", "laundry", "gym", "storage"} <= set(envs)
        assert all(e["name"] and e["why"] and e["tips"] for e in envs.values())
    assert cm.load_lang("fr")["environments"][0]["name"] != cm.load_lang("en")["environments"][0]["name"]


def test_no_environment_asks_for_one():
    r = rules(recommend.compute(cfg_with()))
    assert set(r) == {"set_environment"} and r["set_environment"]["apply"] is None and "Salon" in r["set_environment"]["message"]


def test_living_room_recommends_contexts_and_adaptive_with_an_applicable_patch():
    r = rules(recommend.compute(cfg_with(environment="living_tv")))
    ctx = r["enable_contexts"]
    assert set(ctx["classes"]) == {TV, RADIO, MUSIC} and ctx["apply"]["class_patch"][TV] == {"enabled": True}
    assert r["enable_adaptive"]["apply"] == {"source": "salon", "source_patch": {"adaptive": {"enabled": True}}}
    assert "Television" in ctx["message"] and "Salon" in ctx["message"]
    fr = rules(recommend.compute(cfg_with(environment="living_tv"), "fr"))
    assert "Salon" in fr["enable_contexts"]["message"] and "activez" in fr["enable_contexts"]["message"]


def test_what_is_applied_stays_in_the_list_marked_as_applied():
    cfg = cfg_with(environment="living_tv", adaptive={"enabled": True}, classes={TV: {"enabled": True}, RADIO: {"enabled": True}, MUSIC: {"enabled": True}})
    r = rules(recommend.compute(cfg))
    assert r["enable_contexts"]["applied"] and r["enable_adaptive"]["applied"]
    assert set(r["enable_contexts"]["classes"]) == {TV, RADIO, MUSIC}            # the whole set, so the panel can tell what it is about
    cfg = cfg_with(environment="living_tv")
    r = rules(recommend.compute(cfg))
    assert not r["enable_contexts"]["applied"] and not r["enable_adaptive"]["applied"]
    cfg = cfg_with(environment="bedroom")                     # quiet room: adaptive not recommended
    assert "enable_adaptive" not in rules(recommend.compute(cfg))
    cfg["classes"][TV] = {"enabled": True}                    # enabled globally also counts
    cfg["classes"][MUSIC] = {"enabled": True}
    assert rules(recommend.compute(cfg))["enable_contexts"]["applied"]


def test_partly_applied_lists_only_what_is_missing_and_is_not_applied():
    cfg = cfg_with(environment="living_tv", classes={TV: {"enabled": True}})
    row = rules(recommend.compute(cfg))["enable_contexts"]
    assert not row["applied"] and set(row["classes"]) == {RADIO, MUSIC} and set(row["apply"]["class_patch"]) == {RADIO, MUSIC}


def test_false_detections_propose_a_higher_threshold_only_when_repeated():
    cfg = cfg_with(environment="nursery")
    rows = [{"source": "salon", "mid": BARK, "class": "Bark", "score": 0.58}, {"source": "salon", "mid": BARK, "class": "Bark", "score": 0.68}]
    r = rules(recommend.compute(cfg, "en", None, rows))["raise_threshold"]
    assert r["apply"]["class_patch"] == {BARK: {"threshold": 0.71}} and "2 detections" in r["message"]
    assert "raise_threshold" not in rules(recommend.compute(cfg, "en", None, rows[:1]))           # one is not enough
    cfg["sources"][0]["classes"] = {BARK: {"threshold": 0.8}}
    assert rules(recommend.compute(cfg, "en", None, rows))["raise_threshold"]["applied"]            # already higher: shown as applied


def test_store_stats_feedback_and_masked(tmp_path):
    store = EventStore(str(tmp_path / "e.sqlite"))
    now = dt.datetime(2026, 10, 5, 12, 0, tzinfo=dt.timezone.utc)
    iso = lambda h: (now - dt.timedelta(hours=h)).isoformat()
    for i, (h, src) in enumerate([(0.2, "a"), (0.5, "a"), (3.5, "b"), (30, "a")]):
        store.add({"id": f"e{i}", "source": src, "mid": BARK, "class": "Bark", "score": 0.6, "threshold": 0.5, "duration_s": 1,
                   "level_dbfs": -30, "started_at": iso(h), "detected_at": iso(h)})
    store.add_masked({"id": "m1", "source": "a", "mid": BARK, "class": "Bark", "score": 0.6, "base_threshold": 0.5, "threshold": 0.65,
                      "reasons": ["context", "ambient"], "detected_at": iso(1)})
    assert store.set_feedback("e0", "false") and not store.set_feedback("nope", "false")
    s = store.stats(now.timestamp(), 24)
    assert s["detections"]["total"] == 3 and s["detections"]["by_source"] == {"a": 2, "b": 1}      # the 30 h old one is outside
    assert len(s["detections"]["hourly"]) == 24 and s["detections"]["hourly"][-1] == 2 and s["detections"]["hourly"][-4] == 1
    assert s["masked"]["total"] == 1 and s["false"]["total"] == 1
    assert store.false_detections(0)[0]["score"] == 0.6
    assert store.query()[0]["feedback"] in (None, "false")
    store.set_feedback("e0", None)
    assert store.stats(now.timestamp(), 24)["false"]["total"] == 0


@pytest.fixture
async def client(tmp_path):
    cfgp = tmp_path / "c.yaml"
    yaml.safe_dump({"storage": {"clips_dir": str(tmp_path / "clips"), "db_path": str(tmp_path / "e.sqlite")},
                    "api": {"token": "tok"}, "classes": {"Bark": {"enabled": True}},
                    "sources": [{"id": "salon", "type": "file", "url": "x", "environment": "living_tv"}]}, open(cfgp, "w"))

    class Clf:
        def predict(self, x):
            return np.zeros(521, dtype=np.float32)

    eng = Engine(str(cfgp), "unused", classifier=Clf())
    c = TestClient(TestServer(api.make_app(eng)))
    await c.start_server()
    c.engine = eng
    yield c
    await c.close()


H = {"Authorization": "Bearer tok"}


async def test_api_recommendations_stats_and_feedback(client):
    r = await (await client.get("/api/v1/recommendations?lang=fr", headers=H)).json()
    assert "enable_contexts" in {x["rule"] for x in r["recommendations"]}
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    client.engine.store.add({"id": "ev1", "source": "salon", "mid": BARK, "class": "Bark", "score": 0.6, "threshold": 0.5,
                             "duration_s": 1, "level_dbfs": -30, "started_at": now, "detected_at": now})
    assert (await client.post("/api/v1/events/ev1/feedback", json={"false": True}, headers=H)).status == 200
    assert (await client.post("/api/v1/events/zzz/feedback", json={"false": True}, headers=H)).status == 404
    assert (await client.post("/api/v1/events/ev1/feedback", json={"false": "maybe"}, headers=H)).status == 400
    s = await (await client.get("/api/v1/stats?hours=6", headers=H)).json()
    assert s["detections"]["total"] == 1 and s["false"]["total"] == 1 and len(s["detections"]["hourly"]) == 6
    assert (await client.get("/api/v1/stats?hours=x", headers=H)).status == 400
    assert (await client.get("/api/v1/stats")).status == 401
    cat = await (await client.get("/api/v1/catalog?lang=fr", headers=H)).json()
    assert any(e["id"] == "living_tv" for e in cat["environments"])
    src = (await (await client.get("/api/v1/sources", headers=H)).json())["sources"][0]
    assert {"active_contexts", "ambient_dbfs", "baseline_dbfs", "adaptive_enabled", "adaptive_offset"} <= set(src)


def test_environment_contexts_are_real_inhibiting_sounds():
    inhibitors = {m for c in CAT.raw["classes"] for m in c["inhibiting_contexts"]}
    for e in CAT.raw["environments"]:
        assert set(e["contexts"]) <= inhibitors, e["id"]          # only sounds that really change thresholds are recommended
        assert e["en"]["tips"] and e["fr"]["tips"] and len(e["en"]["tips"]) == len(e["fr"]["tips"])


async def test_api_external_offset(client):
    ok = {"offset": 0.1, "reasons": ["device"], "detail": [{"label": "TV", "value": 0.1}], "ttl_s": 60}
    await client.engine.start()
    try:
        assert (await client.put("/api/v1/sources/salon/external", json=ok, headers=H)).status == 200
        src = (await (await client.get("/api/v1/sources", headers=H)).json())["sources"][0]
        assert src["external_offset"] == 0.0                  # applied at the next audio window (the stand-in source sends none)
        assert (await client.put("/api/v1/sources/nope/external", json=ok, headers=H)).status == 404
        assert (await client.put("/api/v1/sources/salon/external", json={**ok, "offset": 5}, headers=H)).status == 400
        assert (await client.put("/api/v1/sources/salon/external", json={**ok, "ttl_s": 1}, headers=H)).status == 400
        assert (await client.put("/api/v1/sources/salon/external", json=ok)).status == 401
    finally:
        await client.engine.stop()


async def test_the_place_deduced_by_the_integration_stands_in_for_a_missing_environment(client):
    async def put(sid, body):
        return await client.put(f"/api/v1/sources/{sid}/place", json=body, headers=H)

    cfg = client.engine.cfg
    cfg["sources"][0].pop("environment", None)
    rules = lambda: {x["rule"] for x in client.engine.recommendations("en") if x["source"] == "salon"}
    assert "set_environment" in rules()
    assert (await put("salon", {"environment": "living_tv", "ttl_s": 60})).status == 200
    assert "set_environment" not in rules() and "enable_contexts" in rules()                 # recommendations for a living room, not a request for a place
    cfg["sources"][0]["environment"] = "bedroom"
    assert all("Bedroom" in x["message"] for x in client.engine.recommendations("en") if x["rule"] == "enable_contexts" and x["source"] == "salon")
    from soundrec import recommend
    assert recommend.compute(cfg, "en", None, (), {"salon": "kitchen"}) == recommend.compute(cfg, "en")      # the configuration wins
    cfg["sources"][0].pop("environment")
    assert (await put("salon", {"environment": None})).status == 200 and "set_environment" in rules()       # cleared
    assert (await put("nowhere", {"environment": "kitchen"})).status == 404
    assert (await put("salon", {"environment": "moon"})).status == 404
    assert (await put("salon", {"environment": "kitchen", "ttl_s": 1})).status == 400
    assert (await put("salon", {})).status == 400
    client.engine.set_place("salon", "kitchen", 60)
    client.engine.places["salon"] = ("kitchen", 0)                                          # expired
    assert "set_environment" in rules()
    assert (await client.put("/api/v1/sources/salon/place", json={"environment": "kitchen"})).status == 401
