# ArangoDB

> ArangoDB's three faces on the canvas — AQL, documents and graphs — from one node.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/arangodb-plugin |
| **Node name** | `ARANGODB` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Node.js — [`@inflowenger/node-plugin-sdk`](https://github.com/Inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Review — 18 actions are implemented, but the plugin has not yet been run against a live Infra + Fractal, and its repository has no tagged release yet. Read it, try it, report what breaks. |

## What it does

ArangoDB is three databases in one process — a document store, a graph engine
and a query language over both — and this node exposes all three rather than
picking one. Built on [`arangojs`](https://github.com/arangodb/arangojs), against
a single server, a cluster of coordinators, or ArangoGraph.

**AQL**, three nodes: run a read query, run a write query (`INSERT` / `UPDATE` /
`REPLACE` / `REMOVE` / `UPSERT`, committing what the server reports it did), and
explain one — the plan, the indexes the optimiser would use, the rules it
applied and its warnings, without running it. The read and write nodes are
deliberately separate: a query that modifies data is refused by the read action.

**Documents**, five nodes with no AQL to write: get by key, insert (one object or
an array of them, with an `overwriteMode` that makes it an upsert in one round
trip), update or replace, remove, and find — filter by attribute, sort, project,
page, optionally with a total count. Every value is generated as a bind
parameter. Rejections are a first-class result: **Fail if any document is
rejected** off lists them under `errors` and still counts the run a success, and
either way what *was* written is committed so the flow can see which documents
went in.

**Collections and indexes**, six nodes: list, create (document or edge),
inspect, truncate, drop, and **ensure index** — create one if a matching one is
not there yet, which is safe on every flow execution and the way to make a
filter or a sort fast.

**Graphs**, three nodes: traverse out from a vertex within a depth range and
commit the neighbours, the edges or the whole paths; find how two vertices are
connected (the cheapest path, the few cheapest, or every path within a depth
range); and add an edge with its own attributes.

Any string input resolves `{{$.path}}` tokens against the flow scope before the
query runs. In AQL the distinction matters: a token is substituted into the
query *text*, so use one for a collection or an attribute name and a **bind
parameter** for a value — `{"order": {{$.order}}}` binds a whole upstream record
in one go. Reads are capped (1000 rows by default) because every row is
committed into the flow's context.

## Actions

| Method | Title |
|--------|-------|
| `arango.query.run` | Run query |
| `arango.query.exec` | Run write query |
| `arango.query.explain` | Explain query |
| `arango.document.get` | Get documents |
| `arango.document.insert` | Insert documents |
| `arango.document.update` | Update documents |
| `arango.document.remove` | Remove documents |
| `arango.document.search` | Find documents |
| `arango.collection.list` | List collections |
| `arango.collection.create` | Create collection |
| `arango.collection.info` | Collection info |
| `arango.collection.truncate` | Truncate collection |
| `arango.collection.drop` | Drop collection |
| `arango.index.ensure` | Ensure index |
| `arango.graph.traverse` | Traverse graph |
| `arango.graph.path` | Find paths |
| `arango.graph.edge.add` | Add edge |
| `arango.server.info` | Server info |

Actions carry a `class` — `query`, `document`, `collection`, `graph`, `server` —
so the canvas groups them rather than listing eighteen flat.

Meta RPCs: `arango.meta.ping.check` (the settings form's **Test connection**
button and its submit validation — it reads the server's version before the
profile is saved), `arango.meta.database.pick`, `arango.meta.collection.pick`
and `arango.meta.graph.pick`, behind the ↻ buttons on the matching fields.

## Connection

The plugin holds no server configuration. It declares a settings form, the
platform stores the filled-in form as a named settings profile and folds the
values into every call as `body.settings` — so one running plugin serves many
clusters and databases, and rotating a password needs no redeploy. One profile
is one database on one cluster.

| Key | Required | What it is |
|-----|----------|------------|
| `url` | **yes** | `http://localhost:8529`, or `https://` for TLS. Several coordinators may be given comma-separated, and requests are then spread over them with failover. A URL may carry the user, password and database (`http://root:secret@host:8529/_db/sales`), though the fields below are clearer. A `host` (and optional `port`, default 8529) is accepted instead. |
| `database` | no | The database every action runs in. Defaults to `_system`, the one that always exists — production data usually lives in its own. |
| `username` | no | Defaults to `root`. Use a user with only the rights the flow needs. |
| `password` | no | The user's password. Empty for a server started with authentication off. |
| `token` | no | A JWT used instead of a user and password — what ArangoGraph hands out and what `/_open/auth` returns. Given, it wins over the password. |
| `tlsInsecure` | no | Accept a self-signed or mismatched certificate. Off by default. |
| `tlsCa` | no | A CA certificate (PEM) to trust on top of the system roots, for a cluster with its own CA. |
| `timeout` | no | Seconds bounding one request to a coordinator. Default 30. |

Keys are matched leniently — case, spaces, dashes and underscores are ignored
and the usual synonyms accepted (`uri`/`dsn`/`endpoint`/`coordinator` for `url`,
`db`/`dbName` for `database`, `pass`/`secret` for `password`, `jwt`/`bearer` for
`token`). A call that arrives with no profile says so in the words of the person
looking at the node, since the node drawer is where the fix is. One client is
pooled per distinct connection, and the pool is closed on `SIGINT`/`SIGTERM` so
a restart leaves no sockets waiting on the coordinators.

## Install

```bash
git clone https://github.com/Inflowenger/arangodb-plugin
cd arangodb-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL

npm install && npm run build && npm start
```

Node 20+. `npm run dev` runs the TypeScript directly through `tsx` during
development. The SDK logs each subscribed subject on startup, and the plugin
logs the actions it registered — those lines are the confirmation it reached
Infra.

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either
download the filled-in `.env.inflow` and run the commands above, or run the
generated one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **`REQ_TIMEOUT` has to clear the longest query.** A traversal, a
  full-collection scan or a bulk write can legitimately take a while — the query
  forms allow up to 120s — so the plugin raises its own NATS send deadline to
  130s. A lower `REQ_TIMEOUT` turns a query that is still running into a bare
  NATS `TIMEOUT`.
- **A token in AQL is text; a bind parameter is a value.** The server can cache
  a plan for a bind parameter and can never be re-written by one. Use tokens for
  collection and attribute names, which cannot be bound.
- **`ignoreRevs` off is optimistic locking.** A `_rev` in the given document then
  makes the write conditional, so it fails rather than overwriting someone
  else's change.
- **`withTotal` on Find documents costs a second pass** — a second query with
  the same filter and no limit. It is the count a paginated UI needs, not
  something to leave on.
- **A sort with no index behind it is sorted in memory by the server.** Ensure
  index is in the same node set for that reason.
- **`src/arango/` imports nothing from the SDK**, so the database side is
  testable without NATS.
