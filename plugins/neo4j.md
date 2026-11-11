# Neo4j

> A graph database on the canvas — read and write Cypher, plus upsert-a-node, link-two-nodes, find-nodes and create-a-constraint without writing any.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/neo4j-plugin |
| **Node name** | `NEO4J` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Review — the six actions and their 4.x fallbacks are implemented, but the plugin has not yet been run against a live Infra + Fractal. Read it, try it, report what breaks. |

## What it does

Talks to any Neo4j reachable over Bolt with the official
[`neo4j-go-driver/v5`](https://github.com/neo4j/neo4j-go-driver) — a local
container, a self-managed server or cluster on-prem, or Aura — on Community or
Enterprise, 4.4 and later.

Two of the six actions are Cypher: **Run Cypher (read)** in a read transaction a
cluster can answer from a follower, and **Execute Cypher (write)** in a write
transaction routed to the leader. The other four are the graph operations a flow
reaches for constantly, without a statement to write: **upsert a node** on key
properties, **link two nodes** so re-running updates rather than duplicates,
**find nodes** by label and properties with a real `LIMIT`, and **create a
constraint or index** if it is not already there. Nodes, relationships, paths,
temporals and points all come back as plain JSON.

Every action runs inside a **managed transaction**, so the driver retries a
transient failure — a leader election, a deadlock, a dropped connection — on its
own; the plugin never opens an explicit transaction.

The idempotency is explicit rather than implied. **Key properties** on Upsert
Node decides the statement: `email` gives `MERGE (n:Person {email: $key0}) SET
n += $props` and the same node every run, while leaving it empty gives `CREATE`
and another node every run. A key naming a property with no value is refused
rather than merged on a null. Link Nodes requires a match on *both* endpoints —
matching on the label alone would fan the `MERGE` out into one relationship per
matched row — and its error names which endpoint failed and what it looked for.
Every constraint statement carries `IF NOT EXISTS`, so it belongs at the front
of a writing flow: re-running is a no-op and the committed `created` field says
whether it was already there.

Two separate mechanisms supply values, and they are worth keeping straight.
**Cypher parameters** (`$name`, filled from a JSON object) are bound by the
driver, so they can never alter the statement and the server can cache the plan;
types survive, which is what `UNWIND $rows AS row` wants. **`{{$.path}}`
tokens** are resolved by the plugin against the flow scope before the statement
runs, in every text field, so they work in the Cypher itself as well as in the
parameters. A token the scope cannot supply is left verbatim rather than
silently blanked.

Reads return **at most 100 rows** and report `truncated`, because every row is
committed into the flow's context.

## Actions

| Method | Title |
|--------|-------|
| `neo4j.query` | Run Cypher (read) |
| `neo4j.execute` | Execute Cypher (write) |
| `neo4j.node.upsert` | Upsert Node (MERGE) |
| `neo4j.relationship.upsert` | Link Nodes (MERGE relationship) |
| `neo4j.node.find` | Find Nodes |
| `neo4j.constraint.create` | Create Constraint / Index (if not exists) |

Meta RPCs: `neo4j.meta.ping.check` (the settings form's **Test connection**
button — it names the server it reached, e.g. `Neo4j/5.26.0 (localhost:7687)`),
`neo4j.meta.database.pick`, `neo4j.meta.label.pick` and
`neo4j.meta.reltype.pick`. The **Label** field's single ↻ button does double
duty: pressed with the box empty it lists the labels in use, pressed again it
loads the properties nodes with that label carry, sampled from the data so no
special privilege is needed.

## Connection

The plugin holds no database configuration. The settings profile is the only
place a credential lives, and the platform ships it with every call as
`body.settings` — one running plugin serves many databases, and rotating a
password needs no redeploy.

| Key | Required | What it is |
|-----|----------|------------|
| `uri` | **yes** | `neo4j://localhost:7687` on-prem, `neo4j+s://xxxxxxxx.databases.neo4j.io` for Aura. `neo4j://` lets the driver route across a cluster; `bolt://` pins to one server. Port defaults to 7687. A `host` (and optional `port`) is accepted instead. |
| `database` | no | e.g. `neo4j`. Empty uses the server's default — the only option before 4.0. |
| `auth` | no | `basic` (default), `none`, `bearer` or `kerberos`. |
| `user` | no | Defaults to `neo4j`, the user every install ships with. |
| `password` | for `basic` | The password — or, for `bearer` / `kerberos`, the token or ticket. |
| `encryption` | no | `from URI` (default), `off`, `on`, `self-signed`. |
| `connectTimeout` | no | Seconds to wait for the TCP connection. Default 10. |

Keys are matched leniently: case, spaces, dashes and underscores are ignored and
the usual synonyms accepted (`uri`/`url`/`connectionString`/`boltUrl`,
`user`/`username`/`login`, `password`/`pass`/`secret`/`token`). Credentials
pasted into the URI are lifted out of it, because the driver takes its
credentials from the auth token and ignores a URI's userinfo — leaving them in
place would silently mean "no password".

## Install

```bash
git clone https://github.com/Inflowenger/neo4j-plugin
cd neo4j-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL

go run .
```

Pure Go — no cgo and no C library. On startup the SDK logs every subject it
subscribed to, and the plugin logs the actions it registered; those lines are
the confirmation it reached Infra.

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either
download the filled-in `.env.inflow` and run the commands above, or run the
generated one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **Encryption is a URI scheme, not a flag.** Neo4j selects TLS with the scheme
  — `neo4j+s://` (certificate must be trusted), `neo4j+ssc://` (any certificate
  accepted) — and the driver *refuses* a TLS config supplied alongside one of
  them. So the **Encryption** setting rewrites the scheme: `on` →  `neo4j+s://`,
  `self-signed` → `neo4j+ssc://`, `off` → `neo4j://`, `from URI` → unchanged,
  which is what an Aura URI already wants.
- **Two constraint kinds need Enterprise.** `unique` and `index` work on
  Community; `exists` (`REQUIRE n.p IS NOT NULL`) and `node key` are Enterprise
  features.
- **`REQUIRE` is Neo4j 5.** A 4.x server rejects it as a syntax error, and the
  action then retries the same command in the 4.x dialect (`ASSERT`, and
  `exists(n.p)` for existence) — so it works on a server that has not moved to 5
  yet, at the cost of one extra round trip where the first form could never have
  worked.
- **Pair an upsert with a uniqueness constraint on the same properties.** That
  is what turns the `MERGE` into an index lookup, and what stops two concurrent
  runs both creating the node.
