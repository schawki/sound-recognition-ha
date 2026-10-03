"""Sensors: sound level per source, advice count for the service."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SoundRecConfigEntry
from .entity import SoundRecServiceEntity, SoundRecSourceEntity


async def async_setup_entry(hass: HomeAssistant, entry: SoundRecConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    entities: list = [SoundRecWarningsSensor(coord)]
    for s in coord.service_config.get("sources", []):
        if s.get("enabled", True):
            entities.append(SoundRecLevelSensor(coord, s))
    async_add_entities(entities)


class SoundRecLevelSensor(SoundRecSourceEntity, SensorEntity):
    _attr_translation_key = "level"
    _attr_native_unit_of_measurement = "dBFS"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, source) -> None:
        super().__init__(coordinator, source)
        self._attr_unique_id = f"{self._entry_id}_{self._sid}_level"

    @property
    def available(self) -> bool:
        return super().available and bool(self.source_state.get("connected"))

    @property
    def native_value(self) -> float | None:
        return self.source_state.get("level_dbfs")


class SoundRecWarningsSensor(SoundRecServiceEntity, SensorEntity):
    _attr_translation_key = "advice"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_advice"

    def _important(self) -> list[dict]:
        return [w for w in (self.coordinator.data or {}).get("warnings", []) if w["level"] in ("warning", "danger")]

    @property
    def native_value(self) -> int:
        return len(self._important())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"messages": [w["message"] for w in self._important()][:20]}
