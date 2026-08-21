# Plugins

Every Inflowenger plugin we know about. Each file here is a **pointer** — the
plugin's source, releases, and issues live in its author's own repository.

| Plugin | Node | Actions | SDK | Author | Repository |
|--------|------|--------:|-----|--------|------------|
| [Gmail (OpenConnector)](gmail-oc.md) | `Gmail (OpenConnector)` | 4 | Node | [@FloMorphic](https://github.com/FloMorphic) | [gmail-oc-plugin](https://github.com/FloMorphic/gmail-oc-plugin) |
| [Jira](jira.md) | `JIRA` | 14 | Go | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [jira-plugin](https://github.com/mehdi-shokohi/jira-plugin) |
| [MongoDB](mongodb.md) | `MONGODB` | 4 | Go | [@FloMorphic](https://github.com/FloMorphic) | [mongodb-plugin](https://github.com/FloMorphic/mongodb-plugin) |
| [Postgres](postgres.md) | `POSTGRES` | 3 | Go | [@FloMorphic](https://github.com/FloMorphic) | [postgres-plugin](https://github.com/FloMorphic/postgres-plugin) |

[`index.json`](index.json) is the same list in machine-readable form, for tools
that want to consume the catalog.

## Categories

Entries carry one or more categories so the list stays navigable as it grows.

| Category | Meaning |
|----------|---------|
| `issue-tracking` | Issue trackers and project management |
| `communication` | Chat, e-mail, notification delivery |
| `storage` | Object stores, file systems, document stores |
| `database` | SQL and NoSQL engines |
| `ai` | Model providers, embeddings, MCP bridges |
| `devops` | CI/CD, source hosting, infrastructure |
| `crm` | Sales and customer platforms |
| `protocol` | Generic transports — HTTP, gRPC, MQTT, sockets |
| `utility` | Transforms and helpers with no external I/O |

Need one that isn't here? Propose it in your PR.

## Adding an entry

Copy [`../templates/plugin-entry.md`](../templates/plugin-entry.md) to
`<slug>.md`, fill it in, add the plugin to `index.json` and to both tables (here
and in the root [README](../README.md)), then open a PR. Details in
[CONTRIBUTING.md](../CONTRIBUTING.md).
