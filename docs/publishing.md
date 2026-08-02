# Publishing a plugin

Your plugin lives in **your** repository. The catalog only links to it. This is
what to have in place before you submit.

---

## Repository

**Name it after the service, with `-plugin`:** `jira-plugin`, `slack-plugin`,
`postgres-plugin`. Under a personal account or your own org, either is fine.

**Make the Go module path match the repository URL.** `go.mod` says
`module github.com/you/jira-plugin`, and the repo is at
`github.com/you/jira-plugin`. A mismatch means nobody can `go get` your code and
your own imports work only by accident on your machine.

```
your-plugin/
├── main.go                  wiring: intro, settings, actions, meta, Start
├── internal/actions/        one file per action group + the shared job runner
├── internal/<service>/      API client, settings parsing, client pool
├── .env.inflow.example      committed
├── .env.inflow              gitignored — INFRA_CRED is a live credential
├── README.md
└── LICENSE
```

---

## README

The catalog entry is a pointer; your README is where people actually land. Cover:

1. **What it does** — one paragraph, and which versions/flavours of the service
   it supports.
2. **Quick start** — clone, copy the example env, run. Say plainly that the
   plugin must already be provisioned in a space, and that the startup
   subscription log is the confirmation it registered.
3. **How the connection reaches the plugin** — that you store no credentials, what
   the profile keys are, which are required, and how to bind a profile to a node.
   This is the section users need most and the one most often missing.
4. **Actions table** — method, title, one line each.
5. **Meta RPCs** — if you expose any.
6. **Gotchas** — the sharp edges of the upstream API you had to work around.
   Nobody else knows them.
7. **Development** — how to run the tests.

The [Jira plugin README](https://github.com/mehdi-shokohi/jira-plugin) is a
worked example of this shape.

---

## Versioning

Semantic versioning on git tags: `v0.1.0`.

`PluginIntro.Version` must match the tag you cut. It is what shows on the canvas,
so a wrong value sends people chasing bugs in the wrong revision.

What counts as breaking, from a flow author's point of view:

| Change | Breaking? |
|--------|-----------|
| Renaming or removing an action method | **Yes** — every saved node using it breaks. |
| Removing or renaming a form field | **Yes** — saved node configs lose it silently. |
| Removing a settings key | **Yes** — existing profiles stop resolving. |
| Changing the shape of committed output | **Yes** — downstream nodes read those fields. |
| Adding an action | No |
| Adding an optional form field | No |
| Adding a field to the output | No |

Keep a `CHANGELOG.md` once you have users. When you must break a method, add the
new one and keep the old one working for a release, rather than renaming in place.

---

## Licensing

Pick one and commit a `LICENSE` file. Apache 2.0 matches the SDK and the catalog.
Plugins keep their own licenses — the catalog does not impose one.

If you distribute binaries or images, include a `NOTICE` where your license
requires it, and note that "Inflowenger" and "FloMorphic" are trademarks: you may
use them to describe what your plugin integrates with, not to imply it is an
official product.

---

## Deploying

A plugin is an ordinary long-running process. Whatever runs a Go binary runs it —
systemd, Docker, Kubernetes, a VM.

What it needs at runtime:

- `PLUGIN_ID`, `INFRA_CRED`, `INFRA_URL` in the environment or a mounted
  `.env.inflow` (`INFLOW_ENV_FILE` overrides the path).
- Outbound network access to `INFRA_URL` and to whatever service it integrates.
- **Nothing else.** No inbound ports, no database, no per-user configuration —
  connections arrive with each request.

Notes that matter in production:

- **One process serves many accounts.** Pool clients per resolved connection, and
  never key anything on a package-level global.
- **Restarts are cheap.** State lives in the flow context, not in your process.
  Resubscription is automatic on reconnect.
- **Scaling** — run multiple instances of the same `PLUGIN_ID` and NATS
  distributes the work, provided your handlers are stateless.
- **Log the subject subscriptions at startup.** It is how you and your users tell
  "registered" from "silently misconfigured".
- **Never log credentials.** Redact `body.settings` before printing a request.

If you publish a container image, tag it with the same version as the git tag.

---

## Get listed

Once the plugin runs against a real platform:

1. Read the [listing bar](../CONTRIBUTING.md#the-bar).
2. Copy [`templates/plugin-entry.md`](../templates/plugin-entry.md) to
   `plugins/<slug>.md` and fill it in.
3. Add the plugin to [`plugins/index.json`](../plugins/index.json) and one row to
   each table — [`plugins/README.md`](../plugins/README.md) and the root
   [README](../README.md).
4. Open a PR.

Keeping the entry current — new version, new actions, or a status change to
`unmaintained` — is a PR too. If a plugin goes dark, the catalog marks it rather
than quietly dropping it, so existing users can tell what happened.
