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
| `[partner-panel]` | Seen on the ikas Partner panel (partners.ikas.com, 2026-09). App sidebar: **Konfigürasyon** · **Aksiyonlar** · **Yayınlama** · **Planlar** · **İzin Verilen Mağazalar** · **Uygulama Performansı**. Konfigürasyon fields: *Uygulama Kimlik Bilgileri* (`client_id`, `client_secret`), *Uygulama Adres Bilgileri* (Kurulum Adresi, Yönlendirme Adresi), *Uygulama Yetkileri* (Tüm Yetkiler or per family Görüntüle/Düzenle), *Uygulama Adı ve İkon*, *Bildirim Adresi* (single Webhook Adresi). Yayınlama: listing state banner (*Gizli Olarak Yayında* = installable via Kurulum Adresi, not listed), regions grouped by currency (TRY › Türkiye; EUR › Avrupa; USD › Asya, Amerika, Afrika, Okyanusya) each with *Bölgedeki Aktif Planlar*, *Uygulama Bilgileri* (Kategori, Desteklenen Diller, listing languages + store preview). Planlar: plans defined here, then matched to regions under Yayınlama. İzin Verilen Mağazalar: table of dev stores (Mağaza Adı, Tür, Durum *Kullanımda*, İzin Verildiği Tarih) — prerequisite #5 lives here |
| `[schema]` | Verified by unauthenticated introspection of the live Admin API (`https://api.myikas.com/api/v2/admin/graphql`, `scripts/schema.py <name>`), 2026-09-13. Authoritative over `[mcp]` and `[docs]` when they disagree |
| `[mcp]` | Verified through the ikas admin MCP (`https://api.myikas.com/api/v2/admin/mcp`, `list` / `introspect`), 2026-09-11. The MCP exposes a curated subset (59 of 124 operations) and has mis-rendered at least one argument type (`deleteWebhook`) — for signatures prefer `[schema]` |
| `[security]` | Standard web-security reasoning; not an ikas rule |
| `[observed]` | Taken from real ikas review rejection messages (§12 › Rejections R1–R7, 2026). Cite the R-number in the finding; these are as binding as the docs |

---

## §1 Publishing prerequisites `[docs:build-publish]`

ikas lists five prerequisites for publishing to the App Store. Only two are visible in code.

| # | Prerequisite (official wording) | How the skill checks it |
|---|---|---|
| 1 | "ikas Partner hesabınız oluşturulmuş ve uygulamanız bu hesaba eklenmiş olmalıdır" | **DECLARE** |
| 2 | Partner account is verified ("Doğrulama") | **DECLARE** |
| 3 | "Uygulamanın geliştirme süreci tamamlanmış ve ikas içerisindeki OAuth akışı doğru şekilde çalışıyor olmalıdır" | Code: §2 + §3 + §5 |
| 4 | "ikas Mağaza Yönetim paneli içerisinde uygulamanızın kullanabileceği ya da sizin uygulama arayüzünüze gidilebilecek yönlendirmeler olması" | Code: §4 (+ **DECLARE** when the UI is external) |
| 5 | "Uygulamanız en az 2 geliştirme mağazasında kurulmuş ve test edilmeye hazır durumda olmalıdır" | **DECLARE** — ask for the two store names; `[partner-panel]` they appear under *İzin Verilen Mağazalar* with Durum *Kullanımda*. `[observed]` R7: review is **paused** until two dev stores are created and added to the allowed list (docs: `admin-app/allowed-app`) |
| — | `[observed]` R6: the app must offer "en az bir somut fonksiyon" and be "bağımsız olarak işlevsel bir ürün" — a shell whose only purpose is contacting the vendor / advertising a service is rejected outright | Code: an app with no Admin API operations, no actions, no webhooks and no storefront script, whose iframe only shows contact/marketing copy → **Blocker (review)** |
| — | `[observed]` R1, R3: for an external dashboard the reviewer needs a **working test account** sent to dev@ikas.com | **DECLARE** (§4 (b)) |

Publishing flow facts to mention when relevant `[docs:build-publish]` `[partner-panel]`: paid apps must define plans (*Planlar*) before region selection and each region only accepts plans in that region's currency — regions are grouped TRY › Türkiye, EUR › Avrupa, USD › Asya/Amerika/Afrika/Okyanusya, and every enabled region shows its *Bölgedeki Aktif Planlar*; "Herkese Açık" (public) listing goes through ikas review, "Gizli" (private link) does not; store-content fields (logo, name, summary, description, visuals) are mandatory; plan descriptions are mandatory for paid apps; reviewers reach the developer through the emergency e-mail/phone in Partner settings.

**Evidence.** The DECLARE rows go into the report's "Beyan gerekli" table verbatim. A README naming the production URL and the test stores is a good sign, not a requirement.

---

## §2 OAuth flow

Authorization Code flow. Two documented start scenarios `[docs:auth-steps]`: (A) the merchant installs from the ikas Admin and ikas redirects the browser to the app's **Setup Address** with `?storeName=`; (B) the merchant types the store name into the app's own form, which calls the app's authorize route. In both cases ikas redirects back to the **Redirect Address** registered in the Partner panel (*Uygulama Adres Bilgileri › Yönlendirme Adresi* `[partner-panel]`), which must equal `<deployUrl>` + `ikas.config.json.oauthRedirectPath`. The **Setup Address** is the panel's *Uygulama Adresi (Kurulum Adresi)* — the app root the Admin opens in the iframe.

### §2.1 Authorize route

- **MUST** `[docs:auth-steps]` send `client_id`, `redirect_uri`, `scope`, `state`; the `redirect_uri` must be **byte-identical** to the Partner-panel Redirect Address ("birebir aynı olmalıdır"). A doubled slash from a trailing-slash deploy URL breaks this → **Blocker (işlevsel)** if the concatenation is unnormalized *and* the env can carry a trailing slash; otherwise §10 #6 Uyarı.
- **MUST** `[docs:admin-app]` request only the permissions the app uses: "Geliştiriciler, uygulamalarının ihtiyaç duyduğu minimum yetkileri seçmelidir." Unused scopes → **Uyarı** (§10 #16); see §11 for the mapping. Available permissions `[docs:admin-app]` `[partner-panel]`: Görüntüle/Düzenle × Ürünler, Siparişler, Müşteriler, Kampanyalar, Envanter; Mağaza › Düzenle (`write_storefronts`). Mağaza › Görüntüle is pre-checked and disabled on the panel — store info is always readable, which is why there is no `read_storefronts`. "Tüm Yetkiler" ticks every box; an app submitted with it and a narrow scope string in code is the §2.1 mismatch case → Beyan row.
- **MUST** request every scope the app's operations need — an operation whose family has no requested scope (`createStorefrontJSScript` without `write_storefronts`) fails at runtime with a permission error → **Uyarı** (the Partner-panel list is what ikas enforces and may differ from the code) **plus** the Beyan row "Partner panel izin listesi kodla aynı mı?". The skill cannot reproduce runtime calls; do not claim Blocker.
- **MUST** `[docs:auth-steps]` persist `state` and `storeName` server-side (iron-session in the starter) before redirecting.
- **SHOULD** `[security]` generate `state` with a CSPRNG. The official docs and starter use `Math.random().toFixed(16)` `[starter]`, so this is **Uyarı**, never a Blocker (§10 #1).
- **SHOULD** validate `storeName` (non-empty, host-safe) before building the OAuth URL with it.
- **SHOULD NOT** derive `redirect_uri` from the request `Host` header in production. The starter's `getRedirectUri` swaps the host only when the configured deploy URL is `localhost` `[starter]` — that gate is acceptable; a Host-header redirect URI without such a gate is **Uyarı**.

### §2.2 Callback route

ikas calls `GET <redirectPath>?code=…&storeName=…&signature=…&state=…` `[docs:auth-steps]`. `[observed]` R4: an Admin-initiated install lands **directly on the Redirect Address with only `code` and `storeName`** (`…/oauth/callback?code=<uuid>&storeName=dev-…`) — no `state`, no session cookie from the app. R1 shows the same install ending in `?error=missing_code` when the callback expected something the Admin did not send. `signature = HMAC-SHA256(code, clientSecret)` hex `[docs:auth-steps]` `[starter: TokenHelpers.validateCodeSignature]`.

- **MUST** validate the request shape — `code` required (`[starter]` uses zod).
- **MUST** `[docs:auth-steps]` verify `signature` when it is present. The documented pattern is `if (signature && !validateCodeSignature(code, signature, clientSecret)) → 400`. No signature check at all → **Uyarı** (the code exchange with ikas still fails for a forged code, so this is defence in depth, not a hole). A check that exists but compares with `===` → **Bilgi** (timing-safe compare is hardening; `[starter]` uses `===`).
- **MUST** `[docs:auth-steps]` `[observed]` compare `state` with the stored session state **only when both exist**: `if (state && session.state && session.state !== state) → 400`. Scenario (A) installs arrive with no `state` and no app session (R4), so a callback that **requires** `state` or a session (`if (!state) → 400`, "install link has expired", `error=missing_code`) fails every install the reviewer performs → **Blocker (işlevsel)** — R4 was rejected for exactly this. Requiring `state` only when the *session* already holds one (stale state from an abandoned form attempt) → **Uyarı**. Checking *neither* state *nor* signature → **Uyarı**.
- **SHOULD NOT** require `state` merely because the session holds one (`if (session.state) { if (!state || …) → 400 }`) → **Uyarı** (see above). Do **not** downgrade to Bilgi on the theory that the root page always routes through the app's authorize route — R4 proves ikas can send the merchant straight to the callback.
- **MUST** `[observed]` R3 bind the install to the merchant automatically: after the exchange the token row is keyed by `authorizedAppId`/`merchantId` from `getAuthorizedApp`/`getMerchant`, and the app's own dashboard recognises that merchant without a second "connect ikas" step. An app whose external UI still shows the ikas integration as "not connected" after an Admin-initiated install, or asks the merchant to link manually → **Blocker (işlevsel)**. Code evidence: the callback persists the token and (for shape (b)) links it to the app's own account/tenant in the same request; no flow depends on the merchant pasting a store name or key later.
- **SHOULD** `[security]` clear `session.state` after a successful exchange (`[starter]` does `delete session.state`). Missing → **Uyarı**.
- **MUST** exchange the code with `OAuthAPI.getTokenWithAuthorizationCode` (or an equivalent POST to `https://<storeName>.myikas.com/api/admin/oauth/token`) using the same `redirect_uri` as the authorize step.
- `storeName` for the token endpoint: `session.storeName || 'api'` is the official pattern `[starter]` — `'api'` resolves to `https://api.myikas.com/api/admin/oauth`, the canonical token host `[sdk: OAuthAPI.getOAuthUrl, STORE_DOMAIN]`. It is **not** a bug. Reading `storeName` from the callback query first is fine; do not flag either way.
- **MUST** `[docs:callback-api]` `[starter]` resolve identity server-side after the exchange: `getMerchant` + `getAuthorizedApp`, and persist the token keyed by `authorizedAppId` with `merchantId`, `expireDate`, `scope`, `salesChannelId`. `[mcp]` `AuthorizedApp` fields: `id`, `storeAppId`, `partnerId`, `salesChannelId`, `scope: String!` (the **granted** scope string), `deleted`, `supportsMultipleInstallation`, `addedDate`.
- **SHOULD** `[mcp]` compare `getAuthorizedApp.scope` with the scope the code requested and log a mismatch — this is the only runtime check for the Partner-panel ↔ code drift in §2.1. Missing → **Bilgi** (section 4, not kontrat dışı — a § covers it).
- **SHOULD** `[security]` check `getAuthorizedApp.storeAppId === NEXT_PUBLIC_CLIENT_ID` and `!deleted` before persisting; a token for a different app or a deleted authorization must not be stored → missing is **Uyarı**.
- **MUST** `[starter]` `[security]` hand the browser a **short-lived app JWT** (`sub = merchantId`, `aud = authorizedAppId`, `exp`), never the ikas access/refresh token. ikas token in a browser-visible response, cookie or query → **Blocker (güvenlik)**.
- **SHOULD** surface the token-exchange failure reason (upstream status + body minus secrets) in logs; an opaque `Callback failed` is §10 #8 **Uyarı** (`[starter]` is opaque).
- **SHOULD NOT** log the raw callback query on the server. The starter's `/callback` **page** logs `params.toString()` in the *browser* console `[starter]` — that is the app's own short-lived JWT in the merchant's own console: **Uyarı** (§10 #10). Server-side logging of `access_token` / `refresh_token` / `CLIENT_SECRET` → **Blocker (güvenlik)**.

### §2.3 Token lifecycle

- **MUST** refresh the ikas access token server-side (`onCheckToken` → `OAuthAPI.refreshToken`) and write it back `[starter]`.
- **MUST NOT** expose access/refresh tokens to the browser (see §2.2).
- `[sdk]` `OAuthAPI.getTokenWithClientCredentials` (grant `client_credentials`) exists for merchant-owned private apps; an App Store listing that mints tokens this way instead of the authorization-code callback has no per-merchant `authorizedAppId` → **Bilgi** with the question "bu uygulama listelenecek mi, yoksa tek mağazaya özel mi?" (a private app is out of this ruleset's scope).
- **SHOULD** `[security]` treat a token row for an uninstalled app as invalid (`deleted` flag or row removal, §6.2). The starter has no uninstall handling `[starter]`, so a missing check is **Uyarı**, not a Blocker; see §5.1.

**Evidence.** Authorize: `state` generation, session write, `getOAuthUrl`/`/authorize?`, `encodeURIComponent(redirect_uri)`. Callback: zod schema, `validateCodeSignature`/`createHmac`, `session.state` compare, `getTokenWithAuthorizationCode`, `getMerchant`/`getAuthorizedApp`, `AuthTokenManager.put`, `JwtHelpers.createToken`. Config: how the deploy URL is joined with the callback path.

---

## §3 Iframe & App Bridge `[sdk: @ikas/app-helpers AppBridgeHelper]`

After install the panel loads the app in an iframe and shows its own loading overlay until the app posts `CLOSE_LOADER` via `AppBridgeHelper.closeLoader()`. Bridge methods: `closeLoader`, `getNewToken`, `getAuthorizedAppId`, `getDashboardLanguage`, `getMeData`, `closeApp`, `openProductPage`, `openOrderPage`, `openWalletPage`, `startMerchantPayment`, `reAuthorizeApp({redirectUri, state, scope})`. They only work inside the iframe (`window.self !== window.top`).

### §3.1 Closing the loader

- **MUST** call `closeLoader()` on mount of every page the panel can load **as the first document**: the app URL / root `/` (Setup Address), every iframe **action** URL (§7.1), and `/callback` if it renders anything before redirecting. A page reached by client-side navigation (`router.push('/dashboard')` from a root that already closed the loader) inherits the closed state `[starter: root closes, dashboard does not]`. Missing on an entry page → **Blocker (işlevsel)** — the reviewer sees a spinner forever (§10 #4). `[observed]` R2, R3: rejected verbatim for "ikas arayüzünün sürekli yükleniyor durumunda kaldığı"; the reviewer's stated minimum is "en azından entegrasyonun başarıyla kurulduğunu belirten veya kullanıcıyı uygulamanın kendi arayüzüne yönlendiren kullanılabilir bir ekran", and they point at the `useBaseHomePage` hook in the docs.
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
| **(b) External dashboard** | The iframe shows a visible, clickable link/button to the external UI plus a one-line instruction ("kurulum tamamlandı, panele git"); opens in a new tab (`target="_blank" rel="noopener"`); the external UI already knows the merchant (§2.2 R3); **DECLARE**: a reviewer test account for the external UI is sent to dev@ikas.com | No link/instruction → Blocker (review, prerequisite #4). No test account → Beyan gerekli; `[observed]` R1: "test hesabı oluşturup dev@ikas.com iletmeniz gerekmektedir" — review does not proceed without it |
| **(c) Action-only** | The iframe landing (or `/dashboard`) explains that the app works through product/order actions and where to find them; the actions themselves complete (§7) | Empty dashboard with no explanation → Blocker (işlevsel, §10 #13) |
| **(d) Headless / webhook listener** | Same as (b) or (c): a minimal page telling the merchant what the app does and where to manage it | Blank iframe → Blocker (işlevsel) |

- **SHOULD** keep the explanatory copy translatable (`getDashboardLanguage()`), TR + EN at minimum for a TR-region listing → **Bilgi** when only one language exists.

**Evidence.** Read the first component the panel renders (`/` → its redirect target, `/dashboard`). (b): `<a href="https://…" target="_blank">` or `window.open`. (c)/(d): static or i18n copy about actions / the external product.

---

## §5 Backend API contract `[starter]` `[security]`

The browser talks to the app's backend with the app JWT; the backend talks to ikas with the stored OAuth token.

### §5.1 Authenticated routes

- **MUST** verify the app JWT (`getUserFromRequest`, a `withMerchant` wrapper, or equivalent) **before** any work on every route that is not OAuth, webhook, public, or a signed action endpoint, and return 401 without it. A route under the admin namespace with no verification → **Blocker (güvenlik)**.
- **Exempt from the JWT rule** (report as **Bilgi**, not §5.1): a health check that touches no merchant data (`SELECT 1`, static `{ ok: true }`); an operator endpoint gated by a server-side bearer token compared with `timingSafeEqual` and disabled when the env is unset (metrics, ops). Anything that reads or writes a merchant row without a JWT stays a **Blocker (güvenlik)**.
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

**Evidence.** `grep -rln "getUserFromRequest\|withMerchant" src/app/api` vs the route list — and open the guard itself: a `getUserFromRequest` that already checks the installation is `ACTIVE` and the token row is not `deleted` covers every route that calls it, so the `deleted` Uyarı is not raised; `grep -rn "api.myikas.com" src` hits only server code / env; response builders never spread upstream `error.response.data`.

---

## §6 Webhooks

Delivery `[sdk: IkasWebhook]` `[docs:plans sample]`: `POST` with JSON body `{ id, createdAt, scope, merchantId, authorizedAppId, data, signature }` where `data` is a **stringified** JSON payload and `signature = HMAC-SHA256(data, CLIENT_SECRET)` hex `[sdk: validateIkasWebhookSignature]`. SDK helpers: `validateIkasWebhookSignature(webhook, clientSecret)`, `getParsedIkasWebhookData(webhook, clientSecret)` (parses only after a valid signature), `validateIkasWebhookMiddleware(clientSecret)` (401 on mismatch). ikas retries a non-200 response 3 times, then drops the delivery `[docs:webhooks]`.

### §6.1 Every webhook endpoint

- **MUST** `[security]` verify the signature (SDK helper or an equivalent HMAC over `data`) **before** acting on the payload, and return **401** on mismatch. Severity depends on what the handler does with an unverified body: it mutates state (invalidates tokens, deletes scripts, grants entitlement, writes metrics) → **Blocker (güvenlik)** — anyone can forge `authorizedAppId` and trigger it for any merchant (§10 #2). It only logs → **Uyarı** (`[starter: with-subscription-app/payment]` logs without verifying).
- **MUST** fail closed when `CLIENT_SECRET` is not configured (500, do nothing). Note `[sdk]` `validateIkasWebhookSignature` silently uses `''` when the secret is falsy — the guard has to be in the route. `[sdk]` The helper compares with `===`, not `timingSafeEqual`; a hand-rolled `timingSafeEqual` is fine and slightly better, never a finding either way.
- **SHOULD** validate the body shape before touching it (zod `IkasWebhook`: seven fields).
- **SHOULD** use status codes honestly: 400 invalid payload, 401 bad signature, 500 processing failure, 200 only when the work is done or intentionally skipped. `200` from a `catch` hides failures from ikas' retry (§10 #3 **Uyarı**; **Blocker (güvenlik)** when it also means an unsigned body was "accepted").
- **SHOULD** be idempotent — record `webhook.id` and short-circuit duplicates with 200; at-least-once delivery and the 3 retries will replay.
- **SHOULD** keep the handler fast; queue long work.
- **SHOULD** verify `webhook.authorizedAppId` belongs to this app before acting `[docs:plans]`: "Gelen webhook'un kendi uygulamanıza ait olduğunu doğrulamak için kullanın."

### §6.2 Uninstall / app-deleted

- Scope: `store/app/deleted` `[sdk: WebhookScope.APP_DELETED]`. Not on the docs' webhook page; the SDK enum is the source. Older templates also match `store/app/uninstalled` / `store/authorizedApp/deleted` — harmless, but only `store/app/deleted` is in the SDK; when a handler lists them, one **Bilgi** line ("SDK'da yok, ölü dal") so the developer does not rely on them.
- Handling uninstall is **not a documented publishing prerequisite** and `[starter]` has no webhook route at all. Missing → **Uyarı**, worded honestly: after removal the stored token stays usable by the app and anything the app injected into the store (campaigns, webhooks) keeps running — merchants notice and report this.
- **Storefront apps are the exception** `[observed]` R5: "gerekli script'in uygulama kurulurken otomatik olarak eklenmesini ve uygulama kaldırıldığında yine otomatik olarak kaldırılmasını bekliyoruz" (docs: `storefront-events/hosting`). An app whose product runs on the storefront **MUST** call `createStorefrontJSScript` during install (callback or first dashboard load, not a manual button) and `deleteStorefrontJSScript` in the `store/app/deleted` handler. Script not added automatically → **Blocker (review)**; added but never removed → **Blocker (review)** (§10 #17).
- When handled: invalidate the token (delete or `deleted=true`), undo the footprint (`deleteStorefrontJSScript`, campaigns, `deleteWebhook`). Order matters: every Admin API cleanup call needs the token, so make them **before** the local invalidation and tolerate failure (the token may already be revoked when `store/app/deleted` arrives) — the local invalidation must still complete. `[schema]` `deleteStorefrontJSScript()` takes **no arguments** and removes the calling app's script(s); a script record that is neutralized (content blanked) instead → acceptable, **Bilgi** if documented.
- **SHOULD** short-circuit with 200 when the token is already invalidated (second delivery must not run cleanup with a dead token).
- `[partner-panel]` **`store/app/deleted` and `store/app/payment` are delivered to the Partner panel's *Bildirim Adresi › Webhook Adresi***, not to endpoints registered with `saveWebhooks`. Panel copy: "Ücretlendirmeyi ikas üzerinden yönetmeniz durumunda ödeme bildirimlerini, uygulamanız mağazadan silindiğinde ise silinme bildirimini alabilmeniz için Webhook adresinizi tanımlamanız gerekmektedir." One URL receives both scopes, so the handler must branch on `webhook.scope`. → always a **DECLARE** row: "Partner panel › Bildirim Adresi = `<deployUrl><uninstall/payment route>` mi?"
- **SHOULD** register data webhooks at install with `saveWebhooks` (`[docs:webhooks]` `[mcp]`: `WebhookInput { endpoint, scopes, salesChannelIds? }`). `[mcp]` The schema documents the valid scopes as exactly: `store/order/created`, `store/order/updated`, `store/product/created`, `store/product/updated`, `store/customer/created`, `store/customer/updated`, `store/customerFavoriteProducts/created`, `store/customerFavoriteProducts/updated`, `store/stock/created`, `store/stock/updated` — **`store/app/deleted` and `store/app/payment` are not accepted by `saveWebhooks`**; they come only through the Partner-panel *Bildirim Adresi*. `endpoint` **must be `https`**; plain `http` and private/reserved IP ranges are rejected → an install path that calls `saveWebhooks` with a `localhost`/`http` deploy URL fails; guard it (`[starter]` none; test-app skips when not https) → missing guard is **Uyarı** (install breaks in local dev only, so never a Blocker).
- `[schema]` `deleteWebhook(scopes: [String!]!): Boolean!` removes this app's registrations by scope (flat list; the MCP `introspect` output renders it as `[[String!]]` — that rendering is wrong, the live schema and `[docs:webhooks]` agree on `[String!]!`). `[schema]` `listWebhook: [Webhook!]!` (no args) lists the app's registrations `{ id, scope, endpoint, deleted, createdAt, updatedAt }` — not exposed by the MCP, use it in code or via the docs' curl.
- **`saveWebhooks` at install without `deleteWebhook` on uninstall → Bilgi, not Uyarı.** Unverified whether ikas drops an authorization's registrations when the merchant removes the app (docs are silent; not testable from the MCP). What is documented: delivery to a non-200 endpoint stops after 3 retries `[docs:webhooks]`, and a data route that checks the installation status returns 200/ignored anyway. So the residual is at most a few extra deliveries, no security impact. Report it as Bilgi with the concrete suggestion (best-effort `deleteWebhook(scopes)` before token invalidation, `catch` and continue), and add the DECLARE row "kaldır → yeniden kur → `listWebhook`'ta eski kayıt kalıyor mu?" when the developer wants certainty. Escalate to Uyarı only when the data route does **not** check the installation status (a stale delivery then does real work).

### §6.3 Other scopes `[sdk: WebhookScope]`

`store/order/created`, `store/order/updated`, `store/product/created`, `store/product/updated`, `store/product/deleted`, `store/customer/created`, `store/customer/updated`, `store/customer/statusUpdated`, `store/customerFavoriteProducts/created`, `store/customerFavoriteProducts/updated`, `store/stock/created`, `store/stock/updated`, `store/app/deleted`, `store/app/payment`. A scope string outside this list is a typo until proven otherwise. `[mcp]` `saveWebhooks` accepts only ten of these (see §6.2); `store/product/deleted` and `store/customer/statusUpdated` exist in the SDK enum but not in the schema's documented list — treat as **Bilgi** if used.

### §6.4 Plan / payment webhook (paid apps) `[docs:plans]`

- Scope `store/app/payment`, delivered to the Partner-panel *Bildirim Adresi* (§6.2) `[partner-panel]`. Documented payload: `data.merchantAppPayment.{ id, merchantId, storeAppId, storeAppListingSubscriptionId, storeAppListingSubscriptionKey, name, prices, status, type … }` plus `data.merchantLicence.appSubscriptions[]`. The official `with-subscription-app` example parses an older shape (`paymentStatus`, `subscriptionKey`) `[starter]` — accept either, but note the mismatch as **Bilgi** and point at the docs' shape.
- `[mcp]` `MerchantAppPayment.status` ∈ `PAID | PAYMENT_FAILED | WAITING_FOR_PAYMENT`; `type` ∈ `ONE_TIME | SUBSCRIPTION | WALLET_ACTION`; `prices[] { period: MONTHLY|YEARLY|ONE_TIME, price }`; `storeAppListingSubscriptionKey` nullable. `listMerchantAppPayment(id, pagination)` reads the same records server-side. `[schema]` The object also carries `appPaymentKey` ("which type of licence", the older plan-key field), `authorizedAppId`, `storeAppId`, `merchantPaymentUrl`, `paymentDate` — and **no `merchantId`**; a handler that reads `merchantAppPayment.merchantId` relies on the webhook payload only, so treat a missing field as "ignore", not 4xx. `[sdk]` `IWebhookStoreAppPaymentData` types the payload a third way: `merchantAppPayment { _id, appPaymentKey, name, type, status, paymentDate, error }` + `merchantLicence { status, fromDate, toDate, appSubscriptions[] }`. Three shapes (docs / SDK type / old example) — accept whichever the app parses, key the plan on `storeAppListingSubscriptionKey ?? appPaymentKey`, and never grant from the payload alone (reconcile with `getMerchantLicence`).
- **MUST** `[docs:plans]` process only `status === 'PAID'` ("Yalnızca PAID olan kayıtları işleyin"). Granting on any status → **Blocker (güvenlik)** if unsigned, **Uyarı** if signed.
- **MUST** `[docs:plans]` map `storeAppListingSubscriptionKey` to the app's own plan model; unknown keys are logged and ignored, not granted.
- **SHOULD** `[docs:plans]` reconcile with `getMerchantLicence { appSubscriptions { authorizedAppId storeAppListingSubscriptionKey status deleted } }` when gating premium features: entitlement = `status === 'ACTIVE' && deleted === false`. `[mcp]` `MerchantSubscriptionStatusEnum = ACTIVE | WILL_BE_REMOVED | REMOVED`; useful extra fields: `storeAppId` (filter to this app), `lastPaymentDate`, `lastPaymentPeriodInDays` (compute the paid-through date), `lastPaymentPeriod`, `currency`, `merchantAppPaymentId`. `MerchantLicenceResponse.region ∈ AF|AN|AS|EU|OC|PL|TR|US` matches the Partner-panel regions.
- A payment webhook that grants **nothing** from the payload and only triggers a `getMerchantLicence` reconciliation does not need the `PAID` check — the licence query is the source of truth. **Bilgi**; F13 does not apply.
- **SHOULD** show the merchant a way forward when entitlement is missing (a "subscription required" screen pointing at the panel's *Yönet* button, or the plan page) instead of a silent 403/empty dashboard — a reviewer with no plan otherwise sees a broken app (§10 #13). Missing → **Uyarı**.
- Trials: `[docs:plans]` the app tracks the install date itself and enforces expiry.

**Evidence.** Webhook route: schema, `validateIkasWebhookSignature`/`createHmac`, secret guard, distinct statuses, scope constant, cleanup sequence ending in token invalidation, dedupe. Install path or docs: `saveWebhooks` or a Partner-panel note.

---

## §7 App actions `[docs:app-actions]`

Actions add buttons to Product Edit (`/product/edit/:id` ⋮ menu), Order Detail (`/order/view/:id`, general + per-package), Order List (`/order` bulk menu). Two methods: **iframe** ("kullanıcı etkileşimi, çok adımlı akış") and **API** ("arka plan işlemi, toplu/otomasyon"). Configured in the Partner panel › *Aksiyonlar* `[partner-panel]` ("kullanıcıların uygulamanız üzerinden ikas sayfalarında yapabileceği işlemler"); mirrored in `ikas.config.json` `actions[] { name, method: "iframe"|"api", actionUrl, type }` for local dev `[starter: dashboard-actions-app]`.

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
- **SHOULD** have a `.gitignore` covering `.env*` before the first commit. Not a git repository yet, or no `.gitignore` → **Uyarı** (the first `git add .` ships secrets and build output); report Git as *repo yok*. No `.env.example` → **Bilgi** (README must list the env contract).
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
| 17 | Storefront script not injected automatically at install, or not removed on `store/app/deleted` | Reviewer sees the app "eksik çalışıyor"; footprint keeps running after removal | `createStorefrontJSScript` in the install path, `deleteStorefrontJSScript` in the uninstall handler | Blocker (review) for storefront apps; Uyarı for campaigns/webhooks | §6.2 `[observed]` R5 |
| 20 | Callback requires `state` / an app session (`if (!state)`, "install link expired", `error=missing_code`) | Admin-initiated install arrives with `code`+`storeName` only → every reviewer install fails | `state && session.state && …` | Blocker (işlevsel) | §2.2 `[observed]` R4, R1 |
| 21 | External UI does not recognise the merchant after an Admin install (manual "connect ikas" step) | Reviewer sees integration "bağlanmadı" | Bind token → tenant in the callback | Blocker (işlevsel) | §2.2 `[observed]` R3 |
| 22 | App is a contact/marketing shell with no standalone function | Rejected as not a product | — (product decision; report it) | Blocker (review) | §1 `[observed]` R6 |
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

`[schema]` The live Admin API (`https://api.myikas.com/api/v2/admin/graphql`, introspection is unauthenticated) exposes **48 queries and 76 mutations**; the ikas MCP `list` shows a curated subset of 59. Family membership by name (full live list): **orders** `listOrder`, `listOrderTag`, `listOrderTransactions`, `listOrderSession`, `listAbandonedCheckouts`, `listBranch`, `listTerminal`, `createOrderWithTransactions`, `fulfillOrder`, `cancelFulfillment`, `cancelOrderLine`, `refundOrderLine`, `updateOrderPackageStatus`, `updateOrderAddresses`, `addOrderInvoice`, `removeOrderInvoice`, `downloadOrderInvoice`, `approvePendingOrderTransactions`, `addOrderTimelineEntry`, `addOrderTag`, `removeOrderTag`, `createOrderTag`, `updateOrderTag`, `deleteOrderTagList`; **products** `listProduct`, `listProductAttribute`, `listProductBrand`, `listProductTag`, `listCategory`, `listVariantType`, `createProduct`, `updateProduct`, `bulkUpdateProducts`, `updateProductAndVariantAttributes`, `updateProductSalesChannelStatus`, `deleteProductList`, `addVariantToProduct`, `removeVariantFromProduct`, `updateVariantPrices`, `saveVariantType`, `deleteVariantTypeList`, `createCategory`, `updateCategory`, `deleteCategoryList`, `createProductBrand`, `updateProductBrand`, `deleteProductBrandList`, `createProductTag`, `updateProductTag`, `deleteProductTagList`, `createProductAttribute`, `updateProductAttribute`, `deleteProductAttributeList`; **inventories** `saveVariantStocks`, `listStockLocation`, `listProductStockLocation`; **customers** `listCustomer`, `listCustomerAttribute`, `listCustomerGroup`, `listCustomerTag`, `createCustomer`, `updateCustomer`, `updateCustomerAndAddressAttributes`, `deleteCustomerList`, `addCustomerTimelineEntry`, `createCustomerGroup`, `updateCustomerGroup`, `deleteCustomerGroupList`, `createCustomerTag`, `updateCustomerTag`, `deleteCustomerTagList`; **campaigns** `listCampaign`, `listCoupon`, `createCampaign`, `updateCampaign`, `deleteCampaignList`, `addCouponsToCampaign`, `deleteCouponList`; **storefronts** `listStorefront`, `createStorefrontJSScript`, `updateStorefrontJSScript`, `deleteStorefrontJSScript`; **app / identity (no family)** `me`, `getAuthorizedApp`, `getMerchant`, `getMerchantLicence`, `getMerchantSettings`, `getAvailableSubscriptions`, `listMerchantAppPayment`, `createMerchantAppPayment`, `createOneTimeMerchantAppPayment`, `getAppDemoDay`, `saveWebhooks`, `deleteWebhook`, `listWebhook`, `addCustomTimelineEntry`, `getImportJobData`, `getImportJobDataList`; **settings / location (no family)** `getSalesChannel`, `listSalesChannel`, `updateSalesChannel`, `listPriceList`, `createPriceList`, `updatePriceList`, `deletePriceListList`, `listCurrency`, `listPaymentGateway`, `listCargoCompany`, `getGlobalTaxSettings`, `listGlobalTaxSettings`, `createGlobalTaxSettings`, `updateGlobalTaxSettings`, `deleteGlobalTaxSettingsList`, `listShippingSettings`, `listTaxSettings`, `createTaxSettings`, `updateTaxSettings`, `deleteTaxSettingsList`, `listCountry`, `listState`, `listCity`, `listDistrict`, `listTown`. An operation name not in this list is app-local (a codegen alias such as `listOrdersForInvoice`) — map it by its underlying query. Price-list / tax / settings mutations have no documented scope family; do not flag them under §10 #16.

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
- Allowed dev stores — https://builders.ikas.com/docs/app-development/admin-app/allowed-app
- Storefront script hosting — https://builders.ikas.com/docs/storefront-events/hosting
- Official examples — https://github.com/ikascom/ikas-app-examples

### Rejections (real review messages, 2026; app names removed)

| # | Reviewer's reason (paraphrased, key phrase verbatim) | Rule |
|---|---|---|
| R1 | External dashboard: "yönlendirilen adresine giriş yapabileceğimiz bir test hesabı oluşturup dev@ikas.com iletmeniz gerekmektedir"; first install ended at the app's login with `?error=missing_code` | §4 (b), §2.2 |
| R2 | "ikas arayüzünün sürekli yükleniyor durumunda kaldığı" — expects "en azından entegrasyonun başarıyla kurulduğunu belirten veya kullanıcıyı uygulamanın kendi arayüzüne yönlendiren kullanılabilir bir ekran"; links `useBaseHomePage` | §3.1, §4 |
| R3 | Same spinner + after signing up in the external UI "ikas entegrasyonunun bağlanmadığını, manuel olarak bağlamayı denediğimizde de işlemin başarılı olmadığını"; "ikas üzerinden başlatılan kurulum işleminin … mevcut mağaza ile otomatik olarak ilişkilendirilmesi gerekmektedir" | §2.2 auto-bind, §3.1, §4 (b) |
| R4 | Install redirected to `…/oauth/callback?code=…&storeName=dev-…` and showed "This install link has expired. Start again from ikas." | §2.2 state, §10 #20 |
| R5 | Storefront app: "kurulum sırasında storefront'a gerekli script'in eklenmediği"; expects automatic add on install and automatic removal on uninstall | §6.2, §10 #17 |
| R6 | "bağımsız olarak kullanılabilecek somut bir işlev sunmadığı; temel amacının … iletişim kurulmasını sağlamak ve sunduğunuz hizmeti tanıtmak" — not approved | §1, §10 #22 |
| R7 | Review paused: "2 adet geliştirme mağazası oluşturmanız ve bu mağazaları uygulamanızın izin verilen mağazalar listesine eklemeniz gerekmektedir" | §1 #5 |
- Admin API schema (live, authoritative) — `https://api.myikas.com/api/v2/admin/graphql` introspection, no token needed (`scripts/schema.py <operation|type>` prints a signature); tag `[schema]`
- Admin API via MCP — `https://api.myikas.com/api/v2/admin/mcp` (`list`, `introspect <operation>`): curated subset of 59 operations, argument types occasionally mis-rendered (`deleteWebhook`); tag `[mcp]`, verify against `[schema]` when a finding hinges on a signature
- SDK — `@ikas/admin-api-client` (`OAuthAPI`, `validateIkasWebhookSignature`, `getParsedIkasWebhookData`, `WebhookScope`, `APP_SCOPES`), `@ikas/app-helpers` (`AppBridgeHelper`)
