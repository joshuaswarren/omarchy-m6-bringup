#!/bin/bash
# Replace the boot object of the stub volume (the Omarchy Mac installer creates it). Runs ONLY in that volume's own
# recoveryOS ("one true recoveryOS", paired with the volume). The installer uses the same kmutil form; bputil -nc was
# already done for the volume, so it is not repeated here.
#
#   SERVER=http://<host>:<port>/<token> WANT_SHA=<sha256 of boot.bin> VGID=<volume group UUID> SYSTEM_DIR=/Volumes/<stub> \
#       sh enrol-boot-object.sh --check
#   same variables, sh enrol-boot-object.sh --go        (asks for the owner password twice)
#
# Rollback: run the same script with the previous object (its sha256 as WANT_SHA) served as boot.bin.
set -euo pipefail

mode="${1:-}"
[ "$mode" = "--check" ] || [ "$mode" = "--go" ] || { echo "usage: $0 --check | --go" >&2; exit 64; }
: "${SERVER:?SERVER=http://host:port/token}"
: "${WANT_SHA:?WANT_SHA=sha256 of the boot object}"
: "${VGID:?VGID=volume group UUID of the stub volume (see: bputil -d)}"
: "${SYSTEM_DIR:?SYSTEM_DIR=mount point of the stub volume, for example /Volumes/<name>}"

curl -fsS "$SERVER/boot.bin" -o /tmp/boot.bin
got="$(sha256sum /tmp/boot.bin | cut -c1-64)"
[ "$got" = "$WANT_SHA" ] || { echo "ABORT: boot.bin sha256 $got, want $WANT_SHA" >&2; exit 1; }
echo "boot.bin ok: $(wc -c < /tmp/boot.bin) bytes, sha256 $got"

bputil -d -v "$VGID" > /tmp/bp.txt
grep -q 'one true recoveryOS' /tmp/bp.txt || { echo "ABORT: not in one true recoveryOS (1TR)" >&2; exit 1; }
grep -q ': Paired' /tmp/bp.txt || { echo "ABORT: this recoveryOS is not paired with $VGID" >&2; exit 1; }
[ -d "$SYSTEM_DIR" ] || { echo "ABORT: $SYSTEM_DIR is not mounted" >&2; exit 1; }
echo "1TR and Paired for $VGID; system volume $SYSTEM_DIR"

if [ "$mode" = "--check" ]; then
    echo "CHECK ONLY: would run kmutil configure-boot -c /tmp/boot.bin --raw --entry-point 2048 --lowest-virtual-address 0 -v $SYSTEM_DIR"
    exit 0
fi

until kmutil configure-boot -c /tmp/boot.bin --raw --entry-point 2048 --lowest-virtual-address 0 -v "$SYSTEM_DIR"; do
    echo "kmutil failed (password typo?). Press Enter to retry, Ctrl-C to stop."
    read -r _
done
echo "ENROLLED $got. Restart the Mac (do not shut it down: you would need to start it again by hand)."
