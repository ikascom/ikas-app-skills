#!/usr/bin/env python3
"""ikas Admin App pre-review scanner — evidence pass for the ikas-app-preflight skill.

Usage: python3 scan.py [project root] [--json]

Walks a Next.js (App Router) ikas app and prints pattern-level evidence for the
rules in references/app-review.md, one finding per line:

    §      SEVERITY  file:line [git-state]
           message

Severities follow app-review.md §0. BLOCKER messages end with the reason
(güvenlik | review | işlevsel). Calibration: the official example apps in
ikascom/ikas-app-examples must produce zero review-Blockers; anything the
official starter does is at most UYARI unless it is an exploitable hole.

This script collects evidence only. A hit is a place to read; a miss proves
nothing. Exit code is always 0; use --json for tooling.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(next((a for a in sys.argv[1:] if not a.startswith("--")), "."))
AS_JSON = "--json" in sys.argv

SKIP_DIRS = {"node_modules", ".next", ".git", "dist", "build", "out", "coverage", ".turbo", "generated"}
SRC_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs")

findings = []


def add(section, severity, path, line, msg):
    rel = os.path.relpath(path, ROOT) if path else "-"
    findings.append({"section": section, "severity": severity, "file": rel, "line": line, "msg": msg})


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def line_of(text, pattern):
    m = re.search(pattern, text)
    return text[: m.start()].count("\n") + 1 if m else None


def walk_src():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # public/ holds static assets and built widget bundles, not source
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not (dirpath == ROOT and d == "public")]
        for fn in filenames:
            if fn.endswith(SRC_EXT):
                yield os.path.join(dirpath, fn)


# ---------------------------------------------------------------- git state (untracked / ignored files still ship)
git_state = {}
try:
    out = subprocess.run(["git", "status", "--porcelain", "--ignored", "--", "."], cwd=ROOT, capture_output=True, text=True, timeout=20)
    if out.returncode == 0:
        for ln in out.stdout.splitlines():
            code, _, p = ln[:2], ln[2], ln[3:]
            p = p.strip().rstrip("/")
            state = "untracked" if code == "??" else "ignored" if code == "!!" else None
            if state:
                git_state[p] = state
except (OSError, subprocess.SubprocessError):
    pass
git_note = ""
try:
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
    if git_state and head.returncode != 0:
        git_note = "no commits yet — whole tree untracked, per-file git tags suppressed"
        git_state = {k: v for k, v in git_state.items() if v == "ignored"}
except (OSError, subprocess.SubprocessError):
    pass


def git_tag(path):
    if not path:
        return ""
    rel = os.path.relpath(path, ROOT)
    for p, s in git_state.items():
        if rel == p or rel.startswith(p + "/"):
            return f" [{s}]"
    return ""


# ---------------------------------------------------------------- project detection
pkg = {}
pkg_path = os.path.join(ROOT, "package.json")
if os.path.exists(pkg_path):
    try:
        pkg = json.load(open(pkg_path))
    except json.JSONDecodeError:
        pass
deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
ikas_cfg_path = os.path.join(ROOT, "ikas.config.json")
has_cfg = False
if os.path.exists(ikas_cfg_path):
    try:
        has_cfg = "oauthRedirectPath" in json.load(open(ikas_cfg_path))  # theme projects also ship ikas.config.json
    except json.JSONDecodeError:
        has_cfg = True
has_sdk = "@ikas/admin-api-client" in deps
has_bridge = "@ikas/app-helpers" in deps

if not (has_cfg or has_sdk or has_bridge):
    print(f"{ROOT}: ikas app not detected (no ikas.config.json with oauthRedirectPath, @ikas/admin-api-client or @ikas/app-helpers). Nothing to scan.")
    sys.exit(0)

app_dir = next((d for d in (os.path.join(ROOT, "src", "app"), os.path.join(ROOT, "app")) if os.path.isdir(d)), None)
if not app_dir:
    add("§1", "BILGI", None, None, "No App Router directory (src/app or app) — route-based checks skipped")

files = {p: read(p) for p in walk_src()}
app_files = {p: t for p, t in files.items() if app_dir and p.startswith(app_dir + os.sep)}


def rel_route(p):
    return os.path.relpath(p, app_dir).replace(os.sep, "/") if app_dir else p


def is_route(p):
    return os.path.basename(p).startswith("route.") and p in app_files


PUBLIC_KEY_PARAM = re.compile(r"(searchParams\.get|body\.|params\.)\s*\(?\s*['\"]?(publicApiKey|publicKey|apiKey|storefrontKey)")
AUTH_MARKERS = re.compile(r"getUserFromRequest|withMerchant|verifyToken|jwt\.verify|jsonwebtoken|verifyJwt|requireAuth")


def route_group(p):
    r = rel_route(p).lower()
    if "/oauth/" in r or r.startswith("api/oauth"):
        return "oauth"
    if "webhook" in r:
        return "webhook"
    if "/public/" in r or r.startswith("api/public") or "/storefront" in r or "/widget" in r:
        return "public"
    if "action" in r:
        return "action"
    if r.startswith("api/"):
        t = files.get(p, "")
        # anonymous storefront route keyed by a per-merchant public key — §9, not §5.1
        if not AUTH_MARKERS.search(t) and PUBLIC_KEY_PARAM.search(t):
            return "public"
        return "api"
    return "page"


def is_server_file(p):
    t = files.get(p, "")
    return not re.search(r"['\"]use client['\"]", t) and not re.search(r"(^|/)(widget|storefront|components?)/", os.path.relpath(p, ROOT))


# ---------------------------------------------------------------- §2 OAuth
callback_files = [p for p, t in files.items() if "getTokenWithAuthorizationCode" in t]
authorize_files = [p for p, t in files.items() if re.search(r"getOAuthUrl|/authorize\?|oauth/authorize", t) and "client_id" in t]

if not callback_files:
    add("§2.2", "BILGI", None, None, "No OAuth callback (getTokenWithAuthorizationCode) found — hand-rolled exchange or headless app? Inventory the routes by hand")
for p in callback_files:
    t = files[p]
    has_sig = bool(re.search(r"validateCodeSignature|createHmac", t))
    has_state = bool(re.search(r"session\.state|savedState|stateStore", t))
    if not has_sig and not has_state:
        add("§2.2", "UYARI", p, 1, "Callback verifies neither the code signature (HMAC-SHA256(code, CLIENT_SECRET)) nor the session state — documented pattern checks both when present [docs:auth-steps]")
    elif not has_sig:
        add("§2.2", "UYARI", p, 1, "Callback does not verify the `signature` query param (HMAC-SHA256(code, CLIENT_SECRET)) [docs:auth-steps] — defence in depth, not a hole")
    elif "timingSafeEqual" not in t and not any("timingSafeEqual" in files[q] for q in files if "validateCodeSignature" in files[q]):
        add("§2.2", "BILGI", p, line_of(t, r"validateCodeSignature|createHmac"), "Signature compared with === (starter does the same); timingSafeEqual is hardening (F9)")
    if has_state and not re.search(r"delete\s+session\.state|session\.state\s*=\s*undefined|state:\s*undefined|consumeState|clearState", t):
        add("§2.2", "UYARI", p, line_of(t, r"session\.state"), "State is compared but never cleared after the exchange — replayed callback passes the state check")
    if re.search(r"catch[^\n]*\{[^}]*(Callback failed|callback failed)", t, re.S) and not re.search(r"response\?\.status|\.status\b.*\.data|TokenExchangeError|error\.response", t):
        add("§2.2", "UYARI", p, line_of(t, r"Callback failed"), "Token-exchange failures reported as an opaque 'Callback failed' (§10 #8)")
    if re.search(r"console\.(log|info|debug)\([^)]*(access_token|refresh_token|accessToken|refreshToken|client_secret|clientSecret)", t):
        add("§8", "BLOCKER", p, line_of(t, r"console\.(log|info|debug)\([^)]*(access_token|refresh_token|accessToken|refreshToken|client_secret|clientSecret)"), "ikas token / client secret written to server logs (§10 #10) — güvenlik")
    if not re.search(r"getMerchant|getAuthorizedApp", t):
        add("§2.2", "UYARI", p, 1, "Callback does not resolve merchant/authorizedApp identity server-side after the exchange (getMerchant + getAuthorizedApp) [docs:callback-api]")
    if re.search(r"(NextResponse\.json|res\.json|cookies\(\)\.set|searchParams\.set)\([^)]*(access_token|refresh_token|accessToken|refreshToken)", t):
        add("§2.3", "BLOCKER", p, line_of(t, r"(access_token|refresh_token|accessToken|refreshToken)"), "ikas access/refresh token appears in a response, cookie or redirect query — güvenlik")

for p in authorize_files:
    t = files[p]
    if re.search(r"Math\.random\(\)", t):
        add("§2.1", "UYARI", p, line_of(t, r"Math\.random\(\)"), "OAuth state generated with Math.random() — official starter does this too; CSPRNG is hardening (§10 #1, F3)")
    elif not re.search(r"randomBytes|randomUUID|crypto\.getRandomValues|nanoid", t):
        add("§2.1", "BILGI", p, 1, "Could not find how the OAuth state is generated (no Math.random / randomBytes / randomUUID) — read the route")
    if "state" not in t:
        add("§2.1", "UYARI", p, 1, "Authorize route sends no `state` parameter [docs:auth-steps]")

# ikas.config.json ↔ callback route path
if has_cfg:
    try:
        cfg = json.load(open(ikas_cfg_path))
        redirect_path = cfg.get("oauthRedirectPath")
        if not redirect_path:
            add("§8", "UYARI", ikas_cfg_path, 1, "ikas.config.json has no oauthRedirectPath")
        elif app_dir:
            target = os.path.join(app_dir, redirect_path.strip("/"))
            if not any(os.path.exists(os.path.join(target, f"route.{ext}")) for ext in ("ts", "js", "tsx")):
                add("§8", "BLOCKER", ikas_cfg_path, 1, f"oauthRedirectPath '{redirect_path}' has no matching route handler under {os.path.relpath(app_dir, ROOT)} — işlevsel")
        for action in cfg.get("actions", []) or []:
            add("§7", "BILGI", ikas_cfg_path, 1, f"Action configured: {json.dumps(action)[:120]} — verify its page/route exists and follows §7")
    except json.JSONDecodeError:
        add("§8", "UYARI", ikas_cfg_path, 1, "ikas.config.json is not valid JSON")

# deploy URL normalization
for p, t in files.items():
    m = re.search(r"\$\{process\.env\.NEXT_PUBLIC_DEPLOY_URL\}/|process\.env\.NEXT_PUBLIC_DEPLOY_URL\s*\+\s*['\"`]/", t)
    if m and not re.search(r"replace\(\s*/\\/\+?\$/|new URL\(|trimEnd\(['\"]/|endsWith\(['\"]/", t[: m.start()]):
        add("§2.1", "UYARI", p, t[: m.start()].count("\n") + 1, "Raw NEXT_PUBLIC_DEPLOY_URL concatenated into the redirect URI without trailing-slash normalization — a trailing slash in env breaks the byte-identical match (§10 #6, F4)")

# ---------------------------------------------------------------- §3 iframe pages
client_pages = {p: t for p, t in app_files.items() if os.path.basename(p).startswith("page.") and re.search(r"['\"]use client['\"]", t)}
hooks_with_loader = {p for p, t in files.items() if "closeLoader" in t}


def imports_loader_hook(t):
    for p in hooks_with_loader:
        name = os.path.splitext(os.path.basename(p))[0]
        if name in ("page", "layout"):
            continue
        if re.search(r"from\s+['\"][^'\"]*" + re.escape(name) + r"['\"]", t):
            return True
    return False


def is_entry_page(p, t):
    """Pages the panel loads as the first document: root, iframe action pages, callback."""
    r = rel_route(p)
    return r in ("page.tsx", "page.jsx", "page.ts", "page.js") or bool(re.search(r"actionRunId|idList|orderPackageId", t)) or r.startswith("callback/")


for p, t in client_pages.items():
    r = rel_route(p)
    iframe_signal = re.search(r"getNewToken|getTokenForIframeApp|getAuthorizedAppId|useIkasToken|AppBridgeHelper|useSearchParams|actionRunId", t)
    exempt = re.search(r"authorize-store|login|landing", r)
    if iframe_signal and "closeLoader" not in t and not imports_loader_hook(t) and not exempt:
        if r.startswith("callback/") and re.search(r"window\.location\.replace|setToken\(", t):
            add("§3.1", "BILGI", p, 1, "Callback page never calls closeLoader() but redirects immediately (starter pattern) — fine top-level; matters only if it can render inside the iframe")
        elif is_entry_page(p, t):
            add("§3.1", "BLOCKER", p, line_of(t, r"useEffect\(|export default") or 1, "Entry page never calls AppBridgeHelper.closeLoader() — panel spinner never closes (§10 #4, F2) — işlevsel")
        else:
            add("§3.1", "UYARI", p, line_of(t, r"useEffect\(|export default") or 1, "Iframe page never calls closeLoader() — fine when reached by client-side navigation, hangs on a hard reload (F2)")
    if "useSearchParams" in t and "Suspense" not in t:
        if re.search(r"dynamic\s*=\s*['\"]force-dynamic['\"]|cookies\(\)|headers\(\)", t):
            add("§3.3", "UYARI", p, line_of(t, "useSearchParams"), "useSearchParams() without <Suspense> on a dynamic page — builds, but wrap it anyway (§10 #14, F8)")
        else:
            add("§3.3", "BLOCKER", p, line_of(t, "useSearchParams"), "useSearchParams() without a <Suspense> boundary — `next build` fails with 'Missing Suspense boundary' on static pages (§10 #14, F8) — işlevsel")

for p, t in files.items():
    for m in re.finditer(r"window\.location\.(replace|assign|href)\s*\(?\s*=?\s*\(?\s*(redirectUrl|adminUrl|[a-zA-Z_.]*admin[a-zA-Z_.]*)", t, re.I):
        context = t[max(0, m.start() - 800): m.start()]
        if not re.search(r"window\.self\s*!==?\s*window\.top|window\.top\s*!==?\s*window\.self|inIframe|isIframe", context):
            add("§3.3", "UYARI", p, t[: m.start()].count("\n") + 1, "Top-level redirect to the Admin URL with no iframe branch — starter does this; nests a second Admin only if the callback lands inside the iframe (§10 #5, F5)")
        break

# sentinel throw ('redirectUrl-called') not caught in the callback page effect
sentinel_thrown = any("redirectUrl-called" in t and "throw" in t for t in files.values())
for p, t in client_pages.items():
    if sentinel_thrown and rel_route(p).startswith("callback/") and re.search(r"setToken\(", t) and not re.search(r"catch|redirectUrl-called", t):
        add("§3.3", "UYARI", p, line_of(t, r"setToken\("), "setToken throws the 'redirectUrl-called' sentinel and the callback effect has no catch — unhandled rejection after redirect (F6)")

# browser-console logging of the callback query / app JWT (starter does this) — Uyarı
for p, t in client_pages.items():
    m = re.search(r"console\.(log|info|debug)\([^\n]*(params\.toString|searchParams\.toString|callback params|token)", t, re.I)
    if m:
        add("§2.2", "UYARI", p, t[: m.start()].count("\n") + 1, "Callback query / app JWT logged to the browser console — starter pattern; remove (§10 #10, F6)")

# ---------------------------------------------------------------- §5 backend routes
auth_markers = AUTH_MARKERS
TOKEN_LOAD = re.compile(r"AuthTokenManager\.get|getAuthToken|findUnique")
DELETED_CHECK = re.compile(r"\.deleted|isDeleted|uninstalled")
# shared wrappers: non-route files that load the token and export a function used by routes
wrappers = {p: t for p, t in files.items() if not is_route(p) and TOKEN_LOAD.search(t) and re.search(r"export (async )?function \w+|export const \w+ = ", t)
            and re.search(r"withMerchant|requireAuth|getAuthedUser|authed|Authed", t)}
wrappers_with_deleted = {p for p, t in wrappers.items() if DELETED_CHECK.search(t)}
wrappers_without_deleted = set(wrappers) - wrappers_with_deleted
routes_self_loading = []
for p, t in app_files.items():
    if not is_route(p):
        continue
    g = route_group(p)
    r = rel_route(p)
    if g == "api" and not auth_markers.search(t):
        add("§5.1", "BLOCKER", p, 1, "Admin API route has no JWT verification marker (getUserFromRequest/withMerchant/…) — güvenlik")
    elif g in ("api", "public") and TOKEN_LOAD.search(t) and not DELETED_CHECK.search(t):
        routes_self_loading.append(rel_route(p))
if routes_self_loading or wrappers_without_deleted:
    parts = []
    if wrappers_without_deleted:
        parts.append("shared wrapper checks only !authToken: " + ", ".join(os.path.relpath(w, ROOT) for w in sorted(wrappers_without_deleted)) + " (F14)")
    if routes_self_loading:
        how = "bypass the wrapper that checks deleted (F10)" if wrappers_with_deleted else "load the token themselves without a deleted check"
        parts.append(f"routes that {how}: " + ", ".join(sorted(routes_self_loading)))
    add("§5.1", "UYARI", next(iter(sorted(wrappers_without_deleted)), None) or os.path.join(app_dir, routes_self_loading[0]) if app_dir else None, 1,
        "Uninstalled (deleted) tokens are not refused — starter does the same; one finding: " + "; ".join(parts))
for p, t in app_files.items():
    if not is_route(p):
        continue
    g = route_group(p)
    if g == "api" and re.search(r"(body|json|searchParams)[^\n]*(authorizedAppId|merchantId)", t):
        add("§5.1", "UYARI", p, line_of(t, r"(body|json|searchParams)[^\n]*(authorizedAppId|merchantId)"), "authorizedAppId/merchantId read from request input — must come from the verified JWT (Blocker güvenlik if input wins)")
    if re.search(r"gql`|graphql`|query\s*\{|mutation\s*\{", t) and g in ("api", "action"):
        add("§5.3", "UYARI", p, line_of(t, r"gql`|graphql`|query\s*\{|mutation\s*\{"), "Inline GraphQL document in a route handler (§10 #11)")
    if g == "api" and re.search(r"(capture|debug|test|echo|dump)", r) and re.search(r"appendFileSync|writeFileSync|console\.log\([^)]*headers", t):
        add("§8", "BLOCKER", p, 1, "Debug/capture route writes request bodies or headers to disk/logs — must not ship (§10 #19) — güvenlik")

for p, t in files.items():
    rel = os.path.relpath(p, ROOT)
    client_side = re.search(r"['\"]use client['\"]", t) or re.search(r"(^|/)(widget|storefront|public|client)/", rel)
    if not client_side:
        continue
    if re.search(r"api\.myikas\.com/api/(v\d/)?admin|/api/v2/admin/mcp|api\.myikas\.com/api/v1/admin", t):
        add("§5.2", "BLOCKER", p, line_of(t, r"api\.myikas\.com"), "Client-side code calls the ikas Admin API directly (§10 #18) — güvenlik")
    elif re.search(r"api\.myikas\.com/api/sf", t):
        add("§5.2", "BILGI", p, line_of(t, r"api\.myikas\.com/api/sf"), "Client-side call to the anonymous Storefront API — exempt from §5.2 if no credentials are sent; document it in the README")
    elif "api.myikas.com" in t:
        add("§5.2", "UYARI", p, line_of(t, "api.myikas.com"), "Client-side reference to api.myikas.com — confirm it is not the Admin API")

# ---------------------------------------------------------------- §6 webhooks / §7 API actions
# concrete write markers only — a handler that merely logs is not a mutation
MUTATION_MARKERS = re.compile(r"AuthTokenManager\.(put|delete|update)|Manager\.(delete|update|put|create|upsert|markDeleted|markProcessed)|prisma\.\w+\.(update|delete|create|upsert|deleteMany|updateMany)|db\.(insert|update|delete)|mutations\.\w+\(|deleted\s*[:=]\s*true|unlink|appendFileSync|writeFileSync")
signed_inputs = [p for p, t in app_files.items() if is_route(p) and route_group(p) in ("webhook", "action")]
for p in signed_inputs:
    t = files[p]
    g = route_group(p)
    sec = "§6.1" if g == "webhook" else "§7.2"
    statuses = set(re.findall(r"status:\s*(\d{3})", t))
    verifies = bool(re.search(r"validateIkasWebhookSignature|getParsedIkasWebhookData|validateIkasWebhookMiddleware|createHmac", t))
    rejects = bool({"401", "403"} & statuses)
    mutates = bool(MUTATION_MARKERS.search(t))
    problems = []
    if not verifies:
        problems.append("no HMAC signature check")
    elif not rejects:
        problems.append("signature computed but no 401/403 path — result never enforced")
    if statuses <= {"200"}:
        problems.append("only ever returns 200")
    if re.search(r"catch[^{]*\{[^}]*status:\s*200|catch[^{]*\{[^}]*ok:\s*true", t, re.S):
        problems.append("catch block answers 200/ok")
    if problems:
        if g == "action":
            sev, why = "BLOCKER", "API action signature validation is documented as mandatory [docs:app-actions] (§10 #2) — review + güvenlik"
        elif mutates:
            sev, why = "BLOCKER", "handler mutates state on an unverified body (§10 #2/#3) — güvenlik"
        else:
            sev, why = "UYARI", "handler only logs (starter payment example does the same) — still verify before extending it"
        add(sec, sev, p, 1, f"{g} route: " + "; ".join(problems) + f" — {why} (F1)")
    if verifies and "500" not in statuses:
        add(sec, "UYARI", p, 1, "No 500 path — processing failures and a missing CLIENT_SECRET cannot be signalled to ikas retry")
    if not re.search(r"z\.object|zod|yup|valibot|safeParse", t):
        add(sec, "UYARI", p, 1, "Payload shape not validated with a schema before use")
    if verifies and not re.search(r"clientSecret|CLIENT_SECRET", t):
        add(sec, "UYARI", p, 1, "HMAC present but no visible secret reference — check fail-closed behaviour (SDK helper silently uses '' when the secret is unset)")
    if re.search(r"appendFileSync|writeFileSync", t) and re.search(r"signature|headers", t):
        add("§8", "BLOCKER", p, line_of(t, r"appendFileSync|writeFileSync"), "Webhook body/signature/headers written to disk (§10 #19) — güvenlik")
    if g == "webhook":
        if not re.search(r"store/app/deleted|store/app/uninstalled|store/authorizedApp/deleted|uninstall", t, re.I):
            add("§6.2", "BILGI", p, 1, "Webhook route does not match the uninstall scope (store/app/deleted) — is uninstall handled elsewhere?")
        elif "store/app/deleted" not in t:
            add("§6.2", "UYARI", p, line_of(t, r"uninstall|authorizedApp/deleted"), "Official uninstall scope 'store/app/deleted' [sdk: WebhookScope] is not in the matched list")
        if re.search(r"store/app/deleted|uninstall", t, re.I) and re.search(r"if\s*\(\s*!\s*authToken\s*\)", t) and not re.search(r"authToken\??\.deleted", t):
            add("§6.2", "UYARI", p, line_of(t, r"if\s*\(\s*!\s*authToken\s*\)"), "Uninstall handler short-circuits on missing token but not on an already-deleted one — second delivery re-runs cleanup with a dead token (F11)")
        if not re.search(r"markProcessed|dedupe|duplicate|processedAt|webhookEvent|idempot", t, re.I):
            add("§6.1", "BILGI", p, 1, "No idempotency/dedupe marker — the 3 retries will re-run the handler")
        if re.search(r"store/app/payment|merchantAppPayment|paymentStatus", t) and "PAID" not in t:
            sev = "BLOCKER" if mutates and not verifies else "UYARI"
            add("§6.4", sev, p, line_of(t, r"store/app/payment|merchantAppPayment|paymentStatus"), "Payment webhook handled without checking status === 'PAID' [docs:plans] (F13)" + (" — güvenlik" if sev == "BLOCKER" else ""))
        if re.search(r"paymentStatus|subscriptionKey", t) and "merchantAppPayment" not in t:
            add("§6.4", "BILGI", p, line_of(t, r"paymentStatus|subscriptionKey"), "Payment payload parsed with the older example shape (paymentStatus/subscriptionKey); docs show data.merchantAppPayment.{status,storeAppListingSubscriptionKey}")

has_webhook_route = any(route_group(p) == "webhook" for p in app_files if is_route(p))
injects = any(re.search(r"createStorefrontJSScript|saveStorefrontJSScript|createCampaign|saveWebhooks?", t) for t in files.values())
if not has_webhook_route:
    if injects:
        add("§6.2", "UYARI", None, None, "No webhook route, but the app creates storefront scripts/campaigns/webhooks — nothing removes them on uninstall and the token stays usable (§10 #17; not a documented prerequisite, starter has none)")
    else:
        add("§6.2", "BILGI", None, None, "No webhook route — uninstall (store/app/deleted) is not handled; the stored token stays valid after removal (starter has none)")

# ---------------------------------------------------------------- §7 iframe action pages
for p, t in client_pages.items():
    if re.search(r"actionRunId|idList|orderPackageId", t):
        if "closeApp" not in t and not imports_loader_hook(t):
            add("§7.1", "UYARI", p, 1, "Action page never calls AppBridgeHelper.closeApp() — merchant may be left in the modal")
        if "userLocale" not in t:
            add("§7.1", "BILGI", p, 1, "Action page ignores userLocale")
        if not re.search(r"try\s*\{[^}]*JSON\.parse|safeParse", t) and "quantityMap" in t:
            add("§7.1", "UYARI", p, line_of(t, "quantityMap"), "quantityMap parsed without a guard")

# ---------------------------------------------------------------- §8 secrets
for p, t in files.items():
    for m in re.finditer(r"NEXT_PUBLIC_[A-Z0-9_]*(SECRET|PASSWORD|PRIVATE|TOKEN|DATABASE)[A-Z0-9_]*", t):
        add("§8", "BLOCKER", p, t[: m.start()].count("\n") + 1, f"Secret-looking public env var {m.group(0)} is inlined into the browser bundle (F7) — güvenlik")
    if is_server_file(p):
        for m in re.finditer(r"console\.(log|info|debug)\([^\n]*(accessToken|access_token|refreshToken|refresh_token|clientSecret|client_secret|CLIENT_SECRET|\bsignature\b)", t):
            add("§8", "BLOCKER", p, t[: m.start()].count("\n") + 1, "ikas token / secret / signature written to server logs (§10 #10, F6) — güvenlik")
    if re.search(r"verify\([^)]*process\.env\.[A-Z_]+\s*\|\|\s*['\"]{2}", t):
        add("§8", "UYARI", p, line_of(t, r"verify\([^)]*process\.env"), "JWT verified with an empty-string fallback secret (§10 #15)")
    if re.search(r"password:\s*[^,\n]*\|\|\s*['\"]{2}", t):
        add("§8", "UYARI", p, line_of(t, r"password:\s*[^,\n]*\|\|\s*['\"]{2}"), "Session password falls back to an empty string (§10 #15)")

# env files: tracked → Blocker; untracked and not ignored → Uyarı
gi = read(os.path.join(ROOT, ".gitignore"))
for fn in sorted(os.listdir(ROOT)):
    if not fn.startswith(".env") or fn in (".env.example", ".env.sample", ".env.template"):
        continue
    ep = os.path.join(ROOT, fn)
    if not os.path.isfile(ep):
        continue
    content = read(ep)
    looks_real = any(not re.search(r"your_|example|placeholder|changeme|xxx|<", v, re.I)
                     for v in re.findall(r"^(?:CLIENT_SECRET|SECRET_COOKIE_PASSWORD|DATABASE_URL)\s*=\s*(\S{16,})", content, re.M))
    state = git_state.get(fn)
    if state == "ignored":
        continue
    if state == "untracked":
        add("§8", "UYARI" if looks_real else "BILGI", ep, 1, f"{fn} is untracked and not ignored by .gitignore — one `git add .` from being committed (F12)" + (" — contains real-looking values" if looks_real else ""))
    elif git_state or gi:
        # not untracked and not ignored → tracked (or git unavailable: fall back to pattern check)
        tracked = bool(git_state) or not re.search(r"^\s*\.env(\*|$|\s)", gi, re.M)
        if tracked and looks_real:
            add("§8", "BLOCKER", ep, 1, f"{fn} appears to be tracked in git with real values — güvenlik")
        elif tracked:
            add("§8", "UYARI", ep, 1, f"{fn} appears to be tracked in git — confirm it holds placeholders only")
ex = os.path.join(ROOT, ".env.example")
if os.path.exists(ex):
    for m in re.finditer(r"^(CLIENT_SECRET|SECRET_COOKIE_PASSWORD|DATABASE_URL)\s*=\s*(.+)$", read(ex), re.M):
        val = m.group(2).strip()
        if len(val) > 24 and not re.search(r"your_|example|placeholder|xxx|<|user:password|changeme|\{", val, re.I):
            add("§8", "UYARI", ex, read(ex)[: m.start()].count("\n") + 1, f"{m.group(1)} in .env.example looks like a real value")

# ---------------------------------------------------------------- §9 public endpoints
for p, t in app_files.items():
    if not is_route(p) or route_group(p) != "public":
        continue
    if not ("/public/" in rel_route(p) or rel_route(p).startswith("api/public")):
        add("§9", "BILGI", p, 1, "Treated as an anonymous public route (key-based, no JWT) — audit under §9, not §5.1")
    if not re.search(r"rateLimit|ratelimit|Ratelimit|limiter", t) and re.search(r"export async function POST", t):
        add("§9", "UYARI", p, 1, "Anonymous POST endpoint without a rate limiter (Blocker güvenlik if the write is unbounded and merchant-visible)")
    m = re.search(r"\b(value|price|amount|revenue|total|discount)\s*:\s*z\.", t)
    if m:
        add("§9", "BLOCKER", p, t[: m.start()].count("\n") + 1, f"Public schema accepts money-bearing field '{m.group(1)}' from the client (§10 #9) — güvenlik if stored or acted on")
    if not re.search(r"authorizedAppId|merchantId|publicKey|apiKey|key\b", t):
        add("§9", "BLOCKER", p, 1, "Public route has no visible merchant scoping (key / authorizedAppId) — güvenlik if it reads or writes merchant data")

# ---------------------------------------------------------------- §9 CORS for a storefront widget
widget_files = [p for p in files if re.search(r"(^|/)(widget|storefront)/", os.path.relpath(p, ROOT))]
for extra in ("public",):
    d = os.path.join(ROOT, extra)
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.endswith(".js") and re.search(r"widget|storefront|script", fn):
                files.setdefault(os.path.join(d, fn), read(os.path.join(d, fn)))
                widget_files.append(os.path.join(d, fn))
widget_fetches = [p for p in widget_files if re.search(r"fetch\(|XMLHttpRequest|axios", files[p]) and re.search(r"/api/", files[p])]
if widget_fetches:
    cors_anywhere = any(re.search(r"Access-Control-Allow-Origin", t) for t in files.values()) or re.search(r"Access-Control-Allow-Origin", read(os.path.join(ROOT, "next.config.js")) + read(os.path.join(ROOT, "next.config.ts")) + read(os.path.join(ROOT, "next.config.mjs")) + read(os.path.join(ROOT, "middleware.ts")) + read(os.path.join(ROOT, "src", "middleware.ts")))
    if not cors_anywhere:
        add("§9", "BLOCKER", widget_fetches[0], line_of(files[widget_fetches[0]], r"fetch\(|XMLHttpRequest|axios"), "Storefront widget fetches the app's /api from the merchant's domain but no Access-Control-Allow-Origin header is set anywhere (routes, next.config headers(), middleware) — widget silently fails cross-origin — işlevsel (verify on the real storefront)")

# ---------------------------------------------------------------- §4 i18n
if client_pages and not any("getDashboardLanguage" in t for t in files.values()):
    add("§4", "BILGI", None, None, "getDashboardLanguage() is never used — panel copy is single-language (§4 SHOULD: TR + EN for a TR-region listing)")

# ---------------------------------------------------------------- §2.1 / §11 scopes vs operations
scope_decl = None
for p, t in files.items():
    m = re.search(r"REQUIRED_SCOPES\s*=\s*\[([^\]]*)\]|scope[s]?\s*[:=]\s*['\"]([a-z_,\s]+)['\"]", t)
    if m and re.search(r"(read|write)_", m.group(1) or m.group(2) or ""):
        scope_decl = (p, m.group(1) or m.group(2))
        break
ops = set()
for t in files.values():
    ops.update(re.findall(r"\.(?:queries|mutations)\.(\w+)\(", t))
IDENTITY_OPS = {"getMerchant", "getAuthorizedApp", "getMerchantLicence", "me"}
# §11 — operation-name keyword → scope family (heuristic; only zero-operation families are flagged)
FAMILY = {
    "order": "orders", "package": "orders", "fulfil": "orders", "shipment": "orders",
    "product": "products", "variant": "products", "category": "products", "brand": "products", "vendor": "products", "tag": "products", "attribute": "products",
    "customer": "customers", "address": "customers",
    "campaign": "campaigns", "coupon": "campaigns", "discount": "campaigns", "promotion": "campaigns",
    "stock": "inventories", "inventor": "inventories",
    "storefront": "storefronts", "script": "storefronts", "theme": "storefronts",
}
used_families = {}
for op in ops - IDENTITY_OPS:
    lo = op.lower()
    fam = next((f for k, f in FAMILY.items() if k in lo), None)
    if fam:
        used_families.setdefault(fam, set()).add(op)
if scope_decl:
    p, raw = scope_decl
    scopes = sorted(set(re.findall(r"(?:read|write)_[a-z]+", raw)))
    add("§2.1", "BILGI", p, line_of(files[p], r"REQUIRED_SCOPES|scope"), f"Requested scopes: {', '.join(scopes) if scopes else raw.strip()}; operations seen: {', '.join(sorted(ops)) or 'none'}")
    by_family = {}
    for sc in scopes:
        fam = sc.split("_", 1)[1] if "_" in sc else sc
        by_family.setdefault(fam, []).append(sc)
    for fam, scs in sorted(by_family.items()):
        if ops and fam not in used_families:
            add("§2.1", "UYARI", p, line_of(files[p], re.escape(scs[0])), f"{', '.join(scs)} requested but no {fam} operation is called — least-privilege guidance [docs:admin-app] (§10 #16); confirm or drop")
    requested_families = {sc.split("_", 1)[1] for sc in scopes if "_" in sc}
    for fam, fam_ops in sorted(used_families.items()):
        if fam not in requested_families:
            need = "write_storefronts" if fam == "storefronts" else f"read_{fam}/write_{fam}"
            add("§2.1", "UYARI", p, line_of(files[p], r"REQUIRED_SCOPES|scope"), f"{', '.join(sorted(fam_ops))} called but no {fam} scope ({need}) is requested — the call fails with a permission error at runtime (işlevsel; verify against the Partner-panel scope list)")
if has_webhook_route and not any(re.search(r"mutations\.saveWebhooks?\(", t) for t in files.values()):
    add("§6.2", "BILGI", None, None, "Webhook route exists but saveWebhooks is never called — endpoint must be registered in the Partner panel (add a DECLARE row)")

# ---------------------------------------------------------------- output
ORDER = {"BLOCKER": 0, "UYARI": 1, "BILGI": 2}
findings.sort(key=lambda f: (ORDER[f["severity"]], f["section"], f["file"], f["line"] or 0))

if AS_JSON:
    for f in findings:
        f["git"] = git_tag(os.path.join(ROOT, f["file"])).strip(" []") if f["file"] != "-" else ""
    print(json.dumps({"root": ROOT, "findings": findings}, indent=2, ensure_ascii=False))
else:
    print(f"ikas-app-preflight scan — {ROOT}")
    print(f"sdk={'yes' if has_sdk else 'no'} app-helpers={'yes' if has_bridge else 'no'} ikas.config.json={'yes' if has_cfg else 'no'} "
          f"routes={sum(1 for p in app_files if is_route(p))} client-pages={len(client_pages)} git={'yes' if git_state or os.path.isdir(os.path.join(ROOT, '.git')) else 'no'}"
          + (f" ({git_note})" if git_note else ""))
    print()
    for f in findings:
        loc = (f["file"] + (f":{f['line']}" if f["line"] else "") + git_tag(os.path.join(ROOT, f["file"]))) if f["file"] != "-" else "-"
        print(f"{f['section']:<6} {f['severity']:<8} {loc}\n       {f['msg']}")
    counts = {k: sum(1 for f in findings if f["severity"] == k) for k in ORDER}
    print()
    print(f"BLOCKER: {counts['BLOCKER']}  UYARI: {counts['UYARI']}  BILGI: {counts['BILGI']}")
    print("Evidence only — confirm each hit by reading the code against references/app-review.md.")
