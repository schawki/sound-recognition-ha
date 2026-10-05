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
    links = [{"a": s, "b": e, "type": "open"}, {"a": e, "b": c, "type": "door", "sensor": "binary_sensor.porte"}]
    cfg = {"analysis": {"context_boost": 0.15},
           "sources": [{"id": "hall", "name": "Hall", "area": e, "devices": {"enabled": True}}, {"id": "k", "area": c, "devices": {"enabled": True}}]}
    off, reasons, detail = dv.compute(hass, cfg, cfg["sources"][0], {}, set(), {}, links)
    assert reasons == ["device"] and off == pytest.approx(0.081, abs=1e-3)                  # TV via the open space, 100 %
    assert detail[0]["label"].startswith("TV · Salon · 100 %")
    off, _, detail = dv.compute(hass, cfg, cfg["sources"][1], {}, set(), {}, links)                 # kitchen: its own HomePod wins (0.1125) over the TV (door open: 0.7)
    assert off == pytest.approx(0.112, abs=2e-3) and len(detail) == 2
    hass.states.async_set("media_player.homepod", "off", {})
    hass.states.async_set("binary_sensor.porte", "off", {})
    off, _, detail = dv.compute(hass, cfg, cfg["sources"][1], {}, set(), {}, links)                 # door closed: 0.15 x 0.081
    assert off == pytest.approx(0.012, abs=1e-3)
    cfg["sources"][1]["devices"]["exclude"] = ["media_player.tv"]
    assert dv.compute(hass, cfg, cfg["sources"][1], {}, set(), {}, links) == (0.0, [], [])


def test_compute_include_and_shared_context(hass, home):
    s, e = home["Salon"], home["Entrée"]
    hass.states.async_set("switch.fan", "on", {"friendly_name": "Hood"})
    links = [{"a": s, "b": e, "type": "open"}]
    cfg = {"analysis": {"context_boost": 0.15},
           "sources": [{"id": "hall", "name": "Hall", "area": e, "devices": {"enabled": True, "include": ["switch.fan"], "exclude": ["media_player.tv"]}},
                       {"id": "mic", "name": "Salon mic", "area": s, "enabled": True}]}
    off, reasons, _ = dv.compute(hass, cfg, cfg["sources"][0], {}, set(), {}, links)
    assert reasons == ["device"] and off == 0.09                                              # only the hood, 60 % of 0.15
    statuses = {"mic": {"active_contexts": ["/m/tv", "/m/other"]}}
    off, reasons, detail = dv.compute(hass, cfg, cfg["sources"][0], statuses, {"/m/tv"}, {"/m/tv": "Television"}, links)
    assert reasons == ["device", "shared"] and off == 0.15
    assert detail[0]["label"] == "Salon mic: Television · 100 %"
    off, reasons, _ = dv.compute(hass, cfg, cfg["sources"][0], {"mic": {"active_contexts": ["/m/other"]}}, {"/m/tv"}, {}, links)
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


# ------------------------------------------------------------------------------------------------ separations and their sound
def L(kind, a="a", b="b", sensor=None, **kw):
    return {"a": a, "b": b, "type": kind, **({"sensor": sensor} if sensor else {}), **kw}


def test_every_kind_of_separation():
    st = {"s": "on"}
    assert dv.edge_factor(L("open_space"), {}) == 1 and dv.edge_factor(L("open"), {}) == 1            # "open" is the former name
    assert dv.edge_factor(L("opening"), {}) == 0.9 and dv.edge_factor(L("wall"), {}) == 0.05
    assert dv.edge_factor(L("door", sensor="s"), st) == 0.7 and dv.edge_factor(L("door", sensor="s"), {"s": "off"}) == 0.15
    assert dv.edge_factor(L("glass_door", sensor="s"), {"s": "off"}) == 0.25                           # glass lets more through than a door
    assert dv.edge_factor(L("window", sensor="s"), {"s": "closed"}) == 0.1 and dv.edge_factor(L("window", sensor="s"), {"s": "open"}) == 0.6
    assert dv.edge_factor(L("shutter", sensor="s"), {"s": "partial"}) == pytest.approx(0.35)          # states of Home Structure
    assert dv.edge_factor(L("door"), {}) == pytest.approx(0.425)                                       # no sensor
    assert dv.edge_factor(L("door", sensor="s", open_factor=0.9, closed_factor=0.0), {"s": "on"}) == 0.9
    assert dv.edge_factor(L("wall", open_factor=1.0), {}) == 0.05                                      # fixed types ignore the factors


def test_several_separations_between_two_spaces():
    s = {"d": "off", "g": "on", "w": "off", "v": "closed"}
    assert dv.pair_factor([L("door", sensor="d"), L("glass_door", sensor="g")], s) == 0.7              # the most open wins
    assert dv.pair_factor([L("wall"), L("door", sensor="d")], s) == 0.15
    assert dv.pair_factor([L("window", sensor="g"), L("shutter", sensor="v")], s) == pytest.approx(0.3)   # shutter closed halves an open window
    assert dv.pair_factor([L("window", sensor="g"), L("shutter", sensor="x")], s) == pytest.approx(0.45) # shutter unknown: 75 %
    assert dv.pair_factor([L("shutter", sensor="v")], s) == 0.1                                        # alone it is the opening itself
    assert dv.coupling("a", "b", [L("door", sensor="d"), L("glass_door", sensor="g")], s) == 0.7


def test_walls_are_not_followed_but_doors_are():
    links = [L("wall", "a", "b"), L("door", "b", "c", sensor="d"), L("window", "c", "z", sensor="w")]
    assert dv.reachable_areas("a", links) == {"a"}
    assert dv.reachable_areas("b", links) == {"b", "c", "z"}


def test_states_of_home_structure_are_understood():
    assert [dv.link_state(L("door", sensor="s"), {"s": v}) for v in ("open", "on", "closed", "off", "partial", "opening", "unknown", "unavailable")] == \
        ["open", "open", "closed", "closed", "partial", "partial", "unknown", "unknown"]


# ------------------------------------------------------------------------------------------------ link with Home Structure
from custom_components.sound_recognition import structure_link as sl  # noqa: E402

HS = {"spaces": [], "connections": [
    {"id": "c1", "a": "area:salon", "b": "area:entree", "separations": [{"id": "1", "type": "open_space", "state": "open", "sensor": None, "entity_id": "sensor.hs_1"}]},
    {"id": "c2", "a": "area:entree", "b": "area:cuisine", "separations": [{"id": "2", "type": "door", "state": "open", "sensor": "binary_sensor.porte", "entity_id": "sensor.hs_2"},
                                                                          {"id": "3", "type": "window", "state": "closed", "sensor": "binary_sensor.f", "entity_id": None}]},
    {"id": "c3", "a": "area:salon", "b": "zone:rue", "separations": [{"id": "4", "type": "window", "state": "closed", "sensor": "binary_sensor.g", "entity_id": "sensor.hs_4"}]},
]}


def test_links_from_structure():
    assert sl.links_from_structure(HS) == [
        {"a": "salon", "b": "entree", "type": "open_space"},
        {"a": "entree", "b": "cuisine", "type": "door", "sensor": "sensor.hs_2"},        # the Home Structure entity, normalised states
        {"a": "entree", "b": "cuisine", "type": "window", "sensor": "binary_sensor.f"},  # no entity: the raw sensor
    ]                                                                                      # the street has no area: left out


def _hs_service(hass, structure):
    async def handler(call):
        return structure

    from homeassistant.core import SupportsResponse
    hass.services.async_register("home_structure", "get_structure", handler, supports_response=SupportsResponse.ONLY)


def _hs_entry(hass, options=None):
    from homeassistant.config_entries import ConfigEntryState
    e = MockConfigEntry(domain="home_structure", data={}, options=options or {})
    e.add_to_hass(hass)
    e.mock_state(hass, ConfigEntryState.LOADED)
    return e


async def test_status_and_effective_links(hass, home):
    cfg = {}
    assert await sl.status(hass) == "not_installed"
    assert await sl.effective_links(hass, cfg) == ([], "none")
    with patch.object(sl, "async_get_custom_components", return_value={"home_structure": object()}):
        assert await sl.status(hass) == "not_configured"
    _hs_entry(hass)
    _hs_service(hass, {"spaces": [], "connections": []})
    assert await sl.status(hass) == "ready"
    assert (await sl.effective_links(hass, cfg)) == ([], "none")                             # ready but empty: nothing to read
    hass.services.async_remove("home_structure", "get_structure")
    _hs_service(hass, HS)
    links, origin = await sl.effective_links(hass, cfg)
    assert origin == "home_structure" and len(links) == 3


async def test_manager_uses_home_structure(hass, home):
    s, e = home["Salon"], home["Entrée"]
    hass.states.async_set("sensor.hs_door", "open")
    structure = {"spaces": [], "connections": [{"id": "c", "a": f"area:{s}", "b": f"area:{e}", "separations": [
        {"id": "1", "type": "glass_door", "state": "open", "sensor": "binary_sensor.b", "entity_id": "sensor.hs_door"}]}]}
    _hs_entry(hass)
    _hs_service(hass, structure)
    cfg = {"classes": {"Bark": {"enabled": True}},
           "sources": [{"id": "hall", "name": "Hall", "type": "rtsp", "url": "rtsp://x/h", "area": e, "devices": {"enabled": True}}]}
    fs.reset(cfg)
    with patch("custom_components.sound_recognition.SoundRecClient", fs.FakeClient), \
         patch("custom_components.sound_recognition.config_flow.SoundRecClient", fs.FakeClient):
        entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="x", title="Sound Recognition")
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
        await hass.async_block_till_done()
        assert fs.STATE.pushed["hall"]["offset"] == pytest.approx(0.057, abs=2e-3)         # TV 0.081 through an open glass door (0.7)
        assert entry.runtime_data.dynamic.origin == "home_structure"
        hass.states.async_set("sensor.hs_door", "closed")                                  # the door is closed: 0.25 x 0.081 = 0.02
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=4))
        await hass.async_block_till_done()
        assert fs.STATE.pushed["hall"]["offset"] == pytest.approx(0.02, abs=2e-3)
        await hass.config_entries.async_unload(entry.entry_id)
        fs.STATE.stop.set()


async def test_panel_commands_structure(hass, hass_ws_client, home):
    s, e = home["Salon"], home["Entrée"]
    cfg = {"classes": {"Bark": {"enabled": True}},
           "sources": [{"id": "hall", "name": "Hall", "type": "rtsp", "url": "rtsp://x/h", "area": e}]}
    fs.reset(cfg)
    ws_n = [0]
    with patch("custom_components.sound_recognition.SoundRecClient", fs.FakeClient), \
         patch("custom_components.sound_recognition.config_flow.SoundRecClient", fs.FakeClient):
        entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="x", title="Sound Recognition")
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        ws = await hass_ws_client(hass)

        async def call(**kw):
            ws_n[0] += 1
            await ws.send_json({"id": ws_n[0], **kw})
            return (await ws.receive_json())["result"]

        r = await call(type="sound_recognition/structure")
        assert r["status"] == "not_installed" and r["origin"] == "none" and r["links"] == [] and "ha-home-structure" in r["url"]
        recs = (await call(type="sound_recognition/recommendations", language="fr"))["recommendations"]
        install = next(x for x in recs if x["rule"] == "install_home_structure")
        assert install["apply"] is None and "Home Structure" in install["message"] and "voisines" in install["message"]
        with patch.object(sl, "async_get_custom_components", return_value={"home_structure": object()}):
            assert "setup_home_structure" in [x["rule"] for x in (await call(type="sound_recognition/recommendations"))["recommendations"]]
        _hs_entry(hass, {"zones": [], "connections": []})
        _hs_service(hass, {"spaces": [], "connections": []})
        assert "describe_home_structure" in [x["rule"] for x in (await call(type="sound_recognition/recommendations"))["recommendations"]]
        hass.services.async_remove("home_structure", "get_structure")
        _hs_service(hass, HS | {"connections": [{"id": "c", "a": f"area:{s}", "b": f"area:{e}", "separations": [{"id": "1", "type": "door", "state": "closed", "sensor": "binary_sensor.p", "entity_id": "sensor.hs_p"}]}]})
        hass.states.async_set("sensor.hs_p", "closed")
        r = await call(type="sound_recognition/structure")
        assert r["status"] == "ready" and r["origin"] == "home_structure" and r["links"][0]["state"] == "closed" and r["links"][0]["a_name"] == "Salon"
        assert r["plan"] is None                                                          # this structure has no positions (older Home Structure)
        hass.services.async_remove("home_structure", "get_structure")
        _hs_service(hass, {"spaces": [{"id": f"area:{s}", "name": "Salon", "kind": "room", "in_home": True}, {"id": f"area:{e}", "name": "Entrée", "kind": "room", "room_type": "entrance", "in_home": True}],
                           "layout": {f"area:{s}": {"x": 24, "y": 24}, f"area:{e}": {"x": 248, "y": 24}},
                           "connections": [{"id": "c", "a": f"area:{s}", "b": f"area:{e}", "separations": [{"id": "1", "type": "door", "state": "closed", "sensor": "binary_sensor.p", "entity_id": "sensor.hs_p", "shutter": None, "shutter_state": None}]}]})
        r = await call(type="sound_recognition/structure")
        assert [x["name"] for x in r["plan"]["spaces"]] == ["Salon", "Entrée"] and r["plan"]["connections"][0]["separations"][0]["state"] == "closed"
        recs = (await call(type="sound_recognition/recommendations", language="fr"))["recommendations"]
        assert not [x for x in recs if x["rule"].endswith("home_structure")]
        place = next(x for x in recs if x["rule"] == "propose_place")                       # the type of the room proposes a place...
        assert place["source"] == "hall" and place["apply"]["source_patch"] == {"environment": "entrance"} and "Entrée, couloir" in place["message"]
        assert not [x for x in recs if x["rule"] == "set_environment" and x["source"] == "hall"]   # ...instead of the generic request
        assert next(x for x in r["plan"]["spaces"] if x["name"] == "Entrée")["room_type"] == "entrance"
        devs = await call(type="sound_recognition/devices", area_id=e)
        assert {d["area_id"] for d in devs["devices"]} == {s}                                # the living-room TV, reached through the connection described in Home Structure
        await hass.config_entries.async_unload(entry.entry_id)
        fs.STATE.stop.set()


# ------------------------------------------------------------------------------------------------ grille, shutter of a separation, plan
def test_a_grille_hardly_stops_sound_and_a_shutter_lowers_only_its_own_separation():
    assert dv.edge_factor(L("grille"), {}) == pytest.approx(0.875)                                     # no sensor: average of 0.9 and 0.85
    assert dv.edge_factor(L("grille", sensor="s"), {"s": "closed"}) == 0.85 and dv.edge_factor(L("grille", sensor="s"), {"s": "open"}) == 0.9
    glass = L("glass_door", sensor="g", shutter_state="closed")
    assert dv.edge_factor(glass, {"g": "closed"}) == pytest.approx(0.125)                               # 0.25 behind a closed shutter (x0.5)
    assert dv.edge_factor(L("glass_door", sensor="g", shutter_state="open"), {"g": "closed"}) == 0.25
    assert dv.edge_factor(L("window", sensor="w", shutter_state="unknown"), {"w": "open"}) == pytest.approx(0.45)
    # a grille next to a glass door behind its shutter: the grille is the open path
    assert dv.pair_factor([glass, L("grille")], {"g": "closed"}) == pytest.approx(0.875)
    assert dv.coupling("a", "b", [glass], {"g": "closed"}) == pytest.approx(0.125, abs=1e-3)


def test_links_from_structure_carry_the_shutter_of_each_separation():
    st = {"connections": [{"id": "c", "a": "area:salon", "b": "area:jardin", "separations": [
        {"id": "1", "type": "glass_door", "sensor": "binary_sensor.b", "entity_id": "sensor.hs_1", "state": "closed", "shutter": "cover.v", "shutter_state": "partial"},
        {"id": "2", "type": "grille", "sensor": None, "entity_id": "sensor.hs_2", "state": "unknown", "shutter": None, "shutter_state": None}]}]}
    assert sl.links_from_structure(st) == [
        {"a": "salon", "b": "jardin", "type": "glass_door", "sensor": "sensor.hs_1", "shutter_state": "partial"},
        {"a": "salon", "b": "jardin", "type": "grille", "sensor": "sensor.hs_2"}]


def test_plan_from_structure():
    st = {"spaces": [{"id": "area:salon", "name": "Salon", "kind": "room", "in_home": True}, {"id": "zone:rue", "name": "Rue", "kind": "street", "in_home": False},
                     {"id": "area:cave", "name": "Cave", "kind": "room", "in_home": True}],
          "layout": {"area:salon": {"x": 24, "y": 24}, "zone:rue": {"x": 300, "y": 24}},
          "connections": [{"id": "c", "a": "area:salon", "b": "zone:rue", "separations": [{"id": "1", "type": "door", "state": "open", "shutter_state": None}]},
                          {"id": "d", "a": "area:salon", "b": "area:cave", "separations": [{"id": "2", "type": "wall", "state": "closed"}]}]}
    plan = sl.plan_from_structure(st)
    assert [s["id"] for s in plan["spaces"]] == ["area:salon", "zone:rue"] and plan["spaces"][1]["x"] == 300
    assert plan["connections"] == [{"a": "area:salon", "b": "zone:rue", "separations": [{"type": "door", "state": "open", "shutter_state": None}]}]   # Cave is not on the plan
    assert sl.plan_from_structure(None) is None and sl.plan_from_structure({"spaces": st["spaces"], "connections": [], "layout": {}}) is None   # older Home Structure: no positions
