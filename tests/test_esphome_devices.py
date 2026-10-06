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


def _esphome_device(hass, host, name, text_state, area=None, platform="esphome", unique="mac-text_sensor-1"):
    entry = MockConfigEntry(domain="esphome_stand_in", data={"host": host})   # never set up: no real ESPHome connection
    entry.add_to_hass(hass)
    dev = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("esphome", unique)}, name=name)
    ent = er.async_get(hass).async_get_or_create("text_sensor", platform, unique, config_entry=entry, device_id=dev.id,
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
