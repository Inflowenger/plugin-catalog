# Concepts

What a Plugin node is, and what it can do that no other node can. Read this once
before [building one](build-a-plugin.md).

---

## Where the plugin sits

Inflowenger runs software whose logic is a **workflow graph**. A flow executes on
a **Fractal** (the runtime), which is coordinated by **Infra** (identity, spaces,
credentials, messaging). Nodes on the canvas are mostly *principal* nodes — a
small set of primitives — and every higher-level node ultimately compiles down to
them.

A **Plugin node** does not compile to primitives. It is a separate process, on
your infrastructure, that Infra and the Fractal talk to over
[NATS](https://nats.io) using the **`inflowv1`** protocol. When a flow reaches a
plugin node, the runtime sends your process a request and waits for your handler
to report back.

```
   canvas / drawer            Fractal (runtime)              your process
        │                            │                            │
   node config  ──────────────▶  compile flow                     │
                                     │   inflow.v1.<id>.<action>  │
        │                            ├───────────────────────────▶│  RequestHandler(job)
        │                            │                            │
        │◀── progress frames ────────┤◀──── job.Progress ─────────┤
        │                            │◀──── job.CmdGetScope ──────┤
        │                            │◀──── job.CmdSetOnPath ─────┤
        │                            │◀──── job.Done ─────────────┤
```

Because it is an ordinary long-lived process, a plugin can hold open connections,
run background loops, keep caches, and use any library in its language. That is
why it is the platform's extension point: with only the plugin node type, you can
build a complete automation system on top of Inflowenger.

---

## Identity: PLUGIN_ID and spaces

A plugin cannot just connect. It must first be **defined in a space** — a NATS
*account* managed by Infra, which is the unit of authentication, authorization,
and isolation. Registering the plugin there is what turns its `PLUGIN_ID` into a
real, reachable identity and what scopes the subjects it may touch.

- **Single-tenant** — Inflow ships a default plugins space; register there and you
  are running immediately.
- **Multi-tenant / enterprise** — define the plugin in a custom account so each
  tenant or trust boundary is isolated. A plugin's credentials only reach what
  its account permits.

Provisioning gives you three values, and only these three:

| Variable | Meaning |
|----------|---------|
| `PLUGIN_ID` | The identity the plugin was registered under. Every NATS subject is namespaced by it. |
| `INFRA_CRED` | Base64-encoded NATS `.creds` (JWT + NKey seed). It carries the account, so it *is* the authorization boundary. |
| `INFRA_URL` | NATS endpoint, e.g. `localhost:4222`. Always required — Infra may run as a cluster with several endpoints. |

---

## The six things a plugin declares

Everything a plugin exposes is one of these, and each maps to a NATS subject.

| # | Thing | Subject | What it is |
|---|-------|---------|------------|
| 1 | **Intro** | `inflow.v1.<PLUGIN_ID>.@intro` | Name, author, version. The node's identity on the palette. |
| 2 | **Settings** | `inflow.v1.<PLUGIN_ID>.@settings` | The connection form, served to the set-up dialog. |
| 3 | **Actions** | `inflow.v1.<PLUGIN_ID>.@actions` | The list of methods the node can perform. |
| 4 | **Forms** | `inflow.v1.<PLUGIN_ID>.<ACTION>.@form` | Per-action UI: JSON Schema + UI Schema. |
| 5 | **Handlers** | `inflow.v1.<PLUGIN_ID>.<ACTION>` | The work. Spawns a **Job**. |
| 6 | **Meta RPCs** | `inflow.v1.<PLUGIN_ID>.<METHOD>` | Synchronous helpers for building the drawer. No job, no progress. |

The normative subject-by-subject reference is the SDK's
[protocol-inflowv1.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/protocol-inflowv1.md).

---

## Actions vs. meta RPCs

They look similar and behave nothing alike.

|  | **Action** | **Meta RPC** |
|---|---|---|
| Lifecycle | Spawns a `Job` | Plain request/response |
| Progress | `job.Progress(…)` streams to the canvas | None |
| Runs when | The flow executes the node | The user is *configuring* the node |
| Output | Committed as the node's output | Returned to the caller verbatim |
| Signature | `func(sdkv1.Job)` | `func(sdkv1.Request) any` |

Use a meta RPC for anything the drawer needs *before* a run: "test this
connection", "resolve this project name to a key", "which transitions does this
issue have right now". A meta handler can answer with a bare array when that is
the shape the caller expects — it is not forced into the `{data, error}` envelope.

Two different things call a meta method, and they want different answers:

- A **button on a form control** (`x-inflow-ui`) calls one to fill fields in. It
  wants the **patch** — `{"projectKey": "OPS"}` — and receives a *flat* request
  body, not the action envelope. This is how a form handles a field that depends
  on the account or on another field; see
  [dependent-fields.md](dependent-fields.md).
- **`FormBuilder.SubmitTo`** names a meta method for **live validation** of the
  form on submit. That one answers with an `sdkv1.Response`.

Mixing the two up is the most common way a dependent field silently fails.

---

## Settings profiles: how credentials reach you

This is the part that most often surprises new plugin authors.

**Your plugin stores no user credentials and reads no service-specific environment
variables.** It only *declares* what a connection needs; the platform owns the
values.

1. The plugin advertises a settings form on `@intro` / `@settings` — the fields a
   connection requires.
2. The platform stores a filled-in form as a named, reusable **settings profile**,
   keyed by the plugin identity (`ext:<pluginId>`), the way a secret manager
   resolves a named config.
3. A canvas node binds one profile. At compile time the runtime folds that
   profile's values into the node's call body as `settings`.
4. Every request therefore arrives with its own connection:

```jsonc
{
  "_registry": { "jobId": "…", "doneAt": 1754130000 },
  "body": {
    "issueKey": "OPS-42",          // the action's own form fields
    "settings": {                   // ← resolved profile, added by the runtime
      "baseUrl": "https://acme.atlassian.net",
      "apiToken": "…"
    }
  }
}
```

The consequences are worth stating plainly:

- **One process serves many accounts.** Which profile a node binds decides which
  credentials that call uses.
- **Rotating a secret needs no redeploy.** The platform re-resolves the profile.
- **`settings` never appears in your action's own form.** It is the platform's
  half of the body, not something the user retypes on every node. Worth a unit
  test.
- **Pool clients per connection**, not globally — keyed on the resolved settings.

Profiles are often typed by hand as key/value rows, so match your keys leniently:
ignore case, spaces, dashes, and underscores, and accept the obvious synonyms.
When no usable connection arrives, fail the node with a message that names the
fix ("pick a settings profile in the node drawer") rather than a null dereference.

---

## The Job: your handle into a running flow

Inside an action handler you hold a `Job`. It is not just a way to return a value
— it is a live channel into the flow that is currently executing.

| Method | Effect |
|--------|--------|
| `job.Progress(pct, Frame)` | Report `0–100` with a titled status frame. The canvas renders it live. |
| `job.Done(data, key…)` | Complete (progress 100) and commit `data` as the node's output. |
| `job.DoneWithError(msg)` | Complete with an error payload. |
| `job.CmdGetCurrentScope()` | Read the whole current context scope. |
| `job.CmdGetScope(path)` | Read a slice of context by JSON path, e.g. `$.OPA`. |
| `job.CmdSetOnPath(path, m)` | Write into the flow context at a JSON path. |
| `job.CmdNextFilter(tags)` | Route at runtime — follow only the outbound ports carrying these tags. |
| `job.CmdSvcCall(action, data, op)` | Ask the extrinsics service to run an action. Origin-tagged `plugin:<node title>`; the service may refuse ungranted calls. |
| `job.CmdStopFlow()` | Abort the entire workflow run. |

**The one rule that matters:** exactly one terminal call — `Done` *or*
`DoneWithError` — on every path out of your handler. Miss it and the node hangs;
call it twice and you commit twice.

Depth: [jobs-and-commands.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/jobs-and-commands.md).

---

## Forms

Every action carries a form so users configure your node visually instead of
hand-writing JSON. A form is two strings:

- **`Jsonschema`** — a JSON Schema describing the fields, types, and requirements.
- **`Jsonui`** — a [JSON Forms](https://jsonforms.io) UI Schema describing layout,
  plus Inflowenger's `x-inflow-ui` extension, which adds behaviour a static form
  has no vocabulary for: *put a button on this field, and call this plugin
  function when it is clicked*.

Both are plain strings on the wire, so you can keep them as Go string constants,
embed `.json` files with `go:embed`, or generate them.

A form is not limited to what you knew at compile time. `x-inflow-ui` plus a meta
RPC is how a field gets values that only exist at configuration time — the
projects *this* settings profile can see, the users assignable to *that* project,
the transitions available on an issue right now. That pairing has its own
contract and its own limits: **[dependent-fields.md](dependent-fields.md)**.

Reference: [form-builder.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md).

---

## Context

The flow's shared **context** is the data structure every node reads from and
writes to as a run progresses. A plugin reaches it by JSON path mid-execution —
which is what lets a plugin node do things a request/response integration cannot:
inspect what upstream nodes produced, enrich the context in place, and decide
which downstream branch runs.

`job.Done(data)` commits your output normally. `CmdSetOnPath` is for writing
somewhere *else* in the context — a shared accumulator, a well-known key another
branch reads.

---

## Next

- [build-a-plugin.md](build-a-plugin.md) — do it.
- [dependent-fields.md](dependent-fields.md) — forms whose fields depend on the
  account, or on each other.
- [sdks.md](sdks.md) — which language, and what a new SDK must implement.
- [publishing.md](publishing.md) — versioning, deployment, and getting listed.
