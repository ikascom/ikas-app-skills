#!/usr/bin/env python3
"""ikas Admin App pre-review scanner — evidence pass for the ikas-app-preflight skill.

Usage: python3 scan.py [project root] [--json]

Walks a Next.js (App Router) ikas app and reports pattern-level evidence for the
§ rules in references/app-review.md. It collects evidence only: every line is
"§ | severity | file:line | message". The semantic verdict (is this really a
blocker in context?) is made by the skill while reading the code — a hit here is
a place to look, a miss here is not a pass.

Severities: BLOCKER, UYARI, BILGI. Exit code is 0 always; use --json for tooling.
"""
import json
import os
import re
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
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not (dirpath == ROOT and d == "public")]  # Next.js static assets / built bundles
        for fn in filenames:
            if fn.endswith(SRC_EXT):
                yield os.path.join(dirpath, fn)


# ---------------------------------------------------------------- project detection
pkg_path = os.path.join(ROOT, "package.json")
pkg = {}
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
    base = os.path.basename(p)
    return base.startswith("route.") and p in app_files


def route_group(p):
    r = rel_route(p).lower()
    if "/oauth/" in r or r.startswith("api/oauth"):
        return "oauth"
    if "webhook" in r:
        return "webhook"
    if "/public/" in r or r.startswith("api/public"):
        return "public"
    if "action" in r:
        return "action"
    return "api" if r.startswith("api/") else "page"


# ---------------------------------------------------------------- §2 OAuth
callback_files = [p for p, t in files.items() if "getTokenWithAuthorizationCode" in t]
authorize_files = [p for p, t in files.items() if re.search(r"getOAuthUrl|/authorize\?|oauth/authorize", t) and "client_id" in t]

if not callback_files:
    add("§2.2", "BILGI", None, None, "No OAuth callback (getTokenWithAuthorizationCode) found — hand-rolled exchange or headless app? Verify manually")
for p in callback_files:
    t = files[p]
    if not re.search(r"validateCodeSignature|createHmac", t):
        add("§2.2", "BLOCKER", p, 1, "Callback does not verify the authorization-code signature (HMAC-SHA256 of code with CLIENT_SECRET)")
    elif "timingSafeEqual" not in t and not any("timingSafeEqual" in files[q] for q in files if "validateCodeSignature" in files[q]):
        add("§2.2", "UYARI", p, line_of(t, r"validateCodeSignature|createHmac"), "Signature compared without timingSafeEqual")
    if "state" in t:
        if not re.search(r"session\.state\s*=\s*undefined|delete\s+session\.state|state:\s*undefined|consumeState|clearState", t):
            add("§2.2", "UYARI", p, line_of(t, r"\bstate\b"), "State is checked but never consumed/cleared before the exchange — replay possible")
        if re.search(r"if\s*\(\s*state\s*&&\s*session\.state", t):
            add("§2.2", "UYARI", p, line_of(t, r"if\s*\(\s*state\s*&&\s*session\.state"), "State check skipped whenever the callback omits `state` (`if (state && session.state …)`) — attacker can drop the param")
    else:
        add("§2.2", "UYARI", p, 1, "Callback never references `state` — no CSRF binding at all")
    m = re.search(r"storeName[^\n]*\|\|\s*['\"]api['\"]", t)
    if m and not re.search(r"searchParams\.get\(['\"]storeName['\"]\)", t):
        add("§2.2", "BLOCKER", p, line_of(t, re.escape(m.group(0))), "storeName falls back to 'api' without reading the callback's storeName query param (§10 #7)")
    elif m:
        add("§2.2", "BILGI", p, line_of(t, re.escape(m.group(0))), "'api' storeName fallback still present (query param is read first — acceptable, but prefer failing loudly)")
    if re.search(r"catch[^\n]*\{[^}]*(Callback failed|callback failed)", t, re.S) and not re.search(r"response\?\.status|\.status\b.*\.data|TokenExchangeError|error\.response", t):
        add("§2.2", "UYARI", p, line_of(t, r"Callback failed"), "Token-exchange failures are reported as an opaque 'Callback failed' (§10 #8)")
    if re.search(r"console\.(log|info|debug)\([^)]*(token|code|params|searchParams)", t, re.I):
        add("§8", "BLOCKER", p, line_of(t, r"console\.(log|info|debug)\([^)]*(token|code|params|searchParams)"), "Callback logs code/token/params (§10 #10)")
    if not re.search(r"getMerchant|getAuthorizedApp", t):
        add("§2.2", "UYARI", p, 1, "Callback does not resolve merchant/authorizedApp identity server-side after the exchange")

for p in authorize_files:
    t = files[p]
    if re.search(r"Math\.random\(\)", t):
        add("§2.1", "BLOCKER", p, line_of(t, r"Math\.random\(\)"), "OAuth state generated with Math.random() (§10 #1)")
    elif not re.search(r"randomBytes|randomUUID|crypto\.getRandomValues|nanoid", t):
        add("§2.1", "UYARI", p, 1, "Could not find a CSPRNG for the OAuth state (randomBytes/randomUUID)")
    if "state" not in t:
        add("§2.1", "BLOCKER", p, 1, "Authorize route sends no `state` parameter")

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
                add("§8", "BLOCKER", ikas_cfg_path, 1, f"oauthRedirectPath '{redirect_path}' has no matching route handler under {os.path.relpath(app_dir, ROOT)}")
        for action in cfg.get("actions", []) or []:
            add("§7", "BILGI", ikas_cfg_path, 1, f"Action configured: {json.dumps(action)[:120]} — verify its page/route exists and follows §7")
    except json.JSONDecodeError:
        add("§8", "UYARI", ikas_cfg_path, 1, "ikas.config.json is not valid JSON")

# deploy URL normalization — flag direct URL concatenation of the raw env
for p, t in files.items():
    m = re.search(r"\$\{process\.env\.NEXT_PUBLIC_DEPLOY_URL\}/|process\.env\.NEXT_PUBLIC_DEPLOY_URL\s*\+\s*['\"`]/", t)
    if m and not re.search(r"replace\(\s*/\\/\+?\$/|new URL\(|trimEnd\(['\"]/|endsWith\(['\"]/", t[: m.start()]):
        add("§8", "UYARI", p, t[: m.start()].count("\n") + 1, "Raw NEXT_PUBLIC_DEPLOY_URL concatenated into a URL without trailing-slash normalization (§10 #6)")

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


for p, t in client_pages.items():
    r = rel_route(p)
    iframe_signal = re.search(r"getNewToken|getTokenForIframeApp|getAuthorizedAppId|useIkasToken|AppBridgeHelper|useSearchParams|actionRunId", t)
    exempt = re.search(r"authorize-store|login|landing", r)
    if iframe_signal and "closeLoader" not in t and not imports_loader_hook(t) and not exempt:
        add("§3.1", "BLOCKER", p, line_of(t, r"useEffect\(|export default") or 1, "Iframe-facing page never calls AppBridgeHelper.closeLoader() (directly or via an imported hook) (§10 #4)")
    if "useSearchParams" in t and "Suspense" not in t:
        add("§3.3", "BLOCKER", p, line_of(t, "useSearchParams"), "useSearchParams() used without a <Suspense> boundary (§10 #14)")

for p, t in files.items():
    for m in re.finditer(r"window\.location\.(replace|assign|href)\s*\(?\s*=?\s*\(?\s*(redirectUrl|adminUrl|[a-zA-Z_.]*admin[a-zA-Z_.]*)", t, re.I):
        context = t[max(0, m.start() - 800): m.start()]
        window_guard = re.search(r"window\.self\s*!==?\s*window\.top|window\.top\s*!==?\s*window\.self|inIframe|isIframe", context)
        if not window_guard:
            add("§3.3", "BLOCKER", p, t[: m.start()].count("\n") + 1, "Top-level redirect to the Admin URL without an iframe guard — install loop risk (§10 #5)")
        break

# ---------------------------------------------------------------- §5 backend routes
auth_markers = re.compile(r"getUserFromRequest|withMerchant|verifyToken|jwt\.verify|jsonwebtoken|verifyJwt|requireAuth")
for p, t in app_files.items():
    if not is_route(p):
        continue
    g = route_group(p)
    if g == "api" and not auth_markers.search(t):
        add("§5.1", "BLOCKER", p, 1, "Admin API route has no JWT verification marker (getUserFromRequest/withMerchant/…)")
    elif g == "api" and "withMerchant" not in t and re.search(r"AuthTokenManager\.get|getAuthToken|findUnique", t) and not re.search(r"\.deleted|isDeleted|uninstalled", t):
        add("§5.1", "UYARI", p, line_of(t, r"AuthTokenManager\.get|getAuthToken|findUnique"), "Route loads the ikas token itself but never checks the uninstalled/deleted flag — bypasses the shared wrapper (§5.1, §6.2)")
    if g == "api" and re.search(r"(body|json|searchParams)[^\n]*(authorizedAppId|merchantId)", t):
        add("§5.1", "UYARI", p, line_of(t, r"(body|json|searchParams)[^\n]*(authorizedAppId|merchantId)"), "authorizedAppId/merchantId read from request input — must come from the verified JWT")
    if re.search(r"gql`|graphql`|query\s*\{|mutation\s*\{", t) and g in ("api", "action"):
        add("§5.3", "UYARI", p, line_of(t, r"gql`|graphql`|query\s*\{|mutation\s*\{"), "Inline GraphQL document in a route handler (§10 #11)")

for p, t in files.items():
    rel = os.path.relpath(p, ROOT)
    client_side = re.search(r"['\"]use client['\"]", t) or re.search(r"(^|/)(widget|storefront|public|client)/", rel)
    if not client_side:
        continue
    if re.search(r"api\.myikas\.com/api/(v\d/)?admin|/api/v2/admin/mcp|api\.myikas\.com/api/v1/admin", t):
        add("§5.2", "BLOCKER", p, line_of(t, r"api\.myikas\.com"), "Client-side code calls the ikas Admin API directly (§10 #18)")
    elif re.search(r"api\.myikas\.com/api/sf", t):
        add("§5.2", "BILGI", p, line_of(t, r"api\.myikas\.com/api/sf"), "Client-side call to the anonymous Storefront API — exempt from §5.2 if no credentials are sent; document it in the README")
    elif "api.myikas.com" in t:
        add("§5.2", "UYARI", p, line_of(t, "api.myikas.com"), "Client-side reference to api.myikas.com — confirm it is not the Admin API")

# ---------------------------------------------------------------- §6 webhooks / §7 API actions
signed_inputs = [p for p, t in app_files.items() if is_route(p) and route_group(p) in ("webhook", "action")]
for p in signed_inputs:
    t = files[p]
    g = route_group(p)
    sec = "§6.1" if g == "webhook" else "§7.2"
    if not re.search(r"validateIkasWebhookSignature|getParsedIkasWebhookData|createHmac", t):
        add(sec, "BLOCKER", p, 1, f"{g} route does not verify the ikas HMAC signature (§10 #2)")
    statuses = set(re.findall(r"status:\s*(\d{3})", t))
    if statuses <= {"200"}:
        add(sec, "BLOCKER", p, 1, f"{g} route only ever returns 200 — invalid/unsigned/failed deliveries are hidden from ikas retry (§10 #3)")
    else:
        if "401" not in statuses and "403" not in statuses:
            add(sec, "UYARI", p, 1, "No 401/403 path for a bad signature")
        if "500" not in statuses:
            add(sec, "UYARI", p, 1, "No 500 path for processing failures — ikas cannot retry")
    if re.search(r"catch[^{]*\{[^}]*status:\s*200|catch[^{]*\{[^}]*ok:\s*true", t, re.S):
        add(sec, "BLOCKER", p, line_of(t, r"catch"), "catch block answers 200/ok — failures are swallowed (§10 #3)")
    if not re.search(r"z\.object|zod|yup|valibot|safeParse", t):
        add(sec, "UYARI", p, 1, "Payload shape is not validated with a schema before use")
    if not re.search(r"clientSecret|CLIENT_SECRET", t) and re.search(r"createHmac", t):
        add(sec, "UYARI", p, 1, "HMAC present but no obvious secret reference — check fail-closed behaviour when the secret is missing")
    if g == "webhook":
        if not re.search(r"store/app/deleted|store/app/uninstalled|store/authorizedApp/deleted|uninstall", t, re.I):
            add("§6.2", "UYARI", p, 1, "Webhook route does not handle an uninstall scope (store/app/deleted) — is uninstall handled elsewhere?")
        elif "store/app/deleted" not in t:
            add("§6.2", "UYARI", p, line_of(t, r"uninstall|authorizedApp/deleted"), "Official uninstall scope 'store/app/deleted' is not in the matched list")
        if not re.search(r"markProcessed|dedupe|duplicate|processedAt|webhookEvent|idempot", t, re.I):
            add("§6.1", "BILGI", p, 1, "No idempotency/dedupe marker — retries will re-run the handler")
        if re.search(r"store/app/payment|merchantAppPayment", t) and "PAID" not in t:
            add("§6.4", "BLOCKER", p, line_of(t, r"store/app/payment|merchantAppPayment"), "Payment webhook handled without checking status === 'PAID'")

if not any(route_group(p) == "webhook" for p in app_files if is_route(p)):
    add("§6.2", "UYARI", None, None, "No webhook route found — uninstall cleanup (token invalidation, injected script removal) is not handled")

# ---------------------------------------------------------------- §7 iframe action pages
for p, t in client_pages.items():
    if re.search(r"actionRunId|idList|orderPackageId", t):
        if "closeApp" not in t and not imports_loader_hook(t):
            add("§7.1", "UYARI", p, 1, "Action page never calls AppBridgeHelper.closeApp() — merchant may be left in the modal")
        if "userLocale" not in t:
            add("§7.1", "BILGI", p, 1, "Action page ignores userLocale")

# ---------------------------------------------------------------- §8 secrets
for p, t in files.items():
    for m in re.finditer(r"NEXT_PUBLIC_[A-Z0-9_]*(SECRET|PASSWORD|PRIVATE|TOKEN|DATABASE)[A-Z0-9_]*", t):
        add("§8", "BLOCKER", p, t[: m.start()].count("\n") + 1, f"Secret-looking public env var {m.group(0)} is inlined into the browser bundle")
    for m in re.finditer(r"console\.(log|info|debug)\([^\n]*(accessToken|refreshToken|clientSecret|client_secret|jwt|signature|params\.toString|searchParams\.toString|callback params)", t, re.I):
        add("§8", "BLOCKER", p, t[: m.start()].count("\n") + 1, "Token/secret/signature written to console (§10 #10)")
    if re.search(r"verify\([^)]*process\.env\.[A-Z_]+\s*\|\|\s*['\"]{2}", t):
        add("§8", "UYARI", p, line_of(t, r"verify\([^)]*process\.env"), "JWT verified with an empty-string fallback secret (§10 #15)")
    if re.search(r"password:\s*[^,\n]*\|\|\s*['\"]{2}", t):
        add("§8", "UYARI", p, line_of(t, r"password:\s*[^,\n]*\|\|\s*['\"]{2}"), "Session password falls back to an empty string (§10 #15)")

for env_name in (".env", ".env.local", ".env.production"):
    ep = os.path.join(ROOT, env_name)
    if os.path.exists(ep):
        gi = read(os.path.join(ROOT, ".gitignore"))
        if not re.search(r"^\s*\.env(\*|$|\s)", gi, re.M) and env_name not in gi:
            add("§8", "BLOCKER", ep, 1, f"{env_name} exists but .gitignore does not ignore it")
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
    if re.search(r"Access-Control-Allow-Origin[^\n]*\*", t) or "public" in rel_route(p):
        if not re.search(r"rateLimit|ratelimit|Ratelimit|limiter", t) and re.search(r"export async function POST", t):
            add("§9", "UYARI", p, 1, "Anonymous POST endpoint without a rate limiter")
        m = re.search(r"\b(value|price|amount|revenue|total|discount)\s*:\s*z\.", t)
        if m:
            add("§9", "BLOCKER", p, t[: m.start()].count("\n") + 1, f"Public schema accepts money-bearing field '{m.group(1)}' from the client (§10 #9)")
        if not re.search(r"authorizedAppId|merchantId|publicKey|apiKey|key\b", t):
            add("§9", "UYARI", p, 1, "Public route has no visible merchant scoping (key / authorizedAppId)")

# ---------------------------------------------------------------- §2.1 scopes vs usage
scope_decl = None
for p, t in files.items():
    m = re.search(r"REQUIRED_SCOPES\s*=\s*\[([^\]]*)\]|scope[s]?\s*[:=]\s*['\"]([a-z_,\s]+)['\"]", t)
    if m and ("write_" in (m.group(1) or m.group(2) or "") or "read_" in (m.group(1) or m.group(2) or "")):
        scope_decl = (p, m.group(1) or m.group(2))
        break
ops = set()
for t in files.values():
    ops.update(re.findall(r"\.(?:queries|mutations)\.(\w+)\(", t))
FAMILY = {
    "order": "orders", "package": "orders", "fulfil": "orders",
    "product": "products", "variant": "products", "category": "products", "brand": "products", "vendor": "products",
    "customer": "customers", "address": "customers",
    "campaign": "campaigns", "coupon": "campaigns", "discount": "campaigns",
    "stock": "inventories", "inventor": "inventories",
    "storefront": "storefront", "script": "storefront", "theme": "storefront",
}
used_families = {}
for op in ops:
    lo = op.lower()
    fam = next((f for k, f in FAMILY.items() if k in lo), None)
    if fam:
        used_families.setdefault(fam, set()).add(op)
if scope_decl:
    p, raw = scope_decl
    scopes = sorted(set(re.findall(r"(?:read|write)_[a-z]+", raw)))
    add("§2.1", "BILGI", p, line_of(files[p], r"REQUIRED_SCOPES|scope"), f"Requested scopes: {', '.join(scopes) if scopes else raw.strip()}; operations seen: {', '.join(sorted(ops)) or 'none'}")
    for sc in scopes:
        fam = sc.split("_", 1)[1].rstrip("s") if "_" in sc else sc
        fam = {"storefront": "storefront", "inventorie": "inventories", "inventory": "inventories"}.get(fam, fam + "s")
        if ops and fam not in used_families:
            add("§2.1", "UYARI", p, line_of(files[p], re.escape(sc)), f"Scope {sc} requested but no {fam} operation is called (§10 #16) — confirm or drop")
if not any(re.search(r"mutations\.saveWebhooks?\(", t) for t in files.values()) and any(route_group(p) == "webhook" for p in app_files if is_route(p)):
    add("§6.2", "BILGI", None, None, "Webhook route exists but saveWebhook is never called — the endpoint must be registered in the Partner panel (add a DECLARE row)")

# ---------------------------------------------------------------- output
ORDER = {"BLOCKER": 0, "UYARI": 1, "BILGI": 2}
findings.sort(key=lambda f: (ORDER[f["severity"]], f["section"], f["file"], f["line"] or 0))

if AS_JSON:
    print(json.dumps({"root": ROOT, "findings": findings}, indent=2, ensure_ascii=False))
else:
    print(f"ikas-app-preflight scan — {ROOT}")
    print(f"sdk={'yes' if has_sdk else 'no'} app-helpers={'yes' if has_bridge else 'no'} ikas.config.json={'yes' if has_cfg else 'no'} "
          f"routes={sum(1 for p in app_files if is_route(p))} client-pages={len(client_pages)}")
    print()
    for f in findings:
        loc = f["file"] + (f":{f['line']}" if f["line"] else "") if f["file"] != "-" else "-"
        print(f"{f['section']:<6} {f['severity']:<8} {loc}\n       {f['msg']}")
    counts = {k: sum(1 for f in findings if f["severity"] == k) for k in ORDER}
    print()
    print(f"BLOCKER: {counts['BLOCKER']}  UYARI: {counts['UYARI']}  BILGI: {counts['BILGI']}")
    print("Evidence only — confirm each hit by reading the code against references/app-review.md.")
