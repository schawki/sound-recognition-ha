#!/usr/bin/env bash
# Installs (or updates) the sound recognition service on Debian/Ubuntu, as a systemd service.
# Run as root inside the container (or any Debian 12/13 machine):   bash deploy/install.sh
# Re-running updates the code and the model and keeps /etc/soundrec/config.yaml and /var/lib/soundrec untouched.
#
# Overridable for tests / special setups (environment variables):
#   SOUNDREC_ROOT (/opt/soundrec)  SOUNDREC_ETC (/etc/soundrec)  SOUNDREC_VAR (/var/lib/soundrec)  SOUNDREC_USER (soundrec)
#   SOUNDREC_PORT (8765)  SOUNDREC_TZ (system time zone)  SKIP_APT=1  SKIP_SYSTEMD=1  MODEL_FILE=/path/to/yamnet.tflite
#   SOUNDREC_REMOTE_UPDATE=0   do not install the helper that lets Home Assistant update the service (default 1)
set -euo pipefail

MODEL_URL="${MODEL_URL:-https://raw.githubusercontent.com/larsyde/tflite-models-audioset-yamnet/master/yamnet.tflite}"
MODEL_SHA256="${MODEL_SHA256:-e6814cb605db99bf7226a380c0b6708a9f4736c2c1e821a9ea5d3181f6ccf374}"

ROOT="${SOUNDREC_ROOT:-/opt/soundrec}"
ETC="${SOUNDREC_ETC:-/etc/soundrec}"
VAR="${SOUNDREC_VAR:-/var/lib/soundrec}"
USER_NAME="${SOUNDREC_USER:-soundrec}"
PORT="${SOUNDREC_PORT:-8765}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${SOURCE_DIR:-$(dirname "$HERE")}"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run this script as root"
for d in service/soundrec catalog; do
  [ -d "$REPO/$d" ] || die "cannot find service/ and catalog/ in $REPO (run the script from a copy of the repository)"
done

# ------------------------------------------------------------------------------------------------ packages
if [ "${SKIP_APT:-0}" != "1" ]; then
  say "Installing system packages (ffmpeg, python3, venv)"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends python3 python3-venv ffmpeg curl ca-certificates >/dev/null
fi
command -v python3 >/dev/null || die "python3 is missing"
command -v ffmpeg >/dev/null || die "ffmpeg is missing"
command -v curl >/dev/null || die "curl is missing"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || die "Python 3.11 or newer is required"

# ------------------------------------------------------------------------------------------------ user and folders
say "Preparing the service account and folders"
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --home-dir "$VAR" --shell /usr/sbin/nologin "$USER_NAME"
fi
install -d -m 0755 "$ROOT" "$ROOT/models"
install -d -m 0750 -o "$USER_NAME" -g "$USER_NAME" "$ETC" "$VAR"

# ------------------------------------------------------------------------------------------------ code
say "Installing the service into $ROOT"
rm -rf "$ROOT/src" "$ROOT/catalog"
mkdir -p "$ROOT/src"
cp -a "$REPO/service/." "$ROOT/src/"
find "$ROOT/src" \( -name '__pycache__' -o -name '.pytest_cache' -o -name tests -o -name '*.egg-info' \) -prune -exec rm -rf {} + 2>/dev/null || true
cp -a "$REPO/catalog" "$ROOT/catalog"
[ -d "$ROOT/venv" ] || python3 -m venv "$ROOT/venv"
"$ROOT/venv/bin/pip" install --quiet --upgrade pip
"$ROOT/venv/bin/pip" install --quiet --no-cache-dir --upgrade "$ROOT/src"

# what is installed (read by the service, shown in Home Assistant)
{ printf 'commit=%s\n' "$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
  printf 'release=%s\n' "$(git -C "$REPO" describe --tags --always 2>/dev/null || echo unknown)"
  printf 'built=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"; } > "$ROOT/BUILD"
chmod 0644 "$ROOT/BUILD"

# ------------------------------------------------------------------------------------------------ model
MODEL="$ROOT/models/yamnet.tflite"
sha_ok() { [ -f "$1" ] && [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$MODEL_SHA256" ]; }
if sha_ok "$MODEL"; then
  say "YAMNet model already in place"
else
  say "Getting the YAMNet model"
  if [ -n "${MODEL_FILE:-}" ]; then
    cp "$MODEL_FILE" "$MODEL.part"
  else
    curl -fsSL --retry 3 "$MODEL_URL" -o "$MODEL.part" || die "cannot download the model from $MODEL_URL (set MODEL_FILE=/path/to/yamnet.tflite to use a local copy)"
  fi
  sha_ok "$MODEL.part" || { rm -f "$MODEL.part"; die "the model does not match the expected SHA-256 ($MODEL_SHA256)"; }
  mv "$MODEL.part" "$MODEL"
fi

# ------------------------------------------------------------------------------------------------ configuration
CONFIG="$ETC/config.yaml"
if [ -f "$CONFIG" ]; then
  say "Keeping your existing configuration ($CONFIG)"
else
  say "Writing a starter configuration ($CONFIG)"
  TZ_NAME="${SOUNDREC_TZ:-}"
  if [ -z "$TZ_NAME" ] && [ -r /etc/timezone ]; then TZ_NAME="$(cat /etc/timezone)"; fi
  case "$TZ_NAME" in ""|Etc/UTC|UTC) TZ_LINE="# timezone: Europe/Paris   # schedules use this zone (default: the system zone)";; *) TZ_LINE="timezone: $TZ_NAME";; esac
  cat > "$CONFIG" <<CFG
# Sound recognition service. The Home Assistant panel edits this file; you can also edit it by hand
# (restart afterwards: systemctl restart soundrec). The service refuses to start on an invalid file and says why in its log.
api:
  host: 0.0.0.0
  port: $PORT
  # token: generated at the first start and written here
$TZ_LINE
storage:
  clips_dir: $VAR/clips
  db_path: $VAR/events.sqlite
sources: []
CFG
  chown "$USER_NAME:$USER_NAME" "$CONFIG"
  chmod 0640 "$CONFIG"
fi

# ------------------------------------------------------------------------------------------------ systemd
if [ "${SKIP_SYSTEMD:-0}" = "1" ]; then
  say "Skipping systemd (SKIP_SYSTEMD=1)"
  echo "Start by hand:  SOUNDREC_CONFIG=$CONFIG SOUNDREC_MODEL=$MODEL SOUNDREC_CATALOG=$ROOT/catalog $ROOT/venv/bin/python -m soundrec"
  exit 0
fi
say "Installing and starting the systemd service"
sed -e "s#^User=.*#User=$USER_NAME#" -e "s#^Group=.*#Group=$USER_NAME#" \
    -e "s#/opt/soundrec#$ROOT#g" -e "s#/etc/soundrec#$ETC#g" -e "s#/var/lib/soundrec#$VAR#g" \
    "$HERE/soundrec.service" > /etc/systemd/system/soundrec.service
rm -rf /etc/systemd/system/soundrec.service.d

# Updates from Home Assistant: the service (unprivileged) only drops a request file; this root helper does the update.
STATUS="$VAR-update"
if [ "${SOUNDREC_REMOTE_UPDATE:-1}" = "1" ] && [ -d "$REPO/.git" ]; then
  say "Enabling updates from Home Assistant (disable with SOUNDREC_REMOTE_UPDATE=0)"
  install -d -m 0755 -o root -g root "$STATUS"
  install -d -m 0755 -o "$USER_NAME" -g "$USER_NAME" "$VAR/update-request"
  install -m 0755 "$HERE/soundrec-update.sh" /usr/local/sbin/soundrec-update
  { echo "REPO='$REPO'"; echo "REQUEST_DIR='$VAR/update-request'"; echo "STATUS_DIR='$STATUS'"
    for v in SOUNDREC_ROOT SOUNDREC_ETC SOUNDREC_VAR SOUNDREC_USER SOUNDREC_PORT SOUNDREC_TZ; do
      [ -n "${!v:-}" ] && echo "export $v='${!v}'"
    done; } > /etc/soundrec-updater.env
  chmod 0644 /etc/soundrec-updater.env
  sed -e "s#/var/lib/soundrec#$VAR#g" "$HERE/soundrec-update.path" > /etc/systemd/system/soundrec-update.path
  cp "$HERE/soundrec-update.service" /etc/systemd/system/soundrec-update.service
  touch "$STATUS/capable"
  systemctl daemon-reload
  systemctl enable --now soundrec-update.path >/dev/null 2>&1 || true
else
  systemctl disable --now soundrec-update.path >/dev/null 2>&1 || true
  rm -f "$STATUS/capable" /etc/systemd/system/soundrec-update.path /etc/systemd/system/soundrec-update.service
fi
systemctl daemon-reload
systemctl enable soundrec.service >/dev/null 2>&1
systemctl restart soundrec.service

wait_health() { for _ in $(seq 1 30); do curl -fs "http://127.0.0.1:$PORT/api/v1/health" >/dev/null 2>&1 && return 0; sleep 1; done; return 1; }
if ! wait_health; then
  if journalctl -u soundrec -n 30 --no-pager 2>/dev/null | grep -qE "status=226/NAMESPACE|Failed to set up mount namespacing"; then
    say "This container does not allow systemd sandboxing: starting without it"
    mkdir -p /etc/systemd/system/soundrec.service.d
    printf '[Service]\nProtectSystem=\nProtectHome=\nPrivateTmp=\nReadWritePaths=\n' > /etc/systemd/system/soundrec.service.d/no-sandbox.conf
    systemctl daemon-reload
    systemctl restart soundrec.service
  fi
fi
if ! wait_health; then
  journalctl -u soundrec -n 40 --no-pager || true
  die "the service does not answer on port $PORT (see the log above, or: journalctl -u soundrec -e)"
fi

# ------------------------------------------------------------------------------------------------ summary
TOKEN="$("$ROOT/venv/bin/python" -c "import sys, yaml; print((yaml.safe_load(open(sys.argv[1])).get('api') or {}).get('token', ''))" "$CONFIG")"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
say "Sound recognition service is running"
echo "  Address in Home Assistant : host ${IP:-<container IP>}, port $PORT"
echo "  Token                     : $TOKEN"
echo "  Configuration             : $CONFIG"
echo "  Logs                      : journalctl -u soundrec -f"
