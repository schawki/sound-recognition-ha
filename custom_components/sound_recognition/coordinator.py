"""Coordinator: REST refresh + live WebSocket messages from the service; keeps repair issues in sync with its advice."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, SoundRecClient, SoundRecError
from .const import DOMAIN, MANUAL_UPDATE_COMMAND, SIGNAL_LIVE, SIGNAL_MESSAGE, UPDATE_INTERVAL_S
from .helpers import build_index
from .updates import ServiceUpdate

if TYPE_CHECKING:
    from . import SoundRecConfigEntry

_LOGGER = logging.getLogger(__name__)


class SoundRecCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: SoundRecConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SoundRecConfigEntry, client: SoundRecClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=UPDATE_INTERVAL_S))
        self.client = client
        self.lang = hass.config.language
        self.service_config: dict = {}
        self.catalog: dict = {}
        self.index: dict = {}
        self._issues: set[str] = set()
        self.version: str | None = None
        self.health: dict = {}
        self.updates = ServiceUpdate(hass, self)

    @property
    def signal(self) -> str:
        return SIGNAL_MESSAGE.format(self.config_entry.entry_id)

    def class_name(self, mid: str) -> str:
        c = self.index.get("by_mid", {}).get(mid)
        return c["name"] if c else mid

    @property
    def inhibitors(self) -> set[str]:
        """Classes that, once heard, explain other sounds (television, music...)."""
        found: set[str] = set()
        for c in self.index.get("by_mid", {}).values():
            found.update(c.get("inhibiting_contexts") or [])
        return found

    async def _async_setup(self) -> None:
        try:
            self.health = await self.client.health()
            self.version = self.health.get("version")
            self.catalog = await self.client.catalog(self.lang)
            self.service_config = await self.client.get_config()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except SoundRecError as err:
            raise UpdateFailed(str(err)) from err
        self.index = build_index(self.catalog)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            self.health = await self.client.health()
            self.version = self.health.get("version")
            sources = await self.client.sources()
            warnings = await self.client.warnings(self.lang)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except SoundRecError as err:
            raise UpdateFailed(str(err)) from err
        self._sync_issues(warnings)
        self._sync_outdated_issue()
        await self.updates.async_check()
        return {"sources": {s["id"]: s for s in sources}, "warnings": warnings}

    # ---------------------------------------------------------------- live messages
    def start_listener(self) -> None:
        self.config_entry.async_create_background_task(self.hass, self._listen(), f"{DOMAIN}_listener")

    async def _listen(self) -> None:
        backoff = 2
        while True:
            try:
                await self.client.listen(self.lang, self._on_message)
                backoff = 2
            except InvalidAuth:
                self.config_entry.async_start_reauth(self.hass)
                return
            except CannotConnect as err:
                _LOGGER.debug("WebSocket unavailable: %s", err)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    async def _on_message(self, msg: dict) -> None:
        kind = msg.get("type")
        async_dispatcher_send(self.hass, SIGNAL_LIVE.format(self.config_entry.entry_id), msg)
        data = self.data or {"sources": {}, "warnings": []}
        if kind in ("hello", "status"):
            data = {**data, "sources": {s["id"]: s for s in msg.get("sources", [])}}
        elif kind in ("active", "source_state"):
            srcs = dict(data["sources"])
            cur = dict(srcs.get(msg["source"], {}))
            if kind == "active":
                cur["active_classes"] = msg["active_classes"]
            else:
                cur["connected"] = msg["state"] == "connected"
                cur["error"] = msg.get("error")
            srcs[msg["source"]] = cur
            data = {**data, "sources": srcs}
        elif kind == "context":
            srcs = dict(data["sources"])
            cur = dict(srcs.get(msg["source"], {}))
            cur.update({k: v for k, v in msg.items() if k not in ("type", "source")})
            srcs[msg["source"]] = cur
            data = {**data, "sources": srcs}
        elif kind in ("detection", "clip_ready"):
            async_dispatcher_send(self.hass, self.signal, msg)
            return
        else:
            return
        self.async_set_updated_data(data)

    # ---------------------------------------------------------------- repairs
    def _sync_issues(self, warnings: list[dict]) -> None:
        names = {s["id"]: (s.get("name") or s["id"]) for s in self.service_config.get("sources", [])}
        wanted: dict[str, dict] = {}
        for w in warnings:
            if w["level"] not in ("warning", "danger"):
                continue
            iid = f"{self.config_entry.entry_id}_{w['rule']}_{w['source']}_{'_'.join(sorted(c.strip('/').replace('/', '_') for c in w['classes']))}"
            wanted[iid] = w
        for iid, w in wanted.items():
            ir.async_create_issue(
                self.hass, DOMAIN, iid, is_fixable=False,
                severity=ir.IssueSeverity.ERROR if w["level"] == "danger" else ir.IssueSeverity.WARNING,
                translation_key="advice",
                translation_placeholders={"source": names.get(w["source"], w["source"]), "message": w["message"]},
            )
        for iid in self._issues - set(wanted):
            ir.async_delete_issue(self.hass, DOMAIN, iid)
        self._issues = set(wanted)

    def _sync_outdated_issue(self) -> None:
        iid = f"service_outdated_{self.config_entry.entry_id}"
        if self.updates.outdated:
            ir.async_create_issue(
                self.hass, DOMAIN, iid, is_fixable=False, severity=ir.IssueSeverity.WARNING, translation_key="service_outdated",
                translation_placeholders={"version": self.version or "?", "command": MANUAL_UPDATE_COMMAND})
        else:
            ir.async_delete_issue(self.hass, DOMAIN, iid)

    def clear_issues(self) -> None:
        ir.async_delete_issue(self.hass, DOMAIN, f"service_outdated_{self.config_entry.entry_id}")
        for iid in self._issues:
            ir.async_delete_issue(self.hass, DOMAIN, iid)
        self._issues = set()
