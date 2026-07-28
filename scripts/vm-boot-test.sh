#!/usr/bin/env bash
# vm-boot-test.sh — boot the Finix live ISO under QEMU/OVMF (UEFI) headless and
# capture framebuffer evidence to artifacts/vm-boot-test/.
#
# Usage: scripts/vm-boot-test.sh [path/to/finix-live.iso]
#   With no argument, uses result/iso/finix-graphical-install*.iso at the repo root.
#
# Requires: nix (fetches OVMF + qemu + imagemagick), python3 on PATH or via nix,
# and read/write access to /dev/kvm for KVM acceleration (falls back to TCG).
# No root needed.
#
# Exit codes: 0 = desktop detected + screenshot captured, 1 = timeout/failure
# (a best-effort screenshot is still written), 2 = usage/environment error.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="$REPO_ROOT/artifacts/vm-boot-test"
RAM_MB="${RAM_MB:-4096}"
POLL_SECS=30

# ---------------------------------------------------------------- locate ISO
if [ $# -gt 1 ]; then
  echo "usage: $0 [path/to/iso]" >&2
  exit 2
fi
if [ $# -eq 1 ]; then
  ISO="$1"
else
  ISO="$(ls "$REPO_ROOT"/result/iso/finix-graphical-install*.iso 2>/dev/null | head -n1 || true)"
  [ -n "$ISO" ] || ISO="$(ls "$REPO_ROOT"/result/iso/*.iso 2>/dev/null | head -n1 || true)"
fi
if [ -z "${ISO:-}" ] || [ ! -r "$ISO" ]; then
  echo "ERROR: ISO not found (arg or result/iso/*.iso). Run 'nix build .#iso' first." >&2
  exit 2
fi
ISO="$(readlink -f "$ISO")"
echo "ISO: $ISO ($(stat -c%s "$ISO" | numfmt --to=iec 2>/dev/null || stat -c%s "$ISO"))"

command -v nix >/dev/null 2>&1 || {
  echo "ERROR: nix not on PATH (try: export PATH=\$HOME/.nix-profile/bin:\$PATH)" >&2
  exit 2
}

# ------------------------------------------------------------- dependencies
echo "Resolving OVMF + qemu via nix (may download)..."
OVMF_DIR="$(nix build nixpkgs#OVMF.fd --no-link --print-out-paths)"
OVMF_CODE="$OVMF_DIR/FV/OVMF_CODE.fd"
OVMF_VARS="$OVMF_DIR/FV/OVMF_VARS.fd"
if [ ! -r "$OVMF_CODE" ]; then
  # Older layouts ship only the combined image; use it as read-only pflash.
  OVMF_CODE="$OVMF_DIR/FV/OVMF.fd"
  OVMF_VARS=""
fi
[ -r "$OVMF_CODE" ] || { echo "ERROR: OVMF firmware not found under $OVMF_DIR/FV" >&2; exit 2; }

# Multi-output derivations print one path per line; pick the one with the binary.
QEMU=""
while IFS= read -r out; do
  [ -n "$out" ] && [ -x "$out/bin/qemu-system-x86_64" ] || continue
  QEMU="$out/bin/qemu-system-x86_64"
  break
done < <(nix build nixpkgs#qemu_kvm --no-link --print-out-paths)
[ -n "$QEMU" ] || { echo "ERROR: qemu-system-x86_64 not found in any qemu_kvm output" >&2; exit 2; }

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON="$(nix build nixpkgs#python3Minimal --no-link --print-out-paths)/bin/python3"
fi

# ------------------------------------------------------------------- accel
if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
  ACCEL="kvm"
  ACCEL_ARGS=(-enable-kvm -cpu host)
  TIMEOUT_SECS=$(( 15 * 60 ))
else
  ACCEL="tcg"
  ACCEL_ARGS=(-accel tcg -cpu qemu64)
  TIMEOUT_SECS=$(( 45 * 60 ))
  echo "WARNING: /dev/kvm not usable — falling back to TCG (slow, timeout ${TIMEOUT_SECS}s)"
fi

# --------------------------------------------------------------- workspace
mkdir -p "$EVIDENCE_DIR"
WORK="$(mktemp -d /tmp/finix-boot-test.XXXXXX)"
QMP_SOCK="$WORK/qmp.sock"
QEMU_PID=""
cleanup() {
  [ -n "$QEMU_PID" ] && kill "$QEMU_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

PFLASH_ARGS=(-drive "if=pflash,format=raw,readonly=on,file=$OVMF_CODE")
if [ -n "$OVMF_VARS" ]; then
  cp "$OVMF_VARS" "$WORK/OVMF_VARS.fd"
  chmod u+w "$WORK/OVMF_VARS.fd"
  PFLASH_ARGS+=(-drive "if=pflash,format=raw,file=$WORK/OVMF_VARS.fd")
fi

QEMU_CMD=("$QEMU"
  -machine q35
  "${ACCEL_ARGS[@]}"
  -smp 4
  -m "$RAM_MB"
  "${PFLASH_ARGS[@]}"
  -display none
  -vga std
  -qmp "unix:$QMP_SOCK,server,nowait"
  -cdrom "$ISO"
  -boot d
  -serial "file:$WORK/serial.log"
)
echo "QEMU (${ACCEL}): ${QEMU_CMD[*]}"
"${QEMU_CMD[@]}" &
QEMU_PID=$!

# ------------------------------------------------------------- QMP helpers
qmp() { # qmp '<json command>' — one-shot QMP round trip
  "$PYTHON" - "$QMP_SOCK" "$1" <<'EOF'
import json, socket, sys
path, cmd = sys.argv[1], json.loads(sys.argv[2])
s = socket.socket(socket.AF_UNIX)
s.settimeout(30)
s.connect(path)
f = s.makefile("rw")
f.readline()                                        # greeting banner
f.write(json.dumps({"execute": "qmp_capabilities"}) + "\n"); f.flush()
f.readline()
f.write(json.dumps(cmd) + "\n"); f.flush()
while True:
    line = f.readline()
    if not line:
        sys.exit(1)
    msg = json.loads(line)
    if "return" in msg:
        sys.exit(0)
    if "error" in msg:
        print(msg["error"], file=sys.stderr)
        sys.exit(1)
EOF
}

screendump() { # screendump <abs-path.ppm>
  qmp "{\"execute\":\"screendump\",\"arguments\":{\"filename\":\"$1\"}}"
}

# analyze <ppm>: prints "<nonblack-fraction> <distinct-color-buckets>"
analyze() {
  "$PYTHON" - "$1" <<'EOF'
import sys
data = open(sys.argv[1], "rb").read()
if not data.startswith(b"P6"):
    sys.exit("not a P6 ppm")
# qemu writes: P6\n<w> <h>\n255\n<raw rgb>
head, _, rest = data.partition(b"\n")
dims, _, rest = rest.partition(b"\n")
_, _, px = rest.partition(b"\n")
w, h = map(int, dims.split())
n = w * h
step = max(1, n // 20000)
nonblack = 0
total = 0
colors = set()
for i in range(0, n, step):
    r, g, b = px[3 * i], px[3 * i + 1], px[3 * i + 2]
    total += 1
    if r > 30 or g > 30 or b > 30:
        nonblack += 1
    colors.add((r // 16, g // 16, b // 16))
print("%.3f %d" % (nonblack / total, len(colors)))
EOF
}

finalize_evidence() { # finalize_evidence <src.ppm> <basename> — install as evidence, png if possible
  local src="$1" base="$2" out_ppm="$EVIDENCE_DIR/$2.ppm"
  cp "$src" "$out_ppm"
  if nix shell nixpkgs#imagemagick -c magick "$out_ppm" "$EVIDENCE_DIR/$base.png" \
      2>/dev/null; then
    rm -f "$out_ppm"
    echo "evidence: $EVIDENCE_DIR/$base.png"
  else
    echo "evidence: $out_ppm (imagemagick unavailable, kept ppm)"
  fi
}

# ---------------------------------------------------------------- wait loop
# Poll every ${POLL_SECS}s. Heuristic for "graphical desktop up": the sampled
# framebuffer is mostly non-black AND color-rich (a GRUB/console screen is
# black with sparse white text; the Plasma wallpaper is neither). Two
# consecutive hits + a settle delay lets Calamares autostart before the shot.
echo "Waiting for QEMU to create QMP socket..."
for _ in $(seq 1 30); do
  [ -S "$QMP_SOCK" ] && break
  kill -0 "$QEMU_PID" 2>/dev/null || { echo "ERROR: qemu exited early" >&2; exit 1; }
  sleep 1
done
[ -S "$QMP_SOCK" ] || { echo "ERROR: QMP socket never appeared" >&2; exit 1; }

# Nudge past the boot menu in case it waits for input (selects default entry).
sleep 20
qmp '{"execute":"send-key","arguments":{"keys":[{"type":"qcode","data":"ret"}]}}' || true

start=$SECONDS
hits=0
result=1
while [ $(( SECONDS - start )) -lt "$TIMEOUT_SECS" ]; do
  sleep "$POLL_SECS"
  kill -0 "$QEMU_PID" 2>/dev/null || { echo "ERROR: qemu died during boot" >&2; break; }
  if ! screendump "$WORK/poll.ppm"; then
    echo "t+$(( SECONDS - start ))s: screendump failed, retrying"
    continue
  fi
  stats="$(analyze "$WORK/poll.ppm" || echo "0 0")"
  frac="${stats%% *}"
  ncolors="${stats##* }"
  echo "t+$(( SECONDS - start ))s: nonblack=$frac colors=$ncolors"
  if "$PYTHON" -c "import sys; sys.exit(0 if float('$frac') >= 0.35 and int('$ncolors') >= 40 else 1)"; then
    hits=$(( hits + 1 ))
  else
    hits=0
  fi
  if [ "$hits" -ge 2 ]; then
    echo "Desktop heuristic satisfied; capturing boot-desktop..."
    if screendump "$WORK/desktop.ppm"; then
      finalize_evidence "$WORK/desktop.ppm" boot-desktop
    fi
    echo "Settling 90s for Calamares autostart, then capturing boot-calamares..."
    sleep 90
    result=0
    break
  fi
done

# Capture the (post-settle) Calamares frame on success; on timeout/failure
# still write a best-effort boot-desktop frame for diagnosis.
if [ "$result" -eq 0 ]; then
  if screendump "$WORK/calamares.ppm"; then
    finalize_evidence "$WORK/calamares.ppm" boot-calamares
  elif [ -f "$WORK/desktop.ppm" ]; then
    echo "WARNING: calamares screendump failed; reusing desktop frame" >&2
    finalize_evidence "$WORK/desktop.ppm" boot-calamares
  fi
elif screendump "$WORK/final.ppm"; then
  finalize_evidence "$WORK/final.ppm" boot-desktop
elif [ -f "$WORK/poll.ppm" ]; then
  echo "WARNING: final screendump failed; using last poll frame" >&2
  finalize_evidence "$WORK/poll.ppm" boot-desktop
else
  echo "ERROR: no framebuffer capture available" >&2
fi

elapsed=$(( SECONDS - start ))
if [ "$result" -eq 0 ]; then
  echo "PASS: desktop detected after ~${elapsed}s (accel=$ACCEL)"
else
  echo "FAIL: desktop not detected within ${TIMEOUT_SECS}s (accel=$ACCEL)" >&2
fi
exit "$result"
