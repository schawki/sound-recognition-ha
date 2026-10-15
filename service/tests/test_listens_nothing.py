"""A source that is on but listens to no sound: the advice, the sounds it proposes for the kind of room, and the grace given to a new source."""
import copy

import pytest

from soundrec import advisor, catalog as cm, config as cfgmod
from soundrec.settings import Catalog
from test_clips import H, client  # noqa: F401  (fixture)

CAT = Catalog(cm.load_raw())
RULE = "listens_to_nothing"


def cfg_with(**src):
    cfg = copy.deepcopy(cfgmod.DEFAULTS)
    cfg["sources"] = [{"id": "k", "type": "rtsp", "url": "rtsp://x", "name": "Kitchen mic", **src}]
    return cfg


def found(cfg, **kw):
    return [w for w in advisor.compute(cfg, **kw) if w["rule"] == RULE]


def test_a_source_with_no_sound_is_reported_and_the_room_preset_is_the_way_out():
    (w,) = found(cfg_with(environment="kitchen"))
    assert w["level"] == "warning" and w["source"] == "k" and w["classes"] == [] and w["applied"] is False
    assert w["apply"] == {"source": "k", "add_presets": ["room_kitchen"]}
    assert "Kitchen mic" in w["message"] and "Kitchen" in w["message"] and "Smoke detector" in w["message"]


def test_without_a_kind_of_room_nothing_is_guessed():
    (w,) = found(cfg_with())
    assert w["apply"] is None and "what kind of place" in w["message"]


def test_the_place_deduced_by_the_integration_is_used_but_the_configuration_wins():
    (w,) = found(cfg_with(), places={"k": "bedroom"})
    assert w["apply"] == {"source": "k", "add_presets": ["room_bedroom"]}
    (w,) = found(cfg_with(environment="kitchen"), places={"k": "bedroom"})
    assert w["apply"]["add_presets"] == ["room_kitchen"]


def test_the_message_follows_the_language():
    (w,) = found(cfg_with(environment="kitchen"), lang="fr")
    assert "n'écoute aucun son" in w["message"] and "préréglage" in w["message"]
    assert "n'écoute aucun son" in found(cfg_with(), lang="fr")[0]["message"]


def test_a_source_that_listens_to_something_is_left_alone():
    assert found(cfg_with(environment="kitchen", classes={"Bark": {"enabled": True}})) == []


def test_a_sound_enabled_for_all_the_sources_counts():
    cfg = cfg_with(environment="kitchen")
    cfg["classes"] = {"Bark": {"enabled": True}}
    assert found(cfg) == []


def test_a_preset_on_the_source_counts_once_folded_in():
    from soundrec import settings as st
    cfg = cfg_with(environment="kitchen", presets=["room_kitchen"])
    assert found(st.fold(cfg, CAT)) == []                                         # the effective configuration is what the advisor reads


def test_a_source_that_is_off_is_not_reported():
    assert found(cfg_with(enabled=False)) == []


def test_a_new_source_is_given_an_hour_to_be_set_up():
    assert found(cfg_with(), ages={"k": 600}) == []
    assert len(found(cfg_with(), ages={"k": 3700})) == 1
    assert len(found(cfg_with())) == 1                                           # without ages (the check made when saving) it is immediate


def test_it_can_be_ignored_for_a_source_that_is_paused_on_purpose():
    cfg = cfg_with(advice={RULE: "ignore"})
    assert found(cfg) == []
    cfg = cfg_with()
    cfg["advice"] = {RULE: "info"}
    (w,) = found(cfg)
    assert w["level"] == "info"
    assert cfgmod.validate(cfgmod._merge(cfgmod.DEFAULTS, {"sources": [{"id": "k", "type": "file", "url": "x", "advice": {RULE: "ignore"}}]}), CAT) == []


@pytest.mark.asyncio
async def test_the_service_waits_an_hour_after_it_first_sees_a_source(client):
    eng = client.engine
    body = await (await client.get("/api/v1/warnings", headers=H)).json()
    assert not [w for w in body["warnings"] if w["rule"] == RULE]                  # just seen: given time
    for sid in ("salon", "jardin"):
        eng.store.db.execute("UPDATE source_seen SET first_seen = first_seen - 4000 WHERE source = ?", (sid,))
    body = await (await client.get("/api/v1/warnings", headers=H)).json()
    assert {w["source"] for w in body["warnings"] if w["rule"] == RULE} == {"salon", "jardin"}


@pytest.mark.asyncio
async def test_the_check_made_when_saving_is_not_delayed(client):
    cand = {**client.engine.cfg, "sources": [{"id": "n", "type": "file", "url": "x", "environment": "bedroom"}]}
    r = await client.post("/api/v1/config/validate", headers=H, json=cand)
    body = await r.json()
    assert [w["apply"] for w in body["warnings"] if w["rule"] == RULE] == [{"source": "n", "add_presets": ["room_bedroom"]}]
