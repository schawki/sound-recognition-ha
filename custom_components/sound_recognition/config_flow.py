"""Config flow (connection to the service) and options flow (sources, classes, settings, advice)."""
from __future__ import annotations

import copy
import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers import selector as sel
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, InvalidConfig, SoundRecClient, SoundRecError
from .const import DEFAULT_PORT, DOMAIN, SOURCE_TYPES
from .helpers import (
    apply_class_form, apply_selection, build_index, class_form_defaults, enabled_mids, format_warnings, slugify,
    source_form_defaults, source_from_form, unique_id,
)

_LOGGER = logging.getLogger(__name__)
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
INTEREST_ORDER = {"monitor": 0, "optional": 1, "context": 2, "ignore": 3}


def _num(lo: float, hi: float, step: float = 1, unit: str | None = None) -> sel.NumberSelector:
    cfg: dict = {"min": lo, "max": hi, "step": step, "mode": sel.NumberSelectorMode.BOX}
    if unit is not None:
        cfg["unit_of_measurement"] = unit
    return sel.NumberSelector(sel.NumberSelectorConfig(**cfg))


def _select(options: list, key: str | None = None, multiple: bool = False) -> sel.SelectSelector:
    cfg: dict = {"options": options, "multiple": multiple, "mode": sel.SelectSelectorMode.DROPDOWN}
    if key is not None:
        cfg["translation_key"] = key
    return sel.SelectSelector(sel.SelectSelectorConfig(**cfg))


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
    """Everything lives in the service; each step reads the service configuration, edits it and saves it right away."""

    def __init__(self) -> None:
        self._cfg: dict = {}
        self._catalog: dict = {}
        self._idx: dict = {}
        self._scope: str | None = None
        self._next = "classes_pick"
        self._sid: str | None = None
        self._mid: str | None = None
        self._errors_text = ""

    # ---------------------------------------------------------------- plumbing
    @property
    def _client(self) -> SoundRecClient:
        return self.config_entry.runtime_data.client

    @property
    def _lang(self) -> str:
        return self.hass.config.language

    async def _load(self) -> None:
        self._cfg = await self._client.get_config()
        self._catalog = await self._client.catalog(self._lang)
        self._idx = build_index(self._catalog)

    async def _save(self) -> bool:
        """Saves self._cfg in the service. On refusal, keeps the reasons in self._errors_text and returns False."""
        try:
            await self._client.put_config(self._cfg, self._lang)
        except InvalidConfig as err:
            self._errors_text = "; ".join(err.errors)
            return False
        except SoundRecError as err:
            self._errors_text = str(err)
            return False
        self._errors_text = ""
        return True

    def _source_names(self) -> dict[str, str]:
        return {s["id"]: (s.get("name") or s["id"]) for s in self._cfg.get("sources", [])}

    def _src_options(self) -> list[dict]:
        return [{"value": sid, "label": name} for sid, name in self._source_names().items()]

    # ---------------------------------------------------------------- main menu
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        try:
            await self._load()
        except SoundRecError:
            return self.async_abort(reason="cannot_connect")
        return self.async_show_menu(step_id="init", menu_options=["sources", "classes", "class_settings", "defaults", "advice", "advice_rule", "finish"])

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)  # entities follow the new configuration
        return self.async_create_entry(data=dict(self.config_entry.options))

    # ---------------------------------------------------------------- advice
    async def async_step_advice(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_init()
        try:
            warnings = await self._client.warnings(self._lang)
        except SoundRecError:
            warnings = []
        text = format_warnings(warnings, self._source_names())
        return self.async_show_form(step_id="advice" if text else "advice_none", data_schema=vol.Schema({}),
                                    description_placeholders={"advice": text})

    async def async_step_advice_none(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_init()

    async def async_step_advice_rule(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the level of one advice (globally or for one source), or hide it."""
        try:
            warnings = await self._client.warnings(self._lang, overrides=False)   # also lists advice already hidden/changed
        except SoundRecError:
            return self.async_abort(reason="cannot_connect")
        rules: dict[str, str] = {}
        for w in warnings:
            rules.setdefault(w["rule"], w["message"])
        if not rules:
            return await self.async_step_advice_none()
        safety = {w["rule"] for w in warnings if w.get("safety")}
        errors: dict[str, str] = {}
        if user_input is not None:
            rid, sid, level = user_input["rule"], user_input.get("source"), user_input["level"]
            confirm = bool(user_input.get("confirm"))
            if level == "ignore" and rid in safety and not confirm:
                errors["base"] = "confirm_required"
            else:
                backup = copy.deepcopy(self._cfg)
                target = next((x for x in self._cfg.get("sources", []) if x["id"] == sid), None) if sid else self._cfg
                block = target.setdefault("advice", {})
                if level == "default":
                    block.pop(rid, None)
                elif level == "ignore" and rid in safety:
                    block[rid] = {"level": "ignore", "confirm": True}
                else:
                    block[rid] = level
                if not block:
                    target.pop("advice", None)
                if await self._save():
                    return await self.async_step_advice()
                self._cfg = backup
                errors["base"] = "invalid_config"
        options = [{"value": r, "label": f"{m[:90]}{'…' if len(m) > 90 else ''}"} for r, m in rules.items()]
        schema = vol.Schema({
            vol.Required("rule"): _select(options),
            vol.Optional("source"): _select(self._src_options()),
            vol.Required("level", default="info"): _select(["default", "info", "warning", "danger", "ignore"], "advice_level"),
            vol.Optional("confirm", default=False): sel.BooleanSelector(),
        })
        return self.async_show_form(step_id="advice_rule", errors=errors, description_placeholders={"errors": self._errors_text},
                                    data_schema=self.add_suggested_values_to_schema(schema, user_input or {}))

    # ---------------------------------------------------------------- sources
    async def async_step_sources(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="sources", menu_options=["add_source", "edit_source", "remove_source", "init"])

    def _source_schema(self) -> vol.Schema:
        return vol.Schema({
            vol.Required("name"): sel.TextSelector(),
            vol.Required("type"): _select(SOURCE_TYPES, "source_type"),
            vol.Required("url"): sel.TextSelector(),
            vol.Required("enabled"): sel.BooleanSelector(),
            vol.Optional("threshold_offset"): _num(-0.5, 0.5, 0.01),
            vol.Optional("min_volume_dbfs"): _num(-90, 0, 1, "dBFS"),
            vol.Required("schedule_mode"): _select(["continuous", "scheduled"], "schedule_mode"),
            vol.Optional("window_days"): _select(DAYS, "weekday", multiple=True),
            vol.Optional("window_from"): sel.TimeSelector(),
            vol.Optional("window_to"): sel.TimeSelector(),
            vol.Required("clips_allowed"): sel.BooleanSelector(),
            vol.Optional("clips_max_days"): _num(0, 3650, 1),
        })

    async def async_step_add_source(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            taken = {s["id"] for s in self._cfg.get("sources", [])}
            sid = unique_id(slugify(user_input["name"]), taken)
            backup = copy.deepcopy(self._cfg)
            self._cfg.setdefault("sources", []).append(source_from_form(None, user_input, sid))
            if await self._save():
                return await self.async_step_advice()
            self._cfg = backup
            errors["base"] = "invalid_config"
        return self.async_show_form(
            step_id="add_source", errors=errors, description_placeholders={"errors": self._errors_text},
            data_schema=self.add_suggested_values_to_schema(self._source_schema(), user_input or source_form_defaults(None)))

    async def async_step_edit_source(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self._cfg.get("sources"):
            return self.async_show_form(step_id="edit_source", data_schema=vol.Schema({}), errors={"base": "no_sources"})
        if user_input is not None:
            self._sid = user_input["source"]
            return await self.async_step_edit_source_form()
        return self.async_show_form(step_id="edit_source", data_schema=vol.Schema({vol.Required("source"): _select(self._src_options())}))

    async def async_step_edit_source_form(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        i = next(k for k, s in enumerate(self._cfg["sources"]) if s["id"] == self._sid)
        if user_input is not None:
            backup = copy.deepcopy(self._cfg)
            self._cfg["sources"][i] = source_from_form(self._cfg["sources"][i], user_input, self._sid)
            if await self._save():
                return await self.async_step_advice()
            self._cfg = backup
            errors["base"] = "invalid_config"
        n_extra = len(((self._cfg["sources"][i].get("schedule") or {}).get("windows") or [])[1:])
        return self.async_show_form(
            step_id="edit_source_form", errors=errors,
            description_placeholders={"errors": self._errors_text, "source": self._source_names()[self._sid], "extra_windows": str(n_extra)},
            data_schema=self.add_suggested_values_to_schema(self._source_schema(), user_input or source_form_defaults(self._cfg["sources"][i])))

    async def async_step_remove_source(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self._cfg.get("sources"):
            return self.async_show_form(step_id="remove_source", data_schema=vol.Schema({}), errors={"base": "no_sources"})
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("confirm"):
                backup = copy.deepcopy(self._cfg)
                self._cfg["sources"] = [s for s in self._cfg["sources"] if s["id"] != user_input["source"]]
                if await self._save():
                    return await self.async_step_init()
                self._cfg = backup
                errors["base"] = "invalid_config"
            else:
                errors["base"] = "not_confirmed"
        schema = vol.Schema({vol.Required("source"): _select(self._src_options()), vol.Required("confirm", default=False): sel.BooleanSelector()})
        return self.async_show_form(step_id="remove_source", data_schema=schema, errors=errors,
                                    description_placeholders={"errors": self._errors_text})

    # ---------------------------------------------------------------- scope (all sources / one source), shared by classes and class settings
    async def async_step_classes(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._next = "classes_pick"
        return await self.async_step_scope()

    async def async_step_class_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._next = "class_pick"
        return await self.async_step_scope()

    async def async_step_scope(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="scope", menu_options=["scope_global", "scope_source"])

    async def async_step_scope_global(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._scope = None
        return await getattr(self, f"async_step_{self._next}")()

    async def async_step_scope_source(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if not self._cfg.get("sources"):
            return self.async_show_form(step_id="scope_source", data_schema=vol.Schema({}), errors={"base": "no_sources"})
        if user_input is not None:
            self._scope = user_input["source"]
            return await getattr(self, f"async_step_{self._next}")()
        return self.async_show_form(step_id="scope_source", data_schema=vol.Schema({vol.Required("source"): _select(self._src_options())}))

    def _scope_enabled(self) -> set[str]:
        if self._scope is None:
            glob = (self._cfg.get("classes") or {})
            return {self._idx["by_key"][k] for k, b in glob.items() if k in self._idx["by_key"] and (b or {}).get("enabled")}
        src = next(s for s in self._cfg["sources"] if s["id"] == self._scope)
        return enabled_mids(self._cfg, src, self._idx)

    def _scope_label(self) -> str:
        return self._source_names().get(self._scope, "") if self._scope else ""

    # ---------------------------------------------------------------- which classes
    def _class_options(self, keep: set[str]) -> list[dict]:
        cats = self._catalog["categories"]
        rows = [c for c in self._catalog["classes"] if c["interest"] in ("monitor", "optional", "context") or c["mid"] in keep]
        rows.sort(key=lambda c: (INTEREST_ORDER[c["interest"]], c["yamnet_index"]))
        return [{"value": c["mid"], "label": f"{'★ ' if c['interest'] == 'monitor' else ''}{cats[c['category']]} — {c['name']}"} for c in rows]

    async def async_step_classes_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = self._scope_enabled()
        options = self._class_options(current)
        if user_input is not None:
            backup = copy.deepcopy(self._cfg)
            apply_selection(self._cfg, self._idx, self._scope, set(user_input.get("classes", [])), {o["value"] for o in options})
            if await self._save():
                return await self.async_step_advice()
            self._cfg = backup
            return self.async_show_form(step_id="classes_pick", errors={"base": "invalid_config"},
                                        description_placeholders={"errors": self._errors_text, "scope": self._scope_label()},
                                        data_schema=vol.Schema({vol.Optional("classes", default=sorted(current)): _select(options, None, True)}))
        return self.async_show_form(
            step_id="classes_pick", description_placeholders={"errors": "", "scope": self._scope_label()},
            data_schema=vol.Schema({vol.Optional("classes", default=sorted(current)): _select(options, None, True)}))

    # ---------------------------------------------------------------- settings of one class
    async def async_step_class_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        enabled = self._scope_enabled()
        if not enabled:
            return self.async_show_form(step_id="class_pick", data_schema=vol.Schema({}), errors={"base": "no_classes"})
        if user_input is not None:
            self._mid = user_input["class"]
            return await self.async_step_class_form()
        options = [{"value": m, "label": self._idx["by_mid"][m]["name"]} for m in sorted(enabled, key=lambda m: self._idx["by_mid"][m]["yamnet_index"])]
        return self.async_show_form(step_id="class_pick", data_schema=vol.Schema({vol.Required("class"): _select(options)}),
                                    description_placeholders={"scope": self._scope_label()})

    def _class_schema(self, forbidden: bool) -> vol.Schema:
        fields: dict = {
            vol.Required("threshold"): _num(0, 1, 0.01),
            vol.Required("min_duration_s"): _num(0, 600, 0.5, "s"),
            vol.Required("cooldown_s"): _num(0, 86400, 1, "s"),
            vol.Required("pre_roll_s"): _num(0, 120, 1, "s"),
            vol.Required("post_roll_s"): _num(0, 120, 1, "s"),
        }
        fields[vol.Required("clip_retention_days")] = _num(0, 3650, 1)
        fields[vol.Optional("min_volume_dbfs")] = _num(-90, 0, 1, "dBFS")
        fields[vol.Required("always_on")] = sel.BooleanSelector()
        return vol.Schema(fields)

    async def async_step_class_form(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        c = self._idx["by_mid"][self._mid]
        errors: dict[str, str] = {}
        if user_input is not None:
            backup = copy.deepcopy(self._cfg)
            apply_class_form(self._cfg, self._idx, self._scope, self._mid, user_input)
            if await self._save():
                return await self.async_step_advice()
            self._cfg = backup
            errors["base"] = "invalid_config"
        s = c["suggestions"]
        return self.async_show_form(
            step_id="class_form", errors=errors,
            description_placeholders={
                "errors": self._errors_text, "class": c["name"], "scope": self._scope_label(), "note": c.get("note_text") or "",
                "suggested": f"{s['threshold']} / {s['min_duration_s']} s / {s['cooldown_s']} s",
                "forbidden": "🔒" if c["clip_forbidden"] else "",
            },
            data_schema=self.add_suggested_values_to_schema(
                self._class_schema(c["clip_forbidden"]), user_input or class_form_defaults(self._cfg, self._idx, self._scope, self._mid)))

    # ---------------------------------------------------------------- global defaults
    async def async_step_defaults(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        d = self._cfg.get("defaults", {})
        if user_input is not None:
            backup = copy.deepcopy(self._cfg)
            dd = self._cfg.setdefault("defaults", {})
            if user_input.get("min_volume_dbfs") is None:
                dd["min_volume_dbfs"] = None
            else:
                dd["min_volume_dbfs"] = float(user_input["min_volume_dbfs"])
            self._cfg.setdefault("analysis", {})["context_boost"] = round(float(user_input["context_boost"]), 3)
            clips = {"allowed": bool(user_input["clips_allowed"])}
            if user_input.get("clips_max_days") is not None:
                clips["max_retention_days"] = int(user_input["clips_max_days"])
            dd["clips"] = clips
            if await self._save():
                return await self.async_step_advice()
            self._cfg = backup
            errors["base"] = "invalid_config"
        schema = vol.Schema({
            vol.Optional("min_volume_dbfs"): _num(-90, 0, 1, "dBFS"),
            vol.Required("context_boost"): _num(0, 1, 0.01),
            vol.Required("clips_allowed"): sel.BooleanSelector(),
            vol.Optional("clips_max_days"): _num(0, 3650, 1),
        })
        defaults = user_input or {
            "min_volume_dbfs": d.get("min_volume_dbfs"), "context_boost": self._cfg.get("analysis", {}).get("context_boost", 0.15),
            "clips_allowed": (d.get("clips") or {}).get("allowed", True), "clips_max_days": (d.get("clips") or {}).get("max_retention_days"),
        }
        return self.async_show_form(step_id="defaults", errors=errors, description_placeholders={"errors": self._errors_text},
                                    data_schema=self.add_suggested_values_to_schema(schema, {k: v for k, v in defaults.items() if v is not None}))
