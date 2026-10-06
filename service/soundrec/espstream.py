"""Client side of the Sound Recognition ESPHome stream (see esphome/README.md for the device side).

Protocol, over one TCP connection (the service connects to the ESP32):
  1. the device sends  MAGIC (6 bytes, b"SRESP1") + a random nonce (16 bytes);
  2. the service answers HMAC-SHA256(password, nonce) (32 bytes), so the password itself never travels;
  3. the device checks it and sends one byte, 0x01 (accepted). On a wrong answer it closes the connection without sending audio;
  4. then raw audio, signed 16-bit little-endian, 16 kHz, mono, until the connection closes.
"""
import asyncio
import hashlib
import hmac
from urllib.parse import urlparse

MAGIC = b"SRESP1"
NONCE_LEN = 16
DEFAULT_PORT = 6055
AUTH_TIMEOUT_S = 5.0


def parse_url(url):
    """tcp://host[:port] -> (host, port). Raises ValueError for anything else."""
    u = urlparse(url)
    if u.scheme != "tcp" or not u.hostname:
        raise ValueError("an ESPHome source url looks like tcp://192.168.1.50:6055")
    return u.hostname, u.port or DEFAULT_PORT


def answer(password, nonce):
    return hmac.new(password.encode(), nonce, hashlib.sha256).digest()


async def connect(url, password):
    """Opens the stream and authenticates. Returns (reader, writer); raises ConnectionError with a readable message."""
    host, port = parse_url(url)
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=AUTH_TIMEOUT_S)
    except (OSError, asyncio.TimeoutError) as e:
        raise ConnectionError(f"cannot reach {host}:{port} ({e or 'timeout'})") from e
    try:
        hello = await asyncio.wait_for(reader.readexactly(len(MAGIC) + NONCE_LEN), timeout=AUTH_TIMEOUT_S)
        if hello[:len(MAGIC)] != MAGIC:
            raise ConnectionError(f"{host}:{port} is not a Sound Recognition ESPHome stream")
        writer.write(answer(password, hello[len(MAGIC):]))
        await writer.drain()
        ok = await asyncio.wait_for(reader.readexactly(1), timeout=AUTH_TIMEOUT_S)
        if ok != b"\x01":
            raise ConnectionError("the device refused the password")
    except asyncio.IncompleteReadError as e:
        writer.close()
        raise ConnectionError("the device closed the connection (wrong password?)") from e
    except asyncio.TimeoutError as e:
        writer.close()
        raise ConnectionError("the device did not answer in time") from e
    except ConnectionError:
        writer.close()
        raise
    return reader, writer
