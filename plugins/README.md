# Plugins

Every Inflowenger plugin we know about. Each file here is a **pointer** — the
plugin's source, releases, and issues live in its author's own repository.

| Plugin | Node | Actions | SDK | Runs on | Author | Repository |
|--------|------|--------:|-----|---------|--------|------------|
| [Gmail (OpenConnector)](gmail-oc.md) | `Gmail (OpenConnector)` | 4 | Node | FloMorphic ★ | [@FloMorphic](https://github.com/FloMorphic) | [gmail-oc-plugin](https://github.com/FloMorphic/gmail-oc-plugin) |
| [Jira](jira.md) | `JIRA` | 14 | Go | Any host | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [jira-plugin](https://github.com/mehdi-shokohi/jira-plugin) |
| [MongoDB](mongodb.md) | `MONGODB` | 4 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [mongodb-plugin](https://github.com/FloMorphic/mongodb-plugin) |
| [MySQL](mysql.md) | `MYSQL` | 4 | Node | Any host | [@Inflowenger](https://github.com/Inflowenger) | [mysql-plugin](https://github.com/Inflowenger/mysql-plugin) |
| [Postgres](postgres.md) | `POSTGRES` | 3 | Go | Any host | [@FloMorphic](https://github.com/FloMorphic) | [postgres-plugin](https://github.com/FloMorphic/postgres-plugin) |
| [Telegram (OpenConnector)](telegram-oc.md) | `Telegram (OpenConnector)` | 5 | Go | FloMorphic ★ | [@mehdi-shokohi](https://github.com/mehdi-shokohi) | [telegram-oc-plugin](https://github.com/mehdi-shokohi/telegram-oc-plugin) |

[`index.json`](index.json) is the same list in machine-readable form, for tools
that want to consume the catalog.

## Runs on

Every plugin here speaks `inflowv1`, the plain NATS protocol, so it is normally
**portable**: any product that implements `inflowv1` can load it. That is what
**Any host** means in the table.

A **★** marks a plugin that needs more than the protocol — a **host-specific
service** that only one platform provides — so it runs on that platform alone.
[Gmail (OpenConnector)](gmail-oc.md) holds no Google credentials; it asks
FloMorphic's central **Connect / OpenConnector** proxy to run each Gmail action,
reaching it over the `flomorphic.svc.oc.*` NATS subjects. Those subjects are
served by an internal FloMorphic service, so the plugin is bound to FloMorphic and
will not run on a bare `inflowv1` host.

The binding is recorded as a `hostDependency` object in
[`index.json`](index.json) (`platform`, `service`, and the `subjects` it uses).
Omit it and the plugin is treated as portable.

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
