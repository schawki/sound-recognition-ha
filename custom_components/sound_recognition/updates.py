"""Service updates: which release is installed and which is the latest, launching the update and telling when the service is back."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, SoundRecError
from .const import DOMAIN, MANUAL_UPDATE_COMMAND, MIN_API_LEVEL, RELEASE_CHECK_S, REPO, UPDATE_TIMEOUT_S

if TYPE_CHECKING:
    from .coordinator import SoundRecCoordinator

_LOGGER = logging.getLogger(__name__)
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
POLL_S = 4

# Notification texts. English is the reference; add a language by adding a dict with the same keys.
TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Sound Recognition service",
        "done": "The service was updated to **{version}** and is back online.",
        "failed": "The service update failed: {message}",
        "log": "Last lines of the update log:\n```\n{log}\n```",
        "timeout": "The service did not report the end of the update in time. Check it on the machine that runs the service.",
        "unavailable": "Updating from Home Assistant is not enabled on this installation. Run on the machine that runs the service: `{command}`",
    },
    "fr": {
        "title": "Service Sound Recognition",
        "done": "Le service a été mis à jour en **{version}** et il est de nouveau en ligne.",
        "failed": "La mise à jour du service a échoué : {message}",
        "log": "Dernières lignes du journal de mise à jour :\n```\n{log}\n```",
        "timeout": "Le service n'a pas signalé la fin de la mise à jour à temps. Vérifiez sur la machine qui l'héberge.",
        "unavailable": "La mise à jour depuis Home Assistant n'est pas activée sur cette installation. Sur la machine du service, lancez : `{command}`",
    },
}


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    m = TAG.match(f"v{text.lstrip('v')}") if text else None
    return tuple(int(x) for x in m.groups()) if m else None      # type: ignore[return-value]


def latest_tag(names: list[str]) -> str | None:
    """Highest vX.Y.Z among tag names; anything else (branches, pre-releases) is ignored."""
    found = [(parse_version(n), n) for n in names if TAG.match(n)]
    return max(found)[1] if found else None


def changelog_section(text: str, version: str) -> str:
    """The '## <version>' part of a changelog; the top of the file when there is no such heading."""
    lines, out, on = text.splitlines(), [], False
    for line in lines:
        if line.startswith("## "):
            if on:
                break
            on = version in line
            continue
        if on:
            out.append(line)
    return "\n".join(out).strip() or text[:2000]


class ServiceUpdate:
    """Owned by the coordinator. Knows the installed/latest release and follows an update from request to the service coming back."""

    def __init__(self, hass: HomeAssistant, coordinator: SoundRecCoordinator) -> None:
        self.hass, self.coordinator = hass, coordinator
        self.latest: str | None = None          # tag, e.g. "v0.2.0"
        self._next_check = 0.0
        self.installing = False
        self.status: dict[str, Any] = {}
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------ what is installed
    @property
    def health(self) -> dict:
        return self.coordinator.health

    @property
    def installed(self) -> str | None:
        return self.health.get("version")

    @property
    def api_level(self) -> int:
        return int(self.health.get("api_level") or 1)

    @property
    def capable(self) -> bool:
        return bool((self.health.get("update") or {}).get("capable"))

    @property
    def outdated(self) -> bool:
        """The service is too old for this integration (missing features), whatever releases exist."""
        return self.api_level < MIN_API_LEVEL

    @property
    def available(self) -> bool:
        a, b = parse_version(self.installed), parse_version(self.latest)
        return bool(a and b and b > a)

    @property
    def release_url(self) -> str:
        return f"https://github.com/{REPO}/releases/tag/{self.latest}" if self.latest else f"https://github.com/{REPO}/releases"

    # ------------------------------------------------------------------ latest release (GitHub, never fatal)
    async def async_check(self, force: bool = False) -> None:
        if not force and time.monotonic() < self._next_check:
            return
        self._next_check = time.monotonic() + 1800          # a failure is retried in 30 minutes
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(f"https://api.github.com/repos/{REPO}/tags?per_page=50", timeout=_timeout(10),
                                   headers={"Accept": "application/vnd.github+json"}) as resp:
                if resp.status != 200:
                    return
                tag = latest_tag([t.get("name", "") for t in await resp.json()])
            if tag:
                self.latest, self._next_check = tag, time.monotonic() + RELEASE_CHECK_S
        except Exception as err:  # noqa: BLE001 - GitHub being unreachable must never disturb the integration
            _LOGGER.debug("Could not look up the latest release: %s", err)

    async def async_release_notes(self) -> str | None:
        if not self.latest:
            return None
        lang = "fr" if self.coordinator.lang.startswith("fr") else "en"
        names = ("CHANGELOG.fr.md", "CHANGELOG.md") if lang == "fr" else ("CHANGELOG.md",)
        session = async_get_clientsession(self.hass)
        for name in names:
            try:
                async with session.get(f"https://raw.githubusercontent.com/{REPO}/{self.latest}/{name}", timeout=_timeout(10)) as resp:
                    if resp.status == 200:
                        return changelog_section(await resp.text(), self.latest.lstrip("v"))
            except Exception:  # noqa: BLE001
                continue
        return None

    # ------------------------------------------------------------------ summary for the panel
    def summary(self) -> dict:
        return {"installed": self.installed, "latest": self.latest, "available": self.available, "outdated": self.outdated,
                "api_level": self.api_level, "min_api_level": MIN_API_LEVEL, "capable": self.capable, "installing": self.installing,
                "status": self.status, "release_url": self.release_url, "manual_command": MANUAL_UPDATE_COMMAND,
                "commit": self.health.get("commit"), "release": self.health.get("release")}

    # ------------------------------------------------------------------ launching and following an update
    def _text(self, key: str, **kw: str) -> str:
        lang = self.coordinator.lang.split("-")[0]
        return TEXTS.get(lang, TEXTS["en"])[key].format(**kw)

    def _notify(self, message: str) -> None:
        persistent_notification.async_create(self.hass, message, title=self._text("title"),
                                             notification_id=f"{DOMAIN}_update_{self.coordinator.config_entry.entry_id}")

    async def async_start(self) -> dict:
        """Asks the service to update. Raises SoundRecError when it cannot (not enabled / already running)."""
        if self.installing:
            raise SoundRecError("an update is already running")
        try:
            before = (await self.coordinator.client.update_status()).get("updated")
        except SoundRecError:
            before = None
        self.status = await self.coordinator.client.update_start()
        self.installing = True
        self.coordinator.async_update_listeners()
        self._task = self.coordinator.config_entry.async_create_background_task(self.hass, self._follow(before), f"{DOMAIN}_update")
        return self.status

    async def _follow(self, baseline: Any) -> None:
        """Polls until the helper reports an end (its status changed since the request), then until the service answers again."""
        deadline = time.monotonic() + UPDATE_TIMEOUT_S
        client = self.coordinator.client
        final: dict | None = None
        try:
            while time.monotonic() < deadline:
                await asyncio.sleep(POLL_S)
                try:
                    st = await client.update_status()
                except CannotConnect:
                    continue                                    # the service restarts during the installation
                except SoundRecError as err:
                    _LOGGER.debug("update status: %s", err)
                    continue
                self.status = st
                self.coordinator.async_update_listeners()
                if st.get("state") in ("done", "failed") and st.get("updated") != baseline:
                    final = st
                    break
                if st.get("stalled"):
                    final = {**st, "state": "failed", "message": self._text("timeout")}
                    break
            if final is None:
                final = {"state": "failed", "message": self._text("timeout")}
            if final["state"] == "done":
                await self._wait_back(deadline)
            await self.coordinator.async_refresh()
            if final["state"] == "done":
                self._notify(self._text("done", version=self.installed or final.get("to") or ""))
            else:
                msg = self._text("failed", message=final.get("message") or "")
                if final.get("log"):
                    msg += "\n\n" + self._text("log", log=final["log"])
                self._notify(msg)
        finally:
            self.installing = False
            self.coordinator.async_update_listeners()

    async def _wait_back(self, deadline: float) -> None:
        """The helper writes 'done' right after restarting the service: wait until it answers."""
        end = min(deadline, time.monotonic() + 120)
        while time.monotonic() < end:
            try:
                self.coordinator.health = await self.coordinator.client.health()
                return
            except SoundRecError:
                await asyncio.sleep(POLL_S)


def _timeout(seconds: int):
    import aiohttp
    return aiohttp.ClientTimeout(total=seconds)
