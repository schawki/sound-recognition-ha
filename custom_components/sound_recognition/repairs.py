"""Repair issue for entities that the configuration no longer provides: the administrator chooses to remove or keep them."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers import selector as sel

from .api import SoundRecError
from .const import DOMAIN
from .helpers import expected_unique_ids
from .patch import apply_patch, describe_patch

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


class AdviceFixFlow(RepairsFlow):
    """Applies the gesture of an advice after the administrator confirms: the same patch as the Apply button of the panel."""

    def __init__(self, issue_id: str, entry_id: str, patch: dict) -> None:
        self.issue_id, self.entry_id, self.patch = issue_id, entry_id, patch

    async def async_step_init(self, user_input: dict | None = None) -> data_entry_flow.FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> data_entry_flow.FlowResult:
        entry = self.hass.config_entries.async_get_entry(self.entry_id)
        if entry is None or not hasattr(entry, "runtime_data"):
            return self.async_abort(reason="not_loaded")
        co = entry.runtime_data.coordinator
        audio = {c["mid"]: c.get("audioset_name") or c["name"] for c in co.catalog.get("classes", [])}
        names = {c["mid"]: c["name"] for c in co.catalog.get("classes", [])}
        if user_input is None:
            changes = describe_patch(self.patch, names, co.lang)
            src = next((s for s in co.service_config.get("sources", []) if s["id"] == self.patch.get("source")), {})
            return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}),
                                        description_placeholders={"source": src.get("name") or self.patch.get("source", ""), "changes": changes})
        try:
            cfg = apply_patch(await co.client.get_config(), self.patch, audio)
            check = await co.client.validate_config(cfg, co.lang)
            if check.get("errors"):
                return self.async_abort(reason="invalid", description_placeholders={"errors": "; ".join(check["errors"])})
            await co.client.put_config(cfg, co.lang)
        except SoundRecError:
            return self.async_abort(reason="cannot_connect")
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_create_entry(data={})


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict | None) -> RepairsFlow:
    data = data or {}
    if data.get("kind") == "advice":
        return AdviceFixFlow(issue_id, data["entry_id"], data.get("apply") or {})
    return StaleEntitiesFlow(data["entry_id"])
