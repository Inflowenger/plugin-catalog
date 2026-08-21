# SDKs

`inflowv1` is a plain [NATS](https://nats.io) message protocol. An SDK is a
convenience — it wires the subjects, marshals the envelopes, and gives you a
`Job` — but nothing stops a plugin written directly against NATS in any language.

## Status

| Language | Package | Status |
|----------|---------|--------|
| **Go** | [`github.com/Inflowenger/go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) | **Stable.** The reference `inflowv1` implementation and the mainstream path — when the protocol and an SDK disagree, this one is right. v0.1.7, Go 1.26+. |
| **Node.js / TypeScript** | [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) ([repo](https://github.com/Inflowenger/node-plugin-sdk)) | **Stable.** v0.1.1 on npm, Node 18+. Kept in step with the Go SDK, which stays the normative reference. Powers [Gmail (OpenConnector)](../plugins/gmail-oc.md). |
| Python | — | **Planned.** |

Both are available today. Go is the reference implementation and Node.js tracks it
(`npm i @inflowenger/node-plugin-sdk`); the four catalog plugins are built on them
— three in Go, one in Node. See [build-a-plugin.md](build-a-plugin.md).

---

## Writing an SDK in another language

If you want to port `inflowv1` — or hand-roll a plugin without an SDK — this is
the full surface. The normative reference is
[protocol-inflowv1.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/protocol-inflowv1.md);
read the Go implementation alongside it.

### Connect

- Read `PLUGIN_ID`, `INFRA_CRED`, `INFRA_URL` (dotenv or explicit config).
- Base64-decode `INFRA_CRED` into a decorated NATS `.creds` blob (JWT + NKey
  seed) and connect with it. Reconnect automatically.

### Serve six subjects

| Subject | Kind | Responds with |
|---------|------|---------------|
| `inflow.v1.<PLUGIN_ID>.@intro` | request/reply | `{name, author, version, settings?}` |
| `inflow.v1.<PLUGIN_ID>.@settings` | request/reply | the settings `FormBuilder` |
| `inflow.v1.<PLUGIN_ID>.@actions` | request/reply | the action list |
| `inflow.v1.<PLUGIN_ID>.<ACTION>.@form` | request/reply | `{submit_to, jsonschema, jsonui}` |
| `inflow.v1.<PLUGIN_ID>.<ACTION>` | job | init handshake, then commands |
| `inflow.v1.<PLUGIN_ID>.<METHOD>` | request/reply | any JSON value (meta RPC) |

A `FormBuilder` is three strings: `submit_to`, `jsonschema`, `jsonui`. Handler
functions must be excluded from serialization — in Go they carry `json:"-"`,
because a function field makes the marshal fail and the reply is then silently
dropped. Whatever your language, make sure the served payloads contain data only.

### The job handshake

An action request opens a job: the init reply assigns a `jobId`, and every
subsequent command is addressed to it. The command payload is:

```jsonc
{
  "progress": 60,                       // 1–99 = frame, 100 = terminal
  "frame":    { "title": "…", "content": "…", "meta": {} },
  "details":  { },                      // partial data, or the committed result at 100
  "commit_on": ""                       // optional JSON path to commit on ($this allowed)
}
```

- `progress` in `[1,99]` renders a frame on the node.
- `progress` 100 is terminal: `details` is committed to the node's scope, at
  `commit_on` when set.
- A failed job carries its reason as `details["error"]`.

### Request envelope

Every action and meta request body is:

```jsonc
{ "_registry": { "jobId": "…", "doneAt": 0 }, "body": { /* form fields + settings */ } }
```

`_registry` carries metadata about the node's previous runs. `body.settings` is
the resolved settings profile, folded in by the runtime — the plugin never stores
it.

### Commands a job can send

`progress` · `done` · `get current scope` · `get scope by JSON path` · `set on
JSON path` · `next-port filter by tags` · `service call` (extrinsics, origin-tagged
`plugin:<node title>`). Semantics in
[jobs-and-commands.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/jobs-and-commands.md).

A new SDK needs no work to support **`$this`**, inflow's non-standard path root
for the location the current run was handed: an SDK passes paths through
verbatim and the runtime rewrites them. Just don't validate paths against the
JSON path grammar before sending — `$this.a.b` is not valid JSON path and must
survive the trip.

### Ship an Agent Skill with it

The Go SDK ships
[`skills/inflow-plugin/SKILL.md`](https://github.com/Inflowenger/go-plugin-sdk/tree/main/skills/inflow-plugin)
so AI coding agents can use it correctly without being handed the docs. A new SDK
should do the same, in its own language's idioms.

---

## Porting checklist

- [ ] Connects from base64 `.creds`, with automatic reconnect.
- [ ] Serves all six subjects; logs each subscription at startup (that log is how
      an author confirms registration).
- [ ] Intro and settings payloads marshal cleanly with handlers excluded.
- [ ] Job init handshake assigns and threads `jobId`.
- [ ] Progress frames, terminal commit, and error termination all match the
      payload shape above.
- [ ] Context read/write, next-port filter, service call.
- [ ] Typed request casting idiomatic for the language.
- [ ] Meta RPCs may return a bare array, not only the `{data, error}` envelope.
- [ ] Two runnable examples — one adapter (external I/O), one pure transform.
- [ ] Docs mirroring the Go set, plus an Agent Skill.

Porting one? Open an issue on the catalog — it should be listed here.
