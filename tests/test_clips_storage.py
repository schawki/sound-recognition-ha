"""Storage of the clips and change of token, seen from Home Assistant."""
from test_esphome_devices import ws_call
from test_integration import fake_service, setup_entry  # noqa: F401  (fake_service is autouse)

import fake_service as fs


async def test_the_panel_reads_the_storage(hass, hass_ws_client):
    await setup_entry(hass)
    ws = await hass_ws_client(hass)
    r = (await ws_call(ws, 1, type="sound_recognition/storage"))["result"]
    assert r["clips"] == 69 and r["free_bytes"] == 6_000_000_000 and r["path"].endswith("clips")


async def test_changing_the_token_stores_the_new_one_and_keeps_the_connection(hass, hass_ws_client):
    entry = await setup_entry(hass)
    ws = await hass_ws_client(hass)
    msg = await ws_call(ws, 1, type="sound_recognition/token_rotate")
    assert msg["success"] and "token" not in str(msg["result"])                        # the panel never sees it
    await hass.async_block_till_done()
    assert entry.data["token"] == fs.STATE.token == "new-tok"
    assert entry.state.name == "LOADED"
    r = (await ws_call(ws, 2, type="sound_recognition/storage"))["result"]            # still talking to the service
    assert r["clips"] == 69


async def test_advice_when_the_clips_disk_fills_up_or_clips_are_paused(hass, hass_ws_client):
    await setup_entry(hass)
    ws = await hass_ws_client(hass)

    def rules(rows):
        return [x["rule"] for x in rows if x["rule"].startswith("clips_")]
    recs = (await ws_call(ws, 1, type="sound_recognition/recommendations"))["result"]["recommendations"]
    assert rules(recs) == []                                                           # 6 GB left, 2000 days: nothing to say
    fs.STATE.storage = {**fs.STATE.storage, "free_bytes": 1_500_000_000}
    recs = (await ws_call(ws, 2, type="sound_recognition/recommendations"))["result"]["recommendations"]
    assert rules(recs) == ["clips_disk_low"]
    fs.STATE.storage = {**fs.STATE.storage, "free_bytes": 6_000_000_000, "days_left": 9.0}
    recs = (await ws_call(ws, 3, type="sound_recognition/recommendations"))["result"]["recommendations"]
    assert rules(recs) == ["clips_disk_low"] and "9 days" in [x for x in recs if x["rule"] == "clips_disk_low"][0]["message"]
    fs.STATE.storage = {**fs.STATE.storage, "max_gb": 3, "days_left": 9.0}              # a limit is set: the rate says nothing about the disk
    recs = (await ws_call(ws, 4, type="sound_recognition/recommendations"))["result"]["recommendations"]
    assert rules(recs) == []
    fs.STATE.storage = {**fs.STATE.storage, "paused": True, "min_free_gb": 2, "free_bytes": 1_000_000_000}
    recs = (await ws_call(ws, 5, type="sound_recognition/recommendations"))["result"]["recommendations"]
    assert rules(recs) == ["clips_paused"]
