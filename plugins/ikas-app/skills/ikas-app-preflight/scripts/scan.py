#!/usr/bin/env python3
"""ikas Admin App pre-review scanner — evidence pass for the ikas-app-preflight skill.

Usage: python3 scan.py [project root] [--json] [--section oauth|iframe|webhooks|actions|secrets|public]

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

ROOT = os.path.abspath(next((a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--section"), "."))
AS_JSON = "--json" in sys.argv
SECTION_MAP = {"oauth": ("§2",), "iframe": ("§3", "§4"), "webhooks": ("§6",), "actions": ("§7",), "secrets": ("§8", "§5.1", "§5.3"), "public": ("§9", "§5.2")}
_sec = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--section" and i + 1 < len(sys.argv)), None)
SECTION_FILTER = SECTION_MAP.get(_sec) if _sec else None
if _sec and not SECTION_FILTER:
    print(f"unknown --section '{_sec}' (use {', '.join(SECTION_MAP)})")
    sys.exit(0)

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
pages_router = False
if not app_dir:
    # Pages Router fallback: pages/api/**.ts are routes, pages/**.tsx are (client-rendered) pages
    app_dir = next((d for d in (os.path.join(ROOT, "src", "pages"), os.path.join(ROOT, "pages")) if os.path.isdir(d)), None)
    pages_router = bool(app_dir)
    if pages_router:
        add("§1", "BILGI", None, None, f"Pages Router project ({os.path.relpath(app_dir, ROOT)}) — routes = pages/api/**, pages = pages/**; the official examples use the App Router, so read §3 evidence by hand")
    else:
        add("§1", "BILGI", None, None, "No App Router directory (src/app or app) and no pages/ — route-based checks skipped")

files = {p: read(p) for p in walk_src()}
app_files = {p: t for p, t in files.items() if app_dir and p.startswith(app_dir + os.sep)}


def rel_route(p):
    return os.path.relpath(p, app_dir).replace(os.sep, "/") if app_dir else p


def is_route(p):
    if pages_router:
        return p in app_files and rel_route(p).startswith("api/") and not os.path.basename(p).startswith("_")
    return os.path.basename(p).startswith("route.") and p in app_files


def is_page_file(p):
    if pages_router:
        return p in app_files and not rel_route(p).startswith("api/") and not os.path.basename(p).startswith("_") and p.endswith((".tsx", ".jsx"))
    return os.path.basename(p).startswith("page.")


# ---------------------------------------------------------------- local import resolution
# Routes often delegate the signature / JWT / schema check to a helper module
# (`lib/webhooks.ts`, `lib/auth-helpers.ts`). Markers are searched in the route
# file plus the local modules it imports (two levels), so a check that lives in
# a helper is not reported as missing. Still evidence, not proof.
alias_map = {}
for cfg_name in ("tsconfig.json", "jsconfig.json"):
    cfg_p = os.path.join(ROOT, cfg_name)
    if os.path.exists(cfg_p):
        try:
            raw = re.sub(r"//[^\n]*|/\*.*?\*/", "", read(cfg_p), flags=re.S)
            raw = re.sub(r",\s*([}\]])", r"\1", raw)
            paths = json.loads(raw).get("compilerOptions", {}).get("paths", {})
            for k, v in paths.items():
                if v:
                    alias_map[k.rstrip("*")] = os.path.join(ROOT, v[0].rstrip("*"))
        except (json.JSONDecodeError, AttributeError):
            pass
        break
if not alias_map:
    alias_map["@/"] = os.path.join(ROOT, "src") if os.path.isdir(os.path.join(ROOT, "src")) else ROOT

IMPORT_RE = re.compile(r"""(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""")


def resolve_import(from_file, spec):
    if spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(from_file), spec))
    else:
        hit = next((a for a in alias_map if spec.startswith(a)), None)
        if not hit:
            return None
        base = os.path.normpath(os.path.join(alias_map[hit], spec[len(hit):]))
    for cand in (base,) + tuple(base + e for e in SRC_EXT) + tuple(os.path.join(base, "index" + e) for e in SRC_EXT):
        if cand in files:
            return cand
    return None


def local_imports(p, depth=2, seen=None):
    seen = seen if seen is not None else set()
    for spec in IMPORT_RE.findall(files.get(p, "")):
        q = resolve_import(p, spec)
        if q and q not in seen and q != p:
            seen.add(q)
            if depth > 1:
                local_imports(q, depth - 1, seen)
    return seen


_expanded = {}


def expanded(p):
    """Route text plus the text of its local imports (2 levels)."""
    if p not in _expanded:
        _expanded[p] = "\n".join([files.get(p, "")] + [files[q] for q in sorted(local_imports(p))])
    return _expanded[p]


def route_text(p):
    """Own text; for a pure re-export (`export { POST } from '../payment/route'`) the target's text."""
    t = files.get(p, "")
    m = re.search(r"export\s*\{[^}]*\}\s*from\s*['\"]([^'\"]+)['\"]", t)
    if m and len(re.sub(r"//[^\n]*", "", t).strip()) < 200:
        q = resolve_import(p, m.group(1))
        if q:
            return files[q]
    return t


def via(p, pattern):
    """Name the imported module where `pattern` is found, or '' when it is in the route itself."""
    if re.search(pattern, files.get(p, "")):
        return ""
    for q in sorted(local_imports(p)):
        if re.search(pattern, files[q]):
            return f" (via {os.path.relpath(q, ROOT)})"
    return ""


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
        # name says nothing, body does: an HMAC over a signed envelope is a webhook / API action whatever the path
        if re.search(r"validateIkasWebhookSignature|getParsedIkasWebhookData|validateIkasWebhookMiddleware", expanded(p)):
            return "webhook"
        if re.search(r"createHmac\(", expanded(p)) and re.search(r"actionRunId|idList", expanded(p)):
            return "action"
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
    tx = expanded(p)
    has_sig = bool(re.search(r"validateCodeSignature|createHmac", tx))
    has_state = bool(re.search(r"session\.state|savedState|stateStore|expectedState", tx))
    if not has_sig and not has_state:
        add("§2.2", "UYARI", p, 1, "Callback verifies neither the code signature (HMAC-SHA256(code, CLIENT_SECRET)) nor the session state — documented pattern checks both when present [docs:auth-steps]")
    elif not has_sig:
        add("§2.2", "UYARI", p, 1, "Callback does not verify the `signature` query param (HMAC-SHA256(code, CLIENT_SECRET)) [docs:auth-steps] — defence in depth, not a hole")
    elif "timingSafeEqual" not in tx:
        add("§2.2", "BILGI", p, line_of(t, r"validateCodeSignature|createHmac"), "Signature compared with === (starter does the same); timingSafeEqual is hardening (F9)")
    if has_state and not re.search(r"delete\s+session\.state|session\.state\s*=\s*undefined|state:\s*undefined|consumeState|clearState", tx):
        add("§2.2", "UYARI", p, line_of(t, r"session\.state"), "State is compared but never cleared after the exchange — replayed callback passes the state check")
    if re.search(r"catch[^\n]*\{[^}]*(Callback failed|callback failed|tamamlanamadı)", t, re.S) and not re.search(r"response\?\.status|\.status\b.*\.data|TokenExchangeError|error\.response", t):
        logs_error = re.search(r"catch\s*\((\w+)\)[^}]*console\.error\([^)]*\b\1\b", t, re.S)
        add("§2.2", "UYARI", p, line_of(t, r"Callback failed|tamamlanamadı"), "Token-exchange failures reported as an opaque 'Callback failed' (§10 #8)" + ("" if logs_error else " — and the caught error is not logged at all, install failures are undiagnosable"))
    requires_state = False
    for m in re.finditer(r"if\s*\(\s*!\s*(state|params\.state)\s*(\|\||\))", tx):
        if not re.search(r"session\.state|expectedState|savedState", tx[max(0, m.start() - 300): m.start()]):
            requires_state = True  # `if (!state)` outside a session-state guard
    schema_state = re.search(r"state:\s*z\.string\([^\n]*", tx)
    if schema_state and "optional" not in schema_state.group(0) and "nullish" not in schema_state.group(0):
        requires_state = True
    if requires_state or re.search(r"install link has expired|missing_code", tx):
        add("§2.2", "BLOCKER", p, line_of(t, r"!\s*state|state:\s*z\.string|expired|missing_code") or 1, "Callback requires `state` — Admin-initiated installs arrive with code+storeName only, so every reviewer install fails [observed] R4 (§10 #20) — işlevsel")
    elif has_state and re.search(r"if\s*\(\s*(params\.)?(expectedState|session\.state)\s*\)", tx) and not re.search(r"\bstate\s*&&\s*(params\.)?(session\.state|expectedState)|(session\.state|expectedState)\s*&&\s*(params\.)?state\b", tx):
        add("§2.2", "UYARI", p, line_of(t, r"validateOAuthProof|session\.state|expectedState") or 1, "State is required whenever the session holds one — documented pattern compares only when both exist (`state && session.state && …`); a stale session state rejects a legitimate Admin-initiated callback [docs:auth-steps]")
    persists = re.search(r"AuthTokenManager\.put|\.(create|upsert|update)\(|INSERT|db\.", tx)
    if not re.search(r"getMerchant|getAuthorizedApp", tx) and not persists:
        add("§2.2", "BLOCKER", p, 1, "Callback neither resolves the merchant (getMerchant/getAuthorizedApp) nor persists the token server-side — the install is not bound to the store, the merchant has to 'connect ikas' by hand later [observed] R3 (§10 #21) — işlevsel")
    elif re.search(r"session\.(accessToken|refreshToken|access_token|refresh_token)\s*=", tx):
        add("§2.3", "UYARI", p, line_of(t, r"session\.(accessToken|refreshToken|access_token|refresh_token)\s*="), "ikas token written to the browser session cookie instead of a server-side row keyed by authorizedAppId — sealed cookie, so not a leak, but nothing server-side knows the merchant (R3 pattern)")
    if not re.search(r"getMerchant|getAuthorizedApp", t):
        add("§2.2", "UYARI", p, 1, "Callback does not resolve merchant/authorizedApp identity server-side after the exchange (getMerchant + getAuthorizedApp) [docs:callback-api]")
    elif re.search(r"getAuthorizedApp", tx) and not re.search(r"isSuccess|\.errors\b", tx):
        add("§2.3", "UYARI", p, line_of(t, r"getAuthorizedApp") or 1, "getAuthorizedApp result used without an isSuccess/errors check — the SDK never throws, an errored result has no `deleted`/`storeAppId`, so the guard passes on failure [sdk] (fail-open)")
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
            if not any(os.path.exists(os.path.join(target, f"route.{ext}")) for ext in ("ts", "js", "tsx")) and not any(os.path.exists(target + f".{ext}") for ext in ("ts", "js", "tsx")):
                add("§8", "BLOCKER", ikas_cfg_path, 1, f"oauthRedirectPath '{redirect_path}' has no matching route handler under {os.path.relpath(app_dir, ROOT)} — işlevsel")
        for action in cfg.get("actions", []) or []:
            url = action.get("actionUrl") or ""
            path = re.sub(r"^https?://[^/]+", "", url).split("?")[0].strip("/")
            method = action.get("method")
            target = os.path.join(app_dir, path) if app_dir and path else None
            kinds = ("route",) if method == "api" else ("page",)
            exists = target and (any(os.path.exists(os.path.join(target, f"{k}.{ext}")) for k in kinds for ext in ("ts", "tsx", "js", "jsx"))
                                 or any(os.path.exists(target + f".{ext}") or os.path.exists(os.path.join(target, f"index.{ext}")) for ext in ("ts", "tsx", "js", "jsx")))
            label = f"{action.get('name')!r} ({method}, {action.get('type')}) → /{path}"
            if exists:
                add("§7", "BILGI", ikas_cfg_path, 1, f"Action {label} — {kinds[0]} exists; audit under §7.{'2' if method == 'api' else '1'}")
            else:
                add("§7", "UYARI", ikas_cfg_path, 1, f"Action {label} — no matching {kinds[0]} under {os.path.relpath(app_dir, ROOT) if app_dir else 'app'}; Partner-panel URL may differ from the local config, confirm")
    except json.JSONDecodeError:
        add("§8", "UYARI", ikas_cfg_path, 1, "ikas.config.json is not valid JSON")

# deploy URL normalization
for p, t in files.items():
    m = re.search(r"\$\{process\.env\.NEXT_PUBLIC_DEPLOY_URL\}/|process\.env\.NEXT_PUBLIC_DEPLOY_URL\s*\+\s*['\"`]/", t)
    if m and not re.search(r"replace\(\s*/\\/\+?\$/|new URL\(|trimEnd\(['\"]/|endsWith\(['\"]/", t[: m.start()]):
        add("§2.1", "UYARI", p, t[: m.start()].count("\n") + 1, "Raw NEXT_PUBLIC_DEPLOY_URL concatenated into the redirect URI without trailing-slash normalization — a trailing slash in env breaks the byte-identical match (§10 #6, F4)")

# ---------------------------------------------------------------- §3 iframe pages
client_pages = {p: t for p, t in app_files.items() if is_page_file(p) and (pages_router or re.search(r"['\"]use client['\"]", t))}
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
    return r in ("page.tsx", "page.jsx", "page.ts", "page.js", "index.tsx", "index.jsx") or bool(re.search(r"actionRunId|idList|orderPackageId", t)) or r.startswith("callback/") or r.startswith("callback.")


for p, t in client_pages.items():
    r = rel_route(p)
    is_root = r in ("page.tsx", "page.jsx", "index.tsx", "index.jsx")
    iframe_signal = re.search(r"getNewToken|getTokenForIframeApp|getAuthorizedAppId|useIkasToken|AppBridgeHelper|useSearchParams|actionRunId", t)
    exempt = re.search(r"authorize-store|login|landing", r)
    ext = re.search(r"window\.location\.(href|replace|assign)\s*\(?=?\s*['\"`]https?://", t)
    if is_root and ext and not re.search(r"window\.self\s*!==?\s*window\.top|window\.top\s*!==?\s*window\.self", t):
        add("§4", "BLOCKER", p, t[: ext.start()].count("\n") + 1, "Root page redirects the iframe to an external URL with no in-panel screen, link or instruction — the reviewer sees a spinner or a nested login; shape (b) needs a visible link + one-line instruction [observed] R2, R3 (§10 #12) — review")
    if (iframe_signal or is_root) and "closeLoader" not in t and not imports_loader_hook(t) and not exempt:
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
        context = t[: m.start()]
        if not re.search(r"window\.self\s*!==?\s*window\.top|window\.top\s*!==?\s*window\.self|inIframe|isIframe", context[-800:]):
            # is the enclosing function ever called from a file that imports this module? (helper left over from the starter)
            fn = [(m2.group(1) or m2.group(2) or m2.group(3), bool(m2.group(1))) for m2 in re.finditer(r"static\s+(\w+)\s*=\s*(?:async\s*)?\(|function\s+(\w+)\s*\(|const\s+(\w+)\s*=\s*(?:async\s*)?\(", context)]
            name, is_static = fn[-1] if fn else (None, False)
            importers = [q for q in files if q != p and p in local_imports(q, depth=1)]
            # static method → must be called as Class.name(; plain export → named import + bare call
            call_re = r"\." + re.escape(name) + r"\s*\(" if is_static else r"import\s*\{[^}]*\b" + re.escape(name) + r"\b[^}]*\}[\s\S]*(?<![\w.])" + re.escape(name) + r"\s*\("
            called = name and any(re.search(call_re, files[q]) for q in importers)
            if name and not called and not is_route(p) and p not in client_pages:
                add("§3.3", "BILGI", p, t[: m.start()].count("\n") + 1, f"`{name}` does a top-level Admin redirect with no iframe branch but is never called from another file — dead starter code; F5 not needed unless it is wired up")
            else:
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


def auth_expanded(p):
    """Route text plus only the imported modules that define an auth guard (getUserFromRequest / withMerchant …)."""
    guards = [files[q] for q in local_imports(p) if re.search(r"(function|const)\s+(getUserFromRequest|withMerchant|verifyToken|verifyJwt|requireAuth|getAuthedUser)\b", files[q])]
    return "\n".join([files.get(p, "")] + guards)


for p, t in app_files.items():
    if not is_route(p):
        continue
    g = route_group(p)
    r = rel_route(p)
    tx = expanded(p)
    if g == "api" and not auth_markers.search(tx):
        touches_merchant = re.search(r"AuthTokenManager|getIkas\(|merchantId|authorizedAppId|prisma\.(?!\$queryRaw)\w+\.(find|update|delete|create|upsert)", tx)
        operator_token = re.search(r"timingSafeEqual", tx) and re.search(r"authorization", tx, re.I) and re.search(r"process\.env\.\w*(TOKEN|SECRET|KEY)", tx)
        if operator_token:
            add("§5.1", "BILGI", p, 1, "No app-JWT check; gated by an operator bearer token compared with timingSafeEqual — operational endpoint, not a merchant route. Confirm it is disabled when the token env is unset")
        elif not touches_merchant:
            add("§5.1", "BILGI", p, 1, "No JWT check and no merchant data visible (health check / static?) — confirm it exposes nothing merchant-specific")
        else:
            add("§5.1", "BLOCKER", p, 1, "Admin API route has no JWT verification marker (getUserFromRequest/withMerchant/…) and touches merchant data — güvenlik")
    elif g in ("api", "public") and TOKEN_LOAD.search(t) and not DELETED_CHECK.search(auth_expanded(p)):
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
    INPUT_ID = r"\b(body|payload|input|parsed\.data|params|query)\.(authorizedAppId|merchantId)\b|searchParams\.get\(['\"](authorizedAppId|merchantId)['\"]\)"
    if g == "api" and re.search(INPUT_ID, t):
        add("§5.1", "UYARI", p, line_of(t, INPUT_ID), "authorizedAppId/merchantId read from request input — must come from the verified JWT (Blocker güvenlik if input wins)")
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
    t = route_text(p)
    tx = expanded(p)
    g = route_group(p)
    sec = "§6.1" if g == "webhook" else "§7.2"
    statuses = set(re.findall(r"status:\s*(\d{3})", tx)) | set(re.findall(r"WebhookError\([^)]*,\s*(\d{3})\)|errorResponse\([^)]*,\s*(\d{3})", tx) and [x for tup in re.findall(r"WebhookError\([^)]*,\s*(\d{3})\)|errorResponse\([^)]*,\s*(\d{3})", tx) for x in tup if x])
    if re.search(r"readonly status = (\d{3})|status = 400", tx):
        statuses.add("400")
    SIG_RE = r"validateIkasWebhookSignature|getParsedIkasWebhookData|validateIkasWebhookMiddleware|createHmac"
    verifies = bool(re.search(SIG_RE, tx))
    where = via(p, SIG_RE) if verifies else ""
    rejects = bool({"401", "403"} & statuses)
    mutates = bool(MUTATION_MARKERS.search(tx))
    problems = []
    if not verifies:
        problems.append("no HMAC signature check")
    elif not rejects:
        problems.append("signature computed but no 401/403 path — result never enforced")
    if statuses <= {"200"}:
        problems.append("only ever returns 200")
    if re.search(r"catch[^{]*\{[^}]*status:\s*200|catch[^{]*\{[^}]*ok:\s*true", tx, re.S):
        problems.append("catch block answers 200/ok")
    if problems:
        if g == "action":
            sev, why = "BLOCKER", "API action signature validation is documented as mandatory [docs:app-actions] (§10 #2) — review + güvenlik"
        elif mutates:
            sev, why = "BLOCKER", "handler mutates state on an unverified body (§10 #2/#3) — güvenlik"
        else:
            sev, why = "UYARI", "handler only logs (starter payment example does the same) — still verify before extending it"
        add(sec, sev, p, 1, f"{g} route: " + "; ".join(problems) + f" — {why} (F1)")
    elif verifies:
        add(sec, "BILGI", p, 1, f"Signature verified before work, 401 on mismatch{where} — confirm the guard runs before any state change")
    if verifies and not any(s.startswith("5") for s in statuses):
        add(sec, "UYARI", p, 1, "No 5xx path — processing failures and a missing CLIENT_SECRET cannot be signalled to ikas retry")
    if not re.search(r"z\.object|zod|yup|valibot|safeParse", tx):
        add(sec, "UYARI", p, 1, "Payload shape not validated with a schema before use")
    if verifies and not re.search(r"clientSecret|CLIENT_SECRET", tx):
        add(sec, "UYARI", p, 1, "HMAC present but no visible secret reference — check fail-closed behaviour (SDK helper silently uses '' when the secret is unset)")
    if re.search(r"appendFileSync|writeFileSync", t) and re.search(r"signature|headers", t):
        add("§8", "BLOCKER", p, line_of(t, r"appendFileSync|writeFileSync"), "Webhook body/signature/headers written to disk (§10 #19) — güvenlik")
    if g == "webhook":
        UNINSTALL_RE = r"store/app/deleted|store/app/uninstalled|store/authorizedApp/deleted|WebhookScope\.APP_DELETED"
        handles = lambda q: re.search(UNINSTALL_RE, expanded(q)) or re.search(r"uninstall", route_text(q), re.I)
        handled_elsewhere = any(handles(q) for q in signed_inputs if q != p and route_group(q) == "webhook")
        if not handles(p):
            if not handled_elsewhere:
                add("§6.2", "BILGI", p, 1, "Webhook route does not match the uninstall scope (store/app/deleted) — is uninstall handled elsewhere?")
        elif not re.search(r"store/app/deleted|WebhookScope\.APP_DELETED", tx):
            add("§6.2", "UYARI", p, line_of(t, r"uninstall|authorizedApp/deleted") or 1, "Official uninstall scope 'store/app/deleted' [sdk: WebhookScope] is not in the matched list")
        elif re.search(r"store/app/uninstalled|store/authorizedApp/deleted", t):
            add("§6.2", "BILGI", p, line_of(t, r"store/app/uninstalled|store/authorizedApp/deleted") or 1, "Matches 'store/app/uninstalled' / 'store/authorizedApp/deleted' too — not in the SDK enum, dead branches; only store/app/deleted is delivered")
        if re.search(r"store/app/deleted|uninstall", tx, re.I) and re.search(r"if\s*\(\s*!\s*authToken\s*\)", tx) and not re.search(r"authToken\??\.deleted", tx):
            add("§6.2", "UYARI", p, line_of(t, r"if\s*\(\s*!\s*authToken\s*\)") or 1, "Uninstall handler short-circuits on missing token but not on an already-deleted one — second delivery re-runs cleanup with a dead token (F11)")
        if not re.search(r"markProcessed|dedupe|duplicate|processedAt|webhookEvent|idempot", tx, re.I):
            add("§6.1", "BILGI", p, 1, "No idempotency/dedupe marker — the 3 retries will re-run the handler")
        if re.search(r"store/app/payment|merchantAppPayment|paymentStatus|WebhookScope\.APP_PAYMENT", t) and "PAID" not in tx:
            reconciles = re.search(r"getMerchantLicence|refresh\w*Licen[cs]e|reconcil", tx, re.I)
            if reconciles:
                add("§6.4", "BILGI", p, line_of(t, r"store/app/payment|merchantAppPayment|paymentStatus") or 1, "Payment webhook does not check status === 'PAID' but grants nothing from the payload — it triggers a getMerchantLicence reconciliation instead. Acceptable; F13 does not apply")
            else:
                sev = "BLOCKER" if mutates and not verifies else "UYARI"
                add("§6.4", sev, p, line_of(t, r"store/app/payment|merchantAppPayment|paymentStatus") or 1, "Payment webhook handled without checking status === 'PAID' [docs:plans] (F13)" + (" — güvenlik" if sev == "BLOCKER" else ""))
        if re.search(r"paymentStatus|subscriptionKey", t) and "merchantAppPayment" not in tx:
            add("§6.4", "BILGI", p, line_of(t, r"paymentStatus|subscriptionKey"), "Payment payload parsed with the older example shape (paymentStatus/subscriptionKey); docs show data.merchantAppPayment.{status,storeAppListingSubscriptionKey}")

has_webhook_route = any(route_group(p) == "webhook" for p in app_files if is_route(p))
injects = any(re.search(r"createStorefrontJSScript|saveStorefrontJSScript|createCampaign|saveWebhooks?", t) for t in files.values())
# storefront apps: script must be added automatically at install and removed on uninstall [observed] R5
script_files = [p for p, t in files.items() if re.search(r"mutations\.(createStorefrontJSScript|saveStorefrontJSScript)\(", t)]
if script_files:
    # automatic = the callback route (or a server helper it imports, 3 levels) creates the script
    in_install_path = any(re.search(r"createStorefrontJSScript|saveStorefrontJSScript", files.get(q, ""))
                          for p in callback_files for q in [p] + list(local_imports(p, depth=3)))
    callers = sorted({rel_route(p) if p in app_files else os.path.relpath(p, ROOT) for p in files if p not in script_files and any(re.search(r"\b" + n + r"\b", files[p]) for n in re.findall(r"export\s+(?:async\s+)?function\s+(\w+)|export\s+const\s+(\w+)", "\n".join(files[q] for q in script_files)) for n in n if n)})
    if not in_install_path:
        add("§6.2", "BLOCKER", script_files[0], line_of(files[script_files[0]], r"createStorefrontJSScript|saveStorefrontJSScript"), "Storefront script is not created in the OAuth callback; callers: " + (", ".join(callers[:4]) or "none found") + " — if the dashboard installs it automatically on first load, downgrade to Bilgi; if a merchant must click, the reviewer installs, opens the storefront and sees nothing [observed] R5 (§10 #17) — review")
    if not any(re.search(r"deleteStorefrontJSScript", expanded(p)) for p in app_files if is_route(p) and route_group(p) == "webhook"):
        add("§6.2", "BLOCKER", script_files[0], 1, "App injects a storefront script but no webhook route calls deleteStorefrontJSScript on store/app/deleted [observed] R5 (§10 #17) — review")
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
is_git = bool(git_state) or os.path.isdir(os.path.join(ROOT, ".git"))
if not is_git:
    add("§8", "BILGI", None, None, "Not a git repository — untracked/ignored state unknown; report Git as 'repo yok'")
if not os.path.exists(os.path.join(ROOT, ".gitignore")):
    add("§8", "UYARI", None, None, ".gitignore missing — the first `git init && git add .` commits .env* and build output (F12 precondition once a repo exists)")
elif not re.search(r"^\s*\.env(\*|$|\s|\.)", gi, re.M):
    add("§8", "UYARI", os.path.join(ROOT, ".gitignore"), 1, ".gitignore has no .env pattern (F12)")
if not any(os.path.exists(os.path.join(ROOT, n)) for n in (".env.example", ".env.sample", ".env.template")):
    add("§8", "BILGI", None, None, "No .env.example — reviewer/developer cannot see the required env contract; README should list it")
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
# ---------------------------------------------------------------- §5.3 Admin API version ↔ operation names
# [schema] 2026-09-13: /api/v1/admin/graphql and /api/v2/admin/graphql expose DIFFERENT schemas (v1: 63 q / 69 m, v2: 47 q / 76 m).
# Names present in exactly one version — a call to the other version's name fails with GRAPHQL_VALIDATION_FAILED at runtime.
V1_ONLY_OPS = {"getIkasWalletWithBalance", "getImageUploadUrl", "getLastImportJobData", "getTimelineEntry", "getVideoUploadUrl", "listIkasWallet",
               "listIkasWalletTransaction", "listLanguage", "listMerchantSettings", "listProductOptionSet", "listProductOrder", "listProductUnit",
               "listProductVolumeDiscount", "listStorefrontJSScript", "listStorefrontPolicy", "listVendor", "searchProducts",
               "campaignAddCoupons", "changeStockLocation", "createMerchantAppPaymentWithSubscription", "createWalletTransaction", "deleteProductOrderList",
               "deleteProductUnitList", "deleteProductVolumeDiscountList", "deleteStorefrontPolicyList", "deleteVendorList", "generateOrderPaymentLink",
               "getOrderInvoicePdfUrl", "saveCampaign", "saveCategory", "saveCustomer", "saveCustomerGroup", "saveCustomerTag", "saveGlobalTaxSettings",
               "saveOrderTag", "saveProduct", "saveProductAttribute", "saveProductBrand", "saveProductOrder", "saveProductStockLocations", "saveProductTag",
               "saveProductUnit", "saveProductVolumeDiscount", "saveSalesChannel", "saveStorefrontJSScript", "saveStorefrontPolicy", "saveTaxSettings",
               "saveVariantPrices", "saveVendor", "saveWebhook", "updateCustomerB2BStatus", "updateOrderLine", "updateSubscriptionStatus"}
V2_ONLY_OPS = {"getMerchantSettings", "addCouponsToCampaign", "addCustomerTimelineEntry", "addOrderTimelineEntry", "addVariantToProduct", "createCampaign",
               "createCategory", "createCustomer", "createCustomerGroup", "createCustomerTag", "createGlobalTaxSettings", "createOneTimeMerchantAppPayment",
               "createOrderTag", "createPriceList", "createProduct", "createProductAttribute", "createProductBrand", "createProductTag",
               "createStorefrontJSScript", "createTaxSettings", "deletePriceListList", "downloadOrderInvoice", "removeOrderInvoice", "removeVariantFromProduct",
               "saveVariantStocks", "saveWebhooks", "updateCampaign", "updateCategory", "updateCustomer", "updateCustomerAndAddressAttributes",
               "updateCustomerGroup", "updateCustomerTag", "updateGlobalTaxSettings", "updateOrderTag", "updatePriceList", "updateProduct",
               "updateProductAndVariantAttributes", "updateProductAttribute", "updateProductBrand", "updateProductTag", "updateSalesChannel",
               "updateStorefrontJSScript", "updateTaxSettings", "updateVariantPrices"}
api_version = None
for cand in (".env.example", ".env.sample", ".env.template", ".env.local", ".env"):
    cp = os.path.join(ROOT, cand)
    m = re.search(r"api\.myikas\.com/api/(v\d)/admin/graphql", read(cp)) if os.path.exists(cp) else None
    if m:
        api_version = (m.group(1), cp, read(cp)[: m.start()].count("\n") + 1)
        break
if not api_version:
    for p, t in files.items():
        m = re.search(r"api\.myikas\.com/api/(v\d)/admin/graphql", t)
        if m:
            api_version = (m.group(1), p, t[: m.start()].count("\n") + 1)
            break
if api_version:
    ver, vp, vl = api_version
    other = {"v1": V2_ONLY_OPS, "v2": V1_ONLY_OPS}.get(ver, set())
    add("§5.3", "BILGI", vp, vl, f"Admin API version {ver} (NEXT_PUBLIC_GRAPH_API_URL); operations: {', '.join(sorted(ops)) or 'none'}" + (" — ruleset §11 and schema.py default to v2; run `schema.py --v1` for signatures" if ver == "v1" else ""))
    for op in sorted(ops & other):
        op_p = next((q for q, t in files.items() if re.search(r"\.(?:queries|mutations)\." + op + r"\(", t)), None)
        add("§5.3", "UYARI", op_p, line_of(files[op_p], r"\.(?:queries|mutations)\." + op + r"\(") if op_p else None,
            f"{op} exists only in the {'v2' if ver == 'v1' else 'v1'} schema but the app targets {ver} — GRAPHQL_VALIDATION_FAILED at runtime (işlevsel; [schema] 2026-09-13, verify with schema.py)")
IDENTITY_OPS = {"getMerchant", "getAuthorizedApp", "getMerchantLicence", "getMerchantSettings", "getAvailableSubscriptions", "me",
                "listMerchantAppPayment", "createMerchantAppPayment", "createOneTimeMerchantAppPayment", "getAppDemoDay",
                "saveWebhooks", "deleteWebhook", "listWebhook", "addCustomTimelineEntry", "getImportJobData", "getImportJobDataList",
                "getSalesChannel", "listSalesChannel", "updateSalesChannel",
                "listPriceList", "createPriceList", "updatePriceList", "deletePriceListList", "listCurrency", "listPaymentGateway", "listCargoCompany",
                "getGlobalTaxSettings", "listGlobalTaxSettings", "createGlobalTaxSettings", "updateGlobalTaxSettings", "deleteGlobalTaxSettingsList",
                "listShippingSettings", "listTaxSettings", "createTaxSettings", "updateTaxSettings", "deleteTaxSettingsList",
                "listCountry", "listState", "listCity", "listDistrict", "listTown"}  # [schema] no scope family (§11)
# §11 — operation-name keyword → scope family (heuristic; only zero-operation families are flagged)
FAMILY = {
    "order": "orders", "package": "orders", "fulfil": "orders", "shipment": "orders", "branch": "orders", "terminal": "orders",
    "product": "products", "variant": "products", "category": "products", "brand": "products", "vendor": "products", "tag": "products", "attribute": "products",
    "customer": "customers", "address": "customers",
    "campaign": "campaigns", "coupon": "campaigns", "discount": "campaigns", "promotion": "campaigns",
    "stock": "inventories", "inventor": "inventories", "variantstock": "inventories", "stocklocation": "inventories",
    "abandonedcheckout": "orders", "fulfil": "orders", "transaction": "orders", "invoice": "orders",
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
# [observed] E5: saveWebhooks rejects these scopes with INVALID_SCOPE (lifecycle scopes come only via the Partner-panel Bildirim Adresi)
REJECTED_SAVE_SCOPES = r"store/(product/deleted|app/deleted|app/payment)"
for p, t in files.items():
    if re.search(r"mutations\.saveWebhooks?\(", t):
        m = re.search(REJECTED_SAVE_SCOPES, t)
        if m:
            add("§6.2", "UYARI", p, line_of(t, REJECTED_SAVE_SCOPES), f"saveWebhooks is called in a file that lists scope `{m.group(0)}` — the API rejects it with INVALID_SCOPE ([observed] E5); store/app/* arrive only via the Partner-panel Bildirim Adresi, store/product/deleted is not deliverable — işlevsel")
if has_webhook_route and not any(re.search(r"mutations\.saveWebhooks?\(", t) for t in files.values()):
    DATA_SCOPES = r"store/(order|product|customer|customerFavoriteProducts|stock)/"
    data_routes = [rel_route(p) for p in signed_inputs if route_group(p) == "webhook" and re.search(DATA_SCOPES, expanded(p))]
    if data_routes:
        add("§6.2", "UYARI", None, None, "Webhook route handles data scopes (" + ", ".join(data_routes) + ") but saveWebhooks is never called — [mcp] data scopes can only be registered with saveWebhooks; the Partner-panel Bildirim Adresi delivers only store/app/deleted and store/app/payment")
    else:
        add("§6.2", "BILGI", None, None, "Webhook route handles lifecycle scopes only — [partner-panel] register it as Konfigürasyon › Bildirim Adresi (DECLARE row); saveWebhooks is not needed")

# ---------------------------------------------------------------- output
ORDER = {"BLOCKER": 0, "UYARI": 1, "BILGI": 2}
if SECTION_FILTER:
    findings = [f for f in findings if f["section"].startswith(SECTION_FILTER) or f["section"].startswith("§10")]
findings.sort(key=lambda f: (ORDER[f["severity"]], f["section"], f["file"], f["line"] or 0))

if AS_JSON:
    for f in findings:
        f["git"] = git_tag(os.path.join(ROOT, f["file"])).strip(" []") if f["file"] != "-" else ""
    print(json.dumps({"root": ROOT, "findings": findings}, indent=2, ensure_ascii=False))
else:
    print(f"ikas-app-preflight scan — {ROOT}" + (f" — section {_sec}" if _sec else ""))
    print(f"sdk={'yes' if has_sdk else 'no'} app-helpers={'yes' if has_bridge else 'no'} ikas.config.json={'yes' if has_cfg else 'no'} "
          f"routes={sum(1 for p in app_files if is_route(p))} client-pages={len(client_pages)} git={'yes' if is_git else 'no (repo yok)'}"
          + (f" ({git_note})" if git_note else ""))
    print()
    for f in findings:
        loc = (f["file"] + (f":{f['line']}" if f["line"] else "") + git_tag(os.path.join(ROOT, f["file"]))) if f["file"] != "-" else "-"
        print(f"{f['section']:<6} {f['severity']:<8} {loc}\n       {f['msg']}")
    counts = {k: sum(1 for f in findings if f["severity"] == k) for k in ORDER}
    print()
    print(f"BLOCKER: {counts['BLOCKER']}  UYARI: {counts['UYARI']}  BILGI: {counts['BILGI']}")
    print("Evidence only — confirm each hit by reading the code against references/app-review.md.")
