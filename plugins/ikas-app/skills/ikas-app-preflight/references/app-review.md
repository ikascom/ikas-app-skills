# APP-REVIEW.md — Pre-Review Contract for ikas Admin Apps

> **What this is.** The measuring stick for an ikas Admin App (a Next.js app that installs into a merchant's ikas panel through OAuth) before it is submitted to App Store review. It encodes the five official publishing prerequisites, the platform's OAuth / App Bridge / webhook / action contracts, and the security baseline reviewers expect. Every rule here comes from one of three places: the official docs on builders.ikas.com, the SDK surface (`@ikas/admin-api-client`, `@ikas/app-helpers`), or a rejection / fix that actually happened in a shipped app.
>
> **What this is not.** Not a code-style guide, not a Next.js tutorial, not a substitute for the docs. It does not grade UI polish or business logic.
>
> **How to use it.** The `ikas-app-preflight` skill walks §1–§10 in a fixed order and anchors every finding to a § here. Rules are marked **MUST** (a miss is a *Blocker*: review rejection or a security hole), **SHOULD** (a miss is an *Uyarı*), or **DECLARE** (cannot be seen in code — the developer must confirm it; a *Beyan gerekli* item). Each § ends with **Evidence**: what the reviewer should actually find in the repository.
>
> **Sources.** Publishing: `https://builders.ikas.com/docs/app-development/admin-app/build-publish`. Development & OAuth: `/docs/app-development/admin-app/development`. App actions: `/docs/app-development/admin-app/app-actions`. Plans: `/docs/app-development/admin-app/plans`. Allowed stores: `/docs/app-development/admin-app/allowed-app`. CLI: `/docs/app-development/admin-app/ikas-cli`.

---

## 1. Publishing prerequisites

ikas lists five prerequisites for publishing to the App Store. Only two are visible in code.

| # | Prerequisite (official wording, TR) | How it is checked |
|---|---|---|
| 1 | Partner Hesabı — partner account exists and the app is attached to it | **DECLARE** — ask the developer |
| 2 | Doğrulama — the partner account is verified | **DECLARE** — ask the developer |
| 3 | Geliştirmenin Tamamlanmış Olması — development finished and the OAuth flow works inside ikas | Code: §2 + §3 + §5 |
| 4 | ikas Arayüzü — there is somewhere in the ikas panel to use the app, or a way to reach the app's own UI | Code: §4 (+ a **DECLARE** when the UI is external) |
| 5 | Test Ortamı — installed and testable on at least 2 development stores | **DECLARE** — ask for the two store names |

**Publishing flow reminders** (not code, but the report should mention them when relevant): paid apps need plans defined before region selection (§6.4); "Herkese Açık" (public) listing goes through ikas review, "Gizli" (private link) does not; store-content fields (logo, name, summary, description, visuals) are mandatory; plan descriptions are mandatory for paid apps.

**Evidence.** A README or deployment doc naming the production URL and the test stores is a strong signal but not required. The three DECLARE items go into the report's "Beyan gerekli" table verbatim.

---

## 2. OAuth flow

The app uses OAuth 2.0 Authorization Code. ikas opens `<deployUrl>/…/authorize` (or the merchant lands on `/authorize-store` and enters a store name), ikas redirects back to the path declared as `oauthRedirectPath` in `ikas.config.json`, and the app exchanges the code for tokens.

### 2.1 Authorize route

- **MUST** generate `state` with a CSPRNG: `crypto.randomBytes(32).toString('base64url')` or equivalent. `Math.random()` is a Blocker (§10 #1).
- **MUST** persist `state` (and the `storeName` it belongs to) server-side — iron-session or a DB row — before redirecting.
- **MUST** build `redirect_uri` from a **normalized** deploy URL (no trailing slash) + the configured callback path. A doubled slash silently breaks the token exchange with a bare 400 (§10 #6).
- **MUST** request only the scopes the app uses. The docs: "Geliştiriciler, uygulamalarının ihtiyaç duyduğu minimum yetkileri seçmelidir." Compare the requested scope list with the operations actually called.
- **SHOULD** validate `storeName` (non-empty, host-safe) before using it in the OAuth base URL.
- **SHOULD NOT** derive `redirect_uri` from the request `Host` header in production — a dev-only fallback (tunnel hosts when the deploy URL is localhost) is fine if it is clearly gated to development.

### 2.2 Callback route

- **MUST** validate the request shape (zod or equivalent) — `code` required.
- **MUST**, when ikas sends `signature`, verify it: `HMAC-SHA256(code, CLIENT_SECRET)` hex, compared with `crypto.timingSafeEqual` on equal-length buffers. Skipping verification because the parameter is optional is a Blocker (§10 #2).
- **MUST**, when the initiating session carries a `state`, require the callback's `state` to match (timing-safe) and **consume it** (clear from session) before the token exchange, so a replayed callback fails.
- **Documented exception — third-party cookies.** The Admin panel installs apps from inside an iframe, and the cookie written by the authorize route is a third-party cookie that browsers frequently drop. ikas also starts installs from the panel without ever calling the app's authorize route. In both cases there is no session `state` to compare. Accepted posture: *if a session state exists it must match and be consumed; if none exists, the callback is authenticated by the code signature (when present) plus the code exchange itself.* Rejecting every callback without a state breaks legitimate installs — flag as **Uyarı** only if the app neither checks the signature nor documents the exception.
- **MUST** take `storeName` from the callback query first (ikas echoes it), then the session. A hard-coded fallback such as `'api'` posts the code to the wrong host (§10 #7).
- **MUST** surface the token-exchange failure reason (ikas' HTTP status and body, minus secrets) in logs and in the response — an opaque "Callback failed" hides the actual cause (§10 #8).
- **MUST** resolve identity server-side after the exchange: `getMerchant` + `getAuthorizedApp`, and persist the token keyed by `authorizedAppId` (with `merchantId`, `expireDate`, `scope`, `salesChannelId`).
- **MUST** hand the browser a **short-lived app JWT**, not the ikas access/refresh token. JWT: `sub = merchantId`, `aud = authorizedAppId`, `exp` set, signed with a server secret (the starter uses `CLIENT_SECRET`, HS256).
- **MUST NOT** log the raw callback query, the code, or any token (§8, §10 #10).
- **SHOULD** re-use the SDK (`OAuthAPI.getTokenWithAuthorizationCode`, `OAuthAPI.getOAuthUrl`) rather than hand-rolled URLs.

### 2.3 Token lifecycle

- **MUST** refresh the ikas access token server-side (`onCheckToken` in `getIkas` or equivalent) and write the refreshed token back to storage.
- **MUST** treat a token row for an uninstalled app as invalid (`deleted` flag or row removal — see §6.2).
- **MUST NOT** expose access/refresh tokens to the browser in any response, cookie, or query string.

**Evidence.** Authorize route: `randomBytes`, session write, `getOAuthUrl`, `encodeURIComponent(redirect_uri)`. Callback route: zod schema, `validateCodeSignature`/`createHmac` + `timingSafeEqual`, `session.state` compare + clear, `storeNameParam ||`, `TokenExchangeError`-style reporting, `getMerchant`/`getAuthorizedApp`, `AuthTokenManager.put`, `JwtHelpers.createToken`. Config: `.replace(/\/+$/, '')` (or `new URL`) on the deploy URL.

---

## 3. Iframe & App Bridge

After install, the panel loads the app in an iframe and shows its own loading overlay until the app calls `AppBridgeHelper.closeLoader()`. A page that never calls it is a spinner forever — the single most common "it works locally, fails in review" symptom.

### 3.1 Every iframe-mounted page closes the loader

- **MUST** call `AppBridgeHelper.closeLoader()` in a mount-time `useEffect(() => { … }, [])` on **every** page the panel can open directly: the root `/`, `/callback`, `/dashboard` and its sub-routes, every app-action page (§7). A shared hook (`useIkasToken`-style) that does it counts, as long as the page actually uses the hook.
- **SHOULD** call it *before* awaiting anything — the loader should not depend on a network round-trip.

### 3.2 Token acquisition in the iframe

- **MUST** get the browser token through the bridge: `getAuthorizedAppId()` → cached token in `sessionStorage` keyed by app id → check `exp` → otherwise `getNewToken()`. Bridge calls only work when `window.self !== window.top`.
- **MUST** send that token to the app's own backend (`Authorization: JWT <token>` in the starter) — never to `api.myikas.com` directly (§5.2).
- **SHOULD** render a meaningful screen when opened outside the iframe (no token) instead of an empty page or an unhandled error: a short "open this app from your ikas panel" message, or the store-name authorize form.

### 3.3 Post-callback navigation — the install-loop rule

The callback page receives `token`, `redirectUrl` (the Admin URL of the authorized app) and `authorizedAppId`.

- **MUST** branch on `window.self !== window.top`: inside the iframe → route **in place** (`router.replace('/dashboard')`); top-level → `window.location.replace(redirectUrl)`. Redirecting to the Admin URL from inside the Admin iframe loads a second Admin inside the frame, which re-opens the app, which authorizes again — an infinite install loop (§10 #5).
- **MUST** wrap any `useSearchParams()` consumer in `<Suspense>` (Next.js 15 requirement; without it the page fails at build or renders blank).
- **SHOULD** catch the sentinel/throw used to stop execution after a redirect so it does not surface as an unhandled rejection.

### 3.4 Other bridge calls

`closeApp()` (close the action modal), `openProductPage(id)` / `openOrderPage(id)`, `getDashboardLanguage()` (drive i18n from the panel's language), `startMerchantPayment(id)`, `reAuthorizeApp({redirectUri, state, scope})` (request extra scopes later). None are mandatory; when used, the same rules apply: only inside the iframe, never assume synchronous availability.

**Evidence.** `grep -rn "closeLoader"` should hit every page/hook that runs in the iframe; `window.self !== window.top` guards around bridge use and around the callback redirect; `<Suspense>` around `useSearchParams`; a non-iframe fallback render.

---

## 4. ikas interface entry (prerequisite #4)

The reviewer opens the app from the merchant panel after install. What they must find depends on the app's shape. Decide the shape in Pass 1 and audit against exactly one row.

| Shape | What MUST be true | Typical rejection |
|---|---|---|
| **(a) In-panel dashboard** — the app's UI lives in the iframe | The first screen renders real content after the loader closes (§3.1); navigation between app pages stays inside the iframe; the token flow works on every page | Loader never closes; blank page after loader; page redirects to a top-level URL and breaks out of the iframe |
| **(b) External dashboard** — the app's real UI is on the developer's own domain | The iframe shows a visible, clickable link/button to the external UI **plus** a short instruction (what to click, what credentials to use); the link opens in a new tab (`target="_blank"`, `rel="noopener"`); **DECLARE**: a working test account for reviewers is provided in the submission notes | "Redirects to their own system but gave us no test account" — rejected, then accepted after credentials were supplied |
| **(c) Action-only** — the app adds product/order actions (§7) and has no dashboard of its own | The iframe landing (or `/dashboard`) shows a sentence saying the app works through the actions on product/order pages and where to find them; the actions themselves run correctly (UI + logic) | Empty dashboard with no explanation; action opens but never closes or reports a result |
| **(d) Webhook-listener / headless** — backend-only | Still needs shape (b) or (c) text: a minimal page telling the merchant what the app does and where to manage it | Blank iframe |

- **MUST** — whichever shape: after `closeLoader()` the merchant sees *something actionable* within one screen. "Loader closes, then nothing" is a Blocker (§10 #13).
- **SHOULD** — shape (b) and (c) keep the explanatory copy editable/translatable (`getDashboardLanguage()`), TR and EN at minimum for a TR-region listing.

**Evidence.** Read the first component the panel renders (`/` → redirect target, `/dashboard`). For (b): an `<a href="https://…" target="_blank">` or a button with `window.open`. For (c): static or i18n copy mentioning actions. Note the shape in the report header.

---

## 5. Backend API contract

The browser never talks to ikas. It talks to the app's backend with the app JWT; the backend talks to ikas with the stored OAuth token.

### 5.1 Authenticated routes

- **MUST** — every route under the app's admin API namespace (`/api/ikas/*` in the starter; anything that is not `/api/oauth/*`, `/api/webhooks/*`, `/api/public/*` or a signed action endpoint) verifies the JWT (`getUserFromRequest`, a `withMerchant` wrapper, or equivalent) **before** any work, and returns 401 without it.
- **MUST** derive `authorizedAppId` / `merchantId` from the verified JWT (`aud` / `sub`), never from the request body or query.
- **MUST** load the ikas token by that `authorizedAppId` and refuse (404/403) when missing or marked uninstalled. One route that bypasses the shared wrapper and skips the `deleted` check is still a MUST miss — the window is the app JWT's lifetime.
- **SHOULD** require the server secrets at boot (`CLIENT_SECRET`, `SECRET_COOKIE_PASSWORD`): `verify(token, process.env.X || '')` and `password: … || ''` are §10 #15.
- **MUST NOT** accept an ikas access token from the client.

### 5.2 No browser → ikas calls

- **MUST NOT** call the **Admin** API (`api.myikas.com/api/v1/admin/graphql`, `/api/v2/admin/graphql`, the MCP endpoint) from client components or the storefront widget. All admin traffic goes through server routes.
- **Exempt:** the anonymous **Storefront** API (`api.myikas.com/api/sf/graphql`) called without credentials from a storefront widget — that is a public API by design. **SHOULD** still be documented in the README (what is fetched and that no token is sent) so a reviewer does not mistake it for #18.
- Authenticated merchant input on admin routes (a campaign price typed in the dashboard) is **not** §9's "client-supplied money" — it is the merchant's own data; validate it, don't reject it.

### 5.3 Response hygiene

- **MUST NOT** include tokens, secrets, or raw upstream error bodies that contain them in responses.
- **SHOULD** use one error envelope (`{ error: { statusCode, message } }`) and map upstream failures to it.
- **SHOULD** keep GraphQL documents in one place with generated types (the starter's `graphql-requests.ts` + codegen) — inline GraphQL strings in routes are §10 #11 (Uyarı, not Blocker).

**Evidence.** `grep -rln "getUserFromRequest\|withMerchant" src/app/api` covers every non-exempt route; `grep -rn "api.myikas.com" src` hits only server code / env; response builders never spread upstream `error.response.data` verbatim.

---

## 6. Webhooks

ikas delivers webhooks as `POST` with body `{ id, createdAt, scope, merchantId, authorizedAppId, data, signature }` where `data` is a **stringified** JSON payload and `signature = HMAC-SHA256(data, CLIENT_SECRET)` hex. The SDK exposes `validateIkasWebhookSignature(webhook, clientSecret)` and `getParsedIkasWebhookData(webhook, clientSecret)` (parses `data` only after a valid signature). Delivery is retried up to 3 times on any non-200 response, then dropped.

### 6.1 Every webhook endpoint

- **MUST** validate the body shape before touching it (zod `IkasWebhook` schema: all seven fields present and non-empty).
- **MUST** verify the signature with `validateIkasWebhookSignature` (or an equivalent HMAC over `data`) and return **401** on mismatch. Trusting `authorizedAppId` from an unsigned body lets anyone trigger cleanup for any merchant (§10 #2/#3).
- **MUST** fail closed when the secret is not configured: return 500, do nothing.
- **MUST** use status codes honestly: 400 invalid payload, 401 bad signature, 500 processing failure, 200 **only** when the work is done (or intentionally skipped). Returning 200 from a `catch` block hides real failures from ikas' retry (§10 #3).
- **SHOULD** be idempotent: record `webhook.id` (+ scope) and short-circuit duplicates with 200 — retries and at-least-once delivery will replay.
- **SHOULD** keep the handler fast; long work goes to a queue/background job and the endpoint returns 200 after enqueueing.

### 6.2 Uninstall / app-deleted

- **MUST** handle the uninstall scope. Official scope: `store/app/deleted`. Older templates also match `store/app/uninstalled` and `store/authorizedApp/deleted`; matching all three is harmless — matching **none** is a Blocker.
- **MUST** on uninstall: invalidate the stored token (delete or `deleted=true`), and undo what the app created in the merchant's store — storefront scripts (`deleteStorefrontJSScript`), campaigns, webhooks (`deleteWebhook`), anything else with a merchant-visible footprint. A script record that is **neutralized** (content blanked) rather than deleted because the delete mutation cannot target it is acceptable at **Uyarı** level: the footprint is inert, but the orphan record should be documented.
- **SHOULD** short-circuit with 200 when the token is already invalidated (a second uninstall delivery must not run cleanup with a dead token and 500 into ikas' retry).
- **MUST NOT** keep serving that merchant afterwards (§5.1 refuses uninstalled tokens).
- **SHOULD** register the webhook endpoint at install time if the app relies on it (`saveWebhook` with the needed scopes) — or document that it is configured in the Partner panel.

### 6.3 Other scopes

Business webhooks follow §6.1 unchanged. The SDK's `WebhookScope` enum (authoritative): `store/order/created`, `store/order/updated`, `store/product/created`, `store/product/updated`, `store/product/deleted`, `store/customer/created`, `store/customer/updated`, `store/customer/statusUpdated`, `store/customerFavoriteProducts/created`, `store/customerFavoriteProducts/updated`, `store/stock/created`, `store/stock/updated`, `store/app/deleted`, `store/app/payment`. A scope string not in this list is a typo until proven otherwise. Filter by `salesChannelIds` when the app is channel-scoped.

### 6.4 Plan / payment webhook (paid apps)

- **MUST** process `store/app/payment` only when `data.merchantAppPayment.status === 'PAID'`.
- **MUST** map `storeAppListingSubscriptionKey` to the app's own plan model; unknown keys are logged and ignored, not granted.
- **SHOULD** reconcile with `getMerchantLicence { appSubscriptions { authorizedAppId storeAppListingSubscriptionKey status deleted } }` on dashboard load; treat `status !== 'ACTIVE'` as no entitlement.

**Evidence.** Webhook route: zod schema with `signature`, `validateIkasWebhookSignature` import, secret guard returning 500, three distinct non-200 statuses, an uninstall scope constant, a cleanup sequence ending in token invalidation, optional dedupe table. Install path or docs: `saveWebhook` or a Partner-panel note.

---

## 7. App actions

Actions add buttons to Product Edit, Order Detail (general + per-package), and Order List (bulk). They are configured in the Partner panel (and mirrored in `ikas.config.json` `actions` for local dev). Two kinds:

### 7.1 iframe actions

- Opened with query params: `actionRunId`, `idList` (comma-separated ids), `userLocale` (`tr`/`en`); package actions add `orderId`, `orderPackageId`, `orderLineItemIds`, `quantityMap` (JSON string).
- **MUST** follow §3 in full: `closeLoader()` on mount, bridge token, backend call, `<Suspense>` for `useSearchParams`.
- **MUST** parse and validate the params (ids non-empty, `quantityMap` JSON-parsed defensively) and show a user-facing error when they are missing.
- **MUST** end with a visible result — success/failure state in the modal, and `AppBridgeHelper.closeApp()` when the flow is done — never leave the merchant in a modal that neither closes nor explains.
- **SHOULD** honour `userLocale` for copy.

### 7.2 API actions

- ikas POSTs `{ signature, authorizedAppId, merchantId, data }` (`data` stringified JSON).
- **MUST** verify `signature` = `HMAC-SHA256(data, CLIENT_SECRET)` before doing anything — the docs call this mandatory. Same rules as §6.1 (fail closed without secret, 401 on mismatch, honest status codes).
- **MUST** return promptly with a success/failure body; long work is queued.

**Evidence.** Action pages: `useSearchParams` + `closeLoader` + `closeApp`; API action route: HMAC check before business logic. `ikas.config.json` `actions` entries (if any) point at existing routes/pages.

---

## 8. Secrets & configuration

- **MUST** keep `CLIENT_SECRET`, `SECRET_COOKIE_PASSWORD`, DB URLs and any signing secret **out of** `NEXT_PUBLIC_*` — those are inlined into the browser bundle. Only `NEXT_PUBLIC_CLIENT_ID`, `NEXT_PUBLIC_DEPLOY_URL`, `NEXT_PUBLIC_GRAPH_API_URL`, `NEXT_PUBLIC_ADMIN_URL` belong there.
- **MUST** ignore `.env` and `.env*.local` in git; ship `.env.example` with placeholders only.
- **MUST NOT** log tokens, secrets, JWTs, signatures, or the raw OAuth callback query (`console.log('…params', …)` in a callback page is §10 #10).
- **MUST** keep `ikas.config.json` `oauthRedirectPath` equal to the real callback route path; the Partner-panel redirect URI is `<deployUrl><oauthRedirectPath>`.
- **MUST** strip trailing slashes from the deploy URL once, centrally (config module) — see §2.1.
- **SHOULD** require a 32+ char `SECRET_COOKIE_PASSWORD` (iron-session minimum) and fail fast at boot when required env is missing.
- **SHOULD** limit `allowedDevOrigins` / tunnel hosts to development builds.

**Evidence.** `.gitignore` contains `.env`; `.env.example` has no real values; `grep -rn "NEXT_PUBLIC_" src` shows no secret-looking names; `grep -rn "console.log" src | grep -i "token\|secret\|params"` is empty; config module normalizes the deploy URL.

---

## 9. Public / storefront endpoints (only if the app has them)

Apps that inject a storefront script or expose anonymous endpoints (`/api/public/*`) widen the attack surface. ikas has no app-proxy, so these calls come straight from shoppers' browsers to the app's domain.

- **MUST** authenticate the *merchant* on every public call with a per-merchant public key (or equivalent) and scope every read/write to that merchant's `authorizedAppId` — ownership filter on every id the client sends.
- **MUST NOT** accept money-bearing values from the client: prices, revenue, discount amounts, order totals. Anything that ends up in a metric or a decision is computed or verified server-side (a shipped app had client-supplied `value` inflating revenue reports — §10 #9).
- **MUST** rate-limit anonymous writes (per key + session at minimum).
- **SHOULD** set CORS deliberately (`*` is acceptable for truly public read endpoints; write endpoints should still be schema-validated and limited).
- **SHOULD** keep error bodies minimal on anonymous routes (no stack traces, no internal ids beyond what the client already has).
- **SHOULD** serve the storefront script with a short cache and remove it on uninstall (§6.2).
- **SHOULD** not display a metric the server never computes (a "revenue" tile that is always 0 because the client value is correctly dropped) — remove the tile or compute it from an authoritative source. Reviewers read a permanent zero as broken (§10 #13-adjacent).
- **SHOULD** narrow `postMessage` target origins in preview/sandbox iframes where the origin is known.

**Evidence.** Public route: key validation, `rateLimit(...)`, zod schema without price/value fields, ownership `Set`/`where` on merchant id; `next.config` headers for the script path.

---

## 10. Anti-pattern catalogue

Numbered so findings can cite them. Each was observed in a real app or a real review.

| # | Anti-pattern | Why it fails | Fix | Severity |
|---|---|---|---|---|
| 1 | `state = Math.random().toFixed(16)` | Guessable CSRF token | `randomBytes(32).toString('base64url')` | Blocker |
| 2 | `if (signature && !valid) reject` with no other check, or no signature/HMAC check at all on a signed input (callback, webhook, API action) | Attacker omits the field or forges the body | Verify when present (callback); always verify (webhooks, API actions) | Blocker |
| 3 | Webhook handler returns 200 from `catch`, or 200 for invalid/unsigned bodies | Hides failures from ikas retry; unsigned cleanup | 400 / 401 / 500 as in §6.1 | Blocker |
| 4 | Iframe page without `AppBridgeHelper.closeLoader()` | Panel spinner never disappears — reviewer sees a hung app | Mount-time `useEffect` with `closeLoader()` | Blocker |
| 5 | Callback page does `window.location.replace(adminUrl)` unconditionally | Inside the Admin iframe this nests a second Admin → infinite install loop | Branch on `window.self !== window.top`; route in place inside the iframe | Blocker |
| 6 | `redirect_uri = process.env.NEXT_PUBLIC_DEPLOY_URL + '/api/…'` with a trailing slash in the env | `//api/...` no longer matches the registered URI → 400 on token exchange | Normalize once in config | Uyarı (Blocker if reproduced) |
| 7 | `storeName = session.storeName || 'api'` | Session cookie is dropped in the iframe → code posted to the wrong host | Prefer the callback's `storeName` query param | Blocker |
| 8 | `catch { return 'Callback failed' }` with no upstream status/body | Developer cannot see why installs fail; reviewers see a dead end | Carry status + body (minus secrets) into the log and the response | Uyarı |
| 9 | Public endpoint schema accepts `value` / `price` / `amount` and writes it to metrics | Any shopper can inflate revenue or trigger discounts | Drop the field; compute server-side from an authoritative source | Blocker |
| 10 | `console.log('OAuth callback params:', params.toString())` or logging tokens/JWTs | Secrets in logs | Remove; log only non-sensitive ids | Blocker |
| 11 | Inline GraphQL strings inside route handlers | No types, drift from schema, hard to review | Central documents + codegen | Uyarı |
| 12 | External dashboard with no in-iframe link/instruction, or no reviewer test account | Reviewer cannot reach or log into the product | §4 shape (b): link + instruction + DECLARE credentials | Blocker |
| 13 | Loader closes, then an empty/blank screen (action-only app with no explanatory text, dashboard that renders nothing without data) | Reviewer assumes the app is broken | §4 shape (c) copy or an empty-state with next steps | Blocker |
| 14 | `useSearchParams()` outside `<Suspense>` | Next.js 15 build error / blank prerender | Wrap in `<Suspense>` | Blocker |
| 15 | JWT verified with an empty fallback secret (`process.env.X || ''`) and no boot-time env check | Misconfigured deploy accepts tokens signed with `''` | Fail fast when the secret is missing | Uyarı |
| 16 | Requesting write scopes the app never uses | Violates least-privilege guidance; reviewers ask why | Trim the scope list | Uyarı |
| 17 | Uninstall handler that does not invalidate the token / remove injected storefront scripts | App keeps acting on a store that removed it | §6.2 cleanup sequence | Blocker |
| 18 | Client component or widget calling `api.myikas.com` | Token exposure, CORS failure in production | Route through the backend | Blocker |
