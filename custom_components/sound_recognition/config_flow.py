"""Config flow (connection to the service) and options flow (its address; everything else is set in the panel)."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers import selector as sel
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, SoundRecClient, SoundRecError
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _num(lo: float, hi: float, step: float = 1, unit: str | None = None) -> sel.NumberSelector:
    cfg: dict = {"min": lo, "max": hi, "step": step, "mode": sel.NumberSelectorMode.BOX}
    if unit is not None:
        cfg["unit_of_measurement"] = unit
    return sel.NumberSelector(sel.NumberSelectorConfig(**cfg))


async def _check(hass, host: str, port: int, token: str) -> None:
    client = SoundRecClient(async_get_clientsession(hass), host, port, token)
    await client.health()
    await client.sources()  # an authenticated call: raises InvalidAuth for a wrong token


class SoundRecConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port, token = user_input[CONF_HOST].strip(), int(user_input[CONF_PORT]), user_input[CONF_TOKEN].strip()
            try:
                await _check(self.hass, host, port, token)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except SoundRecError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Sound Recognition ({host})",
                                               data={CONF_HOST: host, CONF_PORT: port, CONF_TOKEN: token})
        schema = vol.Schema({
            vol.Required(CONF_HOST): sel.TextSelector(),
            vol.Required(CONF_PORT, default=DEFAULT_PORT): _num(1, 65535),
            vol.Required(CONF_TOKEN): sel.TextSelector(sel.TextSelectorConfig(type=sel.TextSelectorType.PASSWORD)),
        })
        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(schema, user_input), errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _check(self.hass, entry.data[CONF_HOST], entry.data[CONF_PORT], user_input[CONF_TOKEN].strip())
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: user_input[CONF_TOKEN].strip()})
        schema = vol.Schema({vol.Required(CONF_TOKEN): sel.TextSelector(sel.TextSelectorConfig(type=sel.TextSelectorType.PASSWORD))})
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SoundRecOptionsFlow()


class SoundRecOptionsFlow(OptionsFlow):
    """The address of the service. Everything else (sources, sounds, advice, storage, token) is set in the Sound Recognition panel."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = user_input[CONF_HOST].strip(), int(user_input[CONF_PORT])
            try:
                await _check(self.hass, host, port, entry.data[CONF_TOKEN])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except SoundRecError:
                errors["base"] = "unknown"
            else:
                other = next((e for e in self.hass.config_entries.async_entries(DOMAIN)
                              if e.entry_id != entry.entry_id and e.unique_id == f"{host}:{port}"), None)
                if other is not None:
                    errors["base"] = "already_configured"
                else:
                    changed = (host, port) != (entry.data[CONF_HOST], entry.data[CONF_PORT])
                    if changed:
                        self.hass.config_entries.async_update_entry(
                            entry, unique_id=f"{host}:{port}", title=f"Sound Recognition ({host})", data={**entry.data, CONF_HOST: host, CONF_PORT: port})
                        self.hass.config_entries.async_schedule_reload(entry.entry_id)
                    return self.async_create_entry(data=dict(entry.options))
        schema = vol.Schema({
            vol.Required(CONF_HOST): sel.TextSelector(),
            vol.Required(CONF_PORT): _num(1, 65535),
        })
        current = user_input or {CONF_HOST: entry.data[CONF_HOST], CONF_PORT: entry.data[CONF_PORT]}
        return self.async_show_form(step_id="init", data_schema=self.add_suggested_values_to_schema(schema, current), errors=errors)
