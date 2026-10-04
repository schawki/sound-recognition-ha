"""Repair issue for entities that the configuration no longer provides: the administrator chooses to remove or keep them."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers import selector as sel

from .const import DOMAIN
from .helpers import expected_unique_ids

CONF_KEPT = "kept_entities"
SHOWN = 8


def issue_id(entry_id: str) -> str:
    return f"stale_entities_{entry_id}"


def stale_entries(hass: HomeAssistant, entry: ConfigEntry, cfg: dict, index: dict) -> list[er.RegistryEntry]:
    """Registry entries of this config entry that the configuration no longer provides and the administrator has not chosen to keep."""
    if "sources" not in cfg or not index:
        return []                                       # configuration not read properly: claim nothing
    keep = expected_unique_ids(entry.entry_id, cfg, index) | set(entry.options.get(CONF_KEPT, []))
    registry = er.async_get(hass)
    return sorted((r for r in er.async_entries_for_config_entry(registry, entry.entry_id) if r.unique_id not in keep), key=lambda r: r.entity_id)


def _label(reg: er.RegistryEntry) -> str:
    return reg.name or reg.original_name or reg.entity_id


def sync_stale_issue(hass: HomeAssistant, entry: ConfigEntry, cfg: dict, index: dict) -> None:
    stale = stale_entries(hass, entry, cfg, index)
    if not stale:
        ir.async_delete_issue(hass, DOMAIN, issue_id(entry.entry_id))
        return
    names = ", ".join(_label(r) for r in stale[:SHOWN]) + (f" (+{len(stale) - SHOWN})" if len(stale) > SHOWN else "")
    ir.async_create_issue(
        hass, DOMAIN, issue_id(entry.entry_id), is_fixable=True, severity=ir.IssueSeverity.WARNING,
        translation_key="stale_entities", translation_placeholders={"count": str(len(stale)), "entities": names},
        data={"entry_id": entry.entry_id},
    )


def clear_stale_issue(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry.entry_id))


class StaleEntitiesFlow(RepairsFlow):
    def __init__(self, entry_id: str) -> None:
        self.entry_id = entry_id

    async def async_step_init(self, user_input: dict | None = None) -> data_entry_flow.FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if entry is None or not hasattr(entry, "runtime_data"):
            ir.async_delete_issue(self.hass, DOMAIN, issue_id(self.entry_id))
            return self.async_abort(reason="not_loaded")
        coordinator = entry.runtime_data.coordinator
        stale = stale_entries(self.hass, entry, coordinator.service_config, coordinator.index)
        if user_input and "action" in user_input:      # the repairs view opens the step with an empty dict
            if user_input["action"] == "remove":
                registry = er.async_get(self.hass)
                for reg in stale:
                    registry.async_remove(reg.entity_id)
            else:
                kept = set(entry.options.get(CONF_KEPT, [])) | {r.unique_id for r in stale}
                self.hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_KEPT: sorted(kept)})
            ir.async_delete_issue(self.hass, DOMAIN, issue_id(self.entry_id))
            return self.async_create_entry(data={})
        names = ", ".join(_label(r) for r in stale[:SHOWN]) + (f" (+{len(stale) - SHOWN})" if len(stale) > SHOWN else "")
        schema = vol.Schema({vol.Required("action", default="keep"): sel.SelectSelector(sel.SelectSelectorConfig(
            options=["remove", "keep"], mode=sel.SelectSelectorMode.LIST, translation_key="stale_action"))})
        return self.async_show_form(step_id="init", data_schema=schema, description_placeholders={"count": str(len(stale)), "entities": names})


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict | None) -> RepairsFlow:
    return StaleEntitiesFlow((data or {})["entry_id"])
