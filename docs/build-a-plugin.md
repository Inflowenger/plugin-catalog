# Build a plugin

Zero to a plugin running on the canvas, in order. Go, using
[`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`sdkv1`) — the
reference `inflowv1` implementation.

Read [concepts.md](concepts.md) first if you haven't; this guide assumes you know
what a Job and a settings profile are.

**Requirements:** Go 1.26+, and a reachable Inflowenger platform (Infra + at least
one Fractal). To stand one up locally, follow
[getting-started](https://github.com/Inflowenger/getting-started) — the one-liner
brings up both stacks plus the inspector panel.

---

## 1. Provision the plugin

Before any code. A plugin needs an identity in a **space** (a NATS account managed
by Infra) — that is what makes its `PLUGIN_ID` reachable and scopes what it may
touch. Register it in the default plugins space for a single-tenant setup, or in a
custom account when you need tenant isolation.

Infra hands back three values. Put them in a dotenv file:

```env
# .env.inflow
PLUGIN_ID=aa-bbb-ccc-dddd
INFRA_CRED=LS0tLS1CRUdJTiBOQVRTIFVTRVIgSldULS0t...   # base64 of the .creds blob
INFRA_URL=localhost:4222
```

`INFRA_CRED` is a standard decorated NATS `.creds` blob, base64-encoded. The SDK
decodes it, reads the account from the JWT, and connects with automatic
reconnect.

> **Commit `.env.inflow.example`, never `.env.inflow`.** Put the real file in
> `.gitignore` on day one — `INFRA_CRED` is a live credential.

```
.env.inflow
```

**Checklist:** plugin registered in a space · `PLUGIN_ID` · `INFRA_CRED` (base64)
· `INFRA_URL` · Infra and at least one Fractal running.

---

## 2. Scaffold

```bash
mkdir my-plugin && cd my-plugin
go mod init github.com/<you>/my-plugin
go get github.com/Inflowenger/go-plugin-sdk@latest
```

> The module path must match where you will push it. `go get` on a mismatched
> path fails for anyone importing your code.

`main.go` — construct, declare, `Start()`, then **block**:

```go
package main

import (
    "log"
    "os"
    "os/signal"
    "syscall"

    "github.com/Inflowenger/go-plugin-sdk/sdkv1"
)

const version = "v0.1.0"

func main() {
    envFile := os.Getenv("INFLOW_ENV_FILE")
    if envFile == "" {
        envFile = ".env.inflow"
    }

    p, err := sdkv1.NewPlugin(sdkv1.WithDotEnv(envFile))
    if err != nil {
        log.Fatalf("cannot connect to infra (%s): %v", envFile, err)
    }

    p.Intro(sdkv1.PluginIntro{
        Name:    "MY.PLUGIN",   // shown on the canvas / node palette
        Author:  "you",
        Version: version,
    })

    p.AddAction(sdkv1.Action{
        Method: "my.thing.do",
        Title:  "Do The Thing",
        RequestHandler: func(job sdkv1.Job) {
            job.Done(map[string]any{"ok": true})
        },
    })

    if err := p.Start(); err != nil {
        log.Fatalf("start: %v", err)
    }

    // Start() only wires subscriptions — the process must stay alive to serve them.
    stop := make(chan os.Signal, 1)
    signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
    <-stop
    log.Println("shutting down")
}
```

```bash
go run .
```

On startup the SDK logs every subject it subscribed to. **That log is your
confirmation the plugin registered with Infra** — no log, no registration. Add
your node to a flow and run it.

Other ways to construct, if a dotenv doesn't fit your deployment:

```go
p, err := sdkv1.NewPlugin(
    sdkv1.WithInfraConnection("localhost:4222", base64Cred),
    sdkv1.WithPluginId("aa-bbb-ccc-dddd"),
)
```

---

## 3. Name things

Naming is the part users see, and it is annoying to change later.

- **Node name** (`PluginIntro.Name`) — short, uppercase, the vendor or system:
  `JIRA`, `HTTP.CALL`, `POSTGRES`.
- **Method** — dotted, lowercase, `<domain>.<object>.<verb>`, most general
  segment first: `jira.issue.create`, `jira.issue.comment.add`,
  `jira.user.search`. Methods are the wire contract — renaming one breaks every
  saved node using it.
- **Meta methods** — same namespace under `meta`: `jira.meta.projects`.
- **Title** — what the drawer shows: `Create Issue`, not `jira.issue.create`.

---

## 4. Read the request

The body arrives as `{"_registry": {...}, "body": <your fields>}`. Cast it into
your own struct rather than poking at maps:

```go
type CreateInput struct {
    ProjectKey string   `json:"projectKey"`
    Summary    string   `json:"summary"`
    Labels     []string `json:"labels"`

    Settings map[string]any `json:"settings"` // ← added by the runtime
}

RequestHandler: func(job sdkv1.Job) {
    req, err := sdkv1.CastRequestTo[CreateInput](job.Req.Data)
    if err != nil {
        job.DoneWithError("bad request: " + err.Error())
        return
    }

    in := req.Body

    // _registry carries metadata about this node's *previous* runs.
    if prev, ok := req.Registry["jobId"]; ok {
        log.Println("previous run:", prev)
    }
    ...
}
```

`CastRequestTo[T]` returns `*RequestBody[T]` with `.Body` (your `T`) and
`.Registry` (`map[string]any`).

Validate here, before doing any work, and fail with a message that tells the user
which field is wrong — it is rendered on the node.

---

## 5. Report progress and finish

```go
job.Progress(20, sdkv1.Frame{Title: "connecting", Content: "acme.atlassian.net"})
job.Progress(60, sdkv1.Frame{Title: "creating", Content: in.Summary})

job.Done(map[string]any{
    "key": issue.Key,
    "url": issue.URL,
})
```

- `Progress(pct, Frame)` takes `1–99`; the canvas renders a pie from `pct` plus
  the frame's title and content. Use it to make long work legible, not to
  narrate every line.
- `Done(data, key…)` sets progress to 100 and commits `data` as the node's
  output. The optional key is a path to commit on.
- `DoneWithError(msg)` completes with an error payload.
  `DoneWithErrorData(msg, data, key…)` when partial output is still useful.

> **The one rule.** Exactly one terminal call — `Done` or `DoneWithError` — on
> **every** path out of your handler. Miss it and the node hangs until the flow
> times out. Call it twice and you commit twice. Every early `return` needs one
> first; a `defer` that recovers from panic should call `DoneWithError`.

Commit output that downstream nodes can actually use: the identifiers, the
status, the URL. Return the upstream API's response rather than a stringified
summary — a flow can read fields out of it, but not out of prose.

---

## 6. Give the action a form

Without a form, users hand-write JSON. With one, they get a real drawer.

```go
const createSchema = `{
  "type": "object",
  "required": ["projectKey", "summary"],
  "properties": {
    "projectKey": { "type": "string", "title": "Project" },
    "summary":    { "type": "string", "title": "Summary" },
    "labels":     { "type": "array", "title": "Labels", "items": { "type": "string" } }
  }
}`

const createUI = `{
  "type": "VerticalLayout",
  "elements": [
    { "type": "Control", "scope": "#/properties/projectKey" },
    { "type": "Control", "scope": "#/properties/summary" },
    { "type": "Control", "scope": "#/properties/labels" }
  ]
}`

p.AddAction(sdkv1.Action{
    Method:      "my.thing.create",
    Title:       "Create Thing",
    Description: "Create a thing in the connected system",
    Form: sdkv1.FormBuilder{
        Jsonschema: createSchema,
        Jsonui:     createUI,
        SubmitTo:   "my.meta.validate", // optional: a meta method for live validation
    },
    RequestHandler: handleCreate,
})
```

Both are plain strings on the wire — string constants, `go:embed`ed `.json`
files, or generated, whichever you prefer. Layout, widgets, and the
`x-inflow-ui` extensions are documented in
[form-builder.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md).

### Or generate both from one declaration

Hand-written, the two documents drift: rename a property in the schema and forget
the scope in the UI, and the field silently stops rendering. The SDK's optional
[`formkit`](https://github.com/Inflowenger/go-plugin-sdk/tree/main/formkit)
package removes that class of bug by generating the schema *and* the UI schema
from one declaration per field, in the order written:

```go
import "github.com/Inflowenger/go-plugin-sdk/formkit"

form := formkit.New("Create Thing").Add(
    formkit.Text("projectKey", "Project").Required(),
    formkit.Text("summary", "Summary").Required(),
    formkit.List("labels", "Labels"),
).Build() // → sdkv1.FormBuilder

p.AddAction(sdkv1.Action{
    Method:         "my.thing.create",
    Title:          "Create Thing",
    Form:           form,
    RequestHandler: handleCreate,
})
```

It is adopt-per-form — nothing in `sdkv1` depends on it, its output is ordinary
JSON Schema + UI Schema text, and you can build one form with it and hand-write
the next. The same package also generates the dependent-field buttons and the
replies to them ([dependent-fields.md](dependent-fields.md#generating-it-with-formkit)).
Full API in [form-builder.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md).

**Never put connection fields in an action form.** No API tokens, no base URLs.
Those belong to the settings profile (next section) and arrive as
`body.settings`. Worth an actual unit test — walk every action's schema and
assert no `settings` property exists.

---

## 7. Declare settings (the connection form)

The plugin declares what a connection needs; the platform stores and supplies the
values.

```go
settingsForm := sdkv1.FormBuilder{
    Jsonschema: settingsSchema, // baseUrl, apiToken, ...
    Jsonui:     settingsUI,
    SubmitTo:   "my.meta.ping",
}

p.Intro(sdkv1.PluginIntro{
    Name:     "MY.PLUGIN",
    Author:   "you",
    Version:  version,
    Settings: &settingsForm,
})

p.RequiredParams(&sdkv1.Settings{
    FormBuilder: settingsForm,
    SubmitHandler: func(r sdkv1.Request) sdkv1.Response {
        cfg, err := sdkv1.CastRequestTo[MySettings](r.Data)
        if err != nil {
            return sdkv1.Response{Error: "unreadable settings"}
        }
        if err := ping(cfg.Body); err != nil {
            return sdkv1.Response{Error: "cannot reach the service: " + err.Error()}
        }
        return sdkv1.Response{Data: map[string]any{"ok": true}}
    },
})
```

**The submit handler is a validator, not a store.** It checks the submitted values
against the live service and answers ok/error. The platform does the storing.

### Reading settings in an action

```go
raw, ok := req.Body.Settings["baseUrl"]
```

Profiles are often typed by hand as key/value rows, so **match keys leniently** —
ignore case, spaces, dashes, and underscores, and accept the obvious synonyms
(`base_url` / `site` / `url`; `token` / `api_key` / `pat`). Write one
`parseSettings(map[string]any) (Conn, error)` and route every action through it.

When no usable connection arrives, fail with the *fix*, not the symptom:

```go
job.DoneWithError("no connection: pick a settings profile in the node drawer")
```

If the bound profile clearly belongs to another plugin, listing the keys it *did*
contain turns a support ticket into a five-second fix.

### Pool clients per connection

Cache your HTTP/DB client keyed on the resolved settings, not in a package-level
singleton — one process serves many accounts at once, and a global client will
leak one tenant's connection into another's job.

---

## 8. Add meta RPCs

Synchronous helpers the drawer calls while the user is *configuring* the node —
no job, no progress. Each takes the same settings record actions get.

```go
p.AddMeta(sdkv1.Meta{
    Method: "my.meta.projects",
    RequestHandler: func(r sdkv1.Request) any {
        in := decodeMeta[struct {
            Settings map[string]any `json:"settings"`
            Query    string         `json:"query"`
        }](r.Data)
        return listProjects(in.Settings, in.Query)
    },
})
```

A meta handler returns `any` and the SDK marshals it verbatim — a struct, a map,
or a bare array, whichever the caller expects. Call `AddMeta` **before** `Start()`.

**Do not use `CastRequestTo` here.** It unmarshals the action envelope
(`{"_registry":…, "body":{…}}`), but a meta call made from a form arrives **flat**
— the fields are at the top level. You would get a zero-valued struct and an empty
`Settings` map, with no error to tell you. Decode tolerantly instead; see
[dependent-fields.md § What your meta function receives](dependent-fields.md#2-what-your-meta-function-receives)
for the `decodeMeta` helper used above.

Three that nearly every integration plugin wants:

| Method | Purpose |
|--------|---------|
| `<domain>.meta.ping` | Connection test for the settings dialog. |
| `<domain>.meta.<things>` | Resolve or list a dependency (projects, buckets, channels, tables). |
| `<domain>.meta.<state>` | Options that depend on the record being acted on. |

---

## 8b. Wire a meta RPC into the form

A meta RPC is only half of the feature. The other half is a **button on a
control** that calls it and writes the answer back into the form — which is how a
user picks a project they cannot type from memory, or turns a name into the
`accountId` your API demands.

```jsonc
{
  "type": "Control",
  "scope": "#/properties/projectKey",
  "x-inflow-ui": {
    "action": { "name": "pluginFn", "fn": "my.meta.projects" },
    "button": { "position": "append", "label": "Find" }
  }
}
```

The host sends the whole form plus the bound settings profile, and applies what
comes back: an **object** is a patch of `field → value`, anything else is written
to the button's own control. So the handler above must return
`map[string]any{"projectKey": "OPS", …}` — **not** an `sdkv1.Response`, whose
`{data, error}` envelope would be patched in as two fields called `data` and
`error`.

This is the mechanism behind every "identify the project first, then list what
depends on it" form. It has real limits — no runtime `enum` injection, no
on-change firing, no separate error channel — and they shape how you lay a form
out, so read **[dependent-fields.md](dependent-fields.md)** before designing one.

---

## 9. Use the flow's context

The reason a plugin node beats a plain API call: it can read and write the run's
shared state mid-execution.

```go
scope := job.CmdGetCurrentScope()      // whole current scope
opa   := job.CmdGetScope("$.OPA")      // by JSON path
mine  := job.CmdGetScope("$this.id")   // relative to this run's own location

job.CmdSetOnPath(`$["result"]`, map[string]any{"count": 42})

job.CmdNextFilter([]string{"approved"}) // follow only ports tagged "approved"
```

Use `Done` for your node's own output; use `CmdSetOnPath` to write somewhere else
in the context. `CmdNextFilter` is how a plugin becomes a branch point, not just a
step.

`$this` is worth knowing early: it is the location the *current* run was handed.
A node scoped `$.tickets[*]` runs once per ticket, and each run's `$this` is its
own ticket — so `$this.id` beats a hardcoded `$.tickets[0].id`, and your plugin
stops caring where the designer pointed it. See
[concepts.md](concepts.md#this--where-this-run-is-standing).

---

## 10. Structure it

One file works until the third action. A layout that scales:

```
main.go                  wiring: intro, settings, actions, meta, Start
internal/actions/        one file per action group + the shared job runner
internal/<service>/      the API client, settings parsing, client pool
```

Keep transport (`internal/<service>`) free of any `sdkv1` import. Then it is
testable without NATS, and a future SDK version cannot break your client.

Factor the boilerplate every handler repeats — cast, parse settings, get a
client, run, `Done`/`DoneWithError` — into one runner, so an action is just its
own logic.

---

## 11. Test without a platform

Everything worth testing runs offline:

```bash
go test ./...
go vet ./...
```

Cover at least:

- **Forms** — every `Jsonschema` and `Jsonui` parses as JSON, and no action's
  schema declares a `settings` property.
- **Settings parsing** — the lenient key matcher, including the wrong-profile
  case.
- **Envelope decoding** — a realistic `{"_registry":…, "body":…}` payload casts
  into your input struct.
- **The client** — against `httptest`, not the live service.

Handler tests need a `Job`, which needs a connection — so keep handlers thin and
put the logic in functions you can call directly.

Then run it for real against a local platform from
[getting-started](https://github.com/Inflowenger/getting-started), and watch the
inspector panel while a flow executes your node.

---

## Ship checklist

- [ ] `.env.inflow` is gitignored; `.env.inflow.example` is committed.
- [ ] Every handler path ends in exactly one `Done` / `DoneWithError`.
- [ ] No credential appears in any action form, log line, or committed output.
- [ ] Errors name the fix, not just the symptom.
- [ ] Every action has a form with titles and `required` set.
- [ ] Any field a user cannot type from memory has a meta RPC behind a button —
      and is still typable by hand ([dependent-fields.md](dependent-fields.md)).
- [ ] Clients are pooled per connection, not globally.
- [ ] `Version` in `PluginIntro` matches the git tag.
- [ ] README covers: what it does, the actions table, how the connection is
      supplied, and how to run it.
- [ ] `go vet ./...` and `go test ./...` pass.

Then [publish it and get it listed](publishing.md).

---

## Where to look next

| Question | Doc |
|----------|-----|
| How does the wire protocol actually work? | [protocol-inflowv1.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/protocol-inflowv1.md) |
| What else can a Job do? | [jobs-and-commands.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/jobs-and-commands.md) |
| How do I build a richer form? | [form-builder.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md) |
| A field depends on another field, or on the account | [dependent-fields.md](dependent-fields.md) |
| Show me a full worked example | [examples.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/examples.md) · [the Jira plugin](https://github.com/mehdi-shokohi/jira-plugin) |
| Recipe-by-recipe walkthrough | [cookbook.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/cookbook.md) |
