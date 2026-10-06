"""The device code of esphome/components/sound_recognition_stream, compiled for a PC and driven by the real service client.
Skipped when g++ or the OpenSSL headers are missing."""
import asyncio
import os
import shutil
import socket
import subprocess
import time

import numpy as np
import pytest

from soundrec import espstream

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "esphome")
pytestmark = pytest.mark.skipif(shutil.which("g++") is None or not os.path.exists("/usr/include/openssl/hmac.h"),
                                reason="needs g++ and the OpenSSL headers")


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    exe = str(tmp_path_factory.mktemp("esp") / "host_harness")
    comp = os.path.join(ROOT, "components", "sound_recognition_stream")
    subprocess.run(["g++", "-std=c++17", "-O1", "-DUSE_ESP32", "-I" + os.path.join(ROOT, "test", "stubs"), "-I" + comp,
                    os.path.join(ROOT, "test", "host_harness.cpp"), os.path.join(comp, "sound_recognition_stream.cpp"),
                    "-lcrypto", "-lpthread", "-o", exe], check=True)
    return exe


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(harness, port, password="abcdefgh1234", seconds=8):
    p = subprocess.Popen([harness, str(port), password, str(seconds)])
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p
        except OSError:
            time.sleep(0.1)
    p.kill()
    raise RuntimeError("device did not start")


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())


def test_service_client_gets_the_stream_from_the_device_code(harness):
    port = free_port()
    p = start(harness, port)
    try:
        async def go():
            reader, writer = await espstream.connect(f"tcp://127.0.0.1:{port}", "abcdefgh1234")
            data = await asyncio.wait_for(reader.readexactly(4000), timeout=3)
            writer.close()
            return np.frombuffer(data, dtype=np.int16)
        pcm = run(go())
    finally:
        p.kill()
    # the fake microphone sends a 0..999 ramp: consecutive samples increase by one, wrapping at 1000
    steps = np.diff(pcm.astype(int)) % 1000
    assert (steps == 1).all(), "the 16-bit stream stays aligned and in order"


def test_wrong_password_never_gets_audio_and_a_good_client_can_still_connect(harness):
    port = free_port()
    p = start(harness, port)
    try:
        async def go():
            with pytest.raises(ConnectionError):
                await espstream.connect(f"tcp://127.0.0.1:{port}", "wrong-password")
            reader, writer = await espstream.connect(f"tcp://127.0.0.1:{port}", "abcdefgh1234")
            data = await asyncio.wait_for(reader.readexactly(800), timeout=3)
            writer.close()
            return len(data)
        assert run(go()) == 800
    finally:
        p.kill()


def test_raw_connection_receives_only_the_hello_and_nothing_else(harness):
    port = free_port()
    p = start(harness, port)
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=2)
        hello = s.recv(64)
        assert hello[:6] == b"SRESP1" and len(hello) == 22
        s.settimeout(1.0)
        with pytest.raises(socket.timeout):   # no audio without the answer
            s.recv(64)
        s.close()
    finally:
        p.kill()


def test_a_second_authenticated_client_takes_over_a_streaming_one(harness):
    port = free_port()
    p = start(harness, port)
    try:
        async def go():
            r1, w1 = await espstream.connect(f"tcp://127.0.0.1:{port}", "abcdefgh1234")
            await asyncio.wait_for(r1.readexactly(400), timeout=3)
            r2, w2 = await espstream.connect(f"tcp://127.0.0.1:{port}", "abcdefgh1234")
            await asyncio.wait_for(r2.readexactly(400), timeout=3)
            w2.close()
            w1.close()
        run(go())
    finally:
        p.kill()
