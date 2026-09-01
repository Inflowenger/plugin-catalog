# MySQL

> Query and manage MySQL from the Inflowenger canvas — read, write, upsert, and create tables.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/mysql-plugin |
| **Node name** | `MYSQL` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Node — [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **License** | See repository |
| **Status** | Active |

## What it does

Runs SQL against MySQL as four nodes: read a query, execute a write,
insert/upsert a record, and create a table if it does not already exist. It is
the Node/TypeScript sibling of the Go [Postgres](postgres.md) plugin, and targets
any MySQL-wire server — MySQL and MariaDB — over a pooled `mysql2` connection.

Values bind to `?` placeholders, never concatenated into the SQL, and each
parameter keeps its JSON type — `42` is an integer, `true` a boolean, `null` the
SQL NULL, `{"k":1}` serialized JSON, and anything that is not JSON is text. Any
string input — the SQL and every parameter — also resolves double-brace `{{$.path}}`
mustache tokens against the flow scope, so a statement can pull ids and values
straight from upstream nodes. Reads return at most 100 rows.

## Actions

| Method | Title |
|--------|-------|
| `mysql.query` | Run Query (read) |
| `mysql.execute` | Execute (write) |
| `mysql.record.insert` | Insert / Upsert record |
| `mysql.table.create` | Create Table (if not exists) |

Meta RPCs: `mysql.meta.ping.check` (connection test, backs the settings form's
button and its submit validation) and `mysql.meta.table.pick` (the Insert form's
button that lists tables, then loads a table's columns as value fields).

## Connection

The plugin stores no database credentials and reads no database environment
variables. It declares a settings form — a full connection string
(`mysql://user:pass@host:3306/dbname`), or discrete host / port / database /
user / password / SSL mode fields — and the platform ships the bound profile with
every call as `body.settings`. A connection string, when given, wins over the
discrete fields. SSL mode is `disable` (no TLS), `require` (encrypt, no verify),
or `verify-ca` / `verify-full` (encrypt and verify). Keys are matched leniently
(case, spaces, dashes, underscores, and the usual synonyms), so a hand-typed
profile still resolves. One running plugin can serve many databases, and rotating
a password needs no restart.

## Install

```bash
git clone https://github.com/Inflowenger/mysql-plugin
cd mysql-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install
npm run build
npm start
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. MySQL credentials never go in
`.env.inflow`; they are a settings profile. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

- Table and column names are identifiers, not bound parameters. They are
  backtick-quoted (internal backticks doubled) so a name that cannot be
  represented safely is rejected rather than injected. `multipleStatements` is
  disabled, so one field cannot carry several statements.
- The Insert action discovers the primary key automatically: supply every key
  column and a clash becomes an `ON DUPLICATE KEY UPDATE` of the other columns (a
  true upsert); supply only the key and a clash is a no-op; with no usable key it
  is a plain insert.
- MySQL has no `RETURNING`, so a write reports the affected/changed counts and the
  new `AUTO_INCREMENT` id, not the written row.
