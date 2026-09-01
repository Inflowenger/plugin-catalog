# ClickHouse

> Query and manage ClickHouse from the Inflowenger canvas — read, write/DDL, insert, and create tables.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/clickhouse-plugin |
| **Node name** | `CLICKHOUSE` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Node — [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database`, `analytics` |
| **License** | See repository |
| **Status** | Experimental |

## What it does

Runs SQL against ClickHouse as four nodes: read a query, execute a write or DDL
statement, insert a record, and create a table if it does not already exist. It
targets ClickHouse's HTTP interface, and is a close sibling of the
[MySQL](mysql.md) and [Postgres](postgres.md) plugins, tuned for analytics
workloads.

Values bind to ClickHouse's named, typed `{name:Type}` placeholders, never
concatenated into the SQL, so each parameter keeps its type. Any string input —
the SQL and every parameter — also resolves double-brace `{{$.path}}` mustache
tokens against the flow scope, so a statement can pull ids and values straight
from upstream nodes. Reads return at most 100 rows, enforced server-side via
`max_result_rows`.

## Actions

| Method | Title |
|--------|-------|
| `clickhouse.query` | Run Query (read) |
| `clickhouse.execute` | Execute (write / DDL) |
| `clickhouse.record.insert` | Insert record |
| `clickhouse.table.create` | Create Table (if not exists) |

Meta RPCs: `clickhouse.meta.ping.check` (connection test, backs the settings
form's button and its submit validation) and `clickhouse.meta.table.pick` (the
Insert form's button that lists tables, then loads a table's columns as value
fields).

## Connection

The plugin stores no database credentials and reads no database environment
variables. It declares a settings form — a full connection URL
(`http://host:8123`, or `https://host:8443` for TLS), or discrete host / port /
database / user / password / secure fields — and the platform ships the bound
profile with every call as `body.settings`. Port defaults to 8123 (8443 when
secure), user defaults to `default`. One running plugin can serve many ClickHouse
servers, and rotating a password needs no restart.

## Install

```bash
git clone https://github.com/Inflowenger/clickhouse-plugin
cd clickhouse-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install
npm run build
npm start
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. ClickHouse credentials never go in
`.env.inflow`; they are a settings profile. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).
Requires Node 20+.

## Notes

- Unlike Postgres, ClickHouse `INSERT` has no `ON CONFLICT` / upsert. Whether a
  re-inserted row deduplicates is a property of the table engine
  (e.g. `ReplacingMergeTree`), not of the insert.
- Parameters use ClickHouse's own named, typed `{name:Type}` binding, so the type
  is explicit at the call site rather than inferred.
