"""Lists the streams of a go2rtc server, so the panel can offer them when adding a source."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import aiohttp

GO2RTC_API_PORT = 1984
GO2RTC_RTSP_PORT = 8554
CONF_GO2RTC_URL = "go2rtc_url"


class Go2RtcError(Exception):
    """The go2rtc server could not be reached or did not answer as expected."""


def normalize_url(raw: str) -> str:
    """'192.168.1.5' -> 'http://192.168.1.5:1984'; keeps an explicit scheme/port; drops path and trailing slash."""
    raw = raw.strip()
    if not raw:
        raise Go2RtcError("empty address")
    if "://" not in raw:
        raw = "http://" + raw
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise Go2RtcError("invalid address")
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    return f"{parts.scheme}://{host}:{parts.port or GO2RTC_API_PORT}"


def rtsp_url(base: str, name: str) -> str:
    """RTSP address of a stream, on the same host as the go2rtc API."""
    host = urlsplit(base).hostname or ""
    host = f"[{host}]" if ":" in host else host
    return f"rtsp://{host}:{GO2RTC_RTSP_PORT}/{name}"


def parse_streams(data: Any, base: str) -> list[dict[str, str]]:
    """go2rtc answers {name: {producers: [...], consumers: [...]}}."""
    if not isinstance(data, dict):
        raise Go2RtcError("unexpected answer")
    return [{"name": name, "url": rtsp_url(base, name)} for name in sorted(data, key=str.lower)]


async def fetch_streams(session: aiohttp.ClientSession, base: str) -> list[dict[str, str]]:
    try:
        async with session.get(f"{base}/api/streams", timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                raise Go2RtcError(f"HTTP {resp.status}")
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise Go2RtcError(str(err) or err.__class__.__name__) from err
    return parse_streams(data, base)
