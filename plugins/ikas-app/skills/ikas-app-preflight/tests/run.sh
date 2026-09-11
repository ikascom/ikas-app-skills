#!/usr/bin/env bash
# Scanner regression test.
#   tests/run.sh          compare scanner output on every tests/fixtures/<name> with tests/expected/<name>.txt
#   tests/run.sh --update rewrite the expected file from the current scanner
# Then runs scripts/calibrate.sh when IKAS_APP_EXAMPLES points at a clone (skipped otherwise).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(dirname "$HERE")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail=0
for FIX in "$HERE"/fixtures/*/; do
  name="$(basename "$FIX")"
  rm -rf "$WORK/app"; cp -R "$FIX" "$WORK/app"; cd "$WORK/app"
  git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm fixture
  # untracked env file with real-looking values, not covered by .gitignore → §8 UYARI (F12)
  printf 'CLIENT_SECRET=fixture-secret-0123456789abcdef0123456789\nDATABASE_URL=postgresql://u:p@db.internal:5432/app\n' > .env.production
  python3 "$SKILL/scripts/scan.py" . | grep -E '^§|^BLOCKER:' | sed -E 's/ +/ /g' > "$WORK/$name.txt"
  EXPECTED="$HERE/expected/$name.txt"
  if [ "${1:-}" = "--update" ]; then
    mkdir -p "$HERE/expected"; cp "$WORK/$name.txt" "$EXPECTED"; echo "updated $EXPECTED ($(grep -c '^§' "$EXPECTED") findings)"; continue
  fi
  if diff -u "$EXPECTED" "$WORK/$name.txt"; then echo "$name: scanner regression OK ($(grep -c '^§' "$WORK/$name.txt") findings)"; else echo "$name: scanner regression FAILED"; fail=1; fi
done
[ "${1:-}" = "--update" ] && exit 0
[ "$fail" = 0 ] || exit 1
if [ -n "${IKAS_APP_EXAMPLES:-}" ]; then "$SKILL/scripts/calibrate.sh" "$IKAS_APP_EXAMPLES"; else echo "calibration skipped (set IKAS_APP_EXAMPLES=<clone of ikascom/ikas-app-examples>)"; fi
