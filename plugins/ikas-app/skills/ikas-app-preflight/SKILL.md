---
name: ikas-app-preflight
description: Use before submitting an ikas Admin App (Next.js app installed via OAuth into the ikas panel) to App Store review — checks the five publishing prerequisites, the OAuth / App Bridge / iframe contract, webhook and app-action signature verification, secret hygiene, and public-endpoint safety against a fixed ruleset. Read-only by default; `fix` applies a small catalogue of recipe-based repairs. Triggers on "uygulama review'a hazır mı", "app store'a göndermeden önce kontrol et", "ikas app denetle", "webhook imzası doğru mu", "oauth akışı güvenli mi", "install/uninstall akışı", "pre-review", "publish checklist", "is this app ready for review".
context: fork
allowed-tools: Read, Grep, Glob, Bash, Edit
model: opus
effort: high
---

# ikas App Preflight

A **pre-review gate** for ikas Admin Apps. The measuring stick is `references/app-review.md` (bundled with this skill): the five official publishing prerequisites, the platform contracts (OAuth, App Bridge / iframe, webhooks, app actions), the security baseline, and a numbered anti-pattern catalogue distilled from real rejections and real fixes. You read the code to predict what the ikas reviewer and the merchant will experience, and to find the security holes a reviewer would not even reach.

**Core discipline: every finding is anchored.** A finding either cites the app-review.md section it violates (§2.2, §6.1, §10 #4 …) or is explicitly labeled **kontrat dışı**. "Best practice" without a § is how audits drift — cite it, label it, or drop it. Code style, naming, CSS, test coverage, and business logic are out of scope; note once if egregious, move on.

**Not a substitute for running the app.** Some prerequisites (partner verification, two dev stores, reviewer test account) cannot be seen in code. They go into the report as questions, never as passes.

## Severity taxonomy

Classify every finding as exactly one of:

| Class | Meaning | Example |
|---|---|---|
| **Blocker** | Would get the submission rejected, or is a security hole regardless of review: a §2–§9 **MUST** miss, or a §10 item marked Blocker | Webhook handler without signature verification (§6.1, §10 #2) |
| **Uyarı** | A **SHOULD** miss or a §10 item marked Uyarı — must be fixed, but alone would not fail review | Opaque "Callback failed" error (§10 #8) |
| **Beyan gerekli** | A **DECLARE** item: not visible in code, the developer must confirm it before submitting | "At least 2 development stores" (§1 #5) |
| **Bilgi** | Context the developer should know; no action strictly required | Requested scope list, for a least-privilege sanity check |
| **Kontrat dışı** | Would help, but no rule requires it — max 5, kept apart so they cannot be mistaken for requirements | Add a health endpoint |

Blockers lead the report. Bilgi and kontrat dışı never do.

## Invocation modes

| Invocation | Scope | Writes files? |
|---|---|---|
| (none) | Full preflight — Pass 0 → Pass 5, full report | **No** |
| `fix` | Full preflight, then apply only the **Fix Catalogue** recipes whose preconditions hold; report both | Yes — catalogue recipes only |
| `quick` | Pass 0 (scanner) + Pass 4 (anti-patterns); say so in the report | No |
| `section <oauth\|iframe\|webhooks\|actions\|secrets\|public>` | Pass 0 scoped to that area + the matching § in Pass 2/3 | No |

Section → ruleset mapping: `oauth` = §2 + Kurulum stage; `iframe` = §3 + §4 + Callback/Günlük giriş/ikas arayüzü stages; `webhooks` = §6 + Kaldırma/Plan stages; `actions` = §7 + Aksiyon stage; `secrets` = §8 + §5.1/§5.3; `public` = §9 + §5.2. §10 items are always in scope.

In every mode except `fix`, the skill **changes nothing**: no edits, no scaffolding, no config changes, no `git` writes. If the user wants repairs outside the catalogue, list them as the action list and stop.

## Procedure

Work through the passes in order — fixed coverage is what makes two preflights of the same app agree. Open `references/app-review.md` with `Read` and jump to sections as you go; don't grade from memory.

### Pass 0 — Deterministic evidence

```bash
python3 <skill-dir>/scripts/scan.py <project-root>        # add --json for machine output
```

The scanner walks the App Router tree and emits `§ | severity | file:line | message` for pattern-level evidence: `Math.random` state, missing HMAC checks, always-200 webhooks, iframe pages without `closeLoader`, unguarded Admin redirects, `NEXT_PUBLIC_` secrets, money fields in public schemas, and more. Treat every hit as **a place to read**, and every miss as **nothing proven**. Keep the output — it is the evidence column of the report. If the scanner says "ikas app not detected", stop and tell the user this skill is for Admin Apps (Next.js + `@ikas/admin-api-client` / `@ikas/app-helpers`).

### Pass 1 — Surface inventory & app shape

Read `ikas.config.json`, `package.json`, `.env.example`, the route tree under `src/app` (or `app`), and the first component the panel renders (`/` and its redirect target). Establish:

- **Routes by kind:** OAuth (authorize / callback), admin API (JWT-protected), webhooks, app-action pages and API-action routes, public/storefront endpoints, iframe pages.
- **App shape** per §4 — exactly one: (a) in-panel dashboard, (b) external dashboard, (c) action-only, (d) webhook-listener / headless. The shape decides which §4 row applies and which DECLARE items the report must ask for.
- **Paid or free** (§6.4): any `store/app/payment` handling, `getMerchantLicence`, plan keys.
- **Requested scopes** vs operations actually called (§2.1 least privilege).

State the shape and the inventory at the top of the report so the reader can verify the rest against it.

### Pass 2 — Merchant journey

Trace the journey through the code, one stage at a time, reading deeply enough to answer each stage's questions — especially error and edge paths (`catch` blocks, missing-param branches, non-iframe render).

| Stage | What must be true | Ruleset |
|---|---|---|
| **Kurulum** (authorize → callback → first screen) | CSPRNG state stored server-side; normalized `redirect_uri`; callback verifies the code signature (timing-safe), matches + consumes state when a session exists, reads `storeName` from the query, reports exchange failures with the upstream reason, resolves identity via `getMerchant`/`getAuthorizedApp`, persists the token by `authorizedAppId`, hands the browser a short-lived JWT only | §2.1, §2.2 |
| **Callback sayfası** | `closeLoader()` on mount; `useSearchParams` under `<Suspense>`; inside the iframe → route in place, top-level → redirect to Admin; redirect sentinel caught | §3.1, §3.3 |
| **Günlük giriş** (merchant opens the app from the panel) | Root/dashboard closes the loader before any await; token via bridge → sessionStorage → `getNewToken`; something actionable renders within one screen; outside the iframe a meaningful fallback | §3.1, §3.2, §4 |
| **ikas arayüzü** (prerequisite #4) | The §4 row for the app shape holds: real content (a) / visible external link + instruction + test-account DECLARE (b) / explanatory copy (c, d) | §4 |
| **Aksiyon** (if any) | iframe action: params parsed defensively, `closeLoader`, result shown, `closeApp` at the end; API action: HMAC verified first | §7 |
| **Plan satın alma** (paid apps) | Only `PAID` grants; unknown keys ignored; entitlement reconciled with `getMerchantLicence` | §6.4 |
| **Kaldırma** (uninstall) | Webhook verified and shape-checked; fail-closed without secret; honest status codes; `store/app/deleted` matched; token invalidated; injected scripts / campaigns / webhooks removed; API routes refuse the uninstalled token afterwards | §6.1, §6.2, §5.1 |

### Pass 3 — Security layer

Walk §5, §6, §7, §8, §9 line by line against the inventory from Pass 1:

- Every non-exempt API route verifies the JWT **before** work and takes identity from `aud`/`sub`, never from the body (§5.1). Use `Grep` for the auth helper and diff the hit list against the route list — a route the scanner missed is still a route. Routes that bypass the shared wrapper must still refuse `deleted` tokens.
- Requested scopes vs. used operations (§2.1): `Grep` for `queries\.\w+|mutations\.\w+`, map each operation to its scope family (orders / products / customers / campaigns / inventories / storefront), and list families that are requested but never used.
- No client-side call to `api.myikas.com` (§5.2), no upstream error bodies or tokens in responses (§5.3).
- Webhook and API-action routes: schema → signature → secret-present guard → honest statuses → idempotency (§6.1, §7.2).
- Secrets: nothing sensitive under `NEXT_PUBLIC_`, `.env` ignored, no token/param logging, `oauthRedirectPath` matches a real route, deploy URL normalized once (§8).
- Public endpoints, if any: merchant scoping on every id, no client-supplied money values, rate limiting, deliberate CORS (§9).

If the project has the ikas admin MCP configured (`.mcp.json` → `https://api.myikas.com/api/v2/admin/mcp`), use its list/introspect tools to confirm operation names and webhook scope strings you are unsure about. Without it, cite the docs URL from the ruleset header — do not invent scope names.

### Pass 4 — Anti-pattern sweep

Read §10 from the file and check each numbered item explicitly. Items #1–#18 are all in scope. Cite them as `§10 #n` in findings; when an item is also a §2–§9 rule, cite both.

### Pass 5 — Declarations

Build the **Beyan gerekli** table from §1 and §4:

| Soru | Neden |
|---|---|
| Partner hesabı oluşturuldu ve uygulama bu hesaba eklendi mi? | §1 #1 |
| Partner hesabı doğrulandı mı? | §1 #2 |
| Uygulama en az 2 geliştirme mağazasında kurulu ve test edilebilir mi? Mağaza adları? | §1 #5 |
| (Shape b) Reviewer için çalışan bir test hesabı gönderim notlarına eklenecek mi? | §4 (b), §10 #12 |
| (Paid) Planlar Partner panelinde tanımlandı ve bölgelerle eşlendi mi? | §1, §6.4 |
| (Kod `saveWebhook` çağırmıyorsa) Uninstall webhook'u Partner panelinde `<deployUrl><webhook path>` adresine tanımlı mı? | §6.2 |

Only include rows that apply to the app's shape. Add a row for any other DECLARE-shaped gap you hit in §2–§9 (something the code defers to the Partner panel or to deployment). Never mark a DECLARE item as passed.

## Fix Catalogue (`fix` mode only)

Apply a recipe **only** when its precondition is met verbatim in the code; anything else stays in the action list. After all edits run the project's type-check and lint (`pnpm exec tsc --noEmit`, `pnpm lint` or the project's equivalents) and report the result honestly.

| Id | Precondition (what the code looks like) | Recipe | Verify |
|---|---|---|---|
| **F1** | Webhook route with no `validateIkasWebhookSignature` / HMAC, or `catch` returning 200 | Add a zod schema mirroring the SDK's `IkasWebhook` (all seven fields `z.string().min(1)`: `id, createdAt, scope, merchantId, authorizedAppId, data, signature`); import `validateIkasWebhookSignature` from `@ikas/admin-api-client`; return 500 when the secret is missing, 400 on invalid payload, 401 on bad signature, 500 from `catch`; `200 { ok: true, skipped: true }` for scopes the app does not handle or a missing token row; add `store/app/deleted` to the uninstall scope list. Remove header/`body.data` fallbacks the old handler used for `scope`/`authorizedAppId` — the signed envelope carries them | Scanner §6.1 BLOCKER/UYARI hits gone (the idempotency BILGI may remain); `tsc` clean |
| **F2** | `'use client'` page the panel opens directly (`/`, `/callback`, `/dashboard*`, action pages) that uses the bridge — directly or via a helper such as a token helper — or `useSearchParams`, and never calls `closeLoader` (directly or via an imported hook). A store-name form page reached only by in-app navigation is out of scope | Add `useEffect(() => { AppBridgeHelper.closeLoader(); }, []);` as the first effect; import from `@ikas/app-helpers` | Scanner §3.1 hit gone |
| **F3** | `Math.random()` used for OAuth `state` | Replace with `randomBytes(32).toString('base64url')` from `crypto` | Scanner §2.1 hit gone |
| **F4** | Deploy URL concatenated into a URL (`${process.env.NEXT_PUBLIC_DEPLOY_URL}/…`, `+ '/api…'`) without normalization | In the config module only: `const deployUrl = process.env.NEXT_PUBLIC_DEPLOY_URL?.replace(/\/+$/, '');` (keeps `undefined` semantics) and build the redirect URI from it; leave non-URL uses (JWT issuer, logging) alone | Scanner §8 concatenation hit gone; `grep` for raw `NEXT_PUBLIC_DEPLOY_URL}` concatenation empty |
| **F5** | Callback/token helper does `window.location.replace(redirectUrl)` with no iframe branch | Insert `if (window.self !== window.top) { router.replace('/dashboard'); return; }` before the top-level redirect (target route = the app's iframe home) | Scanner §3.3 hit gone |
| **F6** | `console.log` of callback params, tokens, JWTs, signatures | Delete the line and any comment that only describes it (or reduce to a non-sensitive id) | Scanner §8 hit gone |
| **F7** | A secret named `NEXT_PUBLIC_*` | Rename the variable in `.env.example` and every `process.env` reference; tell the user to update deployed env + Partner panel if relevant | Scanner §8 hit gone; `grep` for the old name empty |
| **F8** | `useSearchParams()` outside `<Suspense>` | Split the component and wrap the consumer in `<Suspense>` | Scanner §3.3 hit gone |
| **F9** | Callback resolves `storeName` as `session.storeName \|\| 'api'` without reading the query | Add `storeName` to the callback schema (`z.string().min(1).optional()`) and resolve `searchParams.get('storeName') \|\| session.storeName` first; keep the old fallback last | Scanner §2.2 storeName hit downgraded to BILGI |
| **F10** | Code-signature or state compared with `===` | Compare equal-length `Buffer`s with `crypto.timingSafeEqual` (length mismatch → false) | Scanner §2.2 timingSafeEqual hit gone |
| **F11** | Admin API route loads the ikas token itself and never checks the uninstalled/`deleted` flag, **and** the repo already has a shared wrapper (`withMerchant`-style) that does | Wrap the handler with the existing wrapper and use its context; no new wrapper is written | Scanner §5.1 hit gone |

Never: change scopes, rewrite the OAuth flow (state consumption order, error surfacing), add DB models, drop fields from public schemas (§9 — touches business logic), remove `|| ''` secret fallbacks (needs a boot-time env contract the recipe cannot supply), or "clean up" unrelated code. If a fix would require more than the recipe, leave it in the action list with the reason.

When `node_modules` is absent the type-check cannot run — say so in the report; do not install dependencies to make it run.

## Report contract

The report is in Turkish (unless asked otherwise) and has exactly these parts, in order:

1. **Karar cümlesi** — one sentence: review'a gönderilebilir mi, ve tek en büyük risk ne. A Blocker whose fix is a single, obvious change may be worded "şu düzeltmeyle gönderilebilir" — it still leads the Blocker table. Then one line with the app shape (§4 a/b/c/d) and paid/free.
2. **Blocker'lar** — table: bulgu, kanıt (dosya:satır ve ne görüldü), dayanak (§). Security holes first, then review-rejection items.
3. **Uyarılar** — same table shape.
4. **Beyan gerekli** — the Pass 5 table, filtered to the app's shape.
5. **Bilgi / kontrat dışı** — short bullets, max 5 kontrat dışı, clearly marked "zorunlu değil".
6. **Öncelikli aksiyon listesi** — numbered, blockers first, each one a concrete change in a named file.
7. (`fix` mode only) **Uygulanan düzeltmeler** — table: fix id, dosya, ne değişti; plus the type-check/lint result and a `git diff --stat`. Fixes *not* applied and why.

Evidence means a file path, a line, and what you saw there — enough to verify without re-auditing. Quote the scanner line when it is the evidence.

## Common mistakes

- Passing §4 because `closeLoader()` exists. The loader closing is necessary, not sufficient — a blank screen after it is still §10 #13.
- Rejecting an external dashboard on sight. Shape (b) is allowed; it fails only without the in-iframe link/instruction or the reviewer test account.
- Demanding a session `state` on every callback. The Admin iframe drops third-party cookies and ikas can start installs without the authorize route — read the documented exception in §2.2 before flagging.
- Treating `if (signature && …)` on the **callback** as a Blocker by itself; it is the accepted posture there. On **webhooks and API actions** the signature is always present and must always be verified.
- Trusting the scanner's silence. It is regex over files; a hand-rolled fetch to the token endpoint or a webhook route named `notify` will slip past it. The route inventory in Pass 1 is the source of truth.
- Grading the app against a remembered starter template. Templates have had these bugs; the ruleset is the standard.
- Applying fixes in the default mode, or applying non-catalogue fixes in `fix` mode.
