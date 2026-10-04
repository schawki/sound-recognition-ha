"""Sound Recognition: Home Assistant side of the sound recognition service."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from pathlib import Path

from aiohttp import web
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, SoundRecClient
from . import websocket_api as panel_ws
from .const import CLIP_SIGN_HOURS, CLIP_URL_TEMPLATE, CLIP_VIEW_URL, DOMAIN, PANEL_STATIC_URL, PANEL_URL_PATH, PLATFORMS
from .coordinator import SoundRecCoordinator
from .helpers import expected_unique_ids

_LOGGER = logging.getLogger(__name__)


@dataclass
class SoundRecData:
    client: SoundRecClient
    coordinator: SoundRecCoordinator


type SoundRecConfigEntry = ConfigEntry[SoundRecData]


class SoundRecClipView(HomeAssistantView):
    """Relays clips from the service so it never has to be exposed; requires a Home Assistant login or a signed path."""

    url = CLIP_VIEW_URL
    name = "api:sound_recognition:clip"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, rel: str) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        try:
            body = await entry.runtime_data.client.clip(rel)
        except (CannotConnect, InvalidAuth):
            return web.Response(status=502)
        if body is None:
            return web.Response(status=404)
        return web.Response(body=body, content_type="audio/wav")


def signed_clip_url(hass: HomeAssistant, entry_id: str, rel: str) -> str:
    path = CLIP_URL_TEMPLATE.format(entry_id=entry_id, rel=rel)
    return async_sign_path(hass, path, timedelta(hours=CLIP_SIGN_HOURS))


PANEL_DIR = Path(__file__).parent / "frontend"
PANEL_FILE = "sound-recognition-panel.js"


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Sidebar panel (admins only) and its JavaScript file; done once however many entries exist."""
    if hass.data.get(f"{DOMAIN}_panel"):
        return
    hass.data[f"{DOMAIN}_panel"] = True
    panel_ws.async_register(hass)
    await hass.http.async_register_static_paths([StaticPathConfig(PANEL_STATIC_URL, str(PANEL_DIR), cache_headers=False)])
    version = (PANEL_DIR / PANEL_FILE).stat().st_mtime_ns if (PANEL_DIR / PANEL_FILE).exists() else 0
    await panel_custom.async_register_panel(
        hass, webcomponent_name="sound-recognition-panel", frontend_url_path=PANEL_URL_PATH,
        module_url=f"{PANEL_STATIC_URL}/{PANEL_FILE}?v={version}", sidebar_title="Sound Recognition",
        sidebar_icon="mdi:waveform", require_admin=True, config={}, embed_iframe=False,
    )


def _remove_stale_entities(hass: HomeAssistant, entry: SoundRecConfigEntry, coordinator: SoundRecCoordinator) -> None:
    """Drops the entities of sounds or sources that are no longer in the configuration (they would stay 'unavailable' forever).
    Only this entry's own entities, and never one the user renamed or gave another icon."""
    cfg = coordinator.service_config
    if "sources" not in cfg or not coordinator.index:
        return                                  # configuration not read properly: remove nothing
    keep = expected_unique_ids(entry.entry_id, cfg, coordinator.index)
    registry = er.async_get(hass)
    for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg.unique_id in keep or reg.name is not None or reg.icon is not None:
            continue
        _LOGGER.debug("Removing %s: no longer provided by the configuration", reg.entity_id)
        registry.async_remove(reg.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: SoundRecConfigEntry) -> bool:
    client = SoundRecClient(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_TOKEN])
    coordinator = SoundRecCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:  # noqa: BLE001 - first refresh already maps errors; keep a clear retry for anything else
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = SoundRecData(client, coordinator)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}, name="Sound Recognition",
        manufacturer="Sound Recognition", model="Classification service", sw_version=coordinator.version,
    )
    await _async_register_panel(hass)
    if not hass.data.get(f"{DOMAIN}_view"):
        hass.http.register_view(SoundRecClipView())
        hass.data[f"{DOMAIN}_view"] = True
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _remove_stale_entities(hass, entry, coordinator)
    coordinator.start_listener()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SoundRecConfigEntry) -> bool:
    """The panel stays registered: removing it on every reload (each saved change reloads the entry) sends the browser to the home page."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        entry.runtime_data.coordinator.clear_issues()
    return ok


async def async_remove_entry(hass: HomeAssistant, entry: SoundRecConfigEntry) -> None:
    """Last entry deleted: take the panel out of the sidebar."""
    if not [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id] and hass.data.pop(f"{DOMAIN}_panel", None):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
