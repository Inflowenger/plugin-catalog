# Qdrant

> Vector search and collection management on the Qdrant vector database, from the Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/qdrant-plugin |
| **Node name** | `QDRANT` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Node — [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database`, `ai` |
| **License** | See repository |
| **Status** | Active |

## What it does

Exposes [Qdrant](https://qdrant.tech) collection and point operations as seven
nodes, talking directly to Qdrant's REST API: create and list collections, upsert
points, run nearest-neighbour vector search, and retrieve, scroll, or delete
points. It targets any Qdrant instance — local, self-hosted, or Qdrant Cloud —
over a URL and an optional API key.

Qdrant searches vectors, not text, so the node can embed text for you. Configure
an embedding provider in the settings — **OpenAI**, **Google Gemini**, **Cohere**,
or a **Custom** OpenAI-compatible endpoint (Ollama, LM Studio, vLLM) — and both
**Upsert** and **Vector search** accept plain `text`: it is embedded before it
reaches Qdrant (the source text is kept under `payload.text` on upsert). Leave the
provider **None** to supply raw vectors yourself; a raw `vector` bypasses embedding
on either action. A collection's vector size must match the model's dimension —
the **Test embedding** meta function reads it off. Structured inputs (vectors,
points, filters, ID lists) are entered as JSON.

## Actions

| Method | Title |
|--------|-------|
| `qdrant.collection.create` | Create collection |
| `qdrant.collection.list` | List collections |
| `qdrant.points.upsert` | Upsert points |
| `qdrant.points.search` | Vector search |
| `qdrant.points.retrieve` | Retrieve points |
| `qdrant.points.scroll` | Scroll points |
| `qdrant.points.delete` | Delete points |

Meta RPCs: `qdrant.meta.ping` (Test connection, behind the settings dialog) and
`qdrant.meta.embed` (Test embedding — verifies the provider and reads the model's
vector dimension).

## Connection

The plugin stores no credentials. A Qdrant instance is configured per-account in
the node's settings — the instance **URL** and an optional **API key** — alongside
the optional embedding provider and its own key. The platform stores the filled-in
form as a named settings profile and folds it into every call as `body.settings`.
One running plugin serves many instances, and rotating a key needs no restart.

## Install

```bash
git clone https://github.com/Inflowenger/qdrant-plugin
cd qdrant-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install
npm run build
npm start
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. Qdrant and embedding-provider credentials
never go in `.env.inflow`; they are a settings profile. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

- Raise `REQ_TIMEOUT` (seconds) at deploy time if your Qdrant instance is slow to
  answer.
- On upsert, a point without an `id` gets an auto-generated UUID.
