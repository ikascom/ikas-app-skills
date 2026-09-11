#!/usr/bin/env bash
# Calibration gate (SKILL.md): the official example apps must produce zero BLOCKER lines.
# Usage: scripts/calibrate.sh [path-to-ikas-app-examples-clone]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
EX="${1:-${IKAS_APP_EXAMPLES:-}}"
if [ -z "$EX" ]; then
  EX="$(mktemp -d)/ikas-app-examples"
  git clone -q --depth 1 https://github.com/ikascom/ikas-app-examples.git "$EX"
fi
fail=0
for app in starter-app dashboard-actions-app with-subscription-app; do
  out="$(python3 "$HERE/scan.py" "$EX/examples/$app")"
  n="$(printf '%s\n' "$out" | grep -c '^§[0-9.]* *BLOCKER' || true)"
  printf '%-24s %s\n' "$app" "$(printf '%s\n' "$out" | grep '^BLOCKER:')"
  if [ "$n" != "0" ]; then fail=1; printf '%s\n' "$out" | grep -A1 '^§[0-9.]* *BLOCKER'; fi
done
[ "$fail" = 0 ] && echo "calibration OK" || { echo "calibration FAILED"; exit 1; }
