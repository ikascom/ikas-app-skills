# Fix catalogue

Recipes the skill may apply **after the user approves** (see SKILL.md › Step 6). Each recipe has a precondition, an exact change, and a verification. Apply only recipes whose precondition holds in the code you read; never improvise beyond the recipe. Anything outside this list stays in the action list for the developer.

## Contents

- Rules for applying fixes
- Recipes F1–F14
- Never do

## Rules for applying fixes

1. Apply only the recipes the user selected. "Hepsini uygula" means every recipe whose precondition holds, nothing else.
2. One recipe = one minimal edit set. Match the file's existing style (imports, quotes, semicolons, comment density).
3. After all edits: run the type-check (`npx tsc --noEmit` or the project's `lint`/`typecheck` script) when `node_modules` exists; otherwise say the check was skipped. Do not install dependencies.
4. Report every applied recipe with file + what changed, plus `git diff --stat`. Report every recipe *not* applied with the reason (precondition failed, needs a decision).
5. Never `git add`/`commit`. Never delete files the developer did not ask to delete; F12 is the only recipe that touches a file outside `src/`.

## Recipes

| ID | Precondition (what you read) | Change | Verify |
|---|---|---|---|
| **F1** | A webhook or API-action route (§6.1/§7.2) acts on the payload without verifying the signature, or verifies it but never rejects | Add, before any work: parse → `validateIkasWebhookSignature(body, clientSecret)` (import from `@ikas/admin-api-client`; for API actions compute `createHmac('sha256', secret).update(data, 'utf8').digest('hex')` and compare with `timingSafeEqual` on equal-length buffers) → `401 { error: { statusCode: 401, message: 'invalid signature' } }` on mismatch → `500` when the secret is unset. Keep the existing business logic untouched below the guard. | Scanner §6.1/§7.2 signature hit gone; route still type-checks |
| **F2** | An entry page (root `/`, an iframe action page, `/callback` that renders) never calls `AppBridgeHelper.closeLoader()` directly or through a hook it uses | Add `useEffect(() => { AppBridgeHelper.closeLoader(); }, []);` as the first effect; add the import from `@ikas/app-helpers` | Scanner §3.1 hit gone |
| **F3** | Authorize route builds `state` with `Math.random()` | Replace with `randomBytes(32).toString('base64url')` from `crypto` | Scanner §2.1 hit gone |
| **F4** | Deploy URL concatenated into a URL (`${process.env.NEXT_PUBLIC_DEPLOY_URL}/…` or `+ '/api…'`) with no normalization | In the config module only: `const deployUrl = process.env.NEXT_PUBLIC_DEPLOY_URL?.replace(/\/+$/, '');` (keeps `undefined` semantics) and build the redirect URI from it; leave non-URL uses (JWT issuer, logging) alone | Scanner §2.1 concatenation hit gone |
| **F5** | Callback/token helper does `window.location.replace(redirectUrl)` with no iframe branch | Insert `if (window.self !== window.top) { router.replace('<iframe home>'); return; }` before the top-level redirect. `<iframe home>` = the route the root page navigates to after obtaining a token (Step 2 inventory), not a legacy redirect page | Scanner §3.3 hit gone |
| **F6** | `console.log` / `console.info` of callback params, ikas tokens, JWTs, signatures | Delete the line and any comment that only describes it. If the same callback effect awaits `setToken` inside an async IIFE with no `catch`, add `.catch((e) => { if (e !== 'redirectUrl-called') throw e; })` so the sentinel does not surface | Scanner §8/§2.2 logging hit gone; sentinel hit gone |
| **F7** | A secret named `NEXT_PUBLIC_*` | Rename in `.env.example` and every `process.env` reference; tell the user to update the deployed env and, if it was the client id, the Partner panel | Scanner §8 hit gone; `grep` for the old name empty |
| **F8** | `useSearchParams()` outside `<Suspense>` | Split the consumer into an inner component and wrap it in `<Suspense>` | Scanner §3.3 hit gone |
| **F9** | Callback code **signature** compared with `===` | Compare equal-length `Buffer`s with `crypto.timingSafeEqual` (length mismatch → false). Leave the `state` comparison alone — it is a random nonce, not a secret | Scanner §2.2 timing hit gone |
| **F10** | An admin API route loads the ikas token itself and never checks `deleted`, **and** the repo already has a shared wrapper (`withMerchant`-style) that does | Wrap the handler with the existing wrapper and use its context; delete the now-redundant manual token load | Scanner §5.1 hit gone |
| **F11** | Uninstall webhook handler checks `!authToken` but not `authToken.deleted` before running cleanup | Change to `if (!authToken \|\| authToken.deleted) return 200 { ok: true, skipped: true }` | Scanner §6.2 short-circuit hit gone |
| **F12** | An env file with real values (`.env.bak*`, `.env.backup`, `.env.production`) is not covered by `.gitignore` | Append the missing pattern(s) to `.gitignore`. Do **not** delete the file; tell the user it exists. If the file is already **tracked**, stop and tell the user — untracking history is their call | `git check-ignore <file>` succeeds |
| **F13** | Payment webhook grants entitlement without checking `status === 'PAID'` | Wrap the grant in `if (status === 'PAID')`; leave other statuses logged | Scanner §6.4 hit gone |
| **F14** | A shared auth wrapper (`withMerchant` / `requireAuthedUser`-style) loads the ikas token and checks only `!authToken`, and the token model has a `deleted` (or equivalent) field | Change the guard in the wrapper to `if (!authToken \|\| authToken.deleted)` returning the same error it already returns. One line; no new wrapper | Scanner §5.1 wrapper hit gone |

## Never do

- Change the requested scope list (§2.1) — trimming scopes forces every merchant to re-authorize; the developer decides.
- Rewrite the OAuth flow (state consumption order, error surfacing, storeName resolution).
- Add DB models, migrations, or new wrappers (F14 edits an existing wrapper only; if the model has no `deleted` field, F14 does not apply).
- Drop fields from public schemas (§9) — touches business logic.
- Replace `|| ''` secret fallbacks (§10 #15) — needs a boot-time env contract the recipe cannot supply; leave in the action list.
- Delete routes, files, or "clean up" unrelated code. Test/debug routes (§10 #19) are listed as action item #1, not deleted.
- Apply anything in read-only mode, or before the user answered the approval question.
