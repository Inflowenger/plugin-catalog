# zvec

> Vector, full-text and hybrid search on the embedded zvec engine — a vector database with no server to run.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/zvec-plugin |
| **Node name** | `ZVEC` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database`, `ai` |
| **Runs on** | Any `inflowv1` host — needs the zvec shared library on it (see [Notes](#notes)) |
| **License** | See repository |
| **Status** | Beta |

## What it does

Exposes [zvec](https://github.com/alibaba/zvec) as twelve nodes: collection
lifecycle (create, list, info, optimize, drop) and document operations (upsert,
vector search, full-text search, **hybrid search**, fetch, scan, delete).

zvec is **embedded** — a library, not a service. There is no container to run
beside the plugin, no port, no credential and no network hop: a collection is a
directory on whichever host the plugin process runs on. That makes it the vector
store to reach for when a deployment should carry as little as possible, and the
wrong one when several services need to share an index. Collections are opened
once and held open, because the engine takes an exclusive lock on each
directory — so **one plugin process per data directory**.

**Hybrid search** is the reason to pick zvec over a plain vector store. A vector
half and a full-text half each produce a ranking and the engine fuses them,
either by **RRF** (rank position, so the two halves' scores never have to be
comparable — the default) or by **weights** on the raw scores. One *Query text*
drives both halves; either can be overridden. Pointed at a collection with only
one of the two halves, the action runs as that half's own search rather than
failing.

A collection has a **fixed schema**, declared at creation: a dense vector field
(`hnsw`, `ivf`, `flat`, `ivf_rabitq` or `diskann`, with a metric and optional
`fp16`/`int8`/`int4` quantization), a full-text field (`standard`, `whitespace`,
`ngram` or `jieba` tokenizer, with `lowercase` / `ascii_folding` / `stemmer`
filters), and the scalar fields to filter on. Filters are SQL-like expressions
evaluated before the search — `category = 'bikes' AND qty > 2` — so they narrow
what is searched rather than what is returned.

Like the [Qdrant](qdrant.md) plugin, it can embed text for you: configure
**OpenAI**, **Google Gemini**, **Cohere** or a **Custom** OpenAI-compatible
endpoint (Ollama, LM Studio, vLLM) and Upsert, Vector search and Hybrid search
accept plain text. Leave the provider **None** to supply vectors yourself. A
collection's vector size must match the model's dimension — the **Test
embedding** meta function reads it off.

## Actions

| Method | Title |
|--------|-------|
| `zvec.collection.create` | Create collection |
| `zvec.collection.list` | List collections |
| `zvec.collection.info` | Collection info |
| `zvec.collection.optimize` | Optimize collection |
| `zvec.collection.drop` | Drop collection |
| `zvec.doc.upsert` | Upsert documents |
| `zvec.doc.search` | Vector search |
| `zvec.doc.fts` | Full-text search |
| `zvec.doc.hybrid` | Hybrid search |
| `zvec.doc.fetch` | Fetch documents |
| `zvec.doc.scan` | Scan documents |
| `zvec.doc.delete` | Delete documents |

Meta RPCs: `zvec.meta.ping` (**Check** — validates the data directory and lists
what it holds), `zvec.meta.embed` (**Test embedding** — verifies the provider and
reads the model's vector dimension), `zvec.meta.collections` and
`zvec.meta.fields` (the ↻ pickers on the Collection and field boxes).

## Connection

The plugin stores no credentials and no storage configuration. A settings
profile carries:

| Key | Required | Meaning |
|-----|----------|---------|
| `dataDir` | yes | Directory on the plugin's host holding the collections. Created if absent. |
| `readOnly` | no | Open every collection read-only; the engine then refuses writes itself. |
| `enableMmap` | no | Map segment files instead of reading them in. |
| `embeddingProvider` | no | `none`, `openai`, `gemini`, `cohere` or `custom`. |
| `embeddingModel` / `embeddingApiKey` / `embeddingBaseUrl` | no | The provider's own; the base URL is required for `custom`. |

Keys are matched leniently (case, spaces, dashes and underscores are ignored,
with the usual synonyms), since a profile is often typed by hand. The platform
stores the filled-in form as a named profile and folds it into every call as
`body.settings`, so one running plugin serves many profiles and rotating an
embedding key needs no restart.

Because `dataDir` is a path on the plugin's own host, a profile names storage
rather than a service — two profiles pointing at one directory are one store,
and a second plugin process pointed at it will fail on the engine's lock.

## Install

```bash
git clone https://github.com/Inflowenger/zvec-plugin
cd zvec-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
./scripts/fetch-zvec-lib.sh          # the zvec engine for this platform
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. The data directory and any
embedding-provider key never go in `.env.inflow`; they are a settings profile.
See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

> **One deviation from the standard Go command.** The plugin is built without
> cgo, so on a host that has a **C compiler** installed `go run .` turns cgo on
> and fails with `zvec/c_api.h: No such file or directory`. There, run
> `make run` or `CGO_ENABLED=0 go run .`. A host with no C toolchain — most
> servers and containers — needs nothing extra, because Go disables cgo on its
> own and `go run .` works as written. See the repository's
> **The native library** section.

## Notes

- **The engine is a native library.** zvec is C++ with Go bindings, and this
  plugin uses the bindings' runtime-FFI backend: it builds with
  `CGO_ENABLED=0` — no C compiler, no headers, on any machine with a Go
  toolchain — and loads `libzvec_c_api.so` (`.dylib` / `.dll`) at startup.
  `./scripts/fetch-zvec-lib.sh` downloads the prebuilt library for the host
  into `lib/<goos>_<goarch>/`, which is a path the loader already searches, so
  nothing needs configuring afterwards. `ZVEC_LIBRARY_PATH` overrides it,
  `make dist` lays out the binary with the library beside it, and the
  repository's `Dockerfile` does the same. Linux (glibc and musl), macOS and
  Windows, on x86-64 and ARM64. Upstream publishes no static archive, so there
  is nothing to link in instead.
- **A plugin whose engine is missing still starts** and serves its forms,
  failing each action with a message naming the fix — so a node drawer can be
  opened and read on a host that is not set up yet.
- **Filter syntax is SQL-like**: equality is a single `=`, not `==`, and a quote
  inside a value is escaped with a backslash (`name = 'O\'Brien'`), not by
  doubling it. zvec's own README example uses `==`, which the engine rejects.
- **Run Optimize after a bulk load.** Writes land in new segments whose
  documents are searched by brute force until they are merged. **Collection
  info** reports each index's completeness, which is how you tell whether it is
  needed.
- **Group-by search** exists in the engine but `zvec-go` exposes no way to
  execute the query it builds, so the plugin does not offer it.
- **Scan cannot resume a cursor across flow runs** — the engine's iterator is
  live — so paging means skipping what was already seen. Filter on an indexed
  field instead of scanning a large collection.
- A collection's **schema is fixed** at creation: the vector size, metric and
  index cannot be changed afterwards. A **filtered delete** does not report how
  many documents it removed; the engine does not say.
- Engine-wide tuning is environment-only, because the library is configured once
  per process and so cannot be set per profile: `ZVEC_MEMORY_LIMIT_MB`,
  `ZVEC_QUERY_THREADS`, `ZVEC_OPTIMIZE_THREADS`, `ZVEC_LOG_LEVEL`. `REQ_TIMEOUT`
  (seconds, default 60) is the NATS request/reply deadline.
