#!/usr/bin/env bash
# Scanner regression test.
#   tests/run.sh          compare scanner output on tests/fixtures/broken-app with tests/expected/broken-app.txt
#   tests/run.sh --update rewrite the expected file from the current scanner
# Then runs scripts/calibrate.sh when IKAS_APP_EXAMPLES points at a clone (skipped otherwise).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(dirname "$HERE")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp -R "$HERE/fixtures/broken-app" "$WORK/app"
cd "$WORK/app"
git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm fixture
# untracked env file with real-looking values, not covered by .gitignore → §8 UYARI (F12)
printf 'CLIENT_SECRET=fixture-secret-0123456789abcdef0123456789\nDATABASE_URL=postgresql://u:p@db.internal:5432/app\n' > .env.production
python3 "$SKILL/scripts/scan.py" . | grep -E '^§|^BLOCKER:' | sed -E 's/ +/ /g' > "$WORK/actual.txt"
EXPECTED="$HERE/expected/broken-app.txt"
if [ "${1:-}" = "--update" ]; then
  mkdir -p "$HERE/expected"; cp "$WORK/actual.txt" "$EXPECTED"; echo "updated $EXPECTED"; cat "$EXPECTED"; exit 0
fi
if diff -u "$EXPECTED" "$WORK/actual.txt"; then echo "scanner regression OK ($(grep -c '^§' "$WORK/actual.txt") findings)"; else echo "scanner regression FAILED"; exit 1; fi
if [ -n "${IKAS_APP_EXAMPLES:-}" ]; then "$SKILL/scripts/calibrate.sh" "$IKAS_APP_EXAMPLES"; else echo "calibration skipped (set IKAS_APP_EXAMPLES=<clone of ikascom/ikas-app-examples>)"; fi
