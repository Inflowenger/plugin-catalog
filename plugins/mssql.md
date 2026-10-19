# Microsoft SQL Server

> Read, write, upsert records, and create tables in Microsoft SQL Server from the
> Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/mssql-plugin |
| **Node name** | `MSSQL` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Active |

## What it does

Runs T-SQL against Microsoft SQL Server as four nodes: read a query, execute a
write, insert or upsert a record, and create a table if it does not already
exist. It targets any TDS server the `microsoft/go-mssqldb` driver supports —
SQL Server 2012 and later, Azure SQL Database, Azure SQL Managed Instance, and
SQL Server on Linux or in a container — over a pooled `database/sql` connection.

Values are bound as `@p1, @p2 …` parameters, never concatenated into the SQL, and
each parameter keeps its type — `42` is an integer, `true` a bit, `null` the SQL
NULL, and anything that is not JSON is text. Any string input — the SQL and every
parameter — also resolves double-brace `$.path` mustache tokens against the flow
scope, so a query can pull ids and values straight from upstream nodes.

It is the SQL Server sibling of the [Postgres](postgres.md) (Go) and
[MySQL](mysql.md) (Node) plugins: the same four actions, the same forms, the same
tokens. What differs is the dialect — `@p1` placeholders, a `MERGE … WITH
(HOLDLOCK)` upsert, an `OBJECT_ID` existence check in place of
`CREATE TABLE IF NOT EXISTS` (which T-SQL does not have), and a row cap applied
as the rows are read because T-SQL has no `LIMIT`.

## Actions

| Method | Title |
|--------|-------|
| `mssql.query` | Run Query (read) |
| `mssql.execute` | Execute (write) |
| `mssql.record.insert` | Insert / Upsert record |
| `mssql.table.create` | Create Table (if not exists) |

Meta RPCs: `mssql.meta.ping.check` (connection test, backs the settings form's
button and its submit validation) and `mssql.meta.table.pick` (one button that
lists a connection's tables and then loads the chosen table's columns as form
fields).

## Connection

The plugin stores no database credentials and reads no database environment
variables. It declares a settings form — a full connection string, or discrete
host / port / named instance / database / user / password / encrypt / trust
server certificate fields — and the platform ships the bound profile with every
call as `body.settings`. Bind a profile in the node drawer; a connection string,
when given, wins over the discrete fields. One running plugin can serve many
databases, and rotating a password needs no restart.

Required for a discrete-field profile: **host**, plus whatever the login needs
(**user** and **password** for SQL authentication). **Database** may be left
empty to use the login's default. A connection string may be given in either the
URL form — `sqlserver://user:pass@host:1433?database=mydb&encrypt=true` — or the
ADO form, `server=host;user id=sa;password=…;database=mydb`.

**Azure SQL requires `encrypt=true`.** A development or on-premises server with a
self-signed certificate needs **trust server certificate** switched on once
encryption is enabled. A host may also be written the way SQL Server tooling
writes it, `HOST\INSTANCE` or `HOST,1433`, and the instance or port is split out
automatically.

Credentials come from whoever administers the instance — a SQL Server login, or
`user@tenant` for Azure SQL.

## Install

```bash
git clone https://github.com/Inflowenger/mssql-plugin
cd mssql-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **`CREATE TABLE IF NOT EXISTS` does not exist in T-SQL** — the server rejects
  it. The Create Table action wraps either input shape (a full statement, or bare
  column definitions plus a name) in `IF OBJECT_ID(N'…', N'U') IS NULL BEGIN … END`,
  so re-running a flow is a no-op. Paste the Postgres/MySQL spelling out of habit
  and the clause is stripped for you rather than sent to a server that would
  refuse it.
- **The upsert is a `MERGE … WITH (HOLDLOCK)`.** `HOLDLOCK` is what makes it safe
  under concurrency — without it two flows can both miss the row and both try to
  insert it. The primary key is discovered from `sys.indexes` automatically.
- **An explicit value for an `IDENTITY` column is allowed.** SQL Server normally
  refuses one, so the statement is bracketed with `SET IDENTITY_INSERT … ON/OFF`
  when a value for that column is supplied — which needs `ALTER` permission on the
  table. Leave the column blank and the server generates the key.
- **`OUTPUT` is how a write reads rows back**, in place of PostgreSQL's
  `RETURNING`. SQL Server rejects a plain `OUTPUT` clause on a table carrying
  triggers (it wants `OUTPUT INTO`); use the Execute action for such a table.
- **Max rows is applied as the rows are read**, not pushed into the statement,
  because T-SQL has no `LIMIT` — so the server still computes the full result set.
  Add a `TOP (n)` to make it do less work.
- `decimal`, `numeric` and `money` come back as exact decimal **strings** rather
  than being forced through a float; `uniqueidentifier` comes back as the
  canonical GUID text rather than 16 raw bytes.
- SQL Server has no native JSON column type, so a JSON object or array parameter
  is bound as its JSON **text** — which is what the `NVARCHAR` column that holds
  JSON takes.
