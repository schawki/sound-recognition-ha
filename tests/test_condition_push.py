"""The integration finds the entities the conditions read and keeps the service informed of their states."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

import fake_service as fs
from custom_components.sound_recognition import conditions as cn
from test_integration import fake_service, setup_entry  # noqa: F401  (fixture and helper)

NOBODY = {"people": "nobody_home"}
COND = {"rules": [NOBODY, {"entity": "input_boolean.guests", "op": "is_not", "value": "on"}], "match": "all"}


def test_collect_finds_every_level_and_skips_disabled_sources():
    cfg = {"defaults": {"condition": {"rules": [{"entity": "a.one", "value": "on"}]}},
           "classes": {"Bark": {"condition": {"rules": [NOBODY]}}},
           "sources": [{"id": "s", "classes": {"Bark": {"condition": {"rules": [{"entity": "a.two", "value": "on"}]}}},
                        "condition": {"rules": [{"entity": "a.three", "value": "on"}]}},
                       {"id": "off", "enabled": False, "condition": {"rules": [{"entity": "a.hidden", "value": "on"}]}}]}
    assert cn.collect(cfg) == ({"a.one", "a.two", "a.three"}, True)
    assert cn.collect({}) == (set(), False)
    assert cn.collect({"sources": [{"id": "s", "condition": {"rules": ["bad", {"entity": 3}]}}]}) == (set(), False)


async def test_nothing_is_pushed_without_conditions(hass):
    await setup_entry(hass)
    assert fs.STATE.conditions is None


async def test_states_are_pushed_with_their_time_to_live(hass):
    fs.STATE.cfg["sources"][0]["condition"] = COND
    hass.states.async_set("person.a", "not_home")
    hass.states.async_set("person.b", "home")
    hass.states.async_set("input_boolean.guests", "off")
    hass.states.async_set("sensor.unrelated", "5")
    await setup_entry(hass)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()
    assert fs.STATE.conditions == {"states": {"person.a": "not_home", "person.b": "home", "input_boolean.guests": "off"}, "ttl_s": cn.TTL_S}


async def test_a_change_of_state_is_pushed(hass):
    fs.STATE.cfg["sources"][0]["condition"] = COND
    hass.states.async_set("person.a", "home")
    await setup_entry(hass)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2))
    await hass.async_block_till_done()
    assert fs.STATE.conditions["states"] == {"person.a": "home"}              # an entity Home Assistant does not know is left out: unknown for the service
    hass.states.async_set("person.a", "not_home")
    hass.states.async_set("input_boolean.guests", "on")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=4))
    await hass.async_block_till_done()
    assert fs.STATE.conditions["states"] == {"person.a": "not_home", "input_boolean.guests": "on"}


async def test_a_service_without_the_route_is_tolerated(hass, caplog):
    """An older service answers 404: nothing breaks, and the integration says once that conditions are ignored."""
    from custom_components.sound_recognition.api import SoundRecError

    async def refuse(self, states, ttl_s=120):
        raise SoundRecError("HTTP 404 on /conditions")
    fs.STATE.cfg["sources"][0]["condition"] = COND
    with patch.object(fs.FakeClient, "set_conditions", refuse):
        await setup_entry(hass)
        for n in (2, 4):
            async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=n))
            await hass.async_block_till_done()
    assert caplog.text.count("did not take the states of the conditions") == 1
