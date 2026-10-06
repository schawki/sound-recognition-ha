"""A stand-in for the ESP32 side of the ESPHome stream (same protocol as esphome/components/sound_recognition_stream)."""
import asyncio
import hashlib
import hmac
import os

import numpy as np

from soundrec import espstream


class FakeESP:
    def __init__(self, password="correct-horse", pcm=None, drop_after=None):
        self.password, self.drop_after = password, drop_after
        self.pcm = pcm if pcm is not None else (np.sin(np.arange(16000) * 0.1) * 8000).astype(np.int16)
        self.connections = 0
        self.accepted = 0
        self.server = None

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        self.url = f"tcp://127.0.0.1:{self.port}"
        return self

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

    async def _handle(self, reader, writer):
        self.connections += 1
        nonce = os.urandom(espstream.NONCE_LEN)
        try:
            writer.write(espstream.MAGIC + nonce)
            await writer.drain()
            given = await asyncio.wait_for(reader.readexactly(32), timeout=3)
            if not hmac.compare_digest(given, hmac.new(self.password.encode(), nonce, hashlib.sha256).digest()):
                writer.close()
                return
            self.accepted += 1
            writer.write(b"\x01")
            sent = 0
            while True:
                writer.write(self.pcm.tobytes())
                await writer.drain()
                sent += len(self.pcm)
                if self.drop_after and sent >= self.drop_after:
                    writer.close()
                    return
                await asyncio.sleep(0.05)
        except (ConnectionError, asyncio.IncompleteReadError, asyncio.TimeoutError):
            pass
        finally:
            writer.close()
