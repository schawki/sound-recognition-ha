from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

import fake_service as fs
from custom_components.sound_recognition.const import DOMAIN

DATA = {CONF_HOST: "192.168.1.60", CONF_PORT: 8765, CONF_TOKEN: "tok"}
BARK, SMOKE = fs.CAT.get("Bark")["mid"], fs.CAT.get("Smoke detector, smoke alarm")["mid"]
BASE = {"classes": {"Bark": {"enabled": True}, "Smoke detector, smoke alarm": {"enabled": True}},
        "sources": [{"id": "kitchen", "name": "Kitchen", "type": "rtsp", "url": "rtsp://x/k"}]}


@pytest.fixture(autouse=True)
def fake_service():
    fs.reset(BASE)
    with patch("custom_components.sound_recognition.SoundRecClient", fs.FakeClient), \
         patch("custom_components.sound_recognition.config_flow.SoundRecClient", fs.FakeClient):
        yield
    fs.STATE.stop.set()


async def setup_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="192.168.1.60:8765", title="Sound Recognition")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def eid(hass, platform, entry, suffix):
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{suffix}")


# ------------------------------------------------------------------------------------------------ config flow
async def test_user_flow_creates_entry(hass):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert r["type"] is FlowResultType.FORM
    r = await hass.config_entries.flow.async_configure(r["flow_id"], DATA)
    assert r["type"] is FlowResultType.CREATE_ENTRY and r["data"][CONF_HOST] == "192.168.1.60"


@pytest.mark.parametrize("down,token,error", [(True, "tok", "cannot_connect"), (False, "wrong", "invalid_auth")])
async def test_user_flow_errors(hass, down, token, error):
    fs.STATE.down = down
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], dict(DATA, token=token))
    assert r["type"] is FlowResultType.FORM and r["errors"]["base"] == error


# ------------------------------------------------------------------------------------------------ entities and live messages
async def test_entities_and_live_messages(hass):
    entry = await setup_entry(hass)
    reg = er.async_get(hass)
    bark = eid(hass, "binary_sensor", entry, f"kitchen_{BARK.strip('/').replace('/', '_')}")
    assert bark and hass.states.get(bark).state == "off"
    assert hass.states.get(bark).name.endswith("Bark")
    assert hass.states.get(eid(hass, "binary_sensor", entry, "kitchen_connection")).state == "on"
    assert float(hass.states.get(eid(hass, "sensor", entry, "kitchen_level")).state) == -42.5
    assert eid(hass, "sensor", entry, "advice") and eid(hass, "event", entry, "kitchen_event")

    handler = fs.STATE.handler
    assert handler is not None
    await handler({"type": "active", "source": "kitchen", "active_classes": [BARK]})
    await hass.async_block_till_done()
    assert hass.states.get(bark).state == "on"
    await handler({"type": "active", "source": "kitchen", "active_classes": []})
    await hass.async_block_till_done()
    assert hass.states.get(bark).state == "off"

    ev = eid(hass, "event", entry, "kitchen_event")
    await handler({"type": "detection", "id": "abc", "source": "kitchen", "mid": BARK, "class": "Bark", "name": "Bark", "score": 0.9,
                   "duration_s": 1.2, "level_dbfs": -20, "started_at": "2026-10-05T12:00:00+00:00", "clip_retention_days": 7})
    await hass.async_block_till_done()
    st = hass.states.get(ev)
    assert st.attributes["event_type"] == "detection" and st.attributes["class"] == "Bark" and st.attributes["score"] == 0.9
    await handler({"type": "clip_ready", "id": "abc", "source": "kitchen", "mid": BARK, "clip": "2026-10-05/abc.wav", "expires_at": "x"})
    await hass.async_block_till_done()
    st = hass.states.get(ev)
    assert st.attributes["event_type"] == "clip_ready" and "/api/sound_recognition/clip/" in st.attributes["clip_url"]

    await handler({"type": "source_state", "source": "kitchen", "state": "reconnecting", "error": "no audio"})
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "binary_sensor", entry, "kitchen_connection")).state == "off"
    assert reg.async_get(bark).device_id


async def test_repairs_follow_the_advice(hass):
    fs.STATE.cfg["sources"][0]["clips"] = {"allowed": True}
    fs.STATE.cfg["classes"]["Shatter"] = {"enabled": True, "min_volume_dbfs": -30}     # gate too high for a safety class
    entry = await setup_entry(hass)
    issues = [i for i in ir.async_get(hass).issues.values() if i.domain == DOMAIN]
    assert any("volume" in (i.translation_placeholders or {}).get("message", "").lower() or "Kitchen" in (i.translation_placeholders or {}).get("source", "") for i in issues)
    n = len(issues)
    assert n >= 1
    fs.STATE.cfg["classes"]["Shatter"] = {"enabled": True}
    await entry.runtime_data.coordinator.async_refresh()
    issues2 = [i for i in ir.async_get(hass).issues.values() if i.domain == DOMAIN]
    assert len(issues2) < n
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert not [i for i in ir.async_get(hass).issues.values() if i.domain == DOMAIN]


async def test_unavailable_service_retries(hass):
    fs.STATE.down = True
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="x")
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state.name == "SETUP_RETRY"


# ------------------------------------------------------------------------------------------------ options flow
async def test_options_flow_add_source_pick_classes_and_advice(hass):
    entry = await setup_entry(hass)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["type"] is FlowResultType.MENU
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "sources"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "add_source"})
    assert r["step_id"] == "add_source"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {
        "name": "Nursery", "type": "go2rtc", "url": "rtsp://x/n", "enabled": True, "schedule_mode": "continuous", "clips_allowed": False})
    assert r["type"] is FlowResultType.FORM and r["step_id"] == "advice"                 # saved, advice shown
    assert [s["id"] for s in fs.STATE.cfg["sources"]] == ["kitchen", "nursery"]
    assert fs.STATE.cfg["sources"][1]["clips"] == {"allowed": False}
    r = await hass.config_entries.options.async_configure(r["flow_id"], {})
    assert r["type"] is FlowResultType.MENU
    # which sounds, on the new source only: baby cry in addition to the global ones
    baby = fs.CAT.get("Baby cry, infant cry")["mid"]
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "classes"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "scope_source"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"source": "nursery"})
    assert r["step_id"] == "classes_pick"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"classes": [BARK, SMOKE, baby]})
    assert r["step_id"] == "advice"
    assert fs.STATE.cfg["sources"][1]["classes"] == {baby: {"enabled": True}}
    r = await hass.config_entries.options.async_configure(r["flow_id"], {})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "finish"})
    assert r["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    # entry reloaded: the new source has its device, connection sensor and a detected sensor for each of its 3 classes
    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert eid(hass, "binary_sensor", entry, "nursery_connection")
    assert eid(hass, "binary_sensor", entry, f"nursery_{baby.strip('/').replace('/', '_')}")


async def test_options_flow_refused_configuration_is_explained(hass):
    entry = await setup_entry(hass)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "sources"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "add_source"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {
        "name": "Bad", "type": "rtsp", "enabled": True, "schedule_mode": "scheduled",
        "window_days": ["mon"], "window_from": "08:00:00", "window_to": "10:00:00", "clips_allowed": True, "url": ""})
    assert r["type"] is FlowResultType.FORM and r["errors"]["base"] == "invalid_config"
    assert r["description_placeholders"]["errors"]
    assert len(fs.STATE.cfg["sources"]) == 1                                              # nothing saved


async def test_options_flow_class_settings_and_defaults(hass):
    entry = await setup_entry(hass)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "class_settings"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "scope_global"})
    assert r["step_id"] == "class_pick"
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"class": SMOKE})
    assert r["step_id"] == "class_form"
    sug = fs.CAT.get("Smoke detector, smoke alarm")["suggestions"]
    r = await hass.config_entries.options.async_configure(r["flow_id"], {
        "threshold": 0.35, "min_duration_s": sug["min_duration_s"], "cooldown_s": sug["cooldown_s"], "pre_roll_s": sug["pre_roll_s"],
        "post_roll_s": sug["post_roll_s"], "clip_retention_days": sug["clip_retention_days"], "always_on": True})
    assert r["step_id"] == "advice"
    assert fs.STATE.cfg["classes"]["Smoke detector, smoke alarm"] == {"enabled": True, "threshold": 0.35, "schedule": {"mode": "continuous"}}
    r = await hass.config_entries.options.async_configure(r["flow_id"], {})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "defaults"})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"min_volume_dbfs": -50, "context_boost": 0.2, "clips_allowed": True, "clips_max_days": 10})
    assert fs.STATE.cfg["defaults"]["min_volume_dbfs"] == -50 and fs.STATE.cfg["analysis"]["context_boost"] == 0.2
    assert fs.STATE.cfg["defaults"]["clips"] == {"allowed": True, "max_retention_days": 10}


async def test_options_flow_adjust_advice(hass):
    fs.STATE.cfg["classes"]["Speech"] = {"enabled": True}
    fs.STATE.cfg["sources"][0]["schedule"] = {"mode": "scheduled", "windows": [{"days": ["mon"], "from": "08:00", "to": "09:00"}]}
    entry = await setup_entry(hass)
    warnings = await fs.FakeClient(None, "h", 1, "tok").warnings("en")
    safety = next(w for w in warnings if w["safety"])
    assert any(w["rule"] == "speech_target" and w["level"] == "warning" for w in warnings)

    async def adjust(data):
        r = await hass.config_entries.options.async_init(entry.entry_id)
        r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "advice_rule"})
        assert r["step_id"] == "advice_rule"
        return r, await hass.config_entries.options.async_configure(r["flow_id"], data)

    # global downgrade
    _, r = await adjust({"rule": "speech_target", "level": "info", "confirm": False})
    assert r["step_id"] == "advice" and fs.STATE.cfg["advice"] == {"speech_target": "info"}
    # only for one source, back to catalog default => removes the entry; empty block is dropped
    _, r = await adjust({"rule": "speech_target", "source": "kitchen", "level": "ignore", "confirm": False})
    assert fs.STATE.cfg["sources"][0]["advice"] == {"speech_target": "ignore"}
    _, r = await adjust({"rule": "speech_target", "source": "kitchen", "level": "default", "confirm": False})
    assert "advice" not in fs.STATE.cfg["sources"][0]
    # a safety advice cannot be hidden without confirmation
    _, r = await adjust({"rule": safety["rule"], "level": "ignore", "confirm": False})
    assert r["type"] is FlowResultType.FORM and r["errors"]["base"] == "confirm_required"
    assert safety["rule"] not in fs.STATE.cfg.get("advice", {})
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"rule": safety["rule"], "level": "ignore", "confirm": True})
    assert fs.STATE.cfg["advice"][safety["rule"]] == {"level": "ignore", "confirm": True}
    assert not [w for w in await fs.FakeClient(None, "h", 1, "tok").warnings("en") if w["rule"] == safety["rule"] and w["source"] == safety["source"]]


# ------------------------------------------------------------------------------------------------ panel (WebSocket commands)
async def test_panel_commands(hass, hass_ws_client):
    entry = await setup_entry(hass)
    fs.STATE.events = [{"id": "e1", "ts": 1.0, "source": "kitchen", "mid": BARK, "class": "Bark", "score": 0.9, "clip": "kitchen/e1.wav"}]
    ws = await hass_ws_client(hass)

    async def call(**kw):
        await ws.send_json({"id": call.n, **kw})
        call.n += 1
        return await ws.receive_json()
    call.n = 1

    r = await call(type="sound_recognition/overview")
    assert r["success"] and r["result"]["entry_id"] == entry.entry_id and r["result"]["sources"][0]["id"] == "kitchen"
    assert r["result"]["config"]["api"]["token"] == "***" and r["result"]["language"] == "en"
    r = await call(type="sound_recognition/catalog", language="fr")
    assert r["success"] and len(r["result"]["classes"]) == 521
    r = await call(type="sound_recognition/events", source="kitchen")
    ev = r["result"]["events"][0]
    assert ev["clip_url"].startswith(f"/api/sound_recognition/clip/{entry.entry_id}/kitchen/e1.wav?authSig=")
    r = await call(type="sound_recognition/resolved", source="kitchen", mid=BARK)
    assert r["success"] and "threshold" in r["result"]
    # validation is a dry run; a refused save reports the reasons and changes nothing
    cfg = (await call(type="sound_recognition/config"))["result"]
    bad = {**cfg, "sources": [{"id": "x", "type": "rtsp", "url": ""}]}
    r = await call(type="sound_recognition/config_validate", config=bad)
    assert r["success"] and any("url is required" in e for e in r["result"]["errors"])
    r = await call(type="sound_recognition/config_save", config=bad)
    assert not r["success"] and r["error"]["code"] == "invalid_config" and "url is required" in r["error"]["message"]
    assert len(fs.STATE.cfg["sources"]) == 1
    good = {**cfg, "advice": {"speech_target": "info"}}
    r = await call(type="sound_recognition/config_save", config=good)
    assert r["success"] and fs.STATE.cfg["advice"] == {"speech_target": "info"}
    assert fs.STATE.cfg["api"]["token"] == "tok"                      # masked token never overwrites the real one


async def test_panel_live_subscription_and_admin_only(hass, hass_ws_client, hass_read_only_access_token):
    entry = await setup_entry(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "sound_recognition/subscribe"})
    assert (await ws.receive_json())["success"]
    await fs.STATE.handler({"type": "clip_ready", "id": "e1", "source": "kitchen", "mid": BARK, "clip": "kitchen/e1.wav", "expires_at": "x"})
    msg = (await ws.receive_json())["event"]
    assert msg["type"] == "clip_ready" and msg["name"] and "authSig=" in msg["clip_url"]
    await fs.STATE.handler({"type": "active", "source": "kitchen", "active_classes": [BARK]})
    assert (await ws.receive_json())["event"]["active_classes"] == [BARK]
    # a non-admin user is refused
    ro = await hass_ws_client(hass, hass_read_only_access_token)
    await ro.send_json({"id": 1, "type": "sound_recognition/overview"})
    r = await ro.receive_json()
    assert not r["success"] and r["error"]["code"] == "unauthorized"
    assert entry.state.name == "LOADED"


# ------------------------------------------------------------------------------------------------ go2rtc stream picker
async def test_go2rtc_streams(hass, hass_ws_client):
    from custom_components.sound_recognition import go2rtc

    entry = await setup_entry(hass)
    ws = await hass_ws_client(hass)

    async def call(**kw):
        await ws.send_json({"id": call.n, "type": "sound_recognition/go2rtc_streams", **kw})
        call.n += 1
        return await ws.receive_json()
    call.n = 1

    r = await call()                                           # nothing configured yet
    assert r["success"] and r["result"] == {"configured": False, "url": "", "streams": []}

    async def fake_fetch(session, base):
        assert base == "http://192.168.1.5:1984"
        return go2rtc.parse_streams({"Salon": {}, "cuisine": {"producers": []}}, base)

    with patch("custom_components.sound_recognition.websocket_api.fetch_streams", fake_fetch):
        r = await call(url="192.168.1.5")                      # bare host: scheme and port are completed, and the address is remembered
        assert r["success"] and r["result"]["url"] == "http://192.168.1.5:1984"
        assert [s["name"] for s in r["result"]["streams"]] == ["cuisine", "Salon"]
        assert r["result"]["streams"][0]["url"] == "rtsp://192.168.1.5:8554/cuisine"
        assert entry.options["go2rtc_url"] == "http://192.168.1.5:1984"
        r = await call()                                       # later calls use the remembered address
        assert r["success"] and r["result"]["configured"] and len(r["result"]["streams"]) == 2

    async def broken(session, base):
        raise go2rtc.Go2RtcError("refused")

    with patch("custom_components.sound_recognition.websocket_api.fetch_streams", broken):
        r = await call(url="10.0.0.9:1985")
        assert not r["success"] and r["error"]["code"] == "go2rtc_unreachable" and "10.0.0.9:1985" in r["error"]["message"]
        assert entry.options["go2rtc_url"] == "http://192.168.1.5:1984"   # a failing address is not remembered
    r = await call(url="ftp://x")
    assert not r["success"] and r["error"]["code"] == "go2rtc_invalid"


def test_go2rtc_helpers():
    from custom_components.sound_recognition.go2rtc import Go2RtcError, normalize_url, rtsp_url

    assert normalize_url("frigate.local") == "http://frigate.local:1984"
    assert normalize_url(" https://h:1985/api/ ") == "https://h:1985"
    assert normalize_url("http://[fe80::1]") == "http://[fe80::1]:1984"
    assert rtsp_url("http://[fe80::1]:1984", "cam") == "rtsp://[fe80::1]:8554/cam"
    for bad in ("", "  ", "ftp://x", "http://"):
        with pytest.raises(Go2RtcError):
            normalize_url(bad)


@pytest.mark.allow_hosts(["127.0.0.1"])
async def test_go2rtc_fetch_against_a_real_server(socket_enabled):
    import aiohttp
    from aiohttp import web
    from aiohttp.test_utils import TestServer
    from custom_components.sound_recognition.go2rtc import Go2RtcError, fetch_streams

    async def streams(request):
        return web.json_response({"b_cam": {"producers": []}, "A_cam": {}})
    app = web.Application()
    app.router.add_get("/api/streams", streams)
    async with TestServer(app, host="127.0.0.1") as server, aiohttp.ClientSession() as session:
        base = f"http://127.0.0.1:{server.port}"
        got = await fetch_streams(session, base)
        assert [s["name"] for s in got] == ["A_cam", "b_cam"] and got[0]["url"] == "rtsp://127.0.0.1:8554/A_cam"
        with pytest.raises(Go2RtcError):
            await fetch_streams(session, f"http://127.0.0.1:{server.port + 1}")   # nothing listens there


async def test_panel_survives_reload_and_goes_with_the_last_entry(hass):
    entry = await setup_entry(hass)
    panels = lambda: hass.data["frontend_panels"]
    assert "sound-recognition" in panels()
    assert await hass.config_entries.async_reload(entry.entry_id)       # every saved change reloads the entry
    await hass.async_block_till_done()
    assert "sound-recognition" in panels()                              # not removed, or the browser is sent to the home page
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "sound-recognition" not in panels()
