---
name: ikas-app-preflight
description: Pre-review audit for ikas Admin Apps (Next.js apps installed into the ikas panel via OAuth, using @ikas/admin-api-client / @ikas/app-helpers). Checks the five App Store publishing prerequisites, the OAuth / App Bridge / iframe contract, webhook and app-action signature verification, secret hygiene and public-endpoint safety against a sourced ruleset, writes the report in Turkish, then asks before applying catalogued fixes. Use whenever the user asks if an ikas app is ready for review or the App Store, wants the install / uninstall / OAuth / webhook / action flow checked, or says "review'a hazır mı", "app store'a göndermeden önce kontrol et", "ikas app denetle", "publish checklist", "pre-review" — even if they only name one area (e.g. "webhook imzası doğru mu").
argument-hint: "[quick | section <oauth|iframe|webhooks|actions|secrets|public>] [project-path]"
allowed-tools: Read, Grep, Glob, Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/scan.py *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/schema.py *), Bash(git status *), Bash(git log *), Bash(git rev-parse *), Bash(git check-ignore *), Bash(git diff *)
effort: high
---

# ikas App Preflight

Predict what the ikas reviewer and the merchant will experience, and find the security holes a reviewer would not reach. The ruleset is `references/app-review.md`; the output format is `references/report-template.md`; repairs come only from `references/fix-catalogue.md`.

**Anchoring rule.** Every finding cites a § from app-review.md (with its source tag) or is labeled *kontrat dışı*. No § → not a finding. Code style, naming, CSS, tests and business logic are out of scope.

**Calibration rule.** The official example apps (`ikascom/ikas-app-examples`) must come out with zero review-Blockers under this ruleset. A rule that would fail the official starter is a hardening Uyarı unless it is an exploitable hole. When in doubt, read app-review.md §0 and the `[starter]` tags — do not grade from memory of a template. `scripts/calibrate.sh` runs the scanner over the three official examples and fails on any Blocker; `tests/run.sh` snapshots the scanner on `tests/fixtures/broken-app` (a starter with every catalogued defect injected) — run both after changing `scan.py`, the ruleset or a recipe.

**Honesty rule.** Some prerequisites live outside the code (partner verification, two dev stores, reviewer test account, Partner-panel webhook registration). They are questions in the report, never passes. Never write "review'dan geçer"; write "bu kural setine göre Blocker kalmadı".

## Arguments

| `$ARGUMENTS` | Scope |
|---|---|
| *(none)* or a path | Full preflight — Steps 1–6 |
| `quick` | Step 1 (scanner) + Step 4 (anti-pattern sweep) only; say so in the report header |
| `section <area>` | Step 1 with `--section <area>` (scanner prints only the matching §) + the matching § in Steps 2–3: `oauth` = §2; `iframe` = §3 + §4; `webhooks` = §6; `actions` = §7; `secrets` = §8 + §5.1/§5.3; `public` = §9 + §5.2. §10 is always in scope |

The project root is the last argument if it is a path, otherwise the current working directory. Steps 1–5 change nothing: no edits, no `git` writes. Step 6 edits only after the user says yes.

## Procedure

Copy this checklist into your working notes and tick it as you go:

```
Preflight:
- [ ] Step 1  scanner evidence
- [ ] Step 2  inventory + app shape
- [ ] Step 3  merchant journey + security layer (read the code)
- [ ] Step 4  §10 anti-pattern sweep
- [ ] Step 5  report (Turkish, template)
- [ ] Step 6  ask → apply catalogued fixes → verify
```

### Step 1 — Scanner evidence

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/scan.py <project-root>
```

Output lines are `§ | severity | file:line | message`. The scanner follows a route's local imports two levels deep (`@/` alias from tsconfig), so a signature or JWT check that lives in `lib/webhooks.ts` or `lib/auth-helpers.ts` is credited to the route and reported as `(via <module>)`. Treat every hit as **a place to read** and every silence as **nothing proven** — it is regex over files; a hand-rolled token exchange or a webhook route named `notify` slips past it. Keep the output; it is the evidence column. If it prints `ikas app not detected`, stop and tell the user this skill is for Admin Apps (Next.js + `@ikas/admin-api-client` / `@ikas/app-helpers`). Pages Router projects (`pages/api/**`) are scanned too — a §1 Bilgi line says so; the official examples are App Router, so read §3 evidence by hand there.

Also run `git status --porcelain --ignored` in the project root. Untracked and ignored files are still audited — they ship if the deploy is built from this tree — but the report marks them. Not a repository → header says `Git: repo yok`, `.gitignore` absence is a §8 Uyarı, and no per-file git tags are possible.

### Step 2 — Inventory and app shape

Read `ikas.config.json`, `package.json`, `.env.example`, the `src/app` (or `app`) route tree, and the first component the panel renders (`/` and where it redirects). Produce:

- **Routes by kind:** OAuth authorize/callback; admin API (JWT); webhooks; iframe action pages and API action routes; public/storefront endpoints; iframe pages; operational (health, metrics). The route tree, not the scanner, is the source of truth — open every `api/` route the scanner did not classify by name and decide from the body (an HMAC over `{signature, data}` is a webhook or API action whatever the path is called). If a route's caller still cannot be told from the code (no JWT, no signature, no key, no obvious cron/operator gate), **ask** with AskUserQuestion — "Bu route'u kim çağırıyor?" with options panel (JWT) / ikas webhook or action / storefront (anonymous) / operator or cron — and grade it under the matching §. Never guess a route into §5.1 silence.
- **App shape** per app-review.md §4 — exactly one of (a) in-panel dashboard, (b) external dashboard, (c) action-only, (d) headless. It decides which §4 row and which DECLARE rows apply.
- **Paid or free** — `store/app/payment`, `getMerchantLicence`, plan keys.
- **Requested scopes vs operations** — collect `ikas.queries.X` / `ikas.mutations.X`, map with §11.

### Step 3 — Read the code

Open `references/app-review.md` with Read and grade section by section; do not grade from memory. Trace the merchant journey, reading deep enough to answer each stage — especially `catch` blocks, missing-param branches, and non-iframe renders:

| Stage | Read for | § |
|---|---|---|
| Kurulum | authorize → callback → token stored → JWT to browser | §2.1, §2.2 |
| Callback sayfası | `closeLoader`, `<Suspense>`, iframe branch, sentinel | §3.1, §3.3 |
| Günlük giriş | entry page closes loader, bridge token, something actionable renders, non-iframe fallback | §3.1, §3.2, §4 |
| ikas arayüzü | the §4 row for the shape holds | §4 |
| Aksiyon | iframe: params, loader, result, `closeApp`; API: HMAC first | §7 |
| Plan (paid) | `PAID` only, key mapping, `getMerchantLicence` gating | §6.4 |
| Kaldırma | signature → secret guard → statuses → Admin API cleanup (`deleteStorefrontJSScript`, campaigns, best-effort `deleteWebhook`) → token invalidated → routes refuse the dead token. No webhook route at all → one §6.2 Uyarı (priority 1 if the app injects scripts/campaigns) plus the Partner-panel Beyan row; do not repeat it per route. `saveWebhooks` without `deleteWebhook` is **not a finding** (§6.2 `[observed]` E1: ikas drops the registrations itself); the token is **not** revoked by ikas, so local invalidation + §5.1 `deleted` check is the real control | §6.1, §6.2, §5.1 |

Then the security layer against the inventory: every non-exempt route verifies the JWT before work and takes identity from `aud`/`sub` (§5.1); no client → Admin API (§5.2); webhooks and API actions verify before acting, fail closed, honest statuses (§6.1, §7.2); nothing secret under `NEXT_PUBLIC_`, env files ignored, no token logging, `oauthRedirectPath` matches a route (§8); public endpoints scope by merchant, take no money from the client, rate-limit writes (§9).

Confirm or re-grade every scanner hit from what you read; when you merge or downgrade hits, say so in one line under Bilgi. Severity comes from app-review.md, and each Blocker states its reason: **güvenlik**, **review**, or **işlevsel**.

For facts you are unsure about (an operation name, an argument type, a webhook scope string) run `python3 ${CLAUDE_SKILL_DIR}/scripts/schema.py <operation|type>` — unauthenticated introspection of the live Admin API, the `[schema]` source. The ikas admin MCP (`.mcp.json` → `https://api.myikas.com/api/v2/admin/mcp`) lists only a curated subset and has mis-rendered argument types (`deleteWebhook` shows `[[String!]]`, live schema says `[String!]!`) — never put an MCP-only signature into a Düzeltme line. Docs URLs are in app-review.md §12. Do not invent scope names.

### Step 4 — Anti-pattern sweep

Read app-review.md §10 and check items #1–#22 explicitly (#7 is retired). Cite as `§10 #n`; when an item is also a §2–§9 rule, cite both.

### Step 5 — Report

Write the report in Turkish following `references/report-template.md` exactly: Karar → Bir bakışta → **Yapılacaklar** (the action list, first) → Bulgu özeti (4-column index) → Blocker'lar → Uyarılar → Kod dışında doğrulanacaklar → Temiz alanlar ve notlar → İsteğe bağlı öneriler (max 5). Every finding header names the area in Turkish before the § (`OAuth callback (§2.2)`); every finding has a one-line `Düzeltme:`. Findings are **blocks**; tables only where every cell is short (Bulgu özeti, Beyan, the one-line §10 sweep) — wide tables re-flow into unreadable key/value walls in the terminal; Bilgi bullets are one line each. Evidence = `path:line` + what you saw. Grade SHOULD rules by the severity the ruleset names (most are Bilgi, not kontrat dışı — kontrat dışı is only for advice no § covers). End with one line: the report can be saved as `PREFLIGHT-REPORT.md` in the project root on request (do not write it unasked — Steps 1–5 change nothing). Build the Beyan table from §1 and the app shape:

| Soru | Neden |
|---|---|
| Partner hesabı oluşturuldu ve uygulama bu hesaba eklendi mi? | §1 #1 |
| Partner hesabı doğrulandı mı? | §1 #2 |
| Uygulama en az 2 geliştirme mağazasında kurulu ve test edilebilir mi? Partner panel › İzin Verilen Mağazalar'da "Kullanımda" görünen mağaza adları? | §1 #5 `[partner-panel]` |
| (Shape b) Reviewer için harici panelde çalışan bir test hesabı dev@ikas.com'a gönderilecek mi? Review bunsuz ilerlemiyor | §4 (b) `[observed]` R1 |
| (Storefront app) Script kurulumda otomatik ekleniyor, kaldırmada otomatik siliniyor mu? (kodda `createStorefrontJSScript` kurulum yolunda, `deleteStorefrontJSScript` uninstall handler'da) | §6.2 `[observed]` R5 |
| Uygulama bağımsız, somut bir işlev sunuyor mu — yalnızca iletişim/tanıtım ekranı değil mi? | §1 `[observed]` R6 |
| (Paid) Partner panel › Planlar'da planlar tanımlı ve Yayınlama'da her bölgenin "Bölgedeki Aktif Planlar"ı doğru para biriminde mi? Plan açıklamaları girildi mi? | §1, §6.4 `[partner-panel]` |
| (Actions) Partner panel › Aksiyonlar'daki kayıtlar `ikas.config.json` `actions[]` ile aynı URL/tip/method mü? | §7 `[partner-panel]` |
| Yayınlama › listeleme "Herkese Açık" mı hedefleniyor (review'a giden), yoksa "Gizli" mi (review yok, Kurulum Adresi ile kurulur)? | §1 `[docs:build-publish]` `[partner-panel]` |
| (Webhook route handles `store/app/deleted` / `store/app/payment`) Partner panel › Konfigürasyon › **Bildirim Adresi** `<deployUrl><route>` olarak girildi mi? Bu iki scope yalnızca oradan gelir, `saveWebhooks` ile alınamaz | §6.2, §6.4 `[partner-panel]` |
| (Data webhook route exists, no `saveWebhooks` call) `store/order/*` vb. webhook'lar `saveWebhooks` ile kaydediliyor mu, değilse nasıl tanımlanacak? | §6.2 |
| Partner panel › Uygulama Yetkileri koddaki scope listesiyle birebir aynı mı? ("Tüm Yetkiler" işaretliyse kodda dar scope varken fazla izin istenmiş olur) | §2.1 `[partner-panel]` |
| Partner panel › Uygulama Adresi = `<deployUrl>` ve Yönlendirme Adresi = `<deployUrl><oauthRedirectPath>` mi? | §2.1, §8 `[partner-panel]` |
| Production `NEXT_PUBLIC_DEPLOY_URL` gerçek URL'e set edildi mi (Host-header fallback yalnızca localhost'ta devrede)? | §2.1 |

### Step 6 — Ask, then fix

**Always ask after the report** (AskUserQuestion, in Turkish) — a report with no offer to help reads as "figure it out yourself". Two cases:

**Some finding matches a recipe in `references/fix-catalogue.md`:**
- Question: "Rapordaki bulgular için katalogdaki düzeltmeleri uygulayayım mı?"
- Options: **"Evet, hepsini uygula (Recommended)"** — every recipe whose precondition holds · **"Sadece Blocker'ları düzelt"** · **"Seçeyim"** — then list the applicable `F<n>` ids and ask which · **"Hayır, rapor yeter"**
- On yes: read the catalogue, apply only the selected recipes exactly as written, run the type-check when `node_modules` exists (do not install), then append section 7 of the template: applied fixes, type-check result, `git diff --stat`, recipes not applied with reasons. Never commit.

**No recipe matches (or the recipes are done and hand-work remains):**
- Question: "Katalogda hazır tarif kalmadı. Yapılacaklar listesindeki kod değişikliklerini tek tek, her birini göstererek uygulayayım mı?"
- Options: **"Evet, sırayla uygula (Recommended)"** · **"Seçeyim"** — list the Yapılacaklar items that are code changes · **"Hayır, ben yaparım"**
- On yes: for each selected item, show the intended change in one sentence, make the minimal edit in the named file, and move on; re-run the scanner at the end and report what changed (`git diff --stat` or the file list when there is no repo). Items in the catalogue's "Never do" list (scope trimming, OAuth flow rewrites, `|| ''` env contracts, public-schema field drops, deleting routes) are **still offered** here but with their caveat stated in the option text, and each one is confirmed individually before editing. Partner-panel / declaration items are never "applied" — they stay listed as the developer's job.

## Common mistakes

- Failing the official starter. `Math.random` state, `'api'` storeName fallback, `if (state && session.state && …)`, unconditional `window.location.replace(redirectUrl)`, browser-console logging of the app JWT, no uninstall webhook — all official-example behaviour → Uyarı or Bilgi, never review-Blocker.
- Requiring `state` on the callback. ikas sends Admin-initiated installs straight to the Redirect Address with `code`+`storeName` only (`[observed]` R4); `if (!state) → 400` fails every reviewer install — Blocker, not hardening.
- Calling `signature && …` on the **callback** a hole. It is the documented posture. On **webhooks that mutate state** and on **API actions** the signature is always present and must be verified — that is where Blockers live.
- Passing §4 because `closeLoader()` exists. Necessary, not sufficient: a blank screen after it is §10 #13.
- Rejecting an external dashboard on sight. Shape (b) is allowed; it fails only without the in-iframe link/instruction; the test account is a Beyan row.
- Trusting scanner silence for routes. The inventory from Step 2 is the truth.
- Applying fixes before the user answered, or applying non-catalogue fixes.
- Saying "review'dan geçer".
- Reporting `saveWebhooks`-without-`deleteWebhook` at all: ikas removes the registrations on uninstall (§6.2 `[observed]` E1). The opposite mistake: assuming ikas revokes the access token on uninstall — it does not (E1); the app's own `deleted` flag is what stops post-removal reads.
- Copying a signature from MCP `introspect` into a Düzeltme without checking `schema.py`.
