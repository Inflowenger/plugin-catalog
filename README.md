# Inflowenger Plugin Catalog

The index of **Plugin nodes** for [Inflowenger](https://github.com/Inflowenger/getting-started)
— and the knowledge base for building your own.

Three things live here:

- **[`plugins/`](plugins/)** — the catalog. One entry per plugin, each pointing at
  the plugin's own repository. Plugins are not hosted here; their authors own them.
- **[`docs/`](docs/)** — everything a plugin developer needs: the mental model, a
  build-from-zero guide, the SDK matrix, and how to publish and get listed.
- **[`skills/`](skills/)** — the same knowledge as agent skills, for AI coding
  agents. [`oc-plugin`](skills/oc-plugin/SKILL.md) covers building an **`-oc`**
  plugin against oomol OpenConnector.

Products built on Inflowenger — such as **FloMorphic** — load these plugins as
extensions. A plugin written once against the `inflowv1` protocol runs on any of
them.

---

## The catalog

| Plugin | Node | Actions | SDK | Runs on | Author | Repository |
|--------|------|--------:|-----|---------|--------|------------|
| [ArangoDB](plugins/arangodb.md) **(review)** | `ARANGODB` | 18 | Node | Any host | [@FloMorphic](https://github.com/FloMorphic) | [arangodb-plugin](https://github.com/Inflowenger/arangodb-plugin) |
| [Claude Agent](plugins/claude-agent.md) | `CLAUDE AGENT` | 1 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [claude-agent-plugin](https://github.com/Inflowenger/claude-agent-plugin) |
| [ClickHouse](plugins/clickhouse.md) | `CLICKHOUSE` | 4 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [clickhouse-plugin](https://github.com/Inflowenger/clickhouse-plugin) |
| [Codex Agent](plugins/codex-agent.md) **(beta)** | `CODEX AGENT` | 1 | Python | Any host | [@Inflowenger](https://github.com/Inflowenger) | [codex-agent-plugin](https://github.com/Inflowenger/codex-agent-plugin) |
| [DuckDB](plugins/duckdb.md) | `DUCKDB` | 7 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [duck-plugin](https://github.com/Inflowenger/duck-plugin) |
| [GitHub (OpenConnector)](plugins/github-oc.md) **(beta)** | `GitHub (OpenConnector)` | 13 | Python | FloMorphic ★ | [@FloMorphic](https://github.com/FloMorphic) | [github-oc](https://github.com/FloMorphic/github-oc) |
| [Gmail (OpenConnector)](plugins/gmail-oc.md) | `Gmail (OpenConnector)` | 4 | Node | FloMorphic ★ | [@FloMorphic](https://github.com/FloMorphic) | [gmail-oc-plugin](https://github.com/FloMorphic/gmail-oc-plugin) |
| [Google Workspace (OpenConnector)](plugins/google-oc.md) **(beta)** | `Google Workspace (OpenConnector)` | 30 | Go | FloMorphic ★ | [@FloMorphic](https://github.com/FloMorphic) | [google-office-oc-plugin](https://github.com/FloMorphic/google-office-oc-plugin) |
| [Jira](plugins/jira.md) | `JIRA` | 14 | Go | Any host | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [jira-plugin](https://github.com/mehdi-shokohi/jira-plugin) |
| [Microsoft SQL Server](plugins/mssql.md) | `MSSQL` | 4 | Go | Any host | [@Inflowenger](https://github.com/Inflowenger) | [mssql-plugin](https://github.com/Inflowenger/mssql-plugin) |
| [MinIO](plugins/minio.md) **(review)** | `MINIO` | 12 | Go | Any host | [@Inflowenger](https://github.com/Inflowenger) | [minio-plugin](https://github.com/Inflowenger/minio-plugin) |
| [MongoDB](plugins/mongodb.md) | `MONGODB` | 4 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [mongodb-plugin](https://github.com/FloMorphic/mongodb-plugin) |
| [MySQL](plugins/mysql.md) | `MYSQL` | 4 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [mysql-plugin](https://github.com/Inflowenger/mysql-plugin) |
| [Neo4j](plugins/neo4j.md) **(review)** | `NEO4J` | 6 | Go | Any host | [@Inflowenger](https://github.com/Inflowenger) | [neo4j-plugin](https://github.com/Inflowenger/neo4j-plugin) |
| [Nuclei](plugins/nuclei.md) **(beta)** | `NUCLEI` | 6 | Go | Any host | [@Venapce](https://github.com/Venapce) | [nuclei](https://github.com/Venapce/nuclei) |
| osctrl | `OSCTRL` | 4 | Go | Venapce | [@Venapce](https://github.com/Venapce) | internal (Venapce) |
| [Playwright](plugins/playwright.md) **(beta)** | `Playwright` | 5 | Node | Any host | [@Venapce](https://github.com/Venapce) | [playwright](https://github.com/Venapce/playwright) |
| [Postgres](plugins/postgres.md) | `POSTGRES` | 3 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [postgres-plugin](https://github.com/FloMorphic/postgres-plugin) |
| [Qdrant](plugins/qdrant.md) | `QDRANT` | 7 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [qdrant-plugin](https://github.com/Inflowenger/qdrant-plugin) |
| [Redis](plugins/redis.md) **(review)** | `REDIS` | 22 | Node | Any host | [@FloMorphic](https://github.com/FloMorphic) | [redis-plugin](https://github.com/Inflowenger/redis-plugin) |
| [Scrapli](plugins/scrapli.md) **(beta)** | `SCRAPLI` | 2 | Python | Any host | [@Inflowenger](https://github.com/Inflowenger) | [scrapli-plugin](https://github.com/Inflowenger/scrapli-plugin) |
| [Telegram (OpenConnector)](plugins/telegram-oc.md) | `Telegram (OpenConnector)` | 5 | Go | FloMorphic ★ | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [telegram-oc-plugin](https://github.com/mehdi-shokohi/telegram-oc-plugin) |
| [zvec](plugins/zvec.md) **(beta)** | `ZVEC` | 12 | Go | Any host | [@Inflowenger](https://github.com/Inflowenger) | [zvec-ai-plugin](https://github.com/Inflowenger/zvec-ai-plugin) |

**(review)** — listed, but not yet tested against a live Infra + Fractal. The
action surface is complete and the entry describes it honestly; what is not
proven is the run. Read the source, try it, and report what breaks — that is
what moves it to `beta`.

**Runs on** — every plugin here speaks `inflowv1`, so **Any host** means it runs
on any product that implements the protocol. A **★** marks a plugin that also
needs a **host-specific service** and therefore runs on that platform alone:
[Gmail](plugins/gmail-oc.md), [Google Workspace](plugins/google-oc.md),
[Telegram](plugins/telegram-oc.md) and
[GitHub (OpenConnector)](plugins/github-oc.md) reach FloMorphic's central
**Connect / OpenConnector** proxy over the `flomorphic.svc.oc.*` NATS subjects,
which only FloMorphic provides. The dependency is recorded as `hostDependency` in
[`index.json`](plugins/index.json).

Full entries in **[`plugins/`](plugins/)**. Machine-readable mirror:
[`plugins/index.json`](plugins/index.json).

> Built one? See **[Get your plugin listed](#get-your-plugin-listed)**.

---

## Run a plugin

Every listed plugin starts the same way: clone, copy `.env.inflow.example` to
`.env.inflow`, fill in `PLUGIN_ID` / `INFRA_CRED` / `INFRA_URL`, and run the
**standard command** for its language from the repository root. That is a
catalog rule, not a convention — it is what lets the same one-liner install any
plugin here.

| SDK | Standard command |
|-----|------------------|
| **Go** | `go run .` |
| **Node.js / TypeScript** | `npm install && npm run build && npm start` |
| **Python** | `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python main.py` |

**On FloMorphic** you don't provision by hand. Open the **Extensions** menu,
define the plugin (name + repository), and the extension page gives you two
things: the filled-in **`.env.inflow`** to download, and a generated
**one-liner** that clones the repo, writes the env, detects the language, starts
the process, and injects a **`./plugin.sh`** helper —
`start · stop · restart · status · logs · update` — so you never need to remember
the language's command, a PID, or a log path.

```bash
# copied from Extensions → <your plugin> → Install (carries a live credential)
curl -fsSL "https://<your-flomorphic>/…/install.sh" | bash
./plugin.sh status
./plugin.sh logs -f
```

The full rule, the per-language details, and what the helper does under the
hood: **[docs/run-a-plugin.md](docs/run-a-plugin.md)**.

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
npm install @inflowenger/node-plugin-sdk
```

```ts
import { newPlugin, withDotEnv, castRequestTo, type Job } from "@inflowenger/node-plugin-sdk";

const p = await newPlugin(withDotEnv(".env.inflow"));

p.intro({ name: "HELLO", author: "you", version: "v0.1.0" });

p.addAction({
  method: "hello.greet",
  title: "Greet",
  requestHandler: async (job: Job) => {
    const req = castRequestTo<{ name: string }>(job.req.data);

    await job.progress(50, { title: "greeting", content: req.body.name });
    await job.done({ greeting: `hello ${req.body.name}` });
  },
});

p.start();

// start() only wires subscriptions — the process must stay alive to serve them.
await new Promise(() => {});
```

That is a complete plugin. Read **[docs/build-a-plugin.md](docs/build-a-plugin.md)**
for the rest: provisioning, typed input, forms, settings profiles, context
commands, meta RPCs, and testing without a live platform.

**In another language?** The wire format is identical across the three SDKs, so a
node written in any of them is interchangeable from the runtime's point of view —
pick the language, not a different protocol. Each cookbook opens with this same
scaffold in its own language (*Skill 1 — Scaffold a runnable plugin*), with the
method names carried over from Go: `camelCase` in Node, `snake_case` in Python.

| | Install | Start here |
|---|---|---|
| **Node.js / TypeScript** | `npm install @inflowenger/node-plugin-sdk` | [`node-plugin-sdk`](https://github.com/Inflowenger/node-plugin-sdk) · [cookbook](https://github.com/Inflowenger/node-plugin-sdk/blob/main/cookbook.md) |
| **Go** | `go get github.com/Inflowenger/go-plugin-sdk@latest` | [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) · [cookbook](https://github.com/Inflowenger/go-plugin-sdk/blob/main/cookbook.md) |
| **Python** | `pip install inflowenger-plugin-sdk` | [`py-plugin-sdk`](https://github.com/Inflowenger/py-plugin-sdk) · [cookbook](https://github.com/Inflowenger/py-plugin-sdk/blob/main/cookbook.md) |

### Read in this order

| # | Doc | Why |
|---|-----|-----|
| 1 | [docs/concepts.md](docs/concepts.md) | What a plugin node is, and the six things it can do. Read once. |
| 2 | [docs/build-a-plugin.md](docs/build-a-plugin.md) | Zero to a running plugin, in order. |
| 3 | [docs/dependent-fields.md](docs/dependent-fields.md) | Forms whose fields depend on the connected account or on each other — lookups, cascades, connection tests. Read before you design your second form. |
| 4 | [docs/sdks.md](docs/sdks.md) | Which language you can write in today. |
| 5 | [docs/run-a-plugin.md](docs/run-a-plugin.md) | The standard start command per language, the FloMorphic Extensions one-liner and `plugin.sh`, and the README rule every listed plugin follows. |
| 6 | [docs/publishing.md](docs/publishing.md) | Versioning, deploying, and getting listed. |

Then go deep in the SDK's own docs — they are the normative reference. The
concept docs are language-agnostic, so read them wherever you prefer; the Python
cookbook points at the Go ones.

**Node.js / TypeScript** —
[cookbook](https://github.com/Inflowenger/node-plugin-sdk/blob/main/cookbook.md) ·
[architecture](https://github.com/Inflowenger/node-plugin-sdk/blob/main/docs/architecture.md) ·
[inflowv1 protocol](https://github.com/Inflowenger/node-plugin-sdk/blob/main/docs/protocol-inflowv1.md) ·
[jobs & commands](https://github.com/Inflowenger/node-plugin-sdk/blob/main/docs/jobs-and-commands.md) ·
[form builder](https://github.com/Inflowenger/node-plugin-sdk/blob/main/docs/form-builder.md)

**Go** —
[cookbook](https://github.com/Inflowenger/go-plugin-sdk/blob/main/cookbook.md) ·
[architecture](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/architecture.md) ·
[inflowv1 protocol](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/protocol-inflowv1.md) ·
[jobs & commands](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/jobs-and-commands.md) ·
[form builder](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md)

**Python** —
[cookbook](https://github.com/Inflowenger/py-plugin-sdk/blob/main/cookbook.md),
whose concept docs are the Go ones above.

---

## SDKs

| Language | Package | Status |
|----------|---------|--------|
| **Node.js / TypeScript** | [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) ([repo](https://github.com/Inflowenger/node-plugin-sdk)) | **Stable** — on npm, Node 18+. Tracks the Go SDK feature-for-feature, and the one this README's example is written in. |
| **Go** | [`Inflowenger/go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) | **Stable** — the reference `inflowv1` implementation. Go 1.27+. |
| **Python** | [`inflowenger-plugin-sdk`](https://pypi.org/project/inflowenger-plugin-sdk/) ([repo](https://github.com/Inflowenger/py-plugin-sdk)) | **Beta** — first release on PyPI, Python 3.11+. The Python port of the Go SDK. |

All three are available today: Go is the reference the other two are ported from,
and all three are interchangeable on the wire. The listed plugins are built on
them — eleven in Go, eight in Node, and three in Python
([Scrapli](plugins/scrapli.md), [GitHub (OpenConnector)](plugins/github-oc.md)
and [Codex Agent](plugins/codex-agent.md), all three currently **beta**).

`inflowv1` is a plain NATS message protocol, so nothing stops a plugin in another
language — the SDK is a convenience, not a requirement. If you want to port one,
[docs/sdks.md](docs/sdks.md) lists exactly what an SDK has to implement.

---

## Building with an AI coding agent

All three SDKs ship an **Agent Skill** at `skills/inflow-plugin/SKILL.md` —
[Node](https://github.com/Inflowenger/node-plugin-sdk/tree/main/skills/inflow-plugin) ·
[Go](https://github.com/Inflowenger/go-plugin-sdk/tree/main/skills/inflow-plugin) ·
[Python](https://github.com/Inflowenger/py-plugin-sdk/tree/main/skills/inflow-plugin)
— which teaches Claude Code (or any tool that reads `SKILL.md` files) how to use
that SDK correctly. Because the SDK is imported as a library, install the skill
in **your** plugin project:

```bash
mkdir -p .claude/skills
# Go — the module cache carries the whole repository
cp -r "$(go env GOMODCACHE)"/github.com/\!inflowenger/go-plugin-sdk@*/skills/inflow-plugin .claude/skills/
```

The npm tarball ships only `dist/` and `src/`, and the PyPI wheel only the
package, so for **Node** and **Python** copy the skill out of the SDK's
repository rather than out of `node_modules` or `site-packages`.

Your agent then loads it on its own whenever you ask it to build or extend a
plugin.

If your own plugin repo ships a `SKILL.md`, a `MANUAL.md`, or any other file an
agent or a person reads to start the plugin, it links to your README's `## Run`
section rather than restating a command — one source of truth, so the agent,
the human, and the FloMorphic one-liner all start it the same way
([docs/run-a-plugin.md § The rule](docs/run-a-plugin.md#the-rule)).

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
