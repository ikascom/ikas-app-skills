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
| `[docs:development]` | builders.ikas.com › Admin App › Geliştirme Ortamı (env contract, `ikas.config.json`, `ikas app dev` tunnel) |
| `[docs:hosting]` | builders.ikas.com › Storefront Events › Hosting (`createStorefrontJSScript` input; "the full `script` tag must be used") |
| `[docs:scope-changes]` | builders.ikas.com › Admin App › Authorization › Manage scope changes |
| `[docs:app-actions]` | builders.ikas.com › Admin App › App actions |
| `[docs:plans]` | builders.ikas.com › Admin App › Plans |
| `[docs:webhooks]` | builders.ikas.com › ikas SDK › Webhooks |
| `[docs:admin-app]` | builders.ikas.com › Admin App (overview; permissions list, least-privilege sentence) |
| `[sdk]` | `@ikas/admin-api-client` 2.0.11 **and** 2.1.0 (npm `latest`, 2026-09; the starter pins `^2.0.11`, so a fresh install resolves to 2.1.0) / `@ikas/app-helpers` 1.0.10 type definitions **and** `dist`/`src` implementation (read, not assumed: `api/base.js`, `api/oauth/index.js`, `helpers/webhook-validate.js`, `app-bridge.ts`). 2.1.0 changes that matter here: `OAuthAPI.*` use `fetch` and return `OAuthResponse { data, status, ok }` instead of an Axios response (no throw on 4xx — a `catch (e) { e.response.status }` around the token exchange is dead code; check `res.ok`/`res.data`), `axios`/`qs`/`graphql-request` dropped from dependencies, `IWebhookStoreAppPaymentData` re-typed to the docs' payload shape (§6.4). Unchanged: `WebhookScope`, `APP_SCOPES`, `validateIkasWebhookSignature` (`===`, `clientSecret || ''`), `onCheckToken` before every request. `APP_SCOPES` has no `write_storefronts` member — TypeScript will not catch a missing storefront scope |
| `[starter]` | Behaviour of the official example apps — a rule tagged only `[starter]` describes what the examples do, it is not a requirement |
| `[partner-panel]` | Seen on the ikas Partner panel (partners.ikas.com, 2026-09). App sidebar: **Konfigürasyon** · **Aksiyonlar** · **Yayınlama** · **Planlar** · **İzin Verilen Mağazalar** · **Uygulama Performansı**. Konfigürasyon fields: *Uygulama Kimlik Bilgileri* (`client_id`, `client_secret`), *Uygulama Adres Bilgileri* (Kurulum Adresi, Yönlendirme Adresi), *Uygulama Yetkileri* (Tüm Yetkiler or per family Görüntüle/Düzenle), *Uygulama Adı ve İkon*, *Bildirim Adresi* (single Webhook Adresi). Yayınlama: listing state banner (*Gizli Olarak Yayında* = installable via Kurulum Adresi, not listed), regions grouped by currency (TRY › Türkiye; EUR › Avrupa; USD › Asya, Amerika, Afrika, Okyanusya) each with *Bölgedeki Aktif Planlar*, *Uygulama Bilgileri* (Kategori, Desteklenen Diller, listing languages + store preview). Planlar: plans defined here, then matched to regions under Yayınlama. İzin Verilen Mağazalar: table of dev stores (Mağaza Adı, Tür, Durum *Kullanımda*, İzin Verildiği Tarih) — prerequisite #5 lives here |
| `[schema]` | Verified by unauthenticated introspection of the live Admin API (`https://api.myikas.com/api/v2/admin/graphql`, `scripts/schema.py <name>`), 2026-09-13. **`/api/v1/admin/graphql` is a different schema** (v1: 63 queries / 69 mutations with `saveProduct`, `saveWebhook`, `saveStorefrontJSScript`, `listStorefrontJSScript`…; v2: 47 / 76 with `createProduct`/`updateProduct`, `saveWebhooks`, `createStorefrontJSScript`/`updateStorefrontJSScript`…). The official examples, the Postman collection and this ruleset's `[schema]`/§11 lists are **v2**; the SDK's `DEFAULT_API_VERSION` constant and the ikas.dev API reference are v1. Read `NEXT_PUBLIC_GRAPH_API_URL` first; for a v1 app run `schema.py --v1` and do not grade v1 names against §11. Authoritative over `[mcp]` and `[docs]` when they disagree |
| `[mcp]` | Verified through the ikas admin MCP (`https://api.myikas.com/api/v2/admin/mcp`, `list` / `introspect`), 2026-09-11. The MCP exposes a curated subset (59 of 124 operations) and has mis-rendered at least one argument type (`deleteWebhook`) — for signatures prefer `[schema]` |
| `[security]` | Standard web-security reasoning; not an ikas rule |
| `[observed]` | Taken from real ikas review rejection messages (§12 › Rejections R1–R7, 2026) or from a live experiment on a dev store (§12 › Experiments E1…). Cite the R-/E-number in the finding; these are as binding as the docs |

---

## §1 Publishing prerequisites `[docs:build-publish]`

ikas lists five prerequisites for publishing to the App Store. Only two are visible in code.

| # | Prerequisite (official wording) | How the skill checks it |
|---|---|---|
| 1 | "ikas Partner hesabınız oluşturulmuş ve uygulamanız bu hesaba eklenmiş olmalıdır" | **DECLARE** |
| 2 | Partner account is verified ("Doğrulama") | **DECLARE** |
| 3 | "Uygulamanın geliştirme süreci tamamlanmış ve ikas içerisindeki OAuth akışı doğru şekilde çalışıyor olmalıdır" | Code: §2 + §3 + §5 |
| 4 | "ikas Mağaza Yönetim paneli içerisinde uygulamanızın kullanabileceği ya da sizin uygulama arayüzünüze gidilebilecek yönlendirmeler olması" | Code: §4 (+ **DECLARE** when the UI is external) |
| 5 | "Uygulamanız en az 2 geliştirme mağazasında kurulmuş ve test edilmeye hazır durumda olmalıdır" | **DECLARE** — ask for the two store names; `[partner-panel]` they appear under *İzin Verilen Mağazalar*; Durum is *Kullanımda* while the app is installed there and flips to *Kullanımda Değil* after the merchant removes it (`[observed]` E3) — the row survives, the install does not. `[observed]` R7: review is **paused** until two dev stores are created and added to the allowed list (docs: `admin-app/allowed-app`) |
| — | `[observed]` R6: the app must offer "en az bir somut fonksiyon" and be "bağımsız olarak işlevsel bir ürün" — a shell whose only purpose is contacting the vendor / advertising a service is rejected outright | Code: an app with no Admin API operations, no actions, no webhooks and no storefront script, whose iframe only shows contact/marketing copy → **Blocker (review)** |
| — | `[observed]` R1, R3: for an external dashboard the reviewer needs a **working test account** sent to dev@ikas.com | **DECLARE** (§4 (b)) |

Publishing flow facts to mention when relevant `[docs:build-publish]` `[partner-panel]`: paid apps must define plans (*Planlar*) before region selection and each region only accepts plans in that region's currency — regions are grouped TRY › Türkiye, EUR › Avrupa, USD › Asya/Amerika/Afrika/Okyanusya, and every enabled region shows its *Bölgedeki Aktif Planlar*; "Herkese Açık" (public) listing goes through ikas review, "Gizli" (private link) does not; store-content fields (logo, name, summary, description, visuals) are mandatory; plan descriptions are mandatory for paid apps; reviewers reach the developer through the emergency e-mail/phone in Partner settings.

**Evidence.** The DECLARE rows go into the report's "Beyan gerekli" table verbatim. A README naming the production URL and the test stores is a good sign, not a requirement.

---

## §2 OAuth flow

Authorization Code flow. Two documented start scenarios `[docs:auth-steps]`: (A) the merchant installs from the ikas Admin and ikas opens the app's **Setup Address** — `[observed]` E1: inside the Admin iframe, as `GET /?storeName=…&timestamp=…&merchantId=…&signature=…&authorizedAppId=…` (`[sdk: AuthConnectParams]`, `signature = HMAC-SHA256(storeName + merchantId + timestamp, CLIENT_SECRET)`, `validateAuthSignature` also requires `timestamp` within 120 s). The `authorizedAppId` already exists at this point and the Admin already issues bridge tokens for it, **before the app has exchanged any OAuth code**; (B) the merchant types the store name into the app's own form, which calls the app's authorize route. In both cases ikas redirects back to the **Redirect Address** registered in the Partner panel (*Uygulama Adres Bilgileri › Yönlendirme Adresi* `[partner-panel]`), which must equal `<deployUrl>` + `ikas.config.json.oauthRedirectPath`. The **Setup Address** is the panel's *Uygulama Adresi (Kurulum Adresi)* — the app root the Admin opens in the iframe.

### §2.1 Authorize route

- **MUST** `[docs:auth-steps]` send `client_id`, `redirect_uri`, `scope`, `state`; the `redirect_uri` must be **byte-identical** to the Partner-panel Redirect Address ("birebir aynı olmalıdır"). `[observed]` E1: a mismatch is answered by the authorize endpoint itself with a bare JSON body `{"errors":[{"msg":"redirect_uri is not whitelisted","param":"redirect_uri","location":"query"}]}` — no redirect back, the merchant sees raw JSON. `[observed]` E1: `ikas app dev` (CLI banner 0.0.28; the docs only say the Cloudflare tunnel "8 saat boyunca aktif kalır" `[docs:development]`) whitelists its temporary tunnel for the session ("App URL routing" line in the CLI output; E3: when the app is installed on no store the CLI prints `No allowed merchants found` and its store search did not find an allowed-but-uninstalled dev store — install from the Admin's *Uygulama Kur* button instead), so a `NEXT_PUBLIC_DEPLOY_URL` that still points at an older tunnel produces exactly this error in dev; the starter's localhost host-swap only triggers when the env value contains `localhost`. A doubled slash from a trailing-slash deploy URL breaks this → **Blocker (işlevsel)** if the concatenation is unnormalized *and* the env can carry a trailing slash; otherwise §10 #6 Uyarı.
- **MUST** `[docs:admin-app]` request only the permissions the app uses: "Geliştiriciler, uygulamalarının ihtiyaç duyduğu minimum yetkileri seçmelidir." Unused scopes → **Uyarı** (§10 #16); see §11 for the mapping. Available permissions `[docs:admin-app]` `[partner-panel]`: Görüntüle/Düzenle × Ürünler, Siparişler, Müşteriler, Kampanyalar, Envanter; Mağaza › Düzenle (`write_storefronts`). Mağaza › Görüntüle is pre-checked and disabled on the panel — store info is always readable, which is why there is no `read_storefronts`. "Tüm Yetkiler" ticks every box; an app submitted with it and a narrow scope string in code is the §2.1 mismatch case → Beyan row.
- **MUST** request every scope the app's operations need — an operation whose family has no requested scope (`createStorefrontJSScript` without `write_storefronts`) fails at runtime with a permission error → **Uyarı** (the Partner-panel list is what ikas enforces and may differ from the code) **plus** the Beyan row "Partner panel izin listesi kodla aynı mı?". The skill cannot reproduce runtime calls; do not claim Blocker. `[observed]` E2, mechanism seen in E6: the app's authorize URL asked for 8 scopes, but the grant page ikas redirected to (`…/admin/authorized-app/grant?…&scope=…`) already carried the **Partner panel's list** (11 when the panel had *Tüm Yetkiler*, exactly 3 when the panel was cut to three) and `getAuthorizedApp.scope` matched the panel both times — `https://<store>.myikas.com/api/admin/oauth/authorize` **rewrites** the `scope` parameter to the panel list; the panel list is the grant. Runtime shape of a missing permission `[observed]` E6: `listCustomer` with no customers scope → `UNAUTHORIZED` with `extensions.deniedBy: "FEATURE"`, `requiredFeatures: [11, 12]` (not `LOGIN_REQUIRED`). So "unused scope" (§10 #16) must be judged against the Partner panel, and the code-side list only documents intent.
- **MUST** `[docs:auth-steps]` persist `state` and `storeName` server-side (iron-session in the starter) before redirecting.
- **SHOULD** `[security]` generate `state` with a CSPRNG. The official docs and starter use `Math.random().toFixed(16)` `[starter]`, so this is **Uyarı**, never a Blocker (§10 #1).
- **SHOULD** validate `storeName` (non-empty, host-safe) before building the OAuth URL with it.
- **SHOULD NOT** derive `redirect_uri` from the request `Host` header in production. The starter's `getRedirectUri` swaps the host only when the configured deploy URL is `localhost` `[starter]` — that gate is acceptable; a Host-header redirect URI without such a gate is **Uyarı**.

### §2.2 Callback route

ikas calls `GET <redirectPath>?code=…&storeName=…&signature=…&state=…` `[docs:auth-steps]`. `[observed]` E1: an app-initiated authorize (scenario B) came back as `?code=…&state=…&storeName=…` with **no `signature`** — treat `signature` as optional in both scenarios, exactly as the documented `signature && …` posture does. `[observed]` R4, **reproduced** E3: the Admin's *Uygulama Kur* button opens `…/admin/authorized-app/grant?client_id=…&redirect_uri=<Partner Redirect Address>&scope=<Partner-panel scope list>` (the app's own authorize route and Setup Address are **never** called), and *Uygulamayı Kur* lands **directly on the Redirect Address with only `code` and `storeName`** (`…/oauth/callback?code=<uuid>&storeName=dev-…`) — no `state`, no `signature`, no session cookie from the app. E3 also shows what happens when that callback fails: the app's 500 (`Callback failed`) did **not** stop ikas — the authorization was created, the app appeared under *Uygulamalarım* as installed, the Partner *İzin Verilen Mağazalar* row flipped to *Kullanımda*, and the next click opened the app in the iframe with a bridge token for an `authorizedAppId` the backend had never seen (§10 #23). A callback that fails therefore produces exactly the R2/R3 picture: "installed" in ikas, broken inside. The `authorizedAppId` is reused when the app later completes OAuth for the same store. R1 shows the same install ending in `?error=missing_code` when the callback expected something the Admin did not send. `signature = HMAC-SHA256(code, clientSecret)` hex `[docs:auth-steps]` `[starter: TokenHelpers.validateCodeSignature]`.

- **MUST** validate the request shape — `code` required (`[starter]` uses zod).
- **MUST** `[docs:auth-steps]` verify `signature` when it is present. The documented pattern is `if (signature && !validateCodeSignature(code, signature, clientSecret)) → 400`. No signature check at all → **Uyarı** (the code exchange with ikas still fails for a forged code, so this is defence in depth, not a hole). A check that exists but compares with `===` → **Bilgi** (timing-safe compare is hardening; `[starter]` uses `===`).
- **MUST** `[docs:auth-steps]` `[observed]` compare `state` with the stored session state **only when both exist**: `if (state && session.state && session.state !== state) → 400`. Scenario (A) installs arrive with no `state` and no app session (R4), so a callback that **requires** `state` or a session (`if (!state) → 400`, "install link has expired", `error=missing_code`) fails every install the reviewer performs → **Blocker (işlevsel)** — R4 was rejected for exactly this. Requiring `state` only when the *session* already holds one (stale state from an abandoned form attempt) → **Uyarı**. Checking *neither* state *nor* signature → **Uyarı**.
- **SHOULD NOT** require `state` merely because the session holds one (`if (session.state) { if (!state || …) → 400 }`) → **Uyarı** (see above). Do **not** downgrade to Bilgi on the theory that the root page always routes through the app's authorize route — R4 proves ikas can send the merchant straight to the callback.
- **SHOULD** `[observed]` E1 survive the "authorized but no token yet" state. Seen with a CLI-driven dev install (`ikas app dev` › install to store, "Geliştirici Modu"): the Admin created the `authorizedAppId`, opened the app root **inside the iframe** with the signed `AuthConnectParams`, and issued bridge JWTs for it before any OAuth code was exchanged. A root that treats "bridge token exists" as "installed" and pushes to `/dashboard` then hits 404s (`GET /api/ikas/* 404`, merchant row missing) and never starts OAuth. `[starter]` does the same (`use-base-home-page.ts` → `/dashboard`), so this is **Uyarı**, not a Blocker — the reviewer's App Store install (R4) arrives top-level through the callback and is unaffected. Fix: when the backend has no ikas token for `aud`, start authorize from the top window (`window.top.location = '/api/oauth/authorize/ikas?storeName=…'` or `reAuthorizeApp`), never an in-iframe `/authorize-store` page.
- **MUST** `[observed]` R3 bind the install to the merchant automatically: after the exchange the token row is keyed by `authorizedAppId`/`merchantId` from `getAuthorizedApp`/`getMerchant`, and the app's own dashboard recognises that merchant without a second "connect ikas" step. An app whose external UI still shows the ikas integration as "not connected" after an Admin-initiated install, or asks the merchant to link manually → **Blocker (işlevsel)**. Code evidence: the callback persists the token and (for shape (b)) links it to the app's own account/tenant in the same request; no flow depends on the merchant pasting a store name or key later.
- **SHOULD NOT** `[observed]` R10 ask the merchant to type store information (store name, `myikas.com` domain, merchant id) in the post-install signup form. The OAuth exchange already yields the identity (`getMerchant.storeName`, `merchantId`, `authorizedAppId`, `storeName` from the callback query) — prefill it read-only or store it server-side. If a typed value is kept, the app **MUST** compare it with the OAuth-bound merchant and reject a mismatch; otherwise a user can attach another store to their account. The reviewer flags this even without proof of a hole: "o mağaza ile kullanıcıyı eşleyerek bir kontrol mekanizması olduğunu varsayıyoruz, ancak bunun kontrollerinin eksiksiz olduğundan emin olmak için bu maddeyi ekledik" → typed store field with no server-side comparison → **Uyarı** (güvenlik in the evidence); typed field that is the *only* source of the binding (callback does not link) → Blocker (işlevsel) under R3.
- **SHOULD** `[security]` clear `session.state` after a successful exchange (`[starter]` does `delete session.state`). Missing → **Uyarı**.
- **MUST** exchange the code with `OAuthAPI.getTokenWithAuthorizationCode` (or an equivalent POST to `https://<storeName>.myikas.com/api/admin/oauth/token`) using the same `redirect_uri` as the authorize step.
- `storeName` for the token endpoint: `session.storeName || 'api'` is the official pattern `[starter]` — `'api'` resolves to `https://api.myikas.com/api/admin/oauth`, the canonical token host `[sdk: OAuthAPI.getOAuthUrl, STORE_DOMAIN]`. It is **not** a bug. Reading `storeName` from the callback query first is fine; do not flag either way.
- **MUST** resolve identity server-side after the exchange and persist the token keyed by `authorizedAppId`. Two documented ways, both fine: `[docs:callback-api]` runs `me` and stores `access_token`, `refresh_token`, `token_type`, `expires_in`, `expireDate`, `authorizedAppId` (from `me.id`), then redirects to `https://<storeName>.myikas.com/admin/authorized-app/<authorizedAppId>`; `[starter]` runs `getMerchant` + `getAuthorizedApp` and adds `merchantId`, `scope`, `salesChannelId`. Do not flag `me` as "missing getAuthorizedApp" — it returns the same `AuthorizedApp` fields (`id`, `scope`, `storeAppId`, `deleted`, `salesChannelId`, `partnerId`). `[mcp]` `AuthorizedApp` fields: `id`, `storeAppId`, `partnerId`, `salesChannelId`, `scope: String!` (the **granted** scope string), `deleted`, `supportsMultipleInstallation`, `addedDate`.
- **SHOULD** `[docs:scope-changes]` compare the granted scope (`getAuthorizedApp.scope` / `me.scope`) with the scope the code requested and log a mismatch — this is the only runtime check for the Partner-panel ↔ code drift in §2.1. The docs' `checkForReauthorize` sample does `if (meRes.data.scope !== config.scope) → reAuthorizeApp`; `[observed]` E2 shows the panel can grant a **superset** of the request, so a strict string inequality re-authorizes forever — compare as sets (every requested scope ⊆ granted) → strict `!==` with `reAuthorizeApp` behind it is **Uyarı**, missing check is **Bilgi** (section 4, not kontrat dışı — a § covers it).
- **SHOULD** `[security]` check `getAuthorizedApp.storeAppId === NEXT_PUBLIC_CLIENT_ID` and `!deleted` before persisting (and `isSuccess` first — an errored result has no `deleted` field, see §2.3); a token for a different app or a deleted authorization must not be stored → missing is **Uyarı**.
- **MUST** `[starter]` `[security]` hand the browser a **short-lived app JWT** (`sub = merchantId`, `aud = authorizedAppId`, `exp`), never the ikas access/refresh token. ikas token in a browser-visible response, cookie or query → **Blocker (güvenlik)**.
- **SHOULD** surface the token-exchange failure reason (upstream status + body minus secrets) in logs; an opaque `Callback failed` is §10 #8 **Uyarı** (`[starter]` is opaque).
- **SHOULD NOT** log the raw callback query on the server. The starter's `/callback` **page** logs `params.toString()` in the *browser* console `[starter]` — that is the app's own short-lived JWT in the merchant's own console: **Uyarı** (§10 #10). Server-side logging of `access_token` / `refresh_token` / `CLIENT_SECRET` → **Blocker (güvenlik)**.

### §2.3 Token lifecycle

- **MUST** refresh the ikas access token server-side (`onCheckToken` → `OAuthAPI.refreshToken`) and write it back `[starter]`. `[observed]` E4: a live refresh answers in 0.3 s with `expires_in: 14400` (4 h) and a **new** `refresh_token`; the **old refresh token keeps working** (a second refresh with it succeeded — not single-use) and the **old access token stays valid** after the refresh (no race between concurrent requests). Persist the new pair anyway; nothing says the old one is honoured forever. `[sdk]` `BaseGraphQLAPIClient` calls `onCheckToken(tokenData)` **before every request** and rebuilds the client when it returns a new `accessToken`; a refresh that blocks (E1: dead refresh token hangs > 30 s) blocks every Admin API call behind it — give the refresh a timeout, and skip `onCheckToken` in the uninstall handler. `[sdk]` 2.1.0 `OAuthAPI.refreshToken` / `getTokenWithAuthorizationCode` use `fetch` with no timeout and **do not throw on 4xx/5xx**: a failed refresh comes back as `{ ok: false, status, data: null }` (or `data` = error JSON) — code that only wraps the call in `try/catch` treats a 400 as success and writes `undefined` tokens; check `res.ok && res.data?.access_token` (2.0.11/axios threw on 4xx, so the two versions need different handling).
- `[sdk]` **The client never throws.** `query`/`mutate` return `APIResult { data, errors, error, isSuccess }`; GraphQL errors (including an expired or revoked token, which comes back as HTTP 200 + `errors[].extensions.code = 'LOGIN_REQUIRED'`, and permission errors) land in `errors`, transport failures in `error`. Code that reads `result.data?.x` without checking `isSuccess` treats every failure as "empty" — harmless for a list, **fail-open** when the field gates a decision: `getAuthorizedApp` → `deleted` undefined → `!deleted` passes; `getMerchantLicence` → `appSubscriptions` undefined → "no subscription" (fail-closed, fine). **SHOULD** check `isSuccess` (or `errors`) before using a result that drives install, entitlement or uninstall logic → missing is **Uyarı** on those paths, **Bilgi** elsewhere. `[starter]` checks `isSuccess` in the callback.
- **MUST NOT** expose access/refresh tokens to the browser (see §2.2).
- `[sdk]` `OAuthAPI.getTokenWithClientCredentials` (grant `client_credentials`) exists for merchant-owned private apps (`[observed]` E6: a Partner/App Store app's `client_id`+`client_secret` get **401** from the token endpoint with this grant, on both `<store>.myikas.com` and `api.myikas.com`); an App Store listing that mints tokens this way instead of the authorization-code callback has no per-merchant `authorizedAppId` → **Bilgi** with the question "bu uygulama listelenecek mi, yoksa tek mağazaya özel mi?" (a private app is out of this ruleset's scope).
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
- **SHOULD** render something meaningful when opened outside the iframe (store-name form or "open from your ikas panel" text) instead of an empty page or an unhandled error. `[starter]` routes to `/authorize-store`. `[sdk]` Every bridge call is `window.top.postMessage(event, '*')` with a listener that waits for the reply: outside the iframe `window.top === window`, nobody answers, and the promise **rejects on a timer** — `getAuthorizedAppId` after **5 s**, `getNewToken` / `getDashboardLanguage` / `getMeData` after **30 s** (`'Timed out getNewToken'`). A root that awaits `getTokenForIframeApp()` before rendering therefore shows a blank page for 5–35 s when opened top-level (the reviewer's first click on the Setup Address). Test `window.self !== window.top` **before** the first bridge call; awaiting first → **Uyarı**.
- `[sdk]` The bridge listener does not check `msg.origin`, and `getAuthorizedAppId` / `getMeData` `console.log` every message they see while waiting (the token reply included). Consequences: (i) anything the bridge returns (`getMeData`, `getAuthorizedAppId`, `getDashboardLanguage`) is untrusted client input — the server takes identity from the verified JWT only (§5.1), never from a bridge value forwarded in a body; (ii) browser-console logging of the app JWT is already done by the SDK, so an app that also logs it is at most **Uyarı** (§10 #10), never a Blocker.
- `[sdk]` Other bridge calls the ruleset expects to see: `startMerchantPayment(merchantPaymentId)` after `createMerchantAppPayment` (§6.4 paid flow), `openWalletPage()`, `reAuthorizeApp({ redirectUri, state, scope })` for scope changes `[docs:scope-changes]`, `closeApp()` at the end of an iframe action (§7.1), `openProductPage(id)` / `openOrderPage(id)` for deep links.

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
| **(b) External dashboard** | The iframe shows a visible, clickable link/button to the external UI plus a one-line instruction ("kurulum tamamlandı, panele git"); opens in a new tab (`target="_blank" rel="noopener"`); the external UI already knows the merchant (§2.2 R3); the link/instruction renders in **every re-entry state** (table below), not only right after install; **DECLARE**: a reviewer test account for the external UI is sent to dev@ikas.com | No link/instruction → Blocker (review, prerequisite #4). Link only on the first-install path, spinner/redirect loop on re-entry → Blocker (işlevsel) `[observed]` R8. No test account → Beyan gerekli; `[observed]` R1: "test hesabı oluşturup dev@ikas.com iletmeniz gerekmektedir" — review does not proceed without it |
| **(c) Action-only** | The iframe landing (or `/dashboard`) explains that the app works through product/order actions and where to find them; the actions themselves complete (§7) | Empty dashboard with no explanation → Blocker (işlevsel, §10 #13) |
| **(d) Headless / webhook listener** | Same as (b) or (c): a minimal page telling the merchant what the app does and where to manage it | Blank iframe → Blocker (işlevsel) |

- **SHOULD** keep the explanatory copy translatable (`getDashboardLanguage()`), TR + EN at minimum for a TR-region listing → **Bilgi** when only one language exists.

**Re-entry states for shape (b)** `[observed]` R8. The reviewer's dev stores usually already have the app installed, so the first thing they see is the **re-entry** path, not the install path: "ilk kurulum süreci haricinde her zaman sürekli yükleniyor durumunda kalmadığından emin olmayı ihmal etmeyin". The root must render a usable screen in each state — the reviewer tests all three:

| Merchant state when opening the app from the Admin | Root MUST render | Failure |
|---|---|---|
| Fresh install (no account in the external product yet) | Redirect to the external signup/login, or an in-iframe screen with the link | Spinner → Blocker (işlevsel) |
| Registered in the external product | Info line ("kurulum tamamlandı") + a link to the external UI. Reviewer wording: "en azından bir bilgi alanı ve uygulama sayfasına yönlendirecek bir link" | Spinner / blank → Blocker (işlevsel) R8; `[observed]` R2/R3/R8 all rejected on this exact state |
| Started the signup form on first install, abandoned it, came back later | Info line + a link **back to the registration form** ("yeniden kayıt formuna yönlendirecek bir link ve bilgi alanı") — not a silently logged-in panel, not a spinner | Spinner → Blocker (işlevsel); lands inside the panel without login → Uyarı (R9: the reviewer stops and asks whether the gating is store-specific) |

- **MUST NOT** `[observed]` R9 gate login/registration differently per store (allow-listed dev stores, seeded sessions, `if (storeName === 'dev-…') skip`). The reviewer found a dev store that skipped the login the install flow demands and paused the review with "bu test için belirli mağazalarda geçerli bir durum mu?" — every store, dev stores included, must go through the flow the reviewer will test → **Uyarı**, plus a Beyan row (the seed may live in the DB, not the code).

**Evidence.** Read the first component the panel renders (`/` → its redirect target, `/dashboard`). (b): `<a href="https://…" target="_blank">` or `window.open`, and the branches it takes when the tenant/account row exists, is incomplete, or is missing. (c)/(d): static or i18n copy about actions / the external product.

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
- **MUST** `[schema]` call operation names that exist in the API version the app targets (`NEXT_PUBLIC_GRAPH_API_URL`): a v2 app calling `saveProduct`/`saveWebhook`/`saveStorefrontJSScript`, or a v1 app calling `createProduct`/`saveWebhooks`/`createStorefrontJSScript`, fails with `GRAPHQL_VALIDATION_FAILED` on the first request → **Uyarı** (işlevsel — the scanner's §5.3 line names the operation; codegen against the same URL catches it at build time, hand-written documents do not). A name in neither list is a codegen alias, not a finding.
- **SHOULD** keep GraphQL documents central with generated types (`graphql-requests.ts` + codegen) `[starter]`; inline GraphQL strings in route handlers are §10 #11 **Uyarı**.

**Evidence.** `grep -rln "getUserFromRequest\|withMerchant" src/app/api` vs the route list — and open the guard itself: a `getUserFromRequest` that already checks the installation is `ACTIVE` and the token row is not `deleted` covers every route that calls it, so the `deleted` Uyarı is not raised; `grep -rn "api.myikas.com" src` hits only server code / env; response builders never spread upstream `error.response.data`.

---

## §6 Webhooks

Delivery `[sdk: IkasWebhook]` `[docs:plans sample]`: `POST` with JSON body `{ id, createdAt, scope, merchantId, authorizedAppId, data, signature }` where `data` is a **stringified** JSON payload and `signature = HMAC-SHA256(data, CLIENT_SECRET)` hex `[sdk: validateIkasWebhookSignature]`. SDK helpers: `validateIkasWebhookSignature(webhook, clientSecret)`, `getParsedIkasWebhookData(webhook, clientSecret)` (parses only after a valid signature), `validateIkasWebhookMiddleware(clientSecret)` (401 on mismatch). ikas retries a non-200 response 3 times, then drops the delivery `[docs:webhooks]`.

### §6.1 Every webhook endpoint

- **MUST** `[security]` verify the signature (SDK helper or an equivalent HMAC over `data`) **before** acting on the payload, and return **401** on mismatch. Severity depends on what the handler does with an unverified body: it mutates state (invalidates tokens, deletes scripts, grants entitlement, writes metrics) → **Blocker (güvenlik)** — anyone can forge `authorizedAppId` and trigger it for any merchant (§10 #2). It only logs → **Uyarı** (`[starter: with-subscription-app/payment]` logs without verifying).
- **MUST** fail closed when `CLIENT_SECRET` is not configured (500, do nothing). Note `[sdk]` `validateIkasWebhookSignature` silently uses `''` when the secret is falsy — the guard has to be in the route. `[sdk]` The helper compares with `===`, not `timingSafeEqual` (same in 2.0.11 and 2.1.0); a hand-rolled `timingSafeEqual` is fine and slightly better, never a finding either way.
- **SHOULD** validate the body shape before touching it (zod `IkasWebhook`: seven fields).
- **SHOULD** use status codes honestly: 400 invalid payload, 401 bad signature, 500 processing failure, 200 only when the work is done or intentionally skipped. `200` from a `catch` hides failures from ikas' retry (§10 #3 **Uyarı**; **Blocker (güvenlik)** when it also means an unsigned body was "accepted").
- **SHOULD** be idempotent — record `webhook.id` and short-circuit duplicates with 200; at-least-once delivery and the 3 retries will replay.
- **SHOULD** keep the handler fast; queue long work.
- **SHOULD** verify `webhook.authorizedAppId` belongs to this app before acting `[docs:plans]`: "Gelen webhook'un kendi uygulamanıza ait olduğunu doğrulamak için kullanın."

### §6.2 Uninstall / app-deleted

- Scope: `store/app/deleted` `[sdk: WebhookScope.APP_DELETED]`. Not on the docs' webhook page; the SDK enum is the source. Older templates also match `store/app/uninstalled` / `store/authorizedApp/deleted` — harmless, but only `store/app/deleted` is in the SDK; when a handler lists them, one **Bilgi** line ("SDK'da yok, ölü dal") so the developer does not rely on them.
- Handling uninstall is **not a documented publishing prerequisite** and `[starter]` has no webhook route at all. Missing → **Uyarı**, worded honestly: after removal the stored token stays usable by the app and anything the app injected into the store (campaigns, webhooks) keeps running — merchants notice and report this.
- **Storefront apps are the exception** `[observed]` R5: "gerekli script'in uygulama kurulurken otomatik olarak eklenmesini ve uygulama kaldırıldığında yine otomatik olarak kaldırılmasını bekliyoruz" (docs: `storefront-events/hosting`). `[docs:hosting]` `[observed]` E2: `CreateStorefrontJSScriptInput.scriptContent` with `contentType: SCRIPT` must be wrapped in `<script>…</script>` (docs: "the full `script` tag must be used") (`ARGUMENT_VALIDATION_ERROR` "Script content must be enclosed in <script> tags." otherwise) — an install path that sends bare JS fails unless the error is surfaced. An app whose product runs on the storefront **MUST** call `createStorefrontJSScript` during install (callback or first dashboard load, not a manual button) and `deleteStorefrontJSScript` in the `store/app/deleted` handler. Script not added automatically → **Blocker (review)**; added but never removed → **Blocker (review)** (§10 #17).
- When handled: invalidate the token (delete or `deleted=true`), undo the footprint (`deleteStorefrontJSScript`, campaigns, `deleteWebhook`). Order matters: every Admin API cleanup call needs the token, so make them **before** the local invalidation and tolerate failure (the token may already be revoked when `store/app/deleted` arrives) — the local invalidation must still complete. `[schema]` `[observed]` E2, E5: `deleteStorefrontJSScript()` takes **no arguments** and one call removes **every** script the app created (E5: two scripts created, v1 `listStorefrontJSScript` showed both with this `authorizedAppId`, one call, list empty); with nothing to delete it errors `error_messages.theme.storefront_sf_script_not_found` (code `STOREFRONT_SF_SCRIPT`) — treat that error as success in the uninstall handler. A handler that instead blanks the content with `updateStorefrontJSScript` ("neutralize") because it believes delete cannot target its script is working around a non-problem → **Bilgi**, suggest the plain delete.
- **SHOULD** short-circuit with 200 when the token is already invalidated (second delivery must not run cleanup with a dead token).
- `[partner-panel]` **`store/app/deleted` and `store/app/payment` are delivered to the Partner panel's *Bildirim Adresi › Webhook Adresi***, not to endpoints registered with `saveWebhooks`. Panel copy: "Ücretlendirmeyi ikas üzerinden yönetmeniz durumunda ödeme bildirimlerini, uygulamanız mağazadan silindiğinde ise silinme bildirimini alabilmeniz için Webhook adresinizi tanımlamanız gerekmektedir." One URL receives both scopes, so the handler must branch on `webhook.scope`. → always a **DECLARE** row: "Partner panel › Bildirim Adresi = `<deployUrl><uninstall/payment route>` mi?"
- **SHOULD** register data webhooks at install with `saveWebhooks` (`[docs:webhooks]` `[mcp]`: `WebhookInput { endpoint, scopes, salesChannelIds? }`). `[mcp]` The schema documents the valid scopes as exactly: `store/order/created`, `store/order/updated`, `store/product/created`, `store/product/updated`, `store/customer/created`, `store/customer/updated`, `store/customerFavoriteProducts/created`, `store/customerFavoriteProducts/updated`, `store/stock/created`, `store/stock/updated` — **`store/app/deleted` and `store/app/payment` are not accepted by `saveWebhooks`**; they come only through the Partner-panel *Bildirim Adresi*. `[schema]` `endpoint` **must be `https`** — the live `WebhookInput.endpoint` description says plain `http` and private/reserved IP ranges are rejected (the docs page only says "HTTPS kullanmanız önerilir"; the schema wins — `[observed]` E5: `http://example.com/x` → `ARGUMENT_VALIDATION_ERROR`) → an install path that calls `saveWebhooks` with a `localhost`/`http` deploy URL fails; guard it (`[starter]` none; test-app skips when not https) → missing guard is **Uyarı** (install breaks in local dev only, so never a Blocker).
- `[schema]` `deleteWebhook(scopes: [String!]!): Boolean!` removes this app's registrations by scope (flat list; the MCP `introspect` output renders it as `[[String!]]` — that rendering is wrong, the live schema and `[docs:webhooks]` agree on `[String!]!`). `[schema]` `listWebhook: [Webhook!]!` (no args) lists the app's registrations `{ id, scope, endpoint, deleted, createdAt, updatedAt }` — not exposed by the MCP, use it in code or via the docs' curl.
- **`saveWebhooks` at install without `deleteWebhook` on uninstall → not a finding.** `[observed]` E1 (live test, 2026-09-13, dev store): registrations made with `saveWebhooks` were gone from `listWebhook` immediately after the merchant removed the app and were still gone after re-install under the new `authorizedAppId`. ikas drops an authorization's webhooks itself. Do not ask for a `deleteWebhook` call in the uninstall handler; mention it only as optional hygiene in section 5. (`deleteWebhook(scopes: ["store/order/created", …])` with the flat list returns `true` — verified the same day.)
- **The access token is NOT revoked on uninstall** `[observed]` E1, **reproduced** E3 (second uninstall, T+0 and T+39 min, even after the app was re-installed under a new `authorizedAppId`): the old token still answered `listProduct` and `listStorefront` (data reads work until `expires_in` runs out — 4 h); `getAuthorizedApp` → `null`, `me` / `getMerchant` → `UNAUTHORIZED`; **writes** through the app namespace (`saveWebhooks`, `deleteWebhook`) → `APP_NOT_FOUND`. A refresh with the old `refresh_token` does not fail fast — the token endpoint hung > 30 s twice. Consequences: (i) invalidating the stored token locally on `store/app/deleted` is the **only** thing that stops the app from reading a merchant's data after removal — §5.1's `deleted` check moves from hardening to the real control (still **Uyarı** by the calibration rule, but priority 1 among Uyarılar); (ii) an uninstall handler that calls the Admin API through `onCheckToken` may block on the refresh — do cleanup calls with the existing access token only and give them a timeout; (iii) a webhook route that identifies the merchant by `authorizedAppId` must also check its own installation status, because `getAuthorizedApp` is the only server-side signal and it costs a round-trip.

### §6.3 Other scopes `[sdk: WebhookScope]`

`store/order/created`, `store/order/updated`, `store/product/created`, `store/product/updated`, `store/product/deleted`, `store/customer/created`, `store/customer/updated`, `store/customer/statusUpdated`, `store/customerFavoriteProducts/created`, `store/customerFavoriteProducts/updated`, `store/stock/created`, `store/stock/updated`, `store/app/deleted`, `store/app/payment`. A scope string outside this list is a typo until proven otherwise. The two published lists disagree: `[schema]` `WebhookInput.scopes` documents ten (with `store/customerFavoriteProducts/*`, without `store/customer/statusUpdated`), `[docs:webhooks]` lists nine (with `store/customer/statusUpdated`, without `customerFavoriteProducts`). `[observed]` E5 settles it: `saveWebhooks` **accepts** `store/customer/statusUpdated` and `store/customerFavoriteProducts/created`, **rejects** `store/product/deleted`, `store/app/deleted`, `store/app/payment` with `INVALID_SCOPE` (`error_messages.public.webhook.invalid_scope`). So the union of the two published lists is valid, `store/product/deleted` is dead in the SDK enum, and the two lifecycle scopes come only through the Partner-panel *Bildirim Adresi*. A `saveWebhooks` call whose scopes include any of the three rejected strings fails at install → **Uyarı** (işlevsel; the scanner's §6.2 line names it). Never flag `statusUpdated` or `customerFavoriteProducts`.

### §6.4 Plan / payment webhook (paid apps) `[docs:plans]`

- Scope `store/app/payment`, delivered to the Partner-panel *Bildirim Adresi* (§6.2) `[partner-panel]`. Documented payload: `data.merchantAppPayment.{ id, merchantId, storeAppId, storeAppListingSubscriptionId, storeAppListingSubscriptionKey, name, prices, status, type … }` plus `data.merchantLicence.appSubscriptions[]`. The official `with-subscription-app` example parses an older shape (`paymentStatus`, `subscriptionKey`) `[starter]` — accept either, but note the mismatch as **Bilgi** and point at the docs' shape.
- `[mcp]` `MerchantAppPayment.status` ∈ `PAID | PAYMENT_FAILED | WAITING_FOR_PAYMENT`; `type` ∈ `ONE_TIME | SUBSCRIPTION | WALLET_ACTION`; `prices[] { period: MONTHLY|YEARLY|ONE_TIME, price }`; `storeAppListingSubscriptionKey` nullable. `listMerchantAppPayment(id, pagination)` reads the same records server-side. `[schema]` The GraphQL object also carries `appPaymentKey` ("which type of licence", the older plan-key field), `authorizedAppId`, `storeAppId`, `merchantPaymentUrl`, `paymentDate` and has **no `merchantId`** — but the **webhook payload is not the GraphQL object**: the documented sample `[docs:plans]` carries `merchantAppPayment.merchantId` and `merchantLicence.merchantId` (plus `merchantLicence.{ region, period, activeSubscriptionCode, fromDate, toDate, appSubscriptions[] }`). A handler that requires `merchantAppPayment.merchantId` and compares it with the installation follows the docs — **not a finding**; never grade the payment webhook against `schema.py MerchantAppPayment`. `[sdk]` `IWebhookStoreAppPaymentData` in **2.0.11** types the payload a third way: `merchantAppPayment { _id, appPaymentKey, name, type, status, paymentDate, error }` + `merchantLicence { status, fromDate, toDate, appSubscriptions[] }`; **2.1.0** re-types it to the docs' shape (`merchantAppPayment { id, merchantId, storeAppId, storeAppListingSubscriptionId, storeAppListingSubscriptionKey, appPaymentKey, name, prices[], status, type, paymentDate, error }` + `merchantLicence { merchantId, region, period, activeSubscriptionCode, fromDate, toDate, appSubscriptions[] }`, every field optional). Check the installed version (`package.json` / lockfile) before calling a field name wrong. Three shapes (docs = SDK 2.1.0 / SDK 2.0.11 / old example) — accept whichever the app parses, key the plan on `storeAppListingSubscriptionKey ?? appPaymentKey`, and never grant from the payload alone (reconcile with `getMerchantLicence`).
- **MUST** `[docs:plans]` process only `status === 'PAID'` ("Yalnızca PAID olan kayıtları işleyin"). Granting on any status → **Blocker (güvenlik)** if unsigned, **Uyarı** if signed.
- **MUST** `[docs:plans]` map `storeAppListingSubscriptionKey` to the app's own plan model; unknown keys are logged and ignored, not granted.
- **SHOULD** `[docs:plans]` reconcile with `getMerchantLicence { appSubscriptions { authorizedAppId storeAppListingSubscriptionKey status deleted } }` when gating premium features: entitlement = `status === 'ACTIVE' && deleted === false`. `[mcp]` `MerchantSubscriptionStatusEnum = ACTIVE | WILL_BE_REMOVED | REMOVED`; useful extra fields: `storeAppId` (filter to this app), `lastPaymentDate`, `lastPaymentPeriodInDays` (compute the paid-through date), `lastPaymentPeriod`, `currency`, `merchantAppPaymentId`. `MerchantLicenceResponse.region ∈ AF|AN|AS|EU|OC|PL|TR|US` matches the Partner-panel regions.
- A payment webhook that grants **nothing** from the payload and only triggers a `getMerchantLicence` reconciliation does not need the `PAID` check — the licence query is the source of truth. **Bilgi**; F13 does not apply.
- **SHOULD** show the merchant a way forward when entitlement is missing (a "subscription required" screen pointing at the panel's *Yönet* button, or the plan page) instead of a silent 403/empty dashboard — a reviewer with no plan otherwise sees a broken app (§10 #13). Missing → **Uyarı**.
- Trials: `[docs:plans]` the app tracks the install date itself and enforces expiry.
- `[observed]` S1 (support ticket, 2026-09): an app on `/api/v2/admin/graphql` with `read_orders, read_products, write_storefronts` got `LOGIN_REQUIRED` (`serviceName: merchant-service-public`) **only** for `getMerchantLicence` while `listProduct`, `listStorefront`, `getMerchant`, `createStorefrontJSScript` worked with the same token; the same query on `/api/v1/admin/graphql` answered. **Not reproducible** (2026-09-13, Rush on `dev-kizzle`: the ticket's exact selection set returned 200 with `appSubscriptions: null` on both v1 and v2 with an 11-scope token **and again with a token granted exactly the ticket's three scopes** `read_products, read_orders, write_storefronts` — E6; a `client_credentials` grant for a Partner app is refused with 401, so the ticket's token was an authorization-code token like ours) and the official `with-subscription-app` calls `getMerchantLicence` on v2, so this is **not a rule** and not a scope or endpoint-version issue — when a paid app's licence check is the only call that fails at runtime, ask for the raw request (headers, exact URL, `getAuthorizedApp` with the same token) and escalate to ikas as a platform question; do not tell developers to switch endpoints. The skill cannot see this in code; it is a runtime symptom.

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
| 23 | Root treats a bridge JWT as proof of install and pushes to `/dashboard`; backend has no ikas token for that `authorizedAppId` | Dev-mode / CLI installs land on 404s and never start OAuth | Check the backend token for `aud`; otherwise start authorize from the top window | Uyarı (`[starter]` does it) | §2.2 `[observed]` E1 |
| 24 | Shape (b) root handles only the first-install path; a returning (registered) or abandoned-signup merchant gets a spinner, a redirect loop, or a blank iframe | Reviewer's dev store is already installed — this is the first screen they see | Branch on tenant state: registered → info + link to the external UI; incomplete → info + link back to the form; missing → start signup | Blocker (işlevsel) | §4 (b) `[observed]` R8 |
| 25 | Store-specific auth bypass (allow-listed dev store, seeded session) | Reviewer sees inconsistent gating and pauses the review with a question | Same flow for every store; seed test data, not auth state | Uyarı | §4 `[observed]` R9 |
| 26 | Post-install form asks the merchant to type the store name / domain and binds on that value | Unverified merchant ↔ store mapping; reviewer flags it on sight | Prefill from `getMerchant` / callback `storeName`; compare and reject mismatches | Uyarı (Blocker işlevsel if it is the only binding) | §2.2 `[observed]` R10 |
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

`[schema]` The live Admin API (`https://api.myikas.com/api/v2/admin/graphql`, introspection is unauthenticated) exposes **48 queries and 76 mutations**; the ikas MCP `list` shows a curated subset of 59. Family membership by name (full live list): **orders** `listOrder`, `listOrderTag`, `listOrderTransactions`, `listOrderSession`, `listAbandonedCheckouts`, `listBranch`, `listTerminal`, `createOrderWithTransactions`, `fulfillOrder`, `cancelFulfillment`, `cancelOrderLine`, `refundOrderLine`, `updateOrderPackageStatus`, `updateOrderAddresses`, `addOrderInvoice`, `removeOrderInvoice`, `downloadOrderInvoice`, `approvePendingOrderTransactions`, `addOrderTimelineEntry`, `addOrderTag`, `removeOrderTag`, `createOrderTag`, `updateOrderTag`, `deleteOrderTagList`; **products** `listProduct`, `listProductAttribute`, `listProductBrand`, `listProductTag`, `listCategory`, `listVariantType`, `createProduct`, `updateProduct`, `bulkUpdateProducts`, `updateProductAndVariantAttributes`, `updateProductSalesChannelStatus`, `deleteProductList`, `addVariantToProduct`, `removeVariantFromProduct`, `updateVariantPrices`, `saveVariantType`, `deleteVariantTypeList`, `createCategory`, `updateCategory`, `deleteCategoryList`, `createProductBrand`, `updateProductBrand`, `deleteProductBrandList`, `createProductTag`, `updateProductTag`, `deleteProductTagList`, `createProductAttribute`, `updateProductAttribute`, `deleteProductAttributeList`; **inventories** `saveVariantStocks`, `listStockLocation`, `listProductStockLocation`; **customers** `listCustomer`, `listCustomerAttribute`, `listCustomerGroup`, `listCustomerTag`, `createCustomer`, `updateCustomer`, `updateCustomerAndAddressAttributes`, `deleteCustomerList`, `addCustomerTimelineEntry`, `createCustomerGroup`, `updateCustomerGroup`, `deleteCustomerGroupList`, `createCustomerTag`, `updateCustomerTag`, `deleteCustomerTagList`; **campaigns** `listCampaign`, `listCoupon`, `createCampaign`, `updateCampaign`, `deleteCampaignList`, `addCouponsToCampaign`, `deleteCouponList`; **storefronts** `listStorefront`, `createStorefrontJSScript`, `updateStorefrontJSScript`, `deleteStorefrontJSScript`; **app / identity (no family)** `me`, `getAuthorizedApp`, `getMerchant`, `getMerchantLicence`, `getMerchantSettings`, `getAvailableSubscriptions`, `listMerchantAppPayment`, `createMerchantAppPayment`, `createOneTimeMerchantAppPayment`, `getAppDemoDay`, `saveWebhooks`, `deleteWebhook`, `listWebhook`, `addCustomTimelineEntry`, `getImportJobData`, `getImportJobDataList`; **settings / location (no family)** `getSalesChannel`, `listSalesChannel`, `updateSalesChannel`, `listPriceList`, `createPriceList`, `updatePriceList`, `deletePriceListList`, `listCurrency`, `listPaymentGateway`, `listCargoCompany`, `getGlobalTaxSettings`, `listGlobalTaxSettings`, `createGlobalTaxSettings`, `updateGlobalTaxSettings`, `deleteGlobalTaxSettingsList`, `listShippingSettings`, `listTaxSettings`, `createTaxSettings`, `updateTaxSettings`, `deleteTaxSettingsList`, `listCountry`, `listState`, `listCity`, `listDistrict`, `listTown`. An operation name not in this list is app-local (a codegen alias such as `listOrdersForInvoice`) — map it by its underlying query — **or a v1 name**: v1 uses `save*` upserts (`saveProduct`, `saveCategory`, `saveCustomer`, `saveCampaign`, `saveWebhook`, `saveStorefrontJSScript`, `saveVariantPrices`, `saveProductStockLocations`…) plus `listStorefrontJSScript`, `searchProducts`, `listVendor`, `listProductOptionSet`, wallet queries; map those by the same keywords, and check the version first (§5.3). Price-list / tax / settings mutations have no documented scope family; do not flag them under §10 #16.

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
| R8 | Four messages, same point: "giriş yaptıktan sonra uygulamanızın ikas arayüzü de ilk kurulum süreci haricinde her zaman sürekli yükleniyor durumunda kalmadığından emin olmayı ihmal etmeyin"; "kayıt formunu doldurmuş bir kullanıcı daha sonra … uygulama sayfasına geçtiğinde loading durumunda kalmamalıdır. En azından bir bilgi alanı ve uygulama sayfasına yönlendirecek bir link bulunmalıdır"; "formu doldurmayıp geri döndüyse … yeniden kayıt formuna yönlendirecek bir link ve bilgi alanı bulunabilir". One app was rejected a second time because the resubmission only sent the test account and skipped this note ("ilk review'da belirttiğimiz … noktası atlanmış") | §4 (b) re-entry table, §3.1, §10 #24 |
| R9 | Review paused: the dev store the app was already installed on skipped the login the install flow demands — "formu doldurmayıp tekrardan … uygulamaya girerse bu kez login istemiyor ve kullanıcı panelin içerisinde oluyor. Bu test için belirli mağazalarda geçerli bir durum mu acaba?" | §4 (b), §10 #25 |
| R10 | "Kurulumda kullanıcı doğru yönlendiriliyor, mağaza bilgisi giriyor ama o mağaza ile kullanıcıyı eşleyerek bir kontrol mekanizması olduğunu varsayıyoruz, ancak bunun kontrollerinin eksiksiz olduğundan emin olmak için bu maddeyi ekledik" — listed as a rejection item alongside the R8 spinner | §2.2, §10 #26 |

### Support tickets (developer reports relayed by ikas DevRel, cite as `[observed] S<n>`; single reports, not reproduced)

| # | Report | Rule |
|---|---|---|
| S1 | v2 endpoint, starter-identical setup: `getMerchantLicence` → `LOGIN_REQUIRED` (`merchant-service-public`), every other query fine; v1 endpoint answered the same query. **Closed 2026-09-13 (E6): not reproducible with the same three scopes on either endpoint; not a rule** | §6.4 (diagnostic note only) |

### Experiments (live platform behaviour, dev store, cite as `[observed] E<n>`)

| # | What was done | What was seen | Rule |
|---|---|---|---|
| E1 | 2026-09-13, Rush on `dev-kizzle`: `saveWebhooks` two `store/order/*` scopes → remove app from Admin › Uygulamalarım → probe old token → re-install with `ikas app dev` + top-level authorize → `listWebhook` with the new token | `listWebhook` empty with the old token right after removal and with the new token after re-install (ikas drops registrations). Old access token: `listProduct` still 200 with data 15 min later, `getAuthorizedApp` → `null`, `getMerchant` → `UNAUTHORIZED`; refresh with the old `refresh_token` hangs > 30 s (re-run 2026-09-13 with the same dead token: no response after 45 s, aborted). Admin opened the app in the iframe as `/?storeName&timestamp&merchantId&signature&authorizedAppId` and issued bridge tokens for the new `authorizedAppId` before any OAuth code was exchanged; Rush (same code as the starter) pushed to `/dashboard` on the bridge token alone and hit 404s. App-initiated authorize returned to the callback without `signature`. Wrong `redirect_uri` → JSON `redirect_uri is not whitelisted` | §6.2, §5.1, §2.1, §2.2 |
| E3 | 2026-09-13, Rush on `dev-kizzle`, second uninstall/reinstall cycle, all by the skill author's session: two `saveWebhooks` scopes registered → Admin › Uygulamalarım › Sil → probe old token at T+0 → Admin › *Uygulama Kur* (Redirect Address pointed at a Vercel deployment whose callback 500'd) → Partner addresses temporarily pointed at a local tunnel → app opened from Admin → top-level `/api/oauth/authorize/ikas?storeName=…` → probe old token at T+39 min | Old token: `listProduct`/`listStorefront` 200, `getAuthorizedApp` null, `me`/`getMerchant` UNAUTHORIZED, `saveWebhooks`/`deleteWebhook` APP_NOT_FOUND, `listWebhook` empty, refresh no response after 25 s. Grant page URL carried the Partner-panel scope list and Redirect Address; callback hit with `code`+`storeName` only; app's 500 did not prevent the authorization — Admin listed it as installed, Partner row *Kullanımda*; iframe open sent `storeName, timestamp, merchantId, signature, authorizedAppId`; Rush pushed to `/dashboard`, its `/api/ikas/*` 404'd until OAuth completed; app-initiated callback carried `code, state, storeName` (no `signature`); the same `authorizedAppId` was reused. CLI `ikas app dev`: `No allowed merchants found`, store search empty | §2.1, §2.2, §5.1, §6.2, §10 #23, §1 #5 |
| E6 | 2026-09-13, S1 reproduction attempt: Partner panel permissions cut to exactly `read_products, read_orders, write_storefronts` → top-level authorize → `getMerchantLicence` (ticket's selection set) on v1 and v2 → `listCustomer` → panel restored to *Tüm Yetkiler* → re-authorize. Also `client_credentials` grant with the Partner app's credentials | Grant page `scope` = the panel's 3 (app asked for 8); `getAuthorizedApp.scope` = the 3; `getMerchantLicence` **200** on v1 and v2 (`appSubscriptions: null`, full object with `merchantId` on v2); `listCustomer` → `UNAUTHORIZED` `deniedBy: FEATURE`; re-authorize under the same `authorizedAppId` brought the scope back to 11; `client_credentials` → 401 on both hosts | §6.4 S1 closed, §2.1, §2.3 |
| E4 | 2026-09-13, live `refresh_token` grant, then old access token and old refresh token re-used | 0.3 s, `expires_in` 14400, new refresh token; old access token still 200 on `listProduct`; old refresh token accepted again (different access token) | §2.3 |
| E5 | 2026-09-13, `saveWebhooks` one scope at a time; `http://` endpoint; `deleteWebhook` flat list; `createStorefrontJSScript` ×2 + bare content; `deleteStorefrontJSScript` ×2; v1 `listStorefrontJSScript` before/after | Accepted: `store/customer/statusUpdated`, `store/customerFavoriteProducts/created`. Rejected `INVALID_SCOPE`: `store/product/deleted`, `store/app/deleted`, `store/app/payment`. `http://` → `ARGUMENT_VALIDATION_ERROR`. `deleteWebhook([..])` → true, list empty. Bare `scriptContent` → `ARGUMENT_VALIDATION_ERROR`; one delete emptied the v1 list; second delete → `STOREFRONT_SF_SCRIPT` not_found | §6.2, §6.3 |
| E2 | 2026-09-13, same store, fresh authorization: `getAuthorizedApp.scope` vs the 8 scopes in the authorize URL; `createStorefrontJSScript` ×2 → `deleteStorefrontJSScript` ×1 → `updateStorefrontJSScript` on both ids | Granted scope = Partner panel's 11 scopes, not the requested 8. One `deleteStorefrontJSScript()` removed both scripts (both ids → `storefront_sf_script_not_found`); the same error when nothing is left. `scriptContent` without `<script>` tags → `ARGUMENT_VALIDATION_ERROR` | §2.1, §6.2 |
- Admin API schema (live, authoritative) — `https://api.myikas.com/api/v2/admin/graphql` introspection, no token needed (`scripts/schema.py <operation|type>` prints a signature); tag `[schema]`
- Admin API via MCP — `https://api.myikas.com/api/v2/admin/mcp` (`list`, `introspect <operation>`): curated subset of 59 operations, argument types occasionally mis-rendered (`deleteWebhook`); tag `[mcp]`, verify against `[schema]` when a finding hinges on a signature
- SDK — `@ikas/admin-api-client` (`OAuthAPI`, `validateIkasWebhookSignature`, `getParsedIkasWebhookData`, `WebhookScope`, `APP_SCOPES`), `@ikas/app-helpers` (`AppBridgeHelper`)
