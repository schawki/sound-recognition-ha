"""ESPHome devices running the Sound Recognition microphone component are found in the registries."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from custom_components.sound_recognition import esphome_devices as ed
from test_integration import fake_service, setup_entry  # noqa: F401  (fake_service is autouse)


def test_parse_state():
    assert ed.parse_state("sound-recognition-stream/1 port=6055") == 6055
    assert ed.parse_state("sound-recognition-stream/1 port=7000") == 7000
    assert ed.parse_state("sound-recognition-stream/1") == 6055
    for bad in (None, "", "unknown", "unavailable", "something else port=6055", "sound-recognition-stream/1 port=0"):
        assert ed.parse_state(bad) is None


def _esphome_device(hass, host, name, text_state, area=None, platform="esphome", unique="mac-stream-1"):
    entry = MockConfigEntry(domain="esphome_stand_in", data={"host": host})   # never set up: no real ESPHome connection
    entry.add_to_hass(hass)
    dev = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("esphome", unique)}, name=name)
    ent = er.async_get(hass).async_get_or_create("sensor", platform,   # an ESPHome text sensor is a `sensor` entity in Home Assistant
                                                  unique, config_entry=entry, device_id=dev.id,
                                                 suggested_object_id=f"{unique}_stream")
    if area:
        er.async_get(hass).async_update_entity(ent.entity_id, area_id=area)
    hass.states.async_set(ent.entity_id, text_state)
    return ent


async def test_devices_are_found_with_their_address(hass):
    area = ar.async_get(hass).async_create("Living room")
    _esphome_device(hass, "192.168.1.50", "Mic living room", "sound-recognition-stream/1 port=6055", area=area.id, unique="a")
    _esphome_device(hass, "esp-bedroom.local", "Mic bedroom", "sound-recognition-stream/1 port=7000", unique="b")
    _esphome_device(hass, "192.168.1.60", "Some other ESP", "hello", unique="c")                      # not ours
    _esphome_device(hass, "192.168.1.70", "Imposter", "sound-recognition-stream/1 port=6055", platform="template", unique="d")
    _esphome_device(hass, "fe80::1", "IPv6 mic", "sound-recognition-stream/1 port=6055", unique="e")
    found = ed.find_devices(hass)
    by = {d["name"]: d for d in found}
    assert set(by) == {"Mic living room", "Mic bedroom", "IPv6 mic"}
    assert by["Mic living room"]["url"] == "tcp://192.168.1.50:6055" and by["Mic living room"]["area_id"] == area.id
    assert by["Mic bedroom"]["url"] == "tcp://esp-bedroom.local:7000" and by["Mic bedroom"]["area_id"] == ""
    assert by["IPv6 mic"]["url"] == "tcp://[fe80::1]:6055"
    assert [d["name"] for d in found] == sorted(by, key=str.lower)


async def test_panel_command(hass, hass_ws_client):
    await setup_entry(hass)
    _esphome_device(hass, "192.168.1.50", "Mic", "sound-recognition-stream/1 port=6055", unique="a")
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "sound_recognition/esphome_devices"})
    r = await ws.receive_json()
    assert r["success"] and [d["url"] for d in r["result"]["devices"]] == ["tcp://192.168.1.50:6055"]


# ------------------------------------------------------------------------------------------------ microphones still to add
from homeassistant.helpers import issue_registry as ir  # noqa: E402

from custom_components.sound_recognition.const import DOMAIN  # noqa: E402
import fake_service as fs  # noqa: E402


def test_host_of_and_pending():
    assert ed.host_of("tcp://192.168.1.50:6055") == "192.168.1.50" and ed.host_of("tcp://[FE80::1]:6055") == "fe80::1"
    assert ed.host_of("tcp://Mic.LOCAL:6055") == "mic.local" and ed.host_of("") == "" and ed.host_of(None) == ""
    devices = [{"id": "a", "url": "tcp://192.168.1.50:6055"}, {"id": "b", "url": "tcp://192.168.1.51:6055"}, {"id": "c", "url": "tcp://192.168.1.52:6055"}]
    cfg = {"sources": [{"id": "x", "type": "esphome", "url": "tcp://192.168.1.50:7000"}, {"id": "y", "type": "rtsp", "url": "rtsp://192.168.1.51/s"}]}
    rows = {d["id"]: d for d in ed.annotate(devices, cfg, {"c"})}
    assert rows["a"]["added"] and not rows["b"]["added"] and rows["c"]["ignored"]      # an ESPHome source with this host counts, a camera does not
    assert [d["id"] for d in ed.pending(devices, cfg, {"c"})] == ["b"]


def esp_issues(hass):
    return [i for i in ir.async_get(hass).issues.values() if i.domain == DOMAIN and i.issue_id.startswith("esp_microphone_")]


async def ws_call(ws, n, **kw):
    await ws.send_json({"id": n, **kw})
    return await ws.receive_json()


async def test_a_microphone_to_add_raises_one_repair_a_counter_and_an_advice(hass, hass_ws_client):
    entry = await setup_entry(hass)
    area = ar.async_get(hass).async_create("Kitchen")
    _esphome_device(hass, "192.168.1.50", "Sound Node", "sound-recognition-stream/1 port=6055", area=area.id, unique="a")
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    issues = esp_issues(hass)
    assert len(issues) == 1 and issues[0].is_fixable and issues[0].translation_placeholders == {"name": "Sound Node", "area": " (Kitchen)", "host": "192.168.1.50"}
    ws = await hass_ws_client(hass)
    r = await ws_call(ws, 1, type="sound_recognition/esphome_devices")
    assert r["result"]["pending"] == 1 and r["result"]["devices"][0]["added"] is False and r["result"]["devices"][0]["ignored"] is False
    recs = (await ws_call(ws, 2, type="sound_recognition/recommendations"))["result"]["recommendations"]
    esp = [x for x in recs if x["rule"] == "add_esp_microphone"]
    assert len(esp) == 1 and "Sound Node (Kitchen)" in esp[0]["message"]
    _esphome_device(hass, "192.168.1.51", "Mic bedroom", "sound-recognition-stream/1 port=6055", unique="b")
    esp = [x for x in (await ws_call(ws, 3, type="sound_recognition/recommendations"))["result"]["recommendations"] if x["rule"] == "add_esp_microphone"]
    assert len(esp) == 1 and "Sound Node" in esp[0]["message"] and "Mic bedroom" in esp[0]["message"]       # several: one advice naming them all


async def test_adding_the_device_as_a_source_removes_everything(hass, hass_ws_client):
    entry = await setup_entry(hass)
    _esphome_device(hass, "192.168.1.50", "Sound Node", "sound-recognition-stream/1 port=6055", unique="a")
    await entry.runtime_data.coordinator.async_refresh()
    assert len(esp_issues(hass)) == 1
    fs.STATE.cfg["sources"] = [*fs.STATE.cfg["sources"], {"id": "node", "name": "Sound Node", "type": "esphome", "url": "tcp://192.168.1.50:6055", "password": "12345678"}]   # new list: never mutate the shared defaults
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert esp_issues(hass) == []
    ws = await hass_ws_client(hass)
    r = (await ws_call(ws, 1, type="sound_recognition/esphome_devices"))["result"]
    assert r["pending"] == 0 and r["devices"][0]["added"] is True
    recs = (await ws_call(ws, 2, type="sound_recognition/recommendations"))["result"]["recommendations"]
    assert not [x for x in recs if x["rule"] == "add_esp_microphone"]


async def test_ignore_and_stop_ignoring(hass, hass_ws_client):
    entry = await setup_entry(hass)
    _esphome_device(hass, "192.168.1.50", "Sound Node", "sound-recognition-stream/1 port=6055", unique="a")
    await entry.runtime_data.coordinator.async_refresh()
    ws = await hass_ws_client(hass)
    dev_id = (await ws_call(ws, 1, type="sound_recognition/esphome_devices"))["result"]["devices"][0]["id"]
    r = (await ws_call(ws, 2, type="sound_recognition/esphome_ignore", device=dev_id, ignored=True))["result"]
    assert r["pending"] == 0 and r["devices"][0]["ignored"] is True and esp_issues(hass) == []
    assert entry.options["ignored_esp_devices"] == [dev_id]
    await entry.runtime_data.coordinator.async_refresh()
    assert esp_issues(hass) == []                                                                       # stays ignored after the next refresh
    r = (await ws_call(ws, 3, type="sound_recognition/esphome_ignore", device=dev_id, ignored=False))["result"]
    assert r["pending"] == 1 and len(esp_issues(hass)) == 1 and entry.options["ignored_esp_devices"] == []


async def test_the_repair_flow_ignores_the_device(hass, hass_client):
    entry = await setup_entry(hass)
    _esphome_device(hass, "192.168.1.50", "Sound Node", "sound-recognition-stream/1 port=6055", unique="a")
    await entry.runtime_data.coordinator.async_refresh()
    issue = esp_issues(hass)[0]
    http = await hass_client()
    flow = await (await http.post("/api/repairs/issues/fix", json={"handler": DOMAIN, "issue_id": issue.issue_id})).json()
    assert flow["step_id"] == "confirm" and flow["description_placeholders"]["name"] == "Sound Node"
    assert (await (await http.post(f"/api/repairs/issues/fix/{flow['flow_id']}", json={})).json())["type"] == "create_entry"
    assert esp_issues(hass) == [] and len(entry.options["ignored_esp_devices"]) == 1


async def test_nothing_is_raised_when_no_device_runs_the_component(hass):
    entry = await setup_entry(hass)
    _esphome_device(hass, "192.168.1.60", "Some other ESP", "hello", unique="c")
    await entry.runtime_data.coordinator.async_refresh()
    assert esp_issues(hass) == []
