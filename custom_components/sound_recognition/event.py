"""One event entity per source: fires 'detection' immediately and 'clip_ready' when the clip has been saved."""
from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SoundRecConfigEntry, signed_clip_url
from .entity import SoundRecSourceEntity


async def async_setup_entry(hass: HomeAssistant, entry: SoundRecConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coord = entry.runtime_data.coordinator
    async_add_entities(SoundRecEventEntity(coord, s) for s in coord.service_config.get("sources", []) if s.get("enabled", True))


class SoundRecEventEntity(SoundRecSourceEntity, EventEntity):
    _attr_translation_key = "sound"
    _attr_event_types = ["detection", "clip_ready"]

    def __init__(self, coordinator, source) -> None:
        super().__init__(coordinator, source)
        self._attr_unique_id = f"{self._entry_id}_{self._sid}_event"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(self.hass, self.coordinator.signal, self._handle_message))

    @callback
    def _handle_message(self, msg: dict) -> None:
        if msg.get("source") != self._sid:
            return
        if msg["type"] == "detection":
            self._trigger_event("detection", {
                "event_id": msg["id"], "class": msg.get("name") or msg["class"], "audioset_mid": msg["mid"],
                "score": msg["score"], "duration_s": msg["duration_s"], "level_dbfs": msg.get("level_dbfs"),
                "started_at": msg["started_at"], "clip_retention_days": msg.get("clip_retention_days", 0),
            })
        else:
            self._trigger_event("clip_ready", {
                "event_id": msg["id"], "audioset_mid": msg["mid"], "expires_at": msg["expires_at"],
                "clip_url": signed_clip_url(self.hass, self._entry_id, msg["clip"]),
            })
        self.async_write_ha_state()
