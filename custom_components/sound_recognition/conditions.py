"""Keeps the service informed of the Home Assistant states its conditions read ("listen only when the house is empty").

The conditions are in the configuration (`condition`, next to `schedule`, at the same levels). The service evaluates them; this module only
finds which entities they read and pushes their states, with a time to live: if Home Assistant stops, the states become unknown for the service
and each condition follows its own `if_unknown` (to listen, unless told otherwise)."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval

from .api import SoundRecError

if TYPE_CHECKING:
    from .coordinator import SoundRecCoordinator

_LOGGER = logging.getLogger(__name__)
KEEPALIVE_S, TTL_S, DEBOUNCE_S = 30, 120, 1.0
PERSON_DOMAIN = "person."


def collect(cfg: dict[str, Any]) -> tuple[set[str], bool]:
    """(entities read by the conditions, whether one of them looks at the people of the house). Pure."""
    blocks: list[Any] = [cfg.get("defaults") or {}, *(cfg.get("classes") or {}).values()]
    for src in cfg.get("sources") or []:
        if src.get("enabled", True):
            blocks.append(src)
            blocks.extend((src.get("classes") or {}).values())
    found: set[str] = set()
    people = False
    for blk in blocks:
        cond = blk.get("condition") if isinstance(blk, dict) else None
        for rule in (cond or {}).get("rules") or []:
            if isinstance(rule, dict) and isinstance(rule.get("entity"), str):
                found.add(rule["entity"])
            elif isinstance(rule, dict) and "people" in rule:
                people = True
    return found, people


class ConditionManager:
    def __init__(self, hass: HomeAssistant, coordinator: SoundRecCoordinator) -> None:
        self.hass, self.coordinator = hass, coordinator
        self.entities, self.people = collect(coordinator.service_config)
        self._unsubs: list[CALLBACK_TYPE] = []
        self._track: CALLBACK_TYPE | None = None
        self._tracked: set[str] = set()
        self._timer: CALLBACK_TYPE | None = None
        self._warned = False

    def wanted(self) -> bool:
        return bool(self.entities) or self.people

    def watched(self) -> set[str]:
        found = set(self.entities)
        if self.people:
            found.update(s.entity_id for s in self.hass.states.async_all("person"))
        return found

    def states(self) -> dict[str, str]:
        """{entity_id: state} for what exists; an entity Home Assistant does not know is left out, which the service reads as unknown."""
        out = {}
        for eid in self.watched():
            if (st := self.hass.states.get(eid)) is not None:
                out[eid] = st.state
        return out

    @callback
    def start(self) -> None:
        if not self.wanted():
            return
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

    def _retrack(self) -> None:
        wanted = self.watched()
        if wanted == self._tracked and self._track:
            return
        if self._track:
            self._track()
        self._tracked = wanted
        self._track = async_track_state_change_event(self.hass, list(wanted), self._on_state) if wanted else None

    @callback
    def _on_state(self, _event) -> None:
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

    async def push(self) -> None:
        try:
            await self.coordinator.client.set_conditions(self.states(), TTL_S)
        except SoundRecError as err:
            if not self._warned:
                self._warned = True
                _LOGGER.warning("The service did not take the states of the conditions (%s). A service older than API level 12 ignores conditions: update it.", err)
            else:
                _LOGGER.debug("Could not push the states of the conditions: %s", err)
