"""Moving the clips to another folder (another disk, a NAS), without giving this service any privilege.

Same principle as updater.py: the service only checks the destination and drops a small request file; a root helper installed by
deploy/install.sh (soundrec-move.path + soundrec-move.service) re-checks everything on its own rules, copies the clips, verifies them, points the
configuration at the new folder, restarts the service and writes its progress in a folder the service can read but not write.
The helper never deletes anything: the old folder stays where it is. While a move is requested or running the service keeps detecting but does not
keep new clips and does not purge old ones."""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

DAY_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STALLED_REQUEST_S = 90          # a request nobody picked up: the helper is not running
STALLED_RUN_S = 5 * 60          # the helper touches its status every 20 s while it works
SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/@+-]+$")     # what systemd and the helper handle without surprise (no space, no quote)
MARGIN_BYTES = 50 * 1024 * 1024


class Mover:
    def __init__(self, request_dir: str | None, status_dir: str | None) -> None:
        self.request_dir = Path(request_dir) if request_dir else None
        self.status_dir = Path(status_dir) if status_dir else None
        self._cache: tuple[float, bool] = (0.0, False)

    @classmethod
    def from_env(cls) -> "Mover":
        return cls(os.environ.get("SOUNDREC_UPDATE_REQUEST"), os.environ.get("SOUNDREC_UPDATE_STATUS"))

    @property
    def capable(self) -> bool:
        """The root helper is installed (install.sh left its flag) and a request can be dropped."""
        return bool(self.request_dir and self.status_dir and (self.status_dir / "move-capable").is_file()
                    and self.request_dir.is_dir() and os.access(self.request_dir, os.W_OK))

    def roots(self) -> list[str]:
        """The folders under which a destination is accepted (written by install.sh, root-owned)."""
        try:
            return [l.strip() for l in (self.status_dir / "move-roots").read_text().splitlines() if l.strip().startswith("/")] if self.status_dir else []
        except OSError:
            return []

    # ------------------------------------------------------------------ checks
    def check(self, dest: str, current: str, need_bytes: int) -> list[str]:
        """Why this destination cannot be used (codes the panel words); empty when it can. The helper checks again on its own."""
        if not isinstance(dest, str) or not dest.startswith("/"):
            return ["not_absolute"]
        if not SAFE_PATH.match(dest) or ".." in dest.split("/"):
            return ["bad_characters"]
        dest = dest.rstrip("/") or "/"
        if not os.path.exists(dest):
            return ["not_found"]
        if not os.path.isdir(dest):
            return ["not_directory"]
        if os.path.realpath(dest) != os.path.normpath(dest):
            return ["symlink"]
        cur = os.path.realpath(current)
        if dest == cur:
            return ["same_folder"]
        if dest.startswith(cur + os.sep) or cur.startswith(dest + os.sep):
            return ["nested"]
        roots = self.roots()
        if not any(dest == r.rstrip("/") or dest.startswith(r.rstrip("/") + os.sep) for r in roots):
            return ["outside_roots"]
        if os.listdir(dest):
            return ["not_empty"]
        if not os.access(dest, os.W_OK | os.X_OK):
            return ["not_writable"]
        try:
            if shutil.disk_usage(dest).free < need_bytes * 1.1 + MARGIN_BYTES:
                return ["not_enough_space"]
        except OSError:
            return ["not_found"]
        return []

    # ------------------------------------------------------------------ progress
    def _read(self) -> dict:
        try:
            data = json.loads((self.status_dir / "move.json").read_text()) if self.status_dir else {}
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _log_tail(self, lines: int = 12) -> str:
        try:
            return "\n".join((self.status_dir / "move.log").read_text(errors="replace").splitlines()[-lines:])
        except OSError:
            return ""

    def status(self, now: float | None = None) -> dict:
        """{capable, roots, state: idle | requested | running | done | failed, message, from, to, stalled, log}."""
        now = time.time() if now is None else now
        data = self._read()
        state, stalled = data.get("state", "idle"), False
        if state not in ("idle", "running", "done", "failed"):
            state = "idle"
        pending = self.request_dir / "move" if self.request_dir else None
        if pending is not None and pending.exists() and state != "running":
            state = "requested"
            try:
                stalled = now - pending.stat().st_mtime > STALLED_REQUEST_S
            except OSError:
                pass
        elif state == "running":
            try:
                stalled = now - (self.status_dir / "move.json").stat().st_mtime > STALLED_RUN_S
            except OSError:
                pass
        message = data.get("message", "") if state != "requested" else ""
        return {"capable": self.capable, "roots": self.roots(), "state": state, "message": str(message), "from": data.get("from", ""), "to": data.get("to", ""),
                "stalled": stalled, "log": self._log_tail() if state in ("failed", "running") else "", "clean": self.clean_status(now)}

    # ------------------------------------------------------------------ the old folders kept after a move
    def kept(self) -> list[str]:
        """The folders the helper left behind after a move (it writes the list itself, as root: the service cannot add to it)."""
        try:
            lines = (self.status_dir / "move-old").read_text().splitlines() if self.status_dir else []
        except OSError:
            return []
        return [l.strip() for l in lines if l.strip().startswith("/")]

    def old_folders(self, current: str | None = None) -> list[dict]:
        """Each kept folder that still exists, with what is in it and what stops the helper from removing it completely. Walks the folders: call it off the event loop.
        notes: mount_point (the folder stays), other_files (they stay, and so does the folder), not_writable (the service account cannot delete there: by hand),
        no_helper (nothing here can delete: by hand)."""
        out = []
        cur = os.path.realpath(current) if current else None
        for path in self.kept():
            if not os.path.isdir(path):
                continue
            if cur and (os.path.realpath(path) == cur or cur.startswith(os.path.realpath(path) + os.sep) or os.path.realpath(path).startswith(cur + os.sep)):
                continue                    # the folder the clips are in now (or around / inside it) is never offered for deletion
            clips, size, other = 0, 0, 0
            try:
                for name in os.listdir(path):
                    full = os.path.join(path, name)
                    if DAY_DIR.match(name) and os.path.isdir(full) and not os.path.islink(full):
                        for f in os.listdir(full):
                            fp = os.path.join(full, f)
                            if f.endswith((".wav", ".json")):
                                size += os.path.getsize(fp)
                                clips += f.endswith(".wav")
                            else:
                                other += 1
                    else:
                        other += 1
            except OSError:
                pass
            notes = []
            if os.path.ismount(path):
                notes.append("mount_point")
            if other:
                notes.append("other_files")
            if not os.access(path, os.W_OK | os.X_OK):
                notes.append("not_writable")
            if not self.capable:
                notes.append("no_helper")
            out.append({"path": path, "clips": clips, "bytes": size, "other": other, "notes": notes})
        return out

    def _read_clean(self) -> dict:
        try:
            data = json.loads((self.status_dir / "clean.json").read_text()) if self.status_dir else {}
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def clean_status(self, now: float | None = None) -> dict:
        """{state: idle | requested | running | done | failed, message, path, stalled} for the deletion of an old folder."""
        now = time.time() if now is None else now
        data = self._read_clean()
        state, stalled = data.get("state", "idle"), False
        if state not in ("idle", "running", "done", "failed"):
            state = "idle"
        pending = self.request_dir / "move-delete" if self.request_dir else None
        if pending is not None and pending.exists() and state != "running":
            state = "requested"
            try:
                stalled = now - pending.stat().st_mtime > STALLED_REQUEST_S
            except OSError:
                pass
        elif state == "running":
            try:
                stalled = now - (self.status_dir / "clean.json").stat().st_mtime > STALLED_RUN_S
            except OSError:
                pass
        return {"state": state, "message": str(data.get("message", "")) if state != "requested" else "", "path": data.get("path", ""), "stalled": stalled}

    def request_delete(self, path: str) -> str:
        """Asks the helper to delete the clips of a kept folder. 'requested', 'busy' (a move or a deletion is under way), 'unavailable' (no helper) or 'unknown' (not a kept folder)."""
        if not self.capable:
            return "unavailable"
        if path not in self.kept() or not os.path.isdir(path):
            return "unknown"
        if self.status()["state"] in ("requested", "running") or self.clean_status()["state"] in ("requested", "running"):
            return "busy"
        try:
            fd = os.open(self.request_dir / "move-delete", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return "busy"
        with os.fdopen(fd, "w") as f:
            json.dump({"old": path}, f)
        return "requested"

    def active(self, now: float | None = None) -> bool:
        """A move is requested or running (and its helper is alive): clips must not be written or purged. Cached for two seconds."""
        now = time.time() if now is None else now
        if now - self._cache[0] < 2:
            return self._cache[1]
        if not (self.request_dir and self.status_dir):
            return False
        s = self.status(now)
        active = s["state"] in ("requested", "running") and not s["stalled"]
        self._cache = (now, active)
        return active

    def request(self, dest: str) -> str:
        """Drops the request. Returns 'requested', 'busy' (one is already pending or running) or 'unavailable' (no helper)."""
        if not self.capable:
            return "unavailable"
        if self.status()["state"] in ("requested", "running"):
            return "busy"
        try:
            fd = os.open(self.request_dir / "move", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return "busy"
        with os.fdopen(fd, "w") as f:
            json.dump({"dest": dest.rstrip("/") or "/"}, f)
        self._cache = (0.0, False)
        return "requested"
