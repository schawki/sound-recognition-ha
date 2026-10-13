#!/usr/bin/env bash
# Root helper that moves the clips of the sound recognition service to another folder (another disk, a NAS).
# systemd starts it (soundrec-move.path) when the service drops a request file; install.sh installs it as /usr/local/sbin/soundrec-move.
# The request only carries a destination path. The helper does not trust it: it re-checks everything on rules the service cannot change
# (the root-owned /etc/soundrec-updater.env), copies as the service account (so it can only write where that account could), verifies the copy,
# points the configuration at the new folder and restarts the service. It NEVER deletes anything: the old folder stays where it is.
# While it works the service keeps detecting but keeps no new clip and purges none. On any failure the configuration is left as it was.
set -uo pipefail

ENV_FILE="${SOUNDREC_UPDATER_ENV:-/etc/soundrec-updater.env}"
# shellcheck disable=SC1090
. "$ENV_FILE"
: "${REQUEST_DIR:?}" "${STATUS_DIR:?}" "${CONFIG:?}" "${SERVICE_USER:?}" "${MOVE_ROOTS:?}"
UNIT="${UNIT:-soundrec}"
DROPIN_DIR="${DROPIN_DIR:-/etc/systemd/system/$UNIT.service.d}"
PORT="${SOUNDREC_PORT:-8765}"
LOG="$STATUS_DIR/move.log"
STATUS="$STATUS_DIR/move.json"
FROM="" TO="" KEEPALIVE=""

set_status() {   # set_status <state> <message>
  python3 - "$STATUS" "$1" "$2" "$FROM" "$TO" <<'PY'
import json, os, sys, time
path, state, message, a, b = sys.argv[1:6]
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump({"state": state, "message": message, "from": a, "to": b, "updated": time.time()}, f)
os.replace(tmp, path)
PY
}
stop_keepalive() { if [ -n "$KEEPALIVE" ]; then pkill -P "$KEEPALIVE" 2>/dev/null; kill "$KEEPALIVE" 2>/dev/null; fi; KEEPALIVE=""; }
fail() { stop_keepalive; set_status failed "$1"; echo "FAILED: $1" >>"$LOG"; exit 1; }
log() { echo "$*" >>"$LOG"; }

: > "$LOG"
REQ="$REQUEST_DIR/move"
DEST="$(python3 - "$REQ" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d["dest"] if isinstance(d, dict) and isinstance(d.get("dest"), str) else "")
except Exception:
    print("")
PY
)"
rm -f "$REQ"
set_status running "Checking the destination"

# ---- the destination, on the helper's own rules
case "$DEST" in /*) ;; *) fail "The destination must be an absolute path" ;; esac
[[ "$DEST" =~ ^/[A-Za-z0-9._/@+-]+$ ]] || fail "The destination has characters that are not accepted (letters, digits and . _ / @ + - only)"
case "/$DEST/" in *"/../"*|*"/./"*) fail "The destination must not contain . or .." ;; esac
DEST="${DEST%/}"
[ -d "$DEST" ] || fail "The destination folder does not exist"
[ "$(realpath -e -- "$DEST")" = "$DEST" ] || fail "The destination must not go through a link"
ok_root=0
IFS=: read -ra ROOTS <<< "$MOVE_ROOTS"
for r in "${ROOTS[@]}"; do r="${r%/}"; [ -n "$r" ] && case "$DEST" in "$r"|"$r"/*) ok_root=1 ;; esac; done
[ "$ok_root" = 1 ] || fail "The destination is not under a folder where clips may be kept ($MOVE_ROOTS)"
case "$DEST" in "$REQUEST_DIR"|"$REQUEST_DIR"/*|"$STATUS_DIR"|"$STATUS_DIR"/*) fail "The destination cannot be inside the service's working folders" ;; esac
CURRENT="$(python3 - "$CONFIG" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
m = re.search(r"^[ \t]+clips_dir:[ \t]*['\"]?([^'\"\n#]+?)['\"]?[ \t]*(#.*)?$", text, re.M)
print(m.group(1) if m else "")
PY
)"
[ -n "$CURRENT" ] && [ -d "$CURRENT" ] || fail "Cannot find the current clips folder in the configuration"
CURRENT="$(realpath -e -- "$CURRENT")"
FROM="$CURRENT" TO="$DEST"
[ "$CURRENT" != "$DEST" ] || fail "The clips are already in that folder"
case "$DEST/" in "$CURRENT"/*) fail "The destination cannot be inside the current clips folder" ;; esac
case "$CURRENT/" in "$DEST"/*) fail "The destination cannot contain the current clips folder" ;; esac
runuser -u "$SERVICE_USER" -- test -w "$DEST" -a -x "$DEST" || fail "The service account cannot write in the destination (give it that folder: chown $SERVICE_USER)"

[ -z "$(ls -A -- "$DEST")" ] || fail "The destination folder is not empty"

NEED="$(du -sb -- "$CURRENT" | cut -f1)"
FREE="$(df -B1 --output=avail -- "$DEST" | tail -n1 | tr -d ' ')"
[ "$FREE" -ge $(( NEED + NEED / 10 + 52428800 )) ] || fail "Not enough free space in the destination"

# ---- copy as the service account, verify, then switch
set_status running "Copying the clips"
( while sleep 20; do touch "$STATUS" 2>/dev/null; done ) >/dev/null 2>&1 &
KEEPALIVE=$!
log "copy $CURRENT -> $DEST ($NEED bytes)"
runuser -u "$SERVICE_USER" -- cp -a --no-preserve=ownership -- "$CURRENT/." "$DEST/" >>"$LOG" 2>&1 || fail "Copying the clips failed (see the log); the old folder is untouched"
set_status running "Checking the copy"
A="$(cd "$CURRENT" && find . -type f -printf '%P %s\n' | sort | md5sum)"
B="$(cd "$DEST" && find . -type f -printf '%P %s\n' | sort | md5sum)"
[ "$A" = "$B" ] || fail "The copy does not match the original (see the log); the old folder is untouched"
stop_keepalive

set_status running "Switching to the new folder"
BACKUP="$CONFIG.before-move"
cp -p -- "$CONFIG" "$BACKUP" || fail "Cannot back up the configuration"
if ! python3 - "$CONFIG" "$DEST" <<'PY'
import json, re, sys
path, dest = sys.argv[1:3]
text = open(path).read()
new, n = re.subn(r"^([ \t]+clips_dir:)[ \t]*.*$", lambda m: m.group(1) + " " + json.dumps(dest), text, count=1, flags=re.M)
if n != 1:
    sys.exit(3)
open(path, "w").write(new)
PY
then
  cp -p -- "$BACKUP" "$CONFIG"
  fail "Cannot update the configuration; nothing changed"
fi
mkdir -p "$DROPIN_DIR"
printf '[Service]\nReadWritePaths=%s\n' "$DEST" > "$DROPIN_DIR/clips-path.conf"
systemctl daemon-reload
systemctl restart "$UNIT".service
healthy=0
for _ in $(seq 1 "${HEALTH_TRIES:-30}"); do curl -fs "http://127.0.0.1:$PORT/api/v1/health" >/dev/null 2>&1 && { healthy=1; break; }; sleep 1; done
if [ "$healthy" != 1 ]; then
  cp -p -- "$BACKUP" "$CONFIG"
  rm -f "$DROPIN_DIR/clips-path.conf"
  systemctl daemon-reload
  systemctl restart "$UNIT".service
  fail "The service did not start on the new folder; the previous configuration was restored"
fi
set_status "done" "The clips are now in $DEST. The old folder $CURRENT was kept: delete it yourself once you have checked."
