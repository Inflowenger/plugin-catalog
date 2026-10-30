# DuckDB

> SQL over files on the canvas — query CSV, Parquet, JSON and Excel in place, on disk or in S3/MinIO.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/duck-plugin |
| **Node name** | `DUCKDB` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database`, `storage` |
| **Runs on** | Any `inflowv1` host |
| **License** | Apache 2.0 |
| **Status** | Active |

## What it does

Puts a SQL interface over the files a flow already has. DuckDB is linked into the
plugin — there is no server to install and no port to open — and it reads CSV,
Parquet, JSON and Excel files *where they lie*: on the plugin host's disk, over
`https://`, or in S3-compatible object storage (AWS S3, MinIO, Ceph, Garage,
R2). A glob reads many files as one table, so `s3://bucket/logs/2024-*.csv` is a
single relation a node can `GROUP BY`.

Seven nodes: query a file, describe one (columns, types, stats), list a bucket or
directory, import a file into a table, export a result back out to a file, and
two raw-SQL nodes for joins across files, `ATTACH` and DDL. It is a close sibling
of the [Postgres](postgres.md) and [ClickHouse](clickhouse.md) plugins, for the
case where the data is files rather than a database.

Values on the raw-SQL nodes bind as `$1, $2 …` and keep their type. File paths
are not bindable — they are arguments to a table function — so they are escaped
as SQL string literals and the statement that ran is reported back in the node's
output. Any string input also resolves double-brace `{{$.path}}` mustache tokens
against the flow scope, so a path or a filter can come from an upstream node.
Reads return at most 1000 rows, because every row is committed into the flow's
context; the Export node has no cap, since its data never passes through it.

## Actions

| Method | Title |
|--------|-------|
| `duckdb.file.query` | Query a File (CSV / Parquet / JSON / Excel) |
| `duckdb.file.describe` | Describe a File (schema & stats) |
| `duckdb.file.list` | List Files (local or S3/MinIO) |
| `duckdb.file.import` | Import a File into a Table |
| `duckdb.export` | Export a Query to a File |
| `duckdb.query` | Run Query (read) |
| `duckdb.execute` | Execute (write / DDL) |

Meta RPCs: `duckdb.meta.ping.check` (opens the workspace, reports the DuckDB
version and loaded extensions, and proves S3 keys by listing the default
location — backs the settings form's button and its submit validation),
`duckdb.meta.file.pick` (the path fields' button: lists a prefix as a drop-down,
or reads a chosen file's columns back) and `duckdb.meta.table.pick` (lists the
workspace's tables).

## Connection

The plugin stores no credentials and reads no database environment variables. It
declares a settings form — a DuckDB database file, read-only, a default
location, S3 endpoint / keys / URL style / TLS, and resource limits — and the
platform ships the bound profile with every call as `body.settings`.

Every field is optional, which is the thing that separates this from a
client/server plugin: DuckDB is in-process, so a node with **no profile bound**
still works, on a private in-memory workspace that reads local files and
`https://` URLs. A profile is what adds a database file whose tables outlive the
flow run, object-storage credentials, and limits. For MinIO the endpoint is
`host:port` (an `http://` prefix turns TLS off) and URL style `auto` already
picks the path-style addressing MinIO needs.

## Install

A [release](https://github.com/Inflowenger/duck-plugin/releases) carries one
self-contained binary per platform — Linux and macOS on amd64 and arm64, Windows
on amd64 — with DuckDB and the C++ runtime inside it. Nothing to compile:

```bash
curl -fsSLO https://github.com/Inflowenger/duck-plugin/releases/latest/download/duckdb-plugin-linux-amd64
chmod +x duckdb-plugin-linux-amd64
./duckdb-plugin-linux-amd64 -version        # build stamp + the DuckDB it carries
cp .env.inflow.example .env.inflow          # PLUGIN_ID / INFRA_CRED / INFRA_URL
./duckdb-plugin-linux-amd64
```

Or from source:

```bash
git clone https://github.com/Inflowenger/duck-plugin
cd duck-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
make deps                            # see the note below — a plain build fails without it
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

Building needs Go 1.27+, a C/C++ compiler and `CGO_ENABLED=1`, since DuckDB is a
C++ library linked into the binary; `make doctor` reports which of those is
missing. A release binary needs none of it — on Linux it wants glibc 2.36+ and
not even `libstdc++`.

The repo ships sample data — nested JSON with structs and arrays, the same rows
as NDJSON / CSV / Parquet, and two real public datasets — plus the node settings
that read each one, in `testdata/README.md`.

## Notes

- **`make deps` is not optional on a cold cache.** The driver's prebuilt DuckDB
  libraries ship as ~130 MB per-platform Go modules, and the public Go module
  proxy answers them with HTTP 403 — so they must be fetched with
  `GOPROXY=direct`, which is what that target does. A plain `go build` otherwise
  fails with a confusing proxy error. The Makefile also covers the awkward
  cases: `make libduckdb` / `make static-libs` download DuckDB's shared library
  or static `.a` archives plus `duckdb.h` for the `duckdb_use_lib` /
  `duckdb_use_static_lib` builds, and `make vendor-libs` copies the archives out
  of the module cache for an air-gapped host.
- **CSV, Parquet, JSON and ICU are compiled in; everything else is installed on
  demand.** A statement mentioning `s3://` pulls `httpfs`, one mentioning
  `.xlsx` pulls `excel`, and so on — which needs one-time outbound access to
  `extensions.duckdb.org` and a writable extension directory. A host with
  neither still serves every local file. Set the profile's **extension
  directory** to a persistent path in a container so the fetch happens once.
- **An in-memory workspace is shared per profile, not per node** — which is what
  lets one node create a table the next node reads, and also why it is gone when
  the plugin restarts. Name a database file for anything that must persist.
- **Import in `create` mode is a no-op on a table that already exists**, so
  re-running a flow is safe; the output says `skipped: true`.
- Counting rows in a CSV reads the whole file; in Parquet the count is in the
  footer. The Describe node's row count is a toggle for that reason.
