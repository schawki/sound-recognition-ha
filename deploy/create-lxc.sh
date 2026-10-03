#!/usr/bin/env bash
# Creates an unprivileged Debian 13 LXC container on a Proxmox VE node and installs the sound recognition service in it.
# Run as root ON THE PROXMOX HOST, from a copy of this repository:   bash deploy/create-lxc.sh
#
# Settings (environment variables, all optional):
#   CTID        container id (default: next free id)      HOSTNAME_CT (soundrec)
#   STORAGE     storage for the container disk (local-lvm) TEMPLATE_STORAGE  storage for templates (local)
#   BRIDGE      network bridge (vmbr0)                     IP  "dhcp" (default) or e.g. 192.168.1.50/24
#   GATEWAY     gateway, only with a static IP             DNS  (container default = host's)
#   CORES (2)   MEMORY in MB (1024)   DISK in GB (8)       VLAN  optional vlan tag
#   YES=1       skip the confirmation question
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$HERE")"
HOSTNAME_CT="${HOSTNAME_CT:-soundrec}"
STORAGE="${STORAGE:-local-lvm}"
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
BRIDGE="${BRIDGE:-vmbr0}"
IP="${IP:-dhcp}"
CORES="${CORES:-2}"
MEMORY="${MEMORY:-1024}"
DISK="${DISK:-8}"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run this script as root on the Proxmox host"
{ command -v pct && command -v pveam; } >/dev/null || die "pct/pveam not found: this script must run on a Proxmox VE node"
[ -d "$REPO/service/soundrec" ] && [ -d "$REPO/catalog" ] || die "cannot find service/ and catalog/ in $REPO"
if [ "$IP" != "dhcp" ] && [ -z "${GATEWAY:-}" ]; then die "a static IP needs GATEWAY=..."; fi

CTID="${CTID:-$(pvesh get /cluster/nextid)}"
pct status "$CTID" >/dev/null 2>&1 && die "container $CTID already exists (choose another CTID=...)"

# ---- template
say "Looking for the Debian 13 template"
pveam update >/dev/null 2>&1 || true
TEMPLATE="$(pveam available --section system | awk '{print $2}' | grep -E '^debian-13-standard_.*_amd64\.tar\.zst$' | sort -V | tail -1 || true)"
[ -n "$TEMPLATE" ] || die "no Debian 13 template found in 'pveam available' (is this Proxmox VE up to date? try: pveam update)"
echo "Template: $TEMPLATE"

NET="name=eth0,bridge=$BRIDGE,ip=$IP"
[ "$IP" != "dhcp" ] && NET="$NET,gw=$GATEWAY"
[ -n "${VLAN:-}" ] && NET="$NET,tag=$VLAN"

cat <<MSG

About to create:
  container   $CTID ($HOSTNAME_CT), unprivileged, starts at boot
  resources   $CORES vCPU, $MEMORY MB RAM, ${DISK} GB disk on '$STORAGE'
  network     $NET
  template    $TEMPLATE (from '$TEMPLATE_STORAGE')
MSG
if [ "${YES:-0}" != "1" ]; then
  read -r -p "Continue? [y/N] " ans
  case "$ans" in y|Y|yes|YES) ;; *) die "cancelled" ;; esac
fi

if ! pveam list "$TEMPLATE_STORAGE" | grep -q "$TEMPLATE"; then
  say "Downloading the template"
  pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"
fi

# ---- container
say "Creating container $CTID"
ARGS=(--hostname "$HOSTNAME_CT" --unprivileged 1 --onboot 1 --cores "$CORES" --memory "$MEMORY" --swap 256
      --rootfs "$STORAGE:$DISK" --net0 "$NET" --features nesting=1 --ostype debian)
[ -n "${DNS:-}" ] && ARGS+=(--nameserver "$DNS")
pct create "$CTID" "$TEMPLATE_STORAGE:vztmpl/$TEMPLATE" "${ARGS[@]}"
pct start "$CTID"

say "Waiting for the network in the container"
for _ in $(seq 1 30); do
  pct exec "$CTID" -- sh -c 'getent hosts deb.debian.org >/dev/null 2>&1' && break
  sleep 2
done
pct exec "$CTID" -- sh -c 'getent hosts deb.debian.org >/dev/null 2>&1' || die "the container has no network/DNS (check BRIDGE, IP, GATEWAY, DNS)"

# ---- install
say "Copying the project into the container"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar -C "$REPO" --exclude=node_modules --exclude=__pycache__ --exclude=.pytest_cache --exclude=.git --exclude='panel/test/out' \
    -czf "$TMP/src.tar.gz" service catalog deploy
pct push "$CTID" "$TMP/src.tar.gz" /root/soundrec-src.tar.gz
pct exec "$CTID" -- bash -c 'rm -rf /root/soundrec-src && mkdir /root/soundrec-src && tar -xzf /root/soundrec-src.tar.gz -C /root/soundrec-src'

say "Installing the service"
TZ_HOST="$(cat /etc/timezone 2>/dev/null || true)"
pct exec "$CTID" -- env SOUNDREC_TZ="${SOUNDREC_TZ:-$TZ_HOST}" bash /root/soundrec-src/deploy/install.sh

IPADDR="$(pct exec "$CTID" -- hostname -I 2>/dev/null | awk '{print $1}')"
say "Done"
echo "Container $CTID is running. Service address: http://${IPADDR:-<container ip>}:8765"
echo "Open a shell in it with: pct enter $CTID    Logs: pct exec $CTID -- journalctl -u soundrec -f"
