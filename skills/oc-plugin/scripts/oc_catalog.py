#!/usr/bin/env python3
"""Read an OpenConnector service's action catalog, small enough to reason about.

A `-oc` plugin must be built from the live action contracts, not from memory.
This prints them. Stdlib only.

    export OC_TOKEN='api-<key-from-the-panel>'                    # as the oomol panel gives it
    export OC_BASE_URL='https://connector.oomol.com'   # or a self-hosted origin

The `authorization` header form varies by deployment, so this tries both — see
auth_headers() below.

    oc_catalog.py services
    oc_catalog.py list github [--type read] [--grep issue]
    oc_catalog.py search github "create issue"
    oc_catalog.py show github.create_issue
    oc_catalog.py save github [-o oc/catalog]

Every /v1 response is {success, message, data, meta}; `data` is unwrapped here.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://connector.oomol.com"


def auth_headers(token):
    """Candidate `authorization` values, best first.

    The header form differs by deployment, so try rather than assume:

    - Hosted oomol issues `api-…` keys and documents the header **without** a
      scheme (`Authorization: api-c09b…`). It also accepts `Bearer api-…` —
      both reach the same account API-key verifier.
    - The open-source runtime requires the scheme: its readBearerCredential()
      returns nothing when the header has no recognized `Bearer` prefix, so a
      raw token there reads as no token at all.

    A token that already carries its own scheme (`OC_TOKEN='Bearer xyz'`) is
    sent verbatim and is the escape hatch if a deployment wants something else.
    """
    if " " in token:
        return [token]
    if token.startswith("api-"):
        return [token, "Bearer " + token]
    return ["Bearer " + token, token]


def get(path, params=None):
    base = os.environ.get("OC_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    token = os.environ.get("OC_TOKEN")
    if not token:
        die(
            "OC_TOKEN is not set. Create an access token in the oomol web panel\n"
            "(Connect / OpenConnector console → runtime tokens), then:\n"
            "  export OC_TOKEN='<token>'"
        )

    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)

    candidates = auth_headers(token.strip())
    for index, header in enumerate(candidates):
        last = index == len(candidates) - 1
        req = urllib.request.Request(url, headers={"authorization": header})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as err:
            raw = err.read().decode(errors="replace")
            if err.code == 401 and not last:
                continue  # wrong header form for this deployment — try the other
            die("GET %s failed — %s" % (path, describe_error(err.code, raw)))
        except urllib.error.URLError as err:
            die("cannot reach %s — %s" % (base, err.reason))

        if index > 0:
            print(
                "note: authenticated with '%s…' form, not the first one tried."
                % header.split(" ")[0],
                file=sys.stderr,
            )
        if isinstance(body, dict) and body.get("success") is False:
            die("GET %s failed — %s: %s" % (path, body.get("errorCode"), body.get("message")))
        return body.get("data") if isinstance(body, dict) and "data" in body else body


def describe_error(code, raw):
    raw = raw.strip()
    try:
        env = json.loads(raw)
        detail = "%s: %s" % (
            env.get("errorCode") or env.get("title") or code,
            env.get("message") or env.get("detail") or raw,
        )
    except ValueError:
        detail = "%s: %s" % (code, raw)
    if code == 401:
        detail += (
            "\nDiscovery is authenticated too. Check OC_TOKEN is the token the"
            "\noomol panel issued, and OC_BASE_URL is that deployment's origin."
        )
    return detail


def die(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def required_of(action):
    schema = action.get("inputSchema") or {}
    return list(schema.get("required") or [])


def optional_of(action):
    schema = action.get("inputSchema") or {}
    props = list((schema.get("properties") or {}).keys())
    return [p for p in props if p not in required_of(action)]


def cmd_services(_args):
    for entry in get("/v1/actions") or []:
        print(entry.get("service") if isinstance(entry, dict) else entry)


def cmd_list(args):
    actions = get("/v1/actions", {"service": args.service}) or []
    if args.type:
        actions = [a for a in actions if a.get("operationType") == args.type]
    if args.grep:
        needle = args.grep.lower()
        actions = [
            a
            for a in actions
            if needle in (a.get("id", "") + " " + a.get("description", "")).lower()
        ]

    if not actions:
        print("no actions matched", file=sys.stderr)
        return

    counts = {}
    for a in actions:
        counts[a.get("operationType", "?")] = counts.get(a.get("operationType", "?"), 0) + 1

    for a in sorted(actions, key=lambda x: x.get("id", "")):
        flags = []
        execution = a.get("execution") or {}
        if execution.get("catalogOnly"):
            flags.append("CATALOG-ONLY(not runnable)")
        if a.get("asyncLifecycle"):
            flags.append("async")
        req = ", ".join(required_of(a)) or "-"
        print("%-52s %-11s required: %s%s" % (
            a.get("id", "?"),
            a.get("operationType", "?"),
            req,
            "  [" + " ".join(flags) + "]" if flags else "",
        ))

    print(
        "\n%d actions  (%s)" % (
            len(actions),
            ", ".join("%s %s" % (v, k) for k, v in sorted(counts.items())),
        ),
        file=sys.stderr,
    )
    print("Next: oc_catalog.py show <action-id> for the full input contract.", file=sys.stderr)


def cmd_search(args):
    params = {"q": args.query, "limit": args.limit}
    if args.service:
        params["service"] = args.service
    for hit in get("/v1/actions/search", params) or []:
        print("%-52s %s" % (hit.get("id", "?"), (hit.get("description") or "")[:90]))


def cmd_show(args):
    a = get("/v1/actions/" + urllib.parse.quote(args.action_id))
    print("# %s — %s" % (a.get("id"), a.get("name")))
    print(a.get("description", ""))
    print("\noperationType : %s" % a.get("operationType"))
    print("requiredScopes: %s" % (", ".join(a.get("requiredScopes") or []) or "-"))
    print("providerPerms : %s" % (", ".join(a.get("providerPermissions") or []) or "-"))
    print("execution     : %s" % json.dumps(a.get("execution") or {}))
    if a.get("asyncLifecycle"):
        print("asyncLifecycle: %s" % json.dumps(a["asyncLifecycle"]))
    if a.get("followUpActions"):
        print("followUp      : %s" % ", ".join(
            f.get("actionId", "?") for f in a["followUpActions"]
        ))

    schema = a.get("inputSchema") or {}
    print("\n## inputSchema  (additionalProperties: %s — send nothing else)"
          % schema.get("additionalProperties", "unset"))
    print(json.dumps(schema, indent=2, ensure_ascii=False))

    out = a.get("outputSchema") or {}
    print("\n## outputSchema top-level keys")
    print(", ".join((out.get("properties") or {}).keys()) or "(not an object schema)")

    print("\n## call it as")
    print(json.dumps({"input": {k: "…" for k in required_of(a)}}, indent=2))
    print("POST /v1/actions/%s   header: x-oo-connector-alias: <alias>" % a.get("id"))


def cmd_save(args):
    data = get("/v1/actions", {"service": args.service})
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "%s.json" % args.service)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("%s  (%d actions)" % (path, len(data or [])))


def main():
    parser = argparse.ArgumentParser(
        description="Read an OpenConnector service's action catalog.",
        epilog="Set OC_TOKEN (and OC_BASE_URL for a self-hosted runtime).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("services", help="services that expose actions").set_defaults(fn=cmd_services)

    p = sub.add_parser("list", help="one line per action of a service")
    p.add_argument("service")
    p.add_argument("--type", choices=["read", "write", "destructive"], help="filter by operationType")
    p.add_argument("--grep", help="substring of the id or description")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("search", help="ranked action search (use on big providers)")
    p.add_argument("service", nargs="?")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("show", help="full input contract for one action")
    p.add_argument("action_id")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("save", help="write the raw service catalog to disk")
    p.add_argument("service")
    p.add_argument("-o", "--out", default="oc/catalog")
    p.set_defaults(fn=cmd_save)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
