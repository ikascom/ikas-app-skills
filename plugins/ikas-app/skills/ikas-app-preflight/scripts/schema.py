#!/usr/bin/env python3
"""Print live ikas Admin API signatures by unauthenticated introspection.

  python3 schema.py                      # every query/mutation with argument types
  python3 schema.py deleteWebhook        # one operation (args + return type)
  python3 schema.py WebhookInput         # one type (fields / input fields / enum values)
  python3 schema.py --v1 saveProduct     # against /api/v1/admin/graphql (v1 and v2 are different schemas)

Source of the [schema] tag in references/app-review.md. Read-only; no token, no side effects.
"""
import json
import sys
import urllib.request

VERSION = "v1" if "--v1" in sys.argv else "v2"
URL = f"https://api.myikas.com/api/{VERSION}/admin/graphql"
TYPE_REF = "kind name ofType { kind name ofType { kind name ofType { kind name } } }"


def post(query):
    req = urllib.request.Request(URL, data=json.dumps({"query": query}).encode(), headers={"Content-Type": "application/json", "User-Agent": "ikas-app-preflight/0.3 (schema introspection)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit("introspection failed: " + json.dumps(body["errors"])[:300])
    return body["data"]


def ref(t):
    if t is None:
        return ""
    if t["kind"] == "NON_NULL":
        return ref(t["ofType"]) + "!"
    if t["kind"] == "LIST":
        return "[" + ref(t["ofType"]) + "]"
    return t["name"]


def sig(f):
    args = ", ".join(a["name"] + ": " + ref(a["type"]) for a in f.get("args", []))
    return f"{f['name']}({args}): {ref(f['type'])}"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    name = args[0] if args else None
    schema = post("{ __schema { queryType { fields { name args { name type { %s } } type { %s } } } "
                  "mutationType { fields { name args { name type { %s } } type { %s } } } } }" % ((TYPE_REF,) * 4))["__schema"]
    ops = [("query", f) for f in schema["queryType"]["fields"]] + [("mutation", f) for f in schema["mutationType"]["fields"]]
    if not name:
        for kind, f in sorted(ops, key=lambda x: (x[0], x[1]["name"])):
            print(f"{kind:<8} {sig(f)}")
        print(f"\n{sum(1 for k, _ in ops if k == 'query')} queries, {sum(1 for k, _ in ops if k == 'mutation')} mutations")
        return
    hits = [(k, f) for k, f in ops if f["name"] == name]
    for kind, f in hits:
        print(f"{kind} {sig(f)}")
    t = post('{ __type(name: "%s") { kind name description fields { name description type { %s } } '
             'inputFields { name description type { %s } } enumValues { name } } }' % (name, TYPE_REF, TYPE_REF))["__type"]
    if t:
        print(f"{t['kind']} {t['name']}" + (f" — {t['description']}" if t.get("description") else ""))
        for f in (t.get("fields") or []) + (t.get("inputFields") or []):
            print(f"  {f['name']}: {ref(f['type'])}" + (f"  # {f['description']}" if f.get("description") else ""))
        for e in t.get("enumValues") or []:
            print(f"  {e['name']}")
    if not hits and not t:
        sys.exit(f"'{name}' is neither an operation nor a type in the live {VERSION} schema (try --v1 / without it)")


if __name__ == "__main__":
    main()
