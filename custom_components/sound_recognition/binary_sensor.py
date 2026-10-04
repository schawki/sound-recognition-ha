"""Binary sensors: connection of each source, and one 'sound detected' per enabled class on each source."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SoundRecConfigEntry
from .entity import SoundRecSourceEntity
from .helpers import detected_unique_id, enabled_mids


async def async_setup_entry(hass: HomeAssistant, entry: SoundRecConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    entities: list = []
    for s in coord.service_config.get("sources", []):
        if not s.get("enabled", True):
            continue
        entities.append(SoundRecConnectionSensor(coord, s))
        for mid in sorted(enabled_mids(coord.service_config, s, coord.index)):
            entities.append(SoundRecDetectedSensor(coord, s, mid))
    async_add_entities(entities)


class SoundRecConnectionSensor(SoundRecSourceEntity, BinarySensorEntity):
    _attr_translation_key = "connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, source) -> None:
        super().__init__(coordinator, source)
        self._attr_unique_id = f"{self._entry_id}_{self._sid}_connection"

    @property
    def is_on(self) -> bool:
        return bool(self.source_state.get("connected"))

    @property
    def extra_state_attributes(self) -> dict:
        err = self.source_state.get("error")
        return {"error": err} if err else {}


class SoundRecDetectedSensor(SoundRecSourceEntity, BinarySensorEntity):
    _attr_translation_key = "detected"
    _attr_device_class = BinarySensorDeviceClass.SOUND

    def __init__(self, coordinator, source, mid: str) -> None:
        super().__init__(coordinator, source)
        self._mid = mid
        self._attr_unique_id = detected_unique_id(self._entry_id, self._sid, mid)
        self._attr_translation_placeholders = {"class_name": coordinator.class_name(mid)}

    @property
    def available(self) -> bool:
        return super().available and bool(self.source_state.get("connected"))

    @property
    def is_on(self) -> bool:
        return self._mid in self.source_state.get("active_classes", [])

    @property
    def extra_state_attributes(self) -> dict:
        return {"audioset_mid": self._mid}
