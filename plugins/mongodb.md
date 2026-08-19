# MongoDB

> Find, write, upsert documents, and create collections in MongoDB from the Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/FloMorphic/mongodb-plugin |
| **Node name** | `MONGODB` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **License** | See repository |
| **Status** | Experimental |

## What it does

Runs MongoDB operations as four nodes: **Find** (read documents), **Write**
(insert / update / delete via a chosen operation), **Insert / Upsert document**,
and **Create Collection (if not exists)**. It talks to any MongoDB server —
standalone, replica set, sharded cluster, or Atlas — over the official
`mongo-driver/v2` client.

Filters, documents and updates are written as MongoDB query JSON and parsed into
**BSON**, never string-concatenated, so a value can never alter the shape of the
operation. Relaxed MongoDB **Extended JSON** is accepted, so `{"$oid": …}` and
`{"$date": …}` resolve to real ObjectIDs and dates; BSON in results is normalised
back to clean JSON (an `_id` becomes a hex string, a date an RFC 3339 string).
Any string input — every JSON field and every per-field value — also resolves
double-brace `$.path` mustache tokens against the flow scope, so an operation can
pull ids and values straight from upstream nodes.

## Actions

| Method | Title |
|--------|-------|
| `mongodb.find` | Find (read) |
| `mongodb.write` | Write (insert / update / delete) |
| `mongodb.document.insert` | Insert / Upsert document |
| `mongodb.collection.create` | Create Collection (if not exists) |

Meta RPCs: `mongodb.meta.ping.check` (connection test, backs the settings form's
button and its submit validation) and `mongodb.meta.collection.pick` (lists a
connection's collections, then samples the chosen one's fields as form inputs).

## Connection

The plugin stores no database credentials and reads no database environment
variables. The connection is a MongoDB **URI**, MongoDB Compass style: the
settings form leads with a connection-string field — the primary input, and the
only reliable path for replica sets, sharded clusters and Atlas — and treats the
discrete **host / port / database / user / password / SSL-TLS / auth source /
replica set / direct connection** fields as a convenience that composes a
single-host URI. A pasted URI always wins and is used verbatim. The platform
ships the bound profile with every call as `body.settings`; bind a profile in the
node drawer. One running plugin can serve many databases, and rotating a password
needs no restart.

## Install

```bash
git clone https://github.com/FloMorphic/mongodb-plugin
cd mongodb-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

- **Local / single-node replica sets.** A single-node or local replica set (common
  for enabling transactions) advertises its members by a hostname that is often
  unreachable from outside — e.g. a Docker service name like `mongo_cluster_1`.
  With the discrete fields the **Direct connection** setting defaults to `auto`,
  which adds `directConnection=true` when no replica-set name is given, so the
  driver talks straight to the host you typed instead of chasing the advertised
  name. With a pasted URI, add `?directConnection=true` yourself.
- **Fast connection test.** Server-selection and connect timeouts are bounded, so
  a wrong host or port fails in a few seconds with the server's own message rather
  than hanging.
- **Update vs replace.** `updateOne` / `updateMany` require update operators
  (`{"$set": …}`); a whole-document swap is `replaceOne`. The Insert / Upsert node
  replaces by `_id` when the document carries one that already exists.
