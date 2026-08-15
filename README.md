# Inflowenger Plugin Catalog

The index of **Plugin nodes** for [Inflowenger](https://github.com/Inflowenger/getting-started)
— and the knowledge base for building your own.

Two things live here:

- **[`plugins/`](plugins/)** — the catalog. One entry per plugin, each pointing at
  the plugin's own repository. Plugins are not hosted here; their authors own them.
- **[`docs/`](docs/)** — everything a plugin developer needs: the mental model, a
  build-from-zero guide, the SDK matrix, and how to publish and get listed.

Products built on Inflowenger — such as **FloMorphic** — load these plugins as
extensions. A plugin written once against the `inflowv1` protocol runs on any of
them.

---

## The catalog

| Plugin | Node | Actions | SDK | Author | Repository |
|--------|------|--------:|-----|--------|------------|
| [Jira](plugins/jira.md) | `JIRA` | 14 | Go | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [jira-plugin](https://github.com/mehdi-shokohi/jira-plugin) |
| [Postgres](plugins/postgres.md) | `POSTGRES` | 3 | Go | [@FloMorphic](https://github.com/FloMorphic) | [postgres-plugin](https://github.com/FloMorphic/postgres-plugin) |

Full entries in **[`plugins/`](plugins/)**. Machine-readable mirror:
[`plugins/index.json`](plugins/index.json).

> Built one? See **[Get your plugin listed](#get-your-plugin-listed)**.

---

## What a Plugin node is

Inflowenger runs software whose logic is a **workflow graph**. The platform ships
a handful of primitive nodes, and every higher-level node compiles down to those
primitives.

The **Plugin node is the exception** — it doesn't compile to anything. It is a
live external process that you own and deploy, which the runtime (Fractal) calls
into over [NATS](https://nats.io). That makes it the platform's real extension
point:

- **Its own UI** — every action carries a form (JSON Schema + UI Schema) that the
  drawer renders, so users configure your node visually. Fields can call back
  into the plugin while the form is open, so a picker shows what *this* account
  can actually see.
- **Context access** — read and write the running flow's shared context by JSON
  path, mid-execution.
- **Flow control** — stream progress, finish a job, route outbound ports, or end
  the branch from inside a handler.
- **Long-lived** — a plugin is a persistent process, so it can hold connections,
  run background loops, and surface queues, webhooks, hardware, or third-party
  APIs as nodes on the canvas.

A plugin holds **no user credentials**. It *declares* what a connection needs; the
platform stores the filled-in form as a named **settings profile** and folds the
values into every call as `body.settings`. One running plugin serves many
accounts, and rotating a token needs no redeploy.

More in **[docs/concepts.md](docs/concepts.md)**.

---

## Build one

```bash
go get github.com/Inflowenger/go-plugin-sdk@latest
```

```go
package main

import (
    "log"
    "os"
    "os/signal"
    "syscall"

    "github.com/Inflowenger/go-plugin-sdk/sdkv1"
)

func main() {
    p, err := sdkv1.NewPlugin(sdkv1.WithDotEnv(".env.inflow"))
    if err != nil {
        log.Fatal(err)
    }

    p.Intro(sdkv1.PluginIntro{Name: "HELLO", Author: "you", Version: "v0.1.0"})

    p.AddAction(sdkv1.Action{
        Method: "hello.greet",
        Title:  "Greet",
        RequestHandler: func(job sdkv1.Job) {
            req, err := sdkv1.CastRequestTo[struct {
                Name string `json:"name"`
            }](job.Req.Data)
            if err != nil {
                job.DoneWithError(err.Error())
                return
            }
            job.Progress(50, sdkv1.Frame{Title: "greeting", Content: req.Body.Name})
            job.Done(map[string]any{"greeting": "hello " + req.Body.Name})
        },
    })

    if err := p.Start(); err != nil {
        log.Fatal(err)
    }

    // Start() only wires subscriptions — the process must stay alive to serve them.
    stop := make(chan os.Signal, 1)
    signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
    <-stop
}
```

That is a complete plugin. Read **[docs/build-a-plugin.md](docs/build-a-plugin.md)**
for the rest: provisioning, typed input, forms, settings profiles, context
commands, meta RPCs, and testing without a live platform.

### Read in this order

| # | Doc | Why |
|---|-----|-----|
| 1 | [docs/concepts.md](docs/concepts.md) | What a plugin node is, and the six things it can do. Read once. |
| 2 | [docs/build-a-plugin.md](docs/build-a-plugin.md) | Zero to a running plugin, in order. |
| 3 | [docs/dependent-fields.md](docs/dependent-fields.md) | Forms whose fields depend on the connected account or on each other — lookups, cascades, connection tests. Read before you design your second form. |
| 4 | [docs/sdks.md](docs/sdks.md) | Which language you can write in today. |
| 5 | [docs/publishing.md](docs/publishing.md) | Versioning, deploying, and getting listed. |

Then go deep in the SDK's own docs — they are the normative reference:
[cookbook](https://github.com/Inflowenger/go-plugin-sdk/blob/main/cookbook.md) ·
[architecture](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/architecture.md) ·
[inflowv1 protocol](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/protocol-inflowv1.md) ·
[jobs & commands](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/jobs-and-commands.md) ·
[form builder](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md).

---

## SDKs

| Language | Package | Status |
|----------|---------|--------|
| **Go** | [`Inflowenger/go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) | **Stable** — the reference `inflowv1` implementation. Go 1.26+. |
| Node.js / TypeScript | — | Planned |
| Python | — | Planned |

`inflowv1` is a plain NATS message protocol, so nothing stops a plugin in another
language — the SDK is a convenience, not a requirement. If you want to port one,
[docs/sdks.md](docs/sdks.md) lists exactly what an SDK has to implement.

---

## Building with an AI coding agent

The Go SDK ships an **Agent Skill** —
[`skills/inflow-plugin/SKILL.md`](https://github.com/Inflowenger/go-plugin-sdk/tree/main/skills/inflow-plugin)
— that teaches Claude Code (or any tool that reads `SKILL.md` files) how to use
the SDK correctly. Because the SDK is imported as a library, install the skill in
**your** plugin project:

```bash
mkdir -p .claude/skills
cp -r "$(go env GOMODCACHE)"/github.com/\!inflowenger/go-plugin-sdk@*/skills/inflow-plugin .claude/skills/
```

Your agent then loads it on its own whenever you ask it to build or extend a
plugin.

---

## Get your plugin listed

Anyone can submit — the plugin stays in your account or org, the catalog only
links to it.

1. Check your plugin against the [listing bar](CONTRIBUTING.md#the-bar).
2. Copy [`templates/plugin-entry.md`](templates/plugin-entry.md) to
   `plugins/<slug>.md` and fill it in.
3. Add the same plugin to [`plugins/index.json`](plugins/index.json) and one row
   to the table above.
4. Open a PR.

No plugin is too small. Full instructions: **[CONTRIBUTING.md](CONTRIBUTING.md)**.

---

## License

The catalog and its documentation are licensed under
[Apache 2.0](LICENSE). Listed plugins carry **their own** licenses — check each
repository before use. A listing is not an endorsement or a security review; see
[CONTRIBUTING.md § Trust](CONTRIBUTING.md#trust-and-safety).
