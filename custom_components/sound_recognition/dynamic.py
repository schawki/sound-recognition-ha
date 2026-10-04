"""Keeps the service informed of what the devices around each source (and the neighbouring rooms) do to its thresholds.

Only sources whose `devices.enabled` is true are handled. The result is pushed with a time to live, so if Home Assistant stops, the
service goes back to its normal thresholds by itself."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval
from datetime import timedelta

from . import devices
from .api import SoundRecError
from .const import SIGNAL_LIVE

if TYPE_CHECKING:
    from .coordinator import SoundRecCoordinator

_LOGGER = logging.getLogger(__name__)
KEEPALIVE_S, TTL_S, DEBOUNCE_S = 20, 60, 1.0


class DynamicManager:
    def __init__(self, hass: HomeAssistant, coordinator: SoundRecCoordinator) -> None:
        self.hass, self.coordinator = hass, coordinator
        self.last: dict[str, tuple[float, list[str], list[dict]]] = {}
        self._unsubs: list[CALLBACK_TYPE] = []
        self._track: CALLBACK_TYPE | None = None
        self._tracked: set[str] = set()
        self._timer: CALLBACK_TYPE | None = None

    def enabled_sources(self) -> list[dict]:
        return [s for s in self.coordinator.service_config.get("sources", []) if s.get("enabled", True) and (s.get("devices") or {}).get("enabled")]

    @callback
    def start(self) -> None:
        if not self.enabled_sources():
            return
        self._unsubs.append(async_dispatcher_connect(self.hass, SIGNAL_LIVE.format(self.coordinator.config_entry.entry_id), self._on_live))
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, timedelta(seconds=KEEPALIVE_S)))
        self._retrack()
        self._schedule()

    @callback
    def stop(self) -> None:
        for u in self._unsubs:
            u()
        self._unsubs = []
        for attr in ("_track", "_timer"):
            if (u := getattr(self, attr)):
                u()
                setattr(self, attr, None)

    def _entities(self) -> set[str]:
        cfg = self.coordinator.service_config
        links = cfg.get("area_links") or []
        found = {l["sensor"] for l in links if l.get("sensor")}
        for src in self.enabled_sources():
            found.update(eid for eid, _ in devices.selected(self.hass, src, links))
        return found

    def _retrack(self) -> None:
        wanted = self._entities()
        if wanted == self._tracked and self._track:
            return
        if self._track:
            self._track()
        self._tracked = wanted
        self._track = async_track_state_change_event(self.hass, list(wanted), self._on_state) if wanted else None

    @callback
    def _on_state(self, event) -> None:
        self._schedule()

    @callback
    def _on_live(self, msg: dict) -> None:
        if msg.get("type") == "context":
            self._schedule()

    @callback
    def _schedule(self) -> None:
        if self._timer is None:
            self._timer = async_call_later(self.hass, DEBOUNCE_S, self._fire)

    async def _fire(self, _now) -> None:
        self._timer = None
        await self.push()

    async def _tick(self, _now) -> None:
        self._retrack()
        await self.push()

    def compute_all(self) -> dict[str, tuple[float, list[str], list[dict]]]:
        co = self.coordinator
        statuses = (co.data or {}).get("sources", {})
        names = {m: co.class_name(m) for m in co.inhibitors}
        out = {}
        for src in self.enabled_sources():
            out[src["id"]] = devices.compute(self.hass, co.service_config, src, statuses, co.inhibitors, names)
        return out

    async def push(self) -> None:
        self.last = self.compute_all()
        for sid, (offset, reasons, detail) in self.last.items():
            try:
                await self.coordinator.client.set_external(sid, offset, reasons, detail, TTL_S)
            except SoundRecError as err:
                _LOGGER.debug("Could not push the device offset of %s: %s", sid, err)
