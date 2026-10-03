"""Async client for the Sound Recognition service API."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp


class SoundRecError(Exception):
    """Base error."""


class CannotConnect(SoundRecError):
    """The service cannot be reached."""


class InvalidAuth(SoundRecError):
    """The token was refused."""


class InvalidConfig(SoundRecError):
    """The service rejected a configuration; .errors lists the reasons."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class SoundRecClient:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str) -> None:
        self._session = session
        self._base = f"http://{host}:{port}/api/v1"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, *, json: Any = None, params: dict | None = None, auth: bool = True) -> Any:
        try:
            async with self._session.request(
                method, f"{self._base}{path}", json=json, params=params,
                headers=self._headers if auth else None, timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise InvalidAuth
                if resp.status == 422:
                    raise InvalidConfig((await resp.json()).get("errors", []))
                if resp.status >= 400:
                    raise SoundRecError(f"HTTP {resp.status} on {path}")
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err

    async def health(self) -> dict:
        return await self._request("GET", "/health", auth=False)

    async def sources(self) -> list[dict]:
        return (await self._request("GET", "/sources"))["sources"]

    async def warnings(self, lang: str, overrides: bool = True) -> list[dict]:
        params = {"lang": lang} if overrides else {"lang": lang, "overrides": "0"}
        return (await self._request("GET", "/warnings", params=params))["warnings"]

    async def catalog(self, lang: str) -> dict:
        return await self._request("GET", "/catalog", params={"lang": lang})

    async def get_config(self) -> dict:
        return await self._request("GET", "/config")

    async def put_config(self, cfg: dict, lang: str) -> dict:
        return await self._request("PUT", "/config", json=cfg, params={"lang": lang})

    async def validate_config(self, cfg: dict, lang: str) -> dict:
        return await self._request("POST", "/config/validate", json=cfg, params={"lang": lang})

    async def events(self, lang: str, **query: Any) -> list[dict]:
        params = {"lang": lang, **{k: v for k, v in query.items() if v is not None}}
        return (await self._request("GET", "/events", params=params))["events"]

    async def resolved(self, source: str, mid: str) -> dict:
        return await self._request("GET", "/resolved", params={"source": source, "class": mid})

    async def clip(self, rel: str) -> bytes | None:
        try:
            async with self._session.get(f"{self._base}/clips/{rel}", headers=self._headers,
                                         timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 404:
                    return None
                if resp.status == 401:
                    raise InvalidAuth
                resp.raise_for_status()
                return await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err

    async def listen(self, lang: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        """Receive live messages until the connection drops (the caller reconnects)."""
        try:
            async with self._session.ws_connect(f"{self._base}/ws", params={"lang": lang}, headers=self._headers,
                                                heartbeat=20, timeout=aiohttp.ClientWSTimeout(ws_close=10)) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await handler(msg.json())
                    elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                        break
        except aiohttp.WSServerHandshakeError as err:
            if err.status == 401:
                raise InvalidAuth from err
            raise CannotConnect(str(err)) from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err
