"""Update entity of the service: shows the installed and latest release, installs from Home Assistant when the installation allows it."""
from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SoundRecConfigEntry
from .api import SoundRecError
from .const import MANUAL_UPDATE_COMMAND
from .entity import SoundRecServiceEntity


async def async_setup_entry(hass: HomeAssistant, entry: SoundRecConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([SoundRecServiceUpdate(entry.runtime_data.coordinator)])


class SoundRecServiceUpdate(SoundRecServiceEntity, UpdateEntity):
    _attr_translation_key = "service"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_title = "Sound Recognition"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_service_update"

    @property
    def _up(self):
        return self.coordinator.updates

    @property
    def available(self) -> bool:
        return super().available or self._up.installing        # the service is down while it restarts

    @property
    def supported_features(self) -> UpdateEntityFeature:
        features = UpdateEntityFeature.RELEASE_NOTES | UpdateEntityFeature.PROGRESS
        return features | UpdateEntityFeature.INSTALL if self._up.capable else features

    @property
    def installed_version(self) -> str | None:
        return self._up.installed

    @property
    def latest_version(self) -> str | None:
        return self._up.latest.lstrip("v") if self._up.available and self._up.latest else self._up.installed

    @property
    def release_url(self) -> str:
        return self._up.release_url

    @property
    def in_progress(self) -> bool:
        return self._up.installing

    async def async_release_notes(self) -> str | None:
        notes = await self._up.async_release_notes()
        if self._up.capable:
            return notes
        return f"{notes or ''}\n\n`{MANUAL_UPDATE_COMMAND}`".strip()

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        try:
            await self._up.async_start()
        except SoundRecError as err:
            raise HomeAssistantError(str(err)) from err
