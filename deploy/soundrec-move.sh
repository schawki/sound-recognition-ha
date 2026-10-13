#!/usr/bin/env bash
# Root helper that moves the clips of the sound recognition service to another folder (another disk, a NAS),
# and later deletes the clips left in the old folder. systemd starts it (soundrec-move.path) when the service drops a request file;
# install.sh installs it as /usr/local/sbin/soundrec-move.
#
# MOVE (request file `move`, carrying a destination path). The helper does not trust the path: it re-checks everything on rules the service
# cannot change (the root-owned /etc/soundrec-updater.env), copies as the service account (so it can only write where that account could),
# verifies the copy, points the configuration at the new folder and restarts the service. It NEVER deletes anything while moving; it notes
# the old folder in its own list (move-old, root-owned) so that it can be deleted later.
# While it works the service keeps detecting but keeps no new clip and purges none. On any failure the configuration is left as it was.
#
# DELETE (request file `move-delete`, carrying one of the folders of that list). It acts only if the path is exactly in the list, is not the
# current clips folder, and the current folder holds clips. It removes only what the service writes (day folders with .wav and .json
# files), as the service account, then removes the folder itself if it is empty (never with its content). It never uses rm -r.
set -uo pipefail

ENV_FILE="${SOUNDREC_UPDATER_ENV:-/etc/soundrec-updater.env}"
# shellcheck disable=SC1090
. "$ENV_FILE"
: "${REQUEST_DIR:?}" "${STATUS_DIR:?}" "${CONFIG:?}" "${SERVICE_USER:?}" "${MOVE_ROOTS:?}"
UNIT="${UNIT:-soundrec}"
DROPIN_DIR="${DROPIN_DIR:-/etc/systemd/system/$UNIT.service.d}"
PORT="${SOUNDREC_PORT:-8765}"
KEPT="$STATUS_DIR/move-old"
FROM="" TO="" KEEPALIVE=""

if [ -e "$REQUEST_DIR/move-delete" ]; then
  MODE=delete; LOG="$STATUS_DIR/clean.log"; STATUS="$STATUS_DIR/clean.json"
else
  MODE=move; LOG="$STATUS_DIR/move.log"; STATUS="$STATUS_DIR/move.json"
fi

set_status() {   # set_status <state> <message>
  python3 - "$STATUS" "$1" "$2" "$FROM" "$TO" <<'PY'
import json, os, sys, time
path, state, message, a, b = sys.argv[1:6]
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump({"state": state, "message": message, "from": a, "to": b, "path": b, "updated": time.time()}, f)
os.replace(tmp, path)
PY
}
stop_keepalive() { if [ -n "$KEEPALIVE" ]; then pkill -P "$KEEPALIVE" 2>/dev/null; kill "$KEEPALIVE" 2>/dev/null; fi; KEEPALIVE=""; }
fail() { stop_keepalive; set_status failed "$1"; echo "FAILED: $1" >>"$LOG"; exit 1; }
log() { echo "$*" >>"$LOG"; }
keepalive() { ( while sleep 20; do touch "$STATUS" 2>/dev/null; done ) >/dev/null 2>&1 & KEEPALIVE=$!; }

read_request() {   # read_request <file> <key>: the string under <key> in the JSON request, empty when anything is wrong
  python3 - "$1" "$2" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    v = d.get(sys.argv[2]) if isinstance(d, dict) else None
    print(v if isinstance(v, str) else "")
except Exception:
    print("")
PY
}

current_clips() {   # the clips folder written in the configuration
  python3 - "$CONFIG" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
m = re.search(r"^[ \t]+clips_dir:[ \t]*['\"]?([^'\"\n#]+?)['\"]?[ \t]*(#.*)?$", text, re.M)
print(m.group(1) if m else "")
PY
}

forget() {   # forget <path>: takes a folder off the list of the old folders
  [ -f "$KEPT" ] || return 0
  grep -Fvx -- "$1" "$KEPT" > "$KEPT.tmp" || true
  mv -f "$KEPT.tmp" "$KEPT"; chmod 0644 "$KEPT"
}
remember() {   # remember <path>
  grep -Fxq -- "$1" "$KEPT" 2>/dev/null || echo "$1" >> "$KEPT"
  chmod 0644 "$KEPT"
}

# =====================================================================================================  DELETE
if [ "$MODE" = delete ]; then
  : > "$LOG"
  REQ="$REQUEST_DIR/move-delete"
  OLD="$(read_request "$REQ" old)"
  rm -f "$REQ"
  TO="$OLD"
  set_status running "Checking the old folder"
  [ -n "$OLD" ] || fail "This is not a folder kept after a move"
  grep -Fxq -- "$OLD" "$KEPT" 2>/dev/null || fail "This is not a folder kept after a move"
  if [ ! -d "$OLD" ]; then forget "$OLD"; set_status "done" "The old folder is already gone"; exit 0; fi
  [ "$(realpath -e -- "$OLD")" = "$OLD" ] || fail "The old folder must not go through a link"
  CURRENT="$(current_clips)"
  [ -n "$CURRENT" ] || fail "Cannot find the current clips folder: nothing deleted"
  [ -d "$CURRENT" ] || fail "Cannot find the current clips folder: nothing deleted"
  CURRENT="$(realpath -e -- "$CURRENT")"
  [ "$OLD" != "$CURRENT" ] || fail "This is the folder the clips are in now: nothing deleted"
  case "$OLD/" in "$CURRENT"/*) fail "The old folder is inside the current clips folder: nothing deleted" ;; esac
  case "$CURRENT/" in "$OLD"/*) fail "The current clips folder is inside the old folder: nothing deleted" ;; esac
  if [ -n "$(find "$OLD" -type f -name '*.wav' -print -quit)" ] && [ -z "$(find "$CURRENT" -type f -name '*.wav' -print -quit)" ]; then
    fail "The current clips folder holds no clip while the old one does: check the new folder before deleting the old copy"
  fi
  set_status running "Deleting the old clips"
  keepalive
  log "delete clips in $OLD (current: $CURRENT)"
  if ! runuser -u "$SERVICE_USER" -- find "$OLD" -mindepth 2 -maxdepth 2 -type f -regextype posix-extended -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}/[^/]+\.(wav|json)' -delete >>"$LOG" 2>&1; then
    fail "Some clips could not be deleted: the service account has no right to delete them. Delete the folder $OLD by hand on the machine that runs the service"
  fi
  runuser -u "$SERVICE_USER" -- find "$OLD" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}' -empty -delete >>"$LOG" 2>&1 || true
  stop_keepalive
  if mountpoint -q -- "$OLD"; then
    set_status "done" "The old clips were deleted. The folder $OLD was kept: it is a disk or a share mounted on the machine. Unmount it to remove it."
  elif rmdir -- "$OLD" 2>>"$LOG"; then
    forget "$OLD"
    set_status "done" "The old clips were deleted and the folder $OLD was removed."
  else
    set_status "done" "The old clips were deleted. The folder $OLD was kept: it still holds other files (not clips) or its parent does not let the service remove it. Remove it by hand if you do not need it."
  fi
  exit 0
fi

# =====================================================================================================  MOVE
: > "$LOG"
REQ="$REQUEST_DIR/move"
DEST="$(read_request "$REQ" dest)"
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
CURRENT="$(current_clips)"
[ -n "$CURRENT" ] || fail "Cannot find the current clips folder in the configuration"
[ -d "$CURRENT" ] || fail "The current clips folder in the configuration does not exist"
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
keepalive
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
forget "$DEST"
remember "$CURRENT"
set_status "done" "The clips are now in $DEST. The old folder $CURRENT was kept: delete it from here once you have checked that everything works."
