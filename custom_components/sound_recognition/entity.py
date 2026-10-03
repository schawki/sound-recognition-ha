"""Base entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SoundRecCoordinator


def service_device(entry_id: str) -> tuple[str, str]:
    return (DOMAIN, entry_id)


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
            via_device=service_device(self._entry_id),
        )

    @property
    def source_state(self) -> dict:
        return (self.coordinator.data or {}).get("sources", {}).get(self._sid, {})
