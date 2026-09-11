# Tests

| Command | What it checks |
|---|---|
| `tests/run.sh` | Scanner output on `fixtures/broken-app` equals `expected/broken-app.txt` (section · severity · file:line). `--update` rewrites the snapshot. |
| `IKAS_APP_EXAMPLES=<clone> tests/run.sh` | …plus `scripts/calibrate.sh`: the three official examples must produce zero Blockers. |

`fixtures/broken-app` is the official `starter-app` with every defect the fix catalogue has a recipe for, plus the
two Blockers that have none (`§5.1` unauthenticated route, `§5.2` client-side Admin API call). See its README for the map.

## Recipe verification (manual, 2026-09-12)

All thirteen applicable recipes (F1–F9, F11–F14; F10 is exercised by a separate target) were applied to a copy of the
fixture exactly as written in `references/fix-catalogue.md`:

- Blockers 11 → 2 — the two left are the ones without a recipe (action-list items).
- Every recipe's "Verify" condition held (its scanner hit disappeared); F12 confirmed with `git check-ignore`.
- `tsc --noEmit` after `pnpm install`: no errors in any recipe-touched file (remaining errors are fixture noise — removed
  `components/ui`, un-generated codegen operations, Prisma models the fixture invents).
- Applying F14 makes F10's precondition true for `api/ikas/get-merchant` — expected; the report should list F10 as a
  follow-up in that case.
