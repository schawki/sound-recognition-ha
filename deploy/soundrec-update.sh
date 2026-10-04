#!/usr/bin/env bash
# Root helper that moves the sound recognition service to the latest tagged release (vX.Y.Z) of the repository it was installed from.
# systemd starts it (soundrec-update.path) when the service drops a request file; install.sh installs it as /usr/local/sbin/soundrec-update.
# It reads only /etc/soundrec-updater.env (root-owned) and writes its progress to a folder the service can read but not write.
# The content of the request file is never used. If the update fails, the previous version is installed again.
set -uo pipefail

ENV_FILE="${SOUNDREC_UPDATER_ENV:-/etc/soundrec-updater.env}"
# shellcheck disable=SC1090
. "$ENV_FILE"
: "${REPO:?}" "${REQUEST_DIR:?}" "${STATUS_DIR:?}"
INSTALL="${INSTALL:-$REPO/deploy/install.sh}"
REMOTE="${REMOTE:-origin}"
LOG="$STATUS_DIR/update.log"
FROM="" TO=""

set_status() {   # status <state> <message>
  python3 - "$STATUS_DIR/status.json" "$1" "$2" "$FROM" "$TO" <<'PY'
import json, os, sys, time
path, state, message, a, b = sys.argv[1:6]
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump({"state": state, "message": message, "from": a, "to": b, "updated": time.time()}, f)
os.replace(tmp, path)
PY
}
git_() { git -C "$REPO" "$@"; }
fail() { set_status failed "$1"; exit 1; }

: > "$LOG"
rm -f "$REQUEST_DIR/request"
FROM="$(git_ describe --tags --always 2>/dev/null || echo unknown)"
set_status running "Looking for the latest release"

git_ fetch --quiet --tags "$REMOTE" >>"$LOG" 2>&1 || fail "Cannot reach the repository (git fetch failed)"
LATEST="$(git_ tag --list 'v[0-9]*' --sort=-v:refname | head -n1)"
[ -n "$LATEST" ] || fail "No release found in the repository"
TO="$LATEST"

if git_ merge-base --is-ancestor "$LATEST" HEAD 2>/dev/null; then
  set_status "done" "Already on $LATEST or newer"
  exit 0
fi

OLD="$(git_ rev-parse HEAD)"
git_ merge --ff-only "$LATEST" >>"$LOG" 2>&1 || fail "Cannot move to $LATEST without losing local changes (see the log)"
set_status running "Installing $LATEST"
if bash "$INSTALL" >>"$LOG" 2>&1; then
  set_status "done" "Updated to $LATEST"
  exit 0
fi
set_status running "Installation failed, restoring the previous version"
git_ reset --hard --quiet "$OLD" >>"$LOG" 2>&1
bash "$INSTALL" >>"$LOG" 2>&1
fail "Updating to $LATEST failed; the previous version was restored (see the log)"
