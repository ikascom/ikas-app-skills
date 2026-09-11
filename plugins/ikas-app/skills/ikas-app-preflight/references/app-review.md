# app-review.md — Pre-review ruleset for ikas Admin Apps

The measuring stick for the `ikas-app-preflight` skill. Every finding the skill reports must cite a section here (§2.2, §6.1, §10 #4 …) or be labeled **kontrat dışı**.

## Contents

- §0 How to read this file (severity, source tags)
- §1 Publishing prerequisites
- §2 OAuth flow (authorize, callback, token lifecycle)
- §3 Iframe & App Bridge
- §4 ikas interface entry (prerequisite #4, app shapes)
- §5 Backend API contract
- §6 Webhooks (general, uninstall, payment)
- §7 App actions (iframe, API)
- §8 Secrets & configuration
- §9 Public / storefront endpoints
- §10 Anti-pattern catalogue
- §11 Scope ↔ operation mapping
- §12 Sources

---

## §0 How to read this file

### Severity

| Severity | Meaning | Test |
|---|---|---|
| **Blocker** | Must be fixed before submitting | One of three reasons, always stated in the finding: **review** — a documented publishing prerequisite or documented "zorunlu" rule is missed; **güvenlik** — an unauthenticated party can cause harm (forge a signed input, read/write another merchant's data, inflate a metric); **işlevsel** — the reviewer or the merchant will visibly hit a broken app (spinner never closes, blank screen, build fails, storefront widget cannot reach its endpoint) |
| **Uyarı** | Should be fixed; alone does not fail review | Hardening or robustness beyond what the docs require. The official starter may do it this way. |
| **Beyan gerekli** | Cannot be seen in code; developer confirms before submitting | DECLARE items in §1, §4, §6 |
| **Bilgi** | Context, no action required | — |
| **Kontrat dışı** | Would help; no rule requires it | Max 5 per report, kept separate |

**Calibration rule.** The official example apps (`ikascom/ikas-app-examples`: `starter-app`, `dashboard-actions-app`, `with-subscription-app`) must produce **zero review-Blockers**. If a rule would fail the official starter, it is at most an Uyarı unless it is an actual security hole (tagged **güvenlik**). Do not grade against a remembered template; grade against this file.

### Source tags

Every rule carries where it comes from. Cite the tag in the finding's "dayanak" column when the developer may push back.

| Tag | Meaning |
|---|---|
| `[docs:build-publish]` | builders.ikas.com › Admin App › Build & Publish |
| `[docs:auth-steps]` | builders.ikas.com › Admin App › Authorization › Authorization steps |
| `[docs:callback-api]` | builders.ikas.com › Admin App › Authorization › OAuth Callback API |
| `[docs:scope-changes]` | builders.ikas.com › Admin App › Authorization › Manage scope changes |
| `[docs:app-actions]` | builders.ikas.com › Admin App › App actions |
| `[docs:plans]` | builders.ikas.com › Admin App › Plans |
| `[docs:webhooks]` | builders.ikas.com › ikas SDK › Webhooks |
| `[docs:admin-app]` | builders.ikas.com › Admin App (overview; permissions list, least-privilege sentence) |
| `[sdk]` | `@ikas/admin-api-client` 2.x / `@ikas/app-helpers` 1.x type definitions and implementation |
| `[starter]` | Behaviour of the official example apps — a rule tagged only `[starter]` describes what the examples do, it is not a requirement |
| `[security]` | Standard web-security reasoning; not an ikas rule |
| `[observed]` | A rejection or fix reported from a real submission; not verifiable from docs — say so in the finding |

---

## §1 Publishing prerequisites `[docs:build-publish]`

ikas lists five prerequisites for publishing to the App Store. Only two are visible in code.

| # | Prerequisite (official wording) | How the skill checks it |
|---|---|---|
| 1 | "ikas Partner hesabınız oluşturulmuş ve uygulamanız bu hesaba eklenmiş olmalıdır" | **DECLARE** |
| 2 | Partner account is verified ("Doğrulama") | **DECLARE** |
| 3 | "Uygulamanın geliştirme süreci tamamlanmış ve ikas içerisindeki OAuth akışı doğru şekilde çalışıyor olmalıdır" | Code: §2 + §3 + §5 |
| 4 | "ikas Mağaza Yönetim paneli içerisinde uygulamanızın kullanabileceği ya da sizin uygulama arayüzünüze gidilebilecek yönlendirmeler olması" | Code: §4 (+ **DECLARE** when the UI is external) |
| 5 | "Uygulamanız en az 2 geliştirme mağazasında kurulmuş ve test edilmeye hazır durumda olmalıdır" | **DECLARE** — ask for the two store names |

Publishing flow facts to mention when relevant: paid apps must define plans before region selection and each region only accepts plans in that region's currency; "Herkese Açık" (public) listing goes through ikas review, "Gizli" (private link) does not; store-content fields (logo, name, summary, description, visuals) are mandatory; plan descriptions are mandatory for paid apps; reviewers reach the developer through the emergency e-mail/phone in Partner settings.

**Evidence.** The DECLARE rows go into the report's "Beyan gerekli" table verbatim. A README naming the production URL and the test stores is a good sign, not a requirement.

---

## §2 OAuth flow

Authorization Code flow. Two documented start scenarios `[docs:auth-steps]`: (A) the merchant installs from the ikas Admin and ikas redirects the browser to the app's **Setup Address** with `?storeName=`; (B) the merchant types the store name into the app's own form, which calls the app's authorize route. In both cases ikas redirects back to the **Redirect Address** registered in the Partner panel, which must equal `<deployUrl>` + `ikas.config.json.oauthRedirectPath`.

### §2.1 Authorize route

- **MUST** `[docs:auth-steps]` send `client_id`, `redirect_uri`, `scope`, `state`; the `redirect_uri` must be **byte-identical** to the Partner-panel Redirect Address ("birebir aynı olmalıdır"). A doubled slash from a trailing-slash deploy URL breaks this → **Blocker (işlevsel)** if the concatenation is unnormalized *and* the env can carry a trailing slash; otherwise §10 #6 Uyarı.
- **MUST** `[docs:admin-app]` request only the permissions the app uses: "Geliştiriciler, uygulamalarının ihtiyaç duyduğu minimum yetkileri seçmelidir." Unused scopes → **Uyarı** (§10 #16); see §11 for the mapping. Available permissions `[docs:admin-app]`: read/write × Campaigns, Customers, Inventories, Orders, Products; write × Storefront (`write_storefronts`). There is no `read_storefronts`.
- **MUST** request every scope the app's operations need — an operation whose family has no requested scope (`createStorefrontJSScript` without `write_storefronts`) fails at runtime with a permission error → **Uyarı** (the Partner-panel list is what ikas enforces and may differ from the code) **plus** the Beyan row "Partner panel izin listesi kodla aynı mı?". The skill cannot reproduce runtime calls; do not claim Blocker.
- **MUST** `[docs:auth-steps]` persist `state` and `storeName` server-side (iron-session in the starter) before redirecting.
- **SHOULD** `[security]` generate `state` with a CSPRNG. The official docs and starter use `Math.random().toFixed(16)` `[starter]`, so this is **Uyarı**, never a Blocker (§10 #1).
- **SHOULD** validate `storeName` (non-empty, host-safe) before building the OAuth URL with it.
- **SHOULD NOT** derive `redirect_uri` from the request `Host` header in production. The starter's `getRedirectUri` swaps the host only when the configured deploy URL is `localhost` `[starter]` — that gate is acceptable; a Host-header redirect URI without such a gate is **Uyarı**.

### §2.2 Callback route

ikas calls `GET <redirectPath>?code=…&storeName=…&signature=…&state=…` `[docs:auth-steps]`. `signature = HMAC-SHA256(code, clientSecret)` hex `[docs:auth-steps]` `[starter: TokenHelpers.validateCodeSignature]`.

- **MUST** validate the request shape — `code` required (`[starter]` uses zod).
- **MUST** `[docs:auth-steps]` verify `signature` when it is present. The documented pattern is `if (signature && !validateCodeSignature(code, signature, clientSecret)) → 400`. No signature check at all → **Uyarı** (the code exchange with ikas still fails for a forged code, so this is defence in depth, not a hole). A check that exists but compares with `===` → **Bilgi** (timing-safe compare is hardening; `[starter]` uses `===`).
- **MUST** `[docs:auth-steps]` compare `state` with the stored session state **when both exist**: `if (state && session.state && session.state !== state) → 400`. This is the documented pattern. The Admin iframe drops third-party cookies and scenario (A) installs never call the app's authorize route, so a callback without a session state is legitimate; rejecting it breaks installs. Flag **Uyarı** only when the callback checks *neither* state *nor* signature.
- **SHOULD** `[security]` clear `session.state` after a successful exchange (`[starter]` does `delete session.state`). Missing → **Uyarı**.
- **MUST** exchange the code with `OAuthAPI.getTokenWithAuthorizationCode` (or an equivalent POST to `https://<storeName>.myikas.com/api/admin/oauth/token`) using the same `redirect_uri` as the authorize step.
- `storeName` for the token endpoint: `session.storeName || 'api'` is the official pattern `[starter]` — `'api'` resolves to `https://api.myikas.com/api/admin/oauth`, the canonical token host `[sdk: OAuthAPI.getOAuthUrl, STORE_DOMAIN]`. It is **not** a bug. Reading `storeName` from the callback query first is fine; do not flag either way.
- **MUST** `[docs:callback-api]` `[starter]` resolve identity server-side after the exchange: `getMerchant` + `getAuthorizedApp`, and persist the token keyed by `authorizedAppId` with `merchantId`, `expireDate`, `scope`, `salesChannelId`.
- **MUST** `[starter]` `[security]` hand the browser a **short-lived app JWT** (`sub = merchantId`, `aud = authorizedAppId`, `exp`), never the ikas access/refresh token. ikas token in a browser-visible response, cookie or query → **Blocker (güvenlik)**.
- **SHOULD** surface the token-exchange failure reason (upstream status + body minus secrets) in logs; an opaque `Callback failed` is §10 #8 **Uyarı** (`[starter]` is opaque).
- **SHOULD NOT** log the raw callback query on the server. The starter's `/callback` **page** logs `params.toString()` in the *browser* console `[starter]` — that is the app's own short-lived JWT in the merchant's own console: **Uyarı** (§10 #10). Server-side logging of `access_token` / `refresh_token` / `CLIENT_SECRET` → **Blocker (güvenlik)**.

### §2.3 Token lifecycle

- **MUST** refresh the ikas access token server-side (`onCheckToken` → `OAuthAPI.refreshToken`) and write it back `[starter]`.
- **MUST NOT** expose access/refresh tokens to the browser (see §2.2).
- **SHOULD** `[security]` treat a token row for an uninstalled app as invalid (`deleted` flag or row removal, §6.2). The starter has no uninstall handling `[starter]`, so a missing check is **Uyarı**, not a Blocker; see §5.1.

**Evidence.** Authorize: `state` generation, session write, `getOAuthUrl`/`/authorize?`, `encodeURIComponent(redirect_uri)`. Callback: zod schema, `validateCodeSignature`/`createHmac`, `session.state` compare, `getTokenWithAuthorizationCode`, `getMerchant`/`getAuthorizedApp`, `AuthTokenManager.put`, `JwtHelpers.createToken`. Config: how the deploy URL is joined with the callback path.

---

## §3 Iframe & App Bridge `[sdk: @ikas/app-helpers AppBridgeHelper]`

After install the panel loads the app in an iframe and shows its own loading overlay until the app posts `CLOSE_LOADER` via `AppBridgeHelper.closeLoader()`. Bridge methods: `closeLoader`, `getNewToken`, `getAuthorizedAppId`, `getDashboardLanguage`, `getMeData`, `closeApp`, `openProductPage`, `openOrderPage`, `openWalletPage`, `startMerchantPayment`, `reAuthorizeApp({redirectUri, state, scope})`. They only work inside the iframe (`window.self !== window.top`).

### §3.1 Closing the loader

- **MUST** call `closeLoader()` on mount of every page the panel can load **as the first document**: the app URL / root `/` (Setup Address), every iframe **action** URL (§7.1), and `/callback` if it renders anything before redirecting. A page reached by client-side navigation (`router.push('/dashboard')` from a root that already closed the loader) inherits the closed state `[starter: root closes, dashboard does not]`. Missing on an entry page → **Blocker (işlevsel)** — the reviewer sees a spinner forever (§10 #4).
- **SHOULD** call it on every iframe page anyway (the official `dashboard-actions-app` AGENTS.md says "Always call `AppBridgeHelper.closeLoader()` … on page mount") — a hard reload on `/dashboard` otherwise hangs. Missing on a non-entry page → **Uyarı**.
- **SHOULD** call it before awaiting anything.

### §3.2 Token acquisition in the iframe `[starter: TokenHelpers.getTokenForIframeApp]`

- **MUST** get the browser token through the bridge: `getAuthorizedAppId()` → cached token in `sessionStorage` keyed by app id → check `exp` → otherwise `getNewToken()`.
- **MUST** send that token to the app's own backend (`Authorization: JWT <token>`), never to `api.myikas.com` (§5.2).
- **SHOULD** render something meaningful when opened outside the iframe (store-name form or "open from your ikas panel" text) instead of an empty page or an unhandled error. `[starter]` routes to `/authorize-store`.

### §3.3 Post-callback navigation

The callback page receives `token`, `redirectUrl` (the Admin URL `…/authorized-app/<id>`) and `authorizedAppId` and calls `window.location.replace(redirectUrl)` `[starter: TokenHelpers.setToken]`.

- In the documented install scenarios the callback lands **top-level**, so the starter's unconditional replace is correct there.
- **SHOULD** `[observed]` branch on `window.self !== window.top` and route in place (`router.replace('/dashboard')`) when inside the iframe — a callback that lands inside the Admin iframe (e.g. after `reAuthorizeApp`) would otherwise load a second Admin inside the frame. **Uyarı** (§10 #5); **Blocker (işlevsel)** only if the loop is reproduced.
- **MUST** wrap any `useSearchParams()` consumer in `<Suspense>` — Next.js 15 fails `next build` with "Missing Suspense boundary with useSearchParams" on statically prerendered pages `[starter wraps]`. Missing on a page that has no dynamic opt-out → **Blocker (işlevsel)**; if the page is dynamic (`export const dynamic = 'force-dynamic'`, cookies/headers read) → **Uyarı** (§10 #14).
- **SHOULD** catch the `'redirectUrl-called'` sentinel throw so it does not surface as an unhandled rejection `[starter throws it, and does not catch it]` → **Uyarı**.

**Evidence.** `closeLoader` in root/entry/action pages (directly or via a hook the page uses); `window.self !== window.top` guards; `<Suspense>` around `useSearchParams`; the non-iframe fallback.

---

## §4 ikas interface entry (prerequisite #4) `[docs:build-publish]`

"ikas Mağaza Yönetim paneli içerisinde uygulamanızın kullanabileceği ya da sizin uygulama arayüzünüze gidilebilecek yönlendirmeler olması." Decide the app's shape in Pass 1 and audit exactly one row.

| Shape | What MUST be true | Failure |
|---|---|---|
| **(a) In-panel dashboard** | First screen renders real content after the loader closes; navigation stays in the iframe; the token flow works on every page | Spinner never closes / blank after loader → Blocker (işlevsel) |
| **(b) External dashboard** | The iframe shows a visible, clickable link/button to the external UI plus a one-line instruction; opens in a new tab (`target="_blank" rel="noopener"`); **DECLARE**: a reviewer test account is in the submission notes | No link/instruction → Blocker (review, prerequisite #4). No test account → Beyan gerekli; `[observed]` a submission was held until credentials were supplied |
| **(c) Action-only** | The iframe landing (or `/dashboard`) explains that the app works through product/order actions and where to find them; the actions themselves complete (§7) | Empty dashboard with no explanation → Blocker (işlevsel, §10 #13) |
| **(d) Headless / webhook listener** | Same as (b) or (c): a minimal page telling the merchant what the app does and where to manage it | Blank iframe → Blocker (işlevsel) |

- **SHOULD** keep the explanatory copy translatable (`getDashboardLanguage()`), TR + EN at minimum for a TR-region listing → **Bilgi** when only one language exists.

**Evidence.** Read the first component the panel renders (`/` → its redirect target, `/dashboard`). (b): `<a href="https://…" target="_blank">` or `window.open`. (c)/(d): static or i18n copy about actions / the external product.

---

## §5 Backend API contract `[starter]` `[security]`

The browser talks to the app's backend with the app JWT; the backend talks to ikas with the stored OAuth token.

### §5.1 Authenticated routes

- **MUST** verify the app JWT (`getUserFromRequest`, a `withMerchant` wrapper, or equivalent) **before** any work on every route that is not OAuth, webhook, public, or a signed action endpoint, and return 401 without it. A route under the admin namespace with no verification → **Blocker (güvenlik)**.
- **MUST** derive `authorizedAppId` / `merchantId` from the verified JWT (`aud` / `sub`), never from the body or query → **Blocker (güvenlik)** when input wins over the JWT.
- **MUST NOT** accept an ikas access token from the client.
- **SHOULD** refuse a token row marked uninstalled (`deleted`) when loading the ikas token. `[starter]` only checks `!authToken`. Three cases, each **Uyarı**, reported **once** (list the routes in the evidence): (i) a shared wrapper checks `deleted` but some route bypasses it (F10); (ii) a shared wrapper exists but does not check `deleted` (F14); (iii) no wrapper, every route loads the token itself. Public key-based routes (§9) that load the token are part of the same finding.
- **SHOULD** require server secrets at boot: `verify(token, process.env.X || '')` and `password: … || ''` are §10 #15 **Uyarı** (`[starter]` uses `!` non-null assertions and no boot check).

### §5.2 No browser → ikas Admin API calls

- **MUST NOT** call the Admin API (`api.myikas.com/api/v1/admin/graphql`, `/api/v2/admin/graphql`, `/api/v2/admin/mcp`) from client components or a storefront widget → **Blocker (güvenlik)**: the only way to do it is to ship an ikas token to the browser (§10 #18).
- **Exempt:** the anonymous Storefront API (`api.myikas.com/api/sf/graphql`) from a storefront widget with no credentials. **SHOULD** be documented in the README so a reviewer does not mistake it for #18.
- Authenticated merchant input on admin routes (a price typed in the dashboard) is the merchant's own data — validate it; it is not §9's "client-supplied money".

### §5.3 Response hygiene

- **MUST NOT** include ikas tokens, secrets, or raw upstream error bodies that contain them in responses → **Blocker (güvenlik)**.
- **SHOULD** use one error envelope (`{ error: { statusCode, message } }`) `[starter]`.
- **SHOULD** keep GraphQL documents central with generated types (`graphql-requests.ts` + codegen) `[starter]`; inline GraphQL strings in route handlers are §10 #11 **Uyarı**.

**Evidence.** `grep -rln "getUserFromRequest\|withMerchant" src/app/api` vs the route list; `grep -rn "api.myikas.com" src` hits only server code / env; response builders never spread upstream `error.response.data`.

---

## §6 Webhooks

Delivery `[sdk: IkasWebhook]` `[docs:plans sample]`: `POST` with JSON body `{ id, createdAt, scope, merchantId, authorizedAppId, data, signature }` where `data` is a **stringified** JSON payload and `signature = HMAC-SHA256(data, CLIENT_SECRET)` hex `[sdk: validateIkasWebhookSignature]`. SDK helpers: `validateIkasWebhookSignature(webhook, clientSecret)`, `getParsedIkasWebhookData(webhook, clientSecret)` (parses only after a valid signature), `validateIkasWebhookMiddleware(clientSecret)` (401 on mismatch). ikas retries a non-200 response 3 times, then drops the delivery `[docs:webhooks]`.

### §6.1 Every webhook endpoint

- **MUST** `[security]` verify the signature (SDK helper or an equivalent HMAC over `data`) **before** acting on the payload, and return **401** on mismatch. Severity depends on what the handler does with an unverified body: it mutates state (invalidates tokens, deletes scripts, grants entitlement, writes metrics) → **Blocker (güvenlik)** — anyone can forge `authorizedAppId` and trigger it for any merchant (§10 #2). It only logs → **Uyarı** (`[starter: with-subscription-app/payment]` logs without verifying).
- **MUST** fail closed when `CLIENT_SECRET` is not configured (500, do nothing). Note `[sdk]` `validateIkasWebhookSignature` silently uses `''` when the secret is falsy — the guard has to be in the route.
- **SHOULD** validate the body shape before touching it (zod `IkasWebhook`: seven fields).
- **SHOULD** use status codes honestly: 400 invalid payload, 401 bad signature, 500 processing failure, 200 only when the work is done or intentionally skipped. `200` from a `catch` hides failures from ikas' retry (§10 #3 **Uyarı**; **Blocker (güvenlik)** when it also means an unsigned body was "accepted").
- **SHOULD** be idempotent — record `webhook.id` and short-circuit duplicates with 200; at-least-once delivery and the 3 retries will replay.
- **SHOULD** keep the handler fast; queue long work.
- **SHOULD** verify `webhook.authorizedAppId` belongs to this app before acting `[docs:plans]`: "Gelen webhook'un kendi uygulamanıza ait olduğunu doğrulamak için kullanın."

### §6.2 Uninstall / app-deleted

- Scope: `store/app/deleted` `[sdk: WebhookScope.APP_DELETED]`. Not on the docs' webhook page; the SDK enum is the source. Older templates also match `store/app/uninstalled` / `store/authorizedApp/deleted` — harmless, but only `store/app/deleted` is in the SDK.
- Handling uninstall is **not a documented publishing prerequisite** and `[starter]` has no webhook route at all. Missing → **Uyarı**, worded honestly: after removal the stored token stays usable by the app and anything the app injected into the store (storefront scripts, campaigns, webhooks) keeps running — merchants notice and report this. An app that injects a storefront script and never removes it → **Uyarı** with priority 1 (§10 #17).
- When handled: invalidate the token (delete or `deleted=true`), undo the footprint (`deleteStorefrontJSScript`, campaigns, `deleteWebhook`). A script record that is neutralized (content blanked) rather than deleted because the delete mutation cannot target it → acceptable, **Bilgi** if documented.
- **SHOULD** short-circuit with 200 when the token is already invalidated (second delivery must not run cleanup with a dead token).
- **SHOULD** register the endpoint at install with `saveWebhooks` (`[docs:webhooks]`: input = endpoint, scopes, optional `salesChannelIds`) or document that it is configured in the Partner panel → **DECLARE** row when the code never calls `saveWebhooks`.

### §6.3 Other scopes `[sdk: WebhookScope]`

`store/order/created`, `store/order/updated`, `store/product/created`, `store/product/updated`, `store/product/deleted`, `store/customer/created`, `store/customer/updated`, `store/customer/statusUpdated`, `store/customerFavoriteProducts/created`, `store/customerFavoriteProducts/updated`, `store/stock/created`, `store/stock/updated`, `store/app/deleted`, `store/app/payment`. A scope string outside this list is a typo until proven otherwise (the docs' webhook page lists only the first nine).

### §6.4 Plan / payment webhook (paid apps) `[docs:plans]`

- Scope `store/app/payment`. Documented payload: `data.merchantAppPayment.{ id, merchantId, storeAppId, storeAppListingSubscriptionId, storeAppListingSubscriptionKey, name, prices, status, type … }` plus `data.merchantLicence.appSubscriptions[]`. The official `with-subscription-app` example parses an older shape (`paymentStatus`, `subscriptionKey`) `[starter]` — accept either, but note the mismatch as **Bilgi** and point at the docs' shape.
- **MUST** `[docs:plans]` process only `status === 'PAID'` ("Yalnızca PAID olan kayıtları işleyin"). Granting on any status → **Blocker (güvenlik)** if unsigned, **Uyarı** if signed.
- **MUST** `[docs:plans]` map `storeAppListingSubscriptionKey` to the app's own plan model; unknown keys are logged and ignored, not granted.
- **SHOULD** `[docs:plans]` reconcile with `getMerchantLicence { appSubscriptions { authorizedAppId storeAppListingSubscriptionKey status deleted } }` when gating premium features: entitlement = `status === 'ACTIVE' && deleted === false`. Statuses: `ACTIVE`, `WILL_BE_REMOVED`, `REMOVED`.
- Trials: `[docs:plans]` the app tracks the install date itself and enforces expiry.

**Evidence.** Webhook route: schema, `validateIkasWebhookSignature`/`createHmac`, secret guard, distinct statuses, scope constant, cleanup sequence ending in token invalidation, dedupe. Install path or docs: `saveWebhooks` or a Partner-panel note.

---

## §7 App actions `[docs:app-actions]`

Actions add buttons to Product Edit (`/product/edit/:id` ⋮ menu), Order Detail (`/order/view/:id`, general + per-package), Order List (`/order` bulk menu). Two methods: **iframe** ("kullanıcı etkileşimi, çok adımlı akış") and **API** ("arka plan işlemi, toplu/otomasyon"). Configured in the Partner panel; mirrored in `ikas.config.json` `actions[] { name, method: "iframe"|"api", actionUrl, type }` for local dev `[starter: dashboard-actions-app]`.

### §7.1 iframe actions

- Query params: `actionRunId`, `idList` (comma-separated), `userLocale`; package actions add `orderId`, `orderPackageId`, `orderLineItemIds`, `quantityMap` (JSON string). Base URL is always `action.redirectUrl`.
- **MUST** follow §3: `closeLoader()` on mount (entry page → Blocker işlevsel if missing), bridge token, `<Suspense>` for `useSearchParams`.
- **MUST** parse the params defensively (ids non-empty, `quantityMap` JSON-parsed in try/catch) and show a user-facing error when missing → missing handling is **Uyarı**.
- **SHOULD** end with a visible result and `AppBridgeHelper.closeApp()` when done; a modal that neither closes nor explains → **Uyarı** (§10 #13-adjacent; **Blocker işlevsel** if the action is the app's only surface, shape (c)).
- **SHOULD** honour `userLocale` (`tr`/`en`).

### §7.2 API actions

- Body: `{ signature, authorizedAppId, merchantId, data }`, `data` stringified JSON; `signature = crypto.createHmac('sha256', secret).update(data, 'utf8').digest('hex')`.
- **MUST** verify `signature` before anything else — "API aksiyonlarında imza doğrulaması zorunludur" `[docs:app-actions]`. Missing → **Blocker (review + güvenlik)**. Same fail-closed / 401 / honest-status rules as §6.1.
- **MUST** return promptly with a success/failure body `[starter]`.

**Evidence.** Action pages: `useSearchParams` + `closeLoader` + `closeApp`. API action routes: HMAC check before business logic; secret guard (`[starter]` returns 500 when `CLIENT_SECRET` is unset). `ikas.config.json` `actions[]` URLs map to existing pages/routes.

---

## §8 Secrets & configuration

- **MUST** `[security]` keep `CLIENT_SECRET`, `SECRET_COOKIE_PASSWORD`, DB URLs and signing secrets **out of** `NEXT_PUBLIC_*` (inlined into the browser bundle) → **Blocker (güvenlik)**. Documented public vars `[docs:development]`: `NEXT_PUBLIC_GRAPH_API_URL`, `NEXT_PUBLIC_ADMIN_URL`, `NEXT_PUBLIC_CLIENT_ID`, `NEXT_PUBLIC_DEPLOY_URL`.
- **MUST** `[security]` keep real secrets out of git: `.env`, `.env.local`, `.env.production`, `.env.bak*`, `.env.backup` — a tracked file with real values → **Blocker (güvenlik)**; an untracked/unignored file with real values → **Uyarı** (one `git add .` away); an ignored file with real values → **Bilgi** (normal; note it ships if the deploy is built from this tree). `.env.example` ships placeholders only.
- **MUST NOT** log ikas tokens, `CLIENT_SECRET`, or webhook/action signatures server-side → **Blocker (güvenlik)**. Browser-console logging of the app JWT → **Uyarı** (§2.2).
- **MUST** `[docs:auth-steps]` keep `ikas.config.json` `oauthRedirectPath` equal to the real callback route path; the Partner-panel Redirect Address is `<deployUrl><oauthRedirectPath>`. Path with no matching route → **Blocker (işlevsel)**.
- **SHOULD** normalize the deploy URL once, centrally (§2.1, §10 #6).
- **SHOULD** require a 32+ char `SECRET_COOKIE_PASSWORD` (iron-session minimum) and fail fast at boot when required env is missing (§10 #15).
- **SHOULD** limit `allowedDevOrigins` / tunnel hosts to development.

**Evidence.** `.gitignore` patterns vs `git status --porcelain --ignored`; `.env.example` values; `grep -rn "NEXT_PUBLIC_" src`; `grep -rn "console\.\(log\|info\|debug\)" src | grep -i "token\|secret\|signature"`.

---

## §9 Public / storefront endpoints `[security]` (only if the app has them)

ikas has no app proxy: a storefront script's calls go straight from shoppers' browsers to the app's domain.

- **MUST** identify the merchant on every public call with a per-merchant public key (or equivalent) and scope every read/write to that merchant's `authorizedAppId` — ownership filter on every id the client sends. Missing → **Blocker (güvenlik)**.
- **MUST NOT** accept money-bearing values from the client (price, revenue, discount, total) into metrics or decisions → **Blocker (güvenlik)** when the value is stored or acted on; **Bilgi** when the schema drops it (§10 #9).
- **MUST** rate-limit anonymous writes (per key + session at minimum) → missing is **Uyarı**; **Blocker (güvenlik)** if the write is unbounded and merchant-visible (unlimited events per session inflating a dashboard).
- **MUST** answer CORS for the storefront widget: the widget runs on the merchant's domain (`*.myikas.com` or custom) and fetches the app's domain, so the public endpoint (or `next.config` `headers()` / middleware) must send `Access-Control-Allow-Origin`. Widget fetches the app origin and no CORS header exists anywhere → **Blocker (işlevsel)** — the widget silently renders nothing in production. `*` is acceptable for read endpoints.
- **SHOULD** keep anonymous error bodies minimal (no `error.message` from upstream/Prisma); serve the storefront script with a short cache and remove it on uninstall (§6.2); narrow `postMessage` origins where known.
- **SHOULD NOT** display a metric the server never computes (a revenue tile that is always 0) — reviewers read a permanent zero as broken.

**Evidence.** Public route: key validation, rate limiter, zod schema without money fields, ownership filter on merchant id; `next.config` headers for the script path.

---

## §10 Anti-pattern catalogue

Numbered so findings can cite them. Severity here is the default; §2–§9 wording wins when it is more specific.

| # | Anti-pattern | Why it matters | Fix | Severity | Source |
|---|---|---|---|---|---|
| 1 | `state = Math.random().toFixed(16)` | Predictable CSRF token | `randomBytes(32).toString('base64url')` | Uyarı | `[security]`; `[starter]` does this |
| 2 | Unsigned input acted on: no HMAC check on a webhook or API action that mutates state | Anyone can forge `authorizedAppId` and trigger it | Verify before work; 401 on mismatch | Blocker (güvenlik); API action also review `[docs:app-actions]` | §6.1, §7.2 |
| 3 | Webhook returns 200 from `catch` or for invalid/unsigned bodies | Hides failures from ikas retry; "accepts" forgeries | 400 / 401 / 500 as in §6.1 | Uyarı (Blocker güvenlik with #2) | §6.1 |
| 4 | Entry page (root, action URL) without `closeLoader()` | Panel spinner never disappears | Mount-time `useEffect` with `closeLoader()` | Blocker (işlevsel) | §3.1 |
| 5 | Callback page does `window.location.replace(adminUrl)` with no iframe branch | Nested Admin if the callback lands inside the iframe | Branch on `window.self !== window.top` | Uyarı | §3.3 `[observed]`; `[starter]` is unconditional |
| 6 | `redirect_uri = process.env.NEXT_PUBLIC_DEPLOY_URL + '/api/…'` unnormalized | Trailing slash in env → `//api/…` ≠ registered URI → token exchange 400 | Normalize once in config | Uyarı (Blocker işlevsel if reproduced) | §2.1 `[starter]` concatenates |
| 7 | *(retired — `'api'` storeName fallback is the canonical token host, see §2.2)* | | | | |
| 8 | `catch { return 'Callback failed' }` with no upstream status/body | Install failures are undiagnosable | Carry status + body (minus secrets) into the log | Uyarı | §2.2 `[starter]` |
| 9 | Public endpoint schema accepts `value`/`price`/`amount` and stores it | Any shopper inflates revenue / triggers discounts | Drop the field; compute server-side | Blocker (güvenlik) | §9 |
| 10 | Logging the callback query / tokens | Secrets in logs | Remove; log ids only | Browser JWT: Uyarı `[starter]`; server ikas token: Blocker (güvenlik) | §2.2, §8 |
| 11 | Inline GraphQL strings inside route handlers | No types, drift | Central documents + codegen | Uyarı | §5.3 |
| 12 | External dashboard with no in-iframe link/instruction | Reviewer cannot reach the product | §4 (b) link + instruction; test account → DECLARE | Blocker (review) | §4 `[docs:build-publish]` #4 |
| 13 | Loader closes, then a blank screen | Reviewer assumes the app is broken | §4 (c) copy or an empty state with next steps | Blocker (işlevsel) | §4 |
| 14 | `useSearchParams()` outside `<Suspense>` | `next build` fails on static pages | Wrap in `<Suspense>` | Blocker (işlevsel) if static; Uyarı if dynamic | §3.3 |
| 15 | JWT/session secret with `\|\| ''` fallback, no boot check | Misconfigured deploy accepts tokens signed with `''` | Fail fast at boot | Uyarı | §5.1, §8 |
| 16 | Requesting scopes the app never uses | Violates documented least-privilege guidance | Trim the list | Uyarı | §2.1 `[docs:admin-app]` |
| 17 | No uninstall handling while the app injects storefront scripts / campaigns | Footprint keeps running after removal | §6.2 cleanup | Uyarı (priority 1) | §6.2 `[starter]` has none |
| 18 | Client component or widget calling the ikas Admin API | Requires shipping an ikas token to the browser | Route through the backend | Blocker (güvenlik) | §5.2 |
| 19 | Test/debug route left in the tree (captures bodies to disk, echoes signatures, always 200) | Open unauthenticated endpoint in production | Delete or gate behind the same signature chain | Blocker (güvenlik) | §6.1, §8 `[observed]` |

---

## §11 Scope ↔ operation mapping (heuristic)

Requested scopes come from the app's config (`scope: 'read_orders,write_orders,…'` or a `REQUIRED_SCOPES` array). Operations are the `ikas.queries.X` / `ikas.mutations.X` calls in the codebase. Map by operation-name keyword; this is a heuristic for spotting **unused** scope families, not an authoritative permission table (ikas does not publish one).

| Family | Scope(s) | Operation-name keywords |
|---|---|---|
| orders | `read_orders`, `write_orders` | `order`, `package`, `fulfil`, `shipment` |
| products | `read_products`, `write_products` | `product`, `variant`, `category`, `brand`, `vendor`, `tag`, `attribute` |
| customers | `read_customers`, `write_customers` | `customer`, `address`, `customerGroup` |
| campaigns | `read_campaigns`, `write_campaigns` | `campaign`, `coupon`, `discount`, `promotion` |
| inventories | `read_inventories`, `write_inventories` | `stock`, `inventor`, `stockLocation` |
| storefront | `write_storefronts` (no read scope exists) | `storefront`, `script`, `theme`, `jsScript` |

Always allowed without a scope (identity): `getMerchant`, `getAuthorizedApp`, `getMerchantLicence`, `me`. A `totalStock` / stock field read through a **products** query counts as products, not inventories. A `read_*` scope with only `write_*` operations in its family (or vice versa) is **not** a finding — the SDK does not document read/write separation per operation. Only flag a family with **zero** operations.

---

## §12 Sources

- Build & Publish — https://builders.ikas.com/docs/app-development/admin-app/build-publish
- Authorization steps — https://builders.ikas.com/docs/app-development/admin-app/authorization/authorization-steps
- OAuth Callback API — https://builders.ikas.com/docs/app-development/admin-app/authorization/oauth-callback-api
- Manage scope changes — https://builders.ikas.com/docs/app-development/admin-app/authorization/manage-scope-changes
- App actions — https://builders.ikas.com/docs/app-development/admin-app/app-actions
- Plans — https://builders.ikas.com/docs/app-development/admin-app/plans
- Webhooks — https://builders.ikas.com/docs/app-development/ikas-sdk/webhooks
- Admin App overview (permissions) — https://builders.ikas.com/docs/app-development/admin-app
- Development environment — https://builders.ikas.com/docs/app-development/admin-app/development
- Official examples — https://github.com/ikascom/ikas-app-examples (`examples/starter-app`, `dashboard-actions-app`, `with-subscription-app`)
- SDK — `@ikas/admin-api-client` (`OAuthAPI`, `validateIkasWebhookSignature`, `getParsedIkasWebhookData`, `WebhookScope`, `APP_SCOPES`), `@ikas/app-helpers` (`AppBridgeHelper`)
