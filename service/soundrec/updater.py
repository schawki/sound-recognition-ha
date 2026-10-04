"""Update from Home Assistant, without giving this service any privilege.

The service runs as an unprivileged user and cannot update itself. It only drops a request file; a small root helper installed by
deploy/install.sh (soundrec-update.path + soundrec-update.service) notices it, moves the installation to the latest tagged release and
writes its progress in a folder the service can read but not write. Nothing the service writes is ever interpreted by the helper."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

STALLED_REQUEST_S = 90          # a request nobody picked up: the helper is not running
STALLED_RUN_S = 20 * 60         # an update that has not reported anything for that long


class Updater:
    def __init__(self, request_dir: str | None, status_dir: str | None, build_file: str | None) -> None:
        self.request_dir = Path(request_dir) if request_dir else None
        self.status_dir = Path(status_dir) if status_dir else None
        self.build_file = Path(build_file) if build_file else None

    @classmethod
    def from_env(cls) -> "Updater":
        return cls(os.environ.get("SOUNDREC_UPDATE_REQUEST"), os.environ.get("SOUNDREC_UPDATE_STATUS"), os.environ.get("SOUNDREC_BUILD"))

    # ------------------------------------------------------------------ what is installed
    def build(self) -> dict:
        """commit and release (git describe) recorded by install.sh; empty when unknown."""
        out: dict = {}
        try:
            for line in self.build_file.read_text().splitlines() if self.build_file else []:
                key, _, value = line.partition("=")
                if key in ("commit", "release", "built") and value:
                    out[key] = value.strip()
        except OSError:
            pass
        return out

    @property
    def capable(self) -> bool:
        """The root helper is installed (install.sh left its flag) and a request can be dropped."""
        return bool(self.request_dir and self.status_dir and (self.status_dir / "capable").is_file()
                    and self.request_dir.is_dir() and os.access(self.request_dir, os.W_OK))

    # ------------------------------------------------------------------ progress
    def _read(self) -> dict:
        try:
            data = json.loads((self.status_dir / "status.json").read_text()) if self.status_dir else {}
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _log_tail(self, lines: int = 12) -> str:
        try:
            return "\n".join((self.status_dir / "update.log").read_text(errors="replace").splitlines()[-lines:])
        except OSError:
            return ""

    def status(self, now: float | None = None) -> dict:
        """{capable, state: idle | requested | running | done | failed, message, from, to, updated, stalled, log}."""
        now = time.time() if now is None else now
        data = self._read()
        state, stalled = data.get("state", "idle"), False
        if state not in ("idle", "running", "done", "failed"):
            state = "idle"
        pending = self.request_dir / "request" if self.request_dir else None
        if pending is not None and pending.exists() and state != "running":
            state = "requested"
            try:
                stalled = now - pending.stat().st_mtime > STALLED_REQUEST_S
            except OSError:
                pass
        elif state == "running":
            stalled = now - float(data.get("updated") or now) > STALLED_RUN_S
        message = data.get("message", "") if state != "requested" else ""
        return {"capable": self.capable, "state": state, "message": str(message), "from": data.get("from", ""), "to": data.get("to", ""),
                "updated": data.get("updated"), "stalled": stalled, "log": self._log_tail() if state in ("failed", "running") else "", **self.build()}

    def request(self) -> str:
        """Drops the request. Returns 'requested', 'busy' (one is already pending or running) or 'unavailable' (no helper)."""
        if not self.capable:
            return "unavailable"
        if self.status()["state"] in ("requested", "running"):
            return "busy"
        try:
            fd = os.open(self.request_dir / "request", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return "busy"
        with os.fdopen(fd, "w") as f:
            f.write(str(int(time.time())))
        return "requested"
