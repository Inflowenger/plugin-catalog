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

| Plugin | Node | Actions | SDK | Runs on | Author | Repository |
|--------|------|--------:|-----|---------|--------|------------|
| [Gmail (OpenConnector)](plugins/gmail-oc.md) | `Gmail (OpenConnector)` | 4 | Node | FloMorphic ★ | [@FloMorphic](https://github.com/FloMorphic) | [gmail-oc-plugin](https://github.com/FloMorphic/gmail-oc-plugin) |
| [Jira](plugins/jira.md) | `JIRA` | 14 | Go | Any host | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [jira-plugin](https://github.com/mehdi-shokohi/jira-plugin) |
| [MongoDB](plugins/mongodb.md) | `MONGODB` | 4 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [mongodb-plugin](https://github.com/FloMorphic/mongodb-plugin) |
| [MySQL](plugins/mysql.md) | `MYSQL` | 4 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [mysql-plugin](https://github.com/Inflowenger/mysql-plugin) |
| [Postgres](plugins/postgres.md) | `POSTGRES` | 3 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [postgres-plugin](https://github.com/FloMorphic/postgres-plugin) |
| [Qdrant](plugins/qdrant.md) | `QDRANT` | 7 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [qdrant-plugin](https://github.com/Inflowenger/qdrant-plugin) |
| [Telegram (OpenConnector)](plugins/telegram-oc.md) | `Telegram (OpenConnector)` | 5 | Go | FloMorphic ★ | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [telegram-oc-plugin](https://github.com/mehdi-shokohi/telegram-oc-plugin) |

**Runs on** — every plugin here speaks `inflowv1`, so **Any host** means it runs
on any product that implements the protocol. A **★** marks a plugin that also
needs a **host-specific service** and therefore runs on that platform alone:
[Gmail (OpenConnector)](plugins/gmail-oc.md) reaches FloMorphic's central
**Connect / OpenConnector** proxy over the `flomorphic.svc.oc.*` NATS subjects,
which only FloMorphic provides. The dependency is recorded as `hostDependency` in
[`index.json`](plugins/index.json).

Full entries in **[`plugins/`](plugins/)**. Machine-readable mirror:
[`plugins/index.json`](plugins/index.json).

> Built one? See **[Get your plugin listed](#get-your-plugin-listed)**.

---

## Roadmap

Plugins already in progress and on their way into the catalog. Dates and scope
may shift — this is where the catalog is heading, not a commitment.

### In progress

Being built now; expected to land in the catalog over the next few days.

| Plugin | Node | Scope | Author |
|--------|------|-------|--------|
| osctrl **(next up)** | `OSCTRL` | Confirmed feasible and the next plugin to land. Manage an [osctrl](https://osctrl.net) fleet — the central control panel for osquery clients: list nodes, run queries, and manage the endpoints that have osquery installed | Inflowenger dev team |
| Google Workspace **(in testing)** | `GOOGLE` | First release covers **Docs, Sheets, Drive, and Calendar** — **Docs, Drive, and Calendar are feature-complete and in testing**, effectively done | Inflowenger dev team |
| ClickHouse **(in testing)** | `CLICKHOUSE` | Query ClickHouse for analytics workloads — **feature-complete and in testing**, effectively done | Inflowenger dev team |

### Feasibility study

Candidates under evaluation, **not yet committed**. Each is being weighed for how
well it maps onto the `inflowv1` model and onto FloMorphic's needs, and for the
effort it takes given the current SDKs. Items here **may be cancelled or reshaped**
— *Effort* is a first estimate of quick win vs. hard win, not a promise.

Each of these is a **collector**: the plugin's job is only to access a system and
return data frames. The logic on top — storing frames in a doc store, evaluating
them, running an LLM node for recommendations — is built **downstream in the
workflow graph**, not inside the plugin.

| Plugin | Node | What it would do | Approach under review | Effort | Status |
|--------|------|------------------|-----------------------|--------|--------|
| Network devices | `NETDEVICE` | Collect facts, interfaces, IPs, BGP/ARP/LLDP neighbours from routers, switches, and firewalls across vendors | Connection layer **[scrapligo](https://github.com/scrapli/scrapligo)** on the reference **Go SDK** — the path that ships today (SSH/NETCONF, multivendor; structured transports where the device offers them, CLI + ntc-templates where it doesn't, and we normalise to JSON). NAPALM/**scrapli** would give structured getters for free but need Python, which is the concrete requirement that drove the now-shipping **[Python SDK](docs/sdks.md)** | **Hard win** — Go now (we normalise), or ride the Python SDK | In study |
| ManageEngine | `MANAGEENGINE` | Read/write against a ManageEngine product's REST API (ServiceDesk Plus, Endpoint Central, OpManager, or ADManager Plus) | Standard REST + API-key/OAuth — fits the Go or Node SDK directly, close to the Jira plugin. **Which product** is still open, and that decides the whole node | **Quick win** once the product is chosen | In study |
| Cloud providers | `AWS` · `AZURE` · `GCP` | Pull resource inventory and deployment status, and read each cloud's native security findings — a Wiz-style trace of what's deployed and what's misconfigured | First-class **Go** SDKs, credentials via the settings profile (AWS key/role · Azure service principal · GCP service-account JSON). **The plugin only accesses and collects data frames** — ① inventory + status (CloudFormation/Config · Resource Graph · Cloud Asset Inventory), ② the cloud's *own* posture findings (**Security Hub** · **Defender for Cloud** · **Security Command Center**). The Wiz-style graph, evaluation, and recommendations are built **downstream in the workflow** (collected frames → doc store → LLM node), not in the plugin. One node per provider | **Hard win** — three providers, phased; ① is tractable, ② rides native findings | In study |

### Requested

Plugins people have asked for but nobody has claimed yet. Want to build one — or
request another? Open an issue, or see **[Get your plugin listed](#get-your-plugin-listed)**.

_Nothing open right now._

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
| **Go** | [`Inflowenger/go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) | **Stable** — the reference `inflowv1` implementation, and the mainstream path. Go 1.26+. |
| **Node.js / TypeScript** | [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) | **Stable** — on npm, Node 18+. Tracks the Go SDK feature-for-feature. |
| **Python** | [`inflowenger-plugin-sdk`](https://pypi.org/project/inflowenger-plugin-sdk/) | **Beta** — first release on PyPI, Python 3.11+. The Python port of the Go SDK ([`Inflowenger/py-plugin-sdk`](https://github.com/Inflowenger/py-plugin-sdk)). |

All three SDKs are available today; Go is the reference, and Node.js and Python
follow it. The four listed plugins are built on them — three in Go, one ([Gmail
(OpenConnector)](plugins/gmail-oc.md)) in Node.

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
