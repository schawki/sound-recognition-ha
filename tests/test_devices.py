"""Rooms, devices and links: pure maths first, then discovery in the registries and the push to the service."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

import fake_service as fs
from custom_components.sound_recognition import devices as dv
from custom_components.sound_recognition.const import DOMAIN
from test_integration import DATA

OPEN = {"a": "entree", "b": "salon", "type": "open"}
DOOR = {"a": "entree", "b": "cuisine", "type": "door", "sensor": "binary_sensor.porte"}
NODOOR = {"a": "entree", "b": "cuisine", "type": "door"}


# ------------------------------------------------------------------------------------------------ pure
def test_contribution_media_volume_and_states():
    assert dv.contribution("media_player", "playing", {"volume_level": 0.08}, 0.15) == pytest.approx(0.081, abs=1e-3)
    assert dv.contribution("media_player", "playing", {"volume_level": 1.0}, 0.15) == 0.15
    assert dv.contribution("media_player", "playing", {}, 0.15) == 0.09          # no volume known: 60 %
    assert dv.contribution("media_player", "playing", {"volume_level": 0.5, "is_volume_muted": True}, 0.15) == 0
    assert dv.contribution("media_player", "off", {"volume_level": 0.5}, 0.15) == 0
    assert dv.contribution("media_player", "unavailable", {}, 0.15) == 0
    assert dv.contribution("vacuum", "cleaning", {}, 0.15) == 0.12 and dv.contribution("vacuum", "docked", {}, 0.15) == 0
    assert dv.contribution("switch", "on", {}, 0.1) == 0.06 and dv.contribution("switch", "off", {}, 0.1) == 0
    assert dv.contribution("light", "on", {}, 0.1) == 0 and dv.contribution("media_player", None, {}, 0.1) == 0


def test_coupling_open_door_and_two_hops():
    assert dv.coupling("salon", "salon", [], {}) == 1 and dv.coupling(None, "salon", [OPEN], {}) == 1
    assert dv.coupling("salon", "entree", [OPEN], {}) == 1
    assert dv.coupling("salon", "cuisine", [], {}) == 0
    s = {"binary_sensor.porte": "on"}
    assert dv.coupling("entree", "cuisine", [DOOR], s) == 0.7
    assert dv.coupling("entree", "cuisine", [DOOR], {"binary_sensor.porte": "off"}) == 0.15
    assert dv.coupling("entree", "cuisine", [DOOR], {"binary_sensor.porte": "unavailable"}) == pytest.approx(0.425)
    assert dv.coupling("entree", "cuisine", [NODOOR], {}) == pytest.approx(0.425)
    assert dv.coupling("salon", "cuisine", [OPEN, DOOR], s) == 0.7               # salon-entrée open, entrée-cuisine door open
    assert dv.coupling("cuisine", "salon", [OPEN, DOOR], {"binary_sensor.porte": "off"}) == 0.15
    assert dv.coupling("a", "d", [{"a": "a", "b": "b", "type": "open"}, {"a": "b", "b": "c", "type": "open"}, {"a": "c", "b": "d", "type": "open"}], {}) == 0  # 3 hops


def test_reachable_and_combine():
    assert dv.reachable_areas("salon", [OPEN, DOOR]) == {"salon", "entree", "cuisine"}
    assert dv.reachable_areas(None, [OPEN]) == set()
    assert dv.combine([]) == (0.0, [], [])
    off, reasons, detail = dv.combine([{"kind": "device", "label": "TV", "value": 0.09}, {"kind": "shared", "label": "x", "value": 0.15},
                                       {"kind": "device", "label": "off", "value": 0}])
    assert off == 0.15 and reasons == ["device", "shared"] and [d["label"] for d in detail] == ["x", "TV"]


# ------------------------------------------------------------------------------------------------ registries
@pytest.fixture
def home(hass):
    """Three rooms; a TV with two entities in the living room, a HomePod in the kitchen, a door sensor between hall and kitchen."""
    areas = ar.async_get(hass)
    for aid, name in (("salon", "Salon"), ("entree", "Entrée"), ("cuisine", "Cuisine")):
        areas.async_create(name)
    ids = {a.name: a.id for a in areas.async_list_areas()}
    reg, devreg = er.async_get(hass), dr.async_get(hass)
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    tv = devreg.async_get_or_create(config_entry_id=entry.entry_id, identifiers={("t", "tv")}, name="TV", suggested_area="Salon")
    devreg.async_update_device(tv.id, area_id=ids["Salon"])
    reg.async_get_or_create("media_player", "t", "tv1", device_id=tv.id, config_entry=entry, suggested_object_id="tv")
    reg.async_get_or_create("media_player", "t", "tv2", device_id=tv.id, config_entry=entry, suggested_object_id="tv_2")
    pod = reg.async_get_or_create("media_player", "t", "pod", config_entry=entry, suggested_object_id="homepod")
    reg.async_update_entity(pod.entity_id, area_id=ids["Cuisine"])
    door = reg.async_get_or_create("binary_sensor", "t", "door", config_entry=entry, suggested_object_id="porte", original_device_class="door")
    reg.async_update_entity(door.entity_id, area_id=ids["Entrée"])
    hass.states.async_set("media_player.tv", "playing", {"volume_level": 0.08, "friendly_name": "TV", "supported_features": 100})
    hass.states.async_set("media_player.tv_2", "unavailable", {"friendly_name": "TV 2"})
    hass.states.async_set("media_player.homepod", "playing", {"volume_level": 0.5, "friendly_name": "HomePod"})
    hass.states.async_set("binary_sensor.porte", "on", {"device_class": "door", "friendly_name": "Porte"})
    return ids


def test_discover_folds_duplicates(hass, home):
    rows = dv.discover(hass, home["Salon"])
    assert [(r["entity_id"], r["duplicate_of"]) for r in rows] == [("media_player.tv", None), ("media_player.tv_2", "media_player.tv")]
    assert rows[0]["has_volume"] and not rows[1]["available"]
    assert [r["entity_id"] for r in dv.discover(hass, home["Cuisine"])] == ["media_player.homepod"]
    assert dv.discover(hass, home["Entrée"]) == []
    assert [o["entity_id"] for o in dv.openings(hass)] == ["binary_sensor.porte"]
    assert [a["name"] for a in dv.areas(hass)] == ["Cuisine", "Entrée", "Salon"]


def test_compute_open_space_and_door(hass, home):
    s, e, c = home["Salon"], home["Entrée"], home["Cuisine"]
    cfg = {"area_links": [{"a": s, "b": e, "type": "open"}, {"a": e, "b": c, "type": "door", "sensor": "binary_sensor.porte"}],
           "analysis": {"context_boost": 0.15},
           "sources": [{"id": "hall", "name": "Hall", "area": e, "devices": {"enabled": True}}, {"id": "k", "area": c, "devices": {"enabled": True}}]}
    off, reasons, detail = dv.compute(hass, cfg, cfg["sources"][0], {}, set(), {})
    assert reasons == ["device"] and off == pytest.approx(0.081, abs=1e-3)                  # TV via the open space, 100 %
    assert detail[0]["label"].startswith("TV · Salon · 100 %")
    off, _, detail = dv.compute(hass, cfg, cfg["sources"][1], {}, set(), {})                 # kitchen: its own HomePod wins (0.1125) over the TV (door open: 0.7)
    assert off == pytest.approx(0.112, abs=2e-3) and len(detail) == 2
    hass.states.async_set("media_player.homepod", "off", {})
    hass.states.async_set("binary_sensor.porte", "off", {})
    off, _, detail = dv.compute(hass, cfg, cfg["sources"][1], {}, set(), {})                 # door closed: 0.15 x 0.081
    assert off == pytest.approx(0.012, abs=1e-3)
    cfg["sources"][1]["devices"]["exclude"] = ["media_player.tv"]
    assert dv.compute(hass, cfg, cfg["sources"][1], {}, set(), {}) == (0.0, [], [])


def test_compute_include_and_shared_context(hass, home):
    s, e = home["Salon"], home["Entrée"]
    hass.states.async_set("switch.fan", "on", {"friendly_name": "Hood"})
    cfg = {"area_links": [{"a": s, "b": e, "type": "open"}], "analysis": {"context_boost": 0.15},
           "sources": [{"id": "hall", "name": "Hall", "area": e, "devices": {"enabled": True, "include": ["switch.fan"], "exclude": ["media_player.tv"]}},
                       {"id": "mic", "name": "Salon mic", "area": s, "enabled": True}]}
    off, reasons, _ = dv.compute(hass, cfg, cfg["sources"][0], {}, set(), {})
    assert reasons == ["device"] and off == 0.09                                              # only the hood, 60 % of 0.15
    statuses = {"mic": {"active_contexts": ["/m/tv", "/m/other"]}}
    off, reasons, detail = dv.compute(hass, cfg, cfg["sources"][0], statuses, {"/m/tv"}, {"/m/tv": "Television"})
    assert reasons == ["device", "shared"] and off == 0.15
    assert detail[0]["label"] == "Salon mic: Television · 100 %"
    off, reasons, _ = dv.compute(hass, cfg, cfg["sources"][0], {"mic": {"active_contexts": ["/m/other"]}}, {"/m/tv"}, {})
    assert "shared" not in reasons                                                            # not an inhibiting class


def test_recommendations(hass, home):
    cfg = {"sources": [{"id": "a", "name": "A"}, {"id": "b", "name": "B", "area": home["Salon"]}, {"id": "c", "area": home["Entrée"]},
                       {"id": "d", "area": home["Salon"], "devices": {"enabled": True}}]}
    rows = {r["source"]: r for r in dv.recommendations(hass, cfg, "fr")}
    assert set(rows) == {"a", "b"} and rows["a"]["rule"] == "set_area" and rows["a"]["apply"] is None
    assert rows["b"]["apply"] == {"source": "b", "source_patch": {"devices": {"enabled": True}}} and "TV" in rows["b"]["message"]
    assert "pièce" in rows["a"]["message"]


# ------------------------------------------------------------------------------------------------ push to the service
async def test_manager_pushes_with_ttl(hass, home):
    cfg = {"classes": {"Bark": {"enabled": True}},
           "sources": [{"id": "salon", "name": "Salon", "type": "rtsp", "url": "rtsp://x/s", "area": home["Salon"], "devices": {"enabled": True}},
                       {"id": "off", "name": "Off", "type": "rtsp", "url": "rtsp://x/o", "area": home["Salon"]}]}
    fs.reset(cfg)
    with patch("custom_components.sound_recognition.SoundRecClient", fs.FakeClient), \
         patch("custom_components.sound_recognition.config_flow.SoundRecClient", fs.FakeClient):
        entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="x", title="Sound Recognition")
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
        await hass.async_block_till_done()
        assert fs.STATE.pushed["salon"]["ttl_s"] == 60 and fs.STATE.pushed["salon"]["offset"] == pytest.approx(0.081, abs=1e-3)
        assert "off" not in fs.STATE.pushed                                                    # not enabled for that source
        hass.states.async_set("media_player.tv", "off", {})                                    # TV switched off: pushed within a second
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
        await hass.async_block_till_done()
        assert fs.STATE.pushed["salon"]["offset"] == 0
        await hass.config_entries.async_unload(entry.entry_id)
        fs.STATE.stop.set()
