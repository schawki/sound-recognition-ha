import asyncio

import numpy as np
import pytest

from soundrec import audio, config as cfgmod, espstream
from soundrec import catalog as cm
from soundrec.settings import Catalog
from fake_esp import FakeESP


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())   # other tests expect a current loop


def test_parse_url():
    assert espstream.parse_url("tcp://192.168.1.50:6055") == ("192.168.1.50", 6055)
    assert espstream.parse_url("tcp://esp.local") == ("esp.local", espstream.DEFAULT_PORT)
    for bad in ("rtsp://x/y", "192.168.1.50", "tcp://"):
        with pytest.raises(ValueError):
            espstream.parse_url(bad)


def test_connect_and_read_with_the_right_password():
    async def go():
        esp = await FakeESP().start()
        try:
            reader, writer = await espstream.connect(esp.url, "correct-horse")
            data = await asyncio.wait_for(reader.readexactly(3200), timeout=2)
            writer.close()
            return data, esp.accepted
        finally:
            await esp.stop()
    data, accepted = run(go())
    assert len(data) == 3200 and accepted == 1


def test_wrong_password_gets_no_audio():
    async def go():
        esp = await FakeESP().start()
        try:
            with pytest.raises(ConnectionError):
                await espstream.connect(esp.url, "not-the-password")
            return esp.accepted
        finally:
            await esp.stop()
    assert run(go()) == 0


def test_not_a_stream_and_unreachable():
    async def go():
        srv = await asyncio.start_server(lambda r, w: (w.write(b"HTTP/1.1 400 Bad Request\r\n\r\n"), w.close()), "127.0.0.1", 0)
        port = srv.sockets[0].getsockname()[1]
        try:
            with pytest.raises(ConnectionError, match="not a Sound Recognition"):
                await espstream.connect(f"tcp://127.0.0.1:{port}", "whatever-long")
        finally:
            srv.close()
        with pytest.raises(ConnectionError, match="cannot reach"):
            await espstream.connect(f"tcp://127.0.0.1:{port}", "whatever-long")   # closed now
    run(go())


def test_read_source_streams_and_reconnects():
    async def go():
        esp = await FakeESP(drop_after=16000).start()
        got, states = [], []
        task = asyncio.create_task(audio.read_source({"id": "e", "type": "esphome", "url": esp.url, "password": "correct-horse"},
                                                     got.append, lambda s, e: states.append((s, e)), chunk_samples=1600))
        try:
            for _ in range(100):
                await asyncio.sleep(0.1)
                if esp.accepted >= 2 and len(got) > 12:
                    break
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await esp.stop()
        return got, states, esp.accepted
    got, states, accepted = run(go())
    assert accepted >= 2, "the service reconnected after the device dropped the connection"
    assert all(isinstance(c, np.ndarray) and c.dtype == np.int16 and len(c) == 1600 for c in got)
    assert ("connected", None) in states and any(s == "reconnecting" for s, _ in states)


def test_read_source_reports_a_wrong_password():
    async def go():
        esp = await FakeESP().start()
        states = []
        task = asyncio.create_task(audio.read_source({"id": "e", "type": "esphome", "url": esp.url, "password": "wrong-password"},
                                                     lambda c: None, lambda s, e: states.append((s, e))))
        await asyncio.sleep(0.6)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await esp.stop()
        return states
    states = run(go())
    assert states and states[0][0] == "reconnecting" and "password" in states[0][1]


def test_config_requires_url_and_password():
    cat = Catalog(cm.load_raw())
    def errors(**src):
        cfg = cfgmod._merge(cfgmod.DEFAULTS, {"sources": [{"id": "mic", "type": "esphome", **src}]})
        return cfgmod.validate(cfg, cat)
    assert not errors(url="tcp://192.168.1.50:6055", password="long-enough-pw")
    assert any("password is required" in e for e in errors(url="tcp://192.168.1.50:6055"))
    assert any("at least 8" in e for e in errors(url="tcp://192.168.1.50:6055", password="short"))
    assert any("tcp://" in e for e in errors(url="rtsp://x/y", password="long-enough-pw"))
