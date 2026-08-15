# Postgres

> Read, write, and create tables in PostgreSQL from the Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/FloMorphic/postgres-plugin |
| **Node name** | `POSTGRES` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **License** | See repository |
| **Status** | Experimental |

## What it does

Runs SQL against a PostgreSQL database as three nodes: read a query, execute a
write, and create a table if it does not already exist. It targets any
Postgres-wire server (PostgreSQL and compatibles) over a pooled `pgx/v5`
connection.

Values are bound as `$1, $2 …` parameters, never concatenated into the SQL, and
each parameter keeps its type — `42` is an integer, `true` a boolean, `null` the
SQL NULL, `{"k":1}` a jsonb object, and anything that is not JSON is text. Any
string input — the SQL and every parameter — also resolves double-brace `$.path`
mustache tokens against the flow scope, so a query can pull ids and values
straight from upstream nodes.

## Actions

| Method | Title |
|--------|-------|
| `postgres.query` | Run Query (read) |
| `postgres.execute` | Execute (write) |
| `postgres.table.create` | Create Table (if not exists) |

Meta RPCs: `postgres.meta.ping.check` (connection test, backs the settings form's
button and its submit validation).

## Connection

The plugin stores no database credentials and reads no database environment
variables. It declares a settings form — a full connection string, or discrete
host / port / database / user / password / SSL mode fields — and the platform
ships the bound profile with every call as `body.settings`. Bind a profile in the
node drawer; a connection string, when given, wins over the discrete fields. One
running plugin can serve many databases, and rotating a password needs no
restart.

## Install

```bash
git clone https://github.com/FloMorphic/postgres-plugin
cd postgres-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

- Table and column names are identifiers, not bound parameters. The Create Table
  action quotes the table name with `pgx.Identifier`; the column definitions are
  DDL the flow author writes and are passed through as given.
- Add `RETURNING` to a write and the Execute action reports the returned rows
  alongside the affected count.
