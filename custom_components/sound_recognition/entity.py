"""Base entities."""
from __future__ import annotations

import inspect

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SoundRecCoordinator


def service_device(entry_id: str) -> tuple[str, str]:
    return (DOMAIN, entry_id)


_VIA_DEVICE_ID = "via_device_id" in inspect.signature(dr.DeviceRegistry.async_get_or_create).parameters


def register_source_devices(hass: HomeAssistant, entry_id: str, sources: list[dict]) -> None:
    """Creates the device of every audio source under the service's device.
    The link to the parent is made here with its registry id (`via_device_id`); the `via_device` identifier form of DeviceInfo is deprecated."""
    registry = dr.async_get(hass)
    wanted = service_device(entry_id)                                          # looked up among this entry's own devices: the identifier-only lookup is deprecated
    parent = next((d for d in dr.async_entries_for_config_entry(registry, entry_id) if wanted in d.identifiers), None)
    for s in sources:
        link = ({"via_device_id": parent.id if parent else None} if _VIA_DEVICE_ID
                else {"via_device": service_device(entry_id)})                 # older Home Assistant: only the identifier form exists
        registry.async_get_or_create(
            config_entry_id=entry_id, identifiers={(DOMAIN, f"{entry_id}_{s['id']}")}, name=s.get("name") or s["id"],
            manufacturer="Sound Recognition", model=s.get("type"), **link)


class SoundRecServiceEntity(CoordinatorEntity[SoundRecCoordinator]):
    """Entity attached to the service device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SoundRecCoordinator) -> None:
        super().__init__(coordinator)
        self._entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(identifiers={service_device(self._entry_id)})


class SoundRecSourceEntity(CoordinatorEntity[SoundRecCoordinator]):
    """Entity attached to one audio source (microphone, camera...)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SoundRecCoordinator, source: dict) -> None:
        super().__init__(coordinator)
        self._sid = source["id"]
        self._entry_id = coordinator.config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._sid}")},
            name=source.get("name") or self._sid,
            manufacturer="Sound Recognition",
            model=source.get("type"),
        )

    @property
    def source_state(self) -> dict:
        return (self.coordinator.data or {}).get("sources", {}).get(self._sid, {})
