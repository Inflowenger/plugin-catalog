# Jira

> Everyday Jira REST operations as nodes on the Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/mehdi-shokohi/jira-plugin |
| **Node name** | `JIRA` |
| **Author** | [@mehdi-shokohi](https://github.com/mehdi-shokohi) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `issue-tracking`, `devops` |
| **License** | See repository |
| **Status** | Active |

## What it does

Create, read, update, delete, search, transition, assign, comment, link, log
work, attach files, and look up projects and users — 14 actions plus 4 meta RPCs
for building the node's drawer.

It targets both Jira flavours from one binary: **Jira Cloud** (REST v3, ADF rich
text, `accountId` users) and **Jira Server / Data Center** (REST v2, wiki markup,
username users). The bound connection says which, and the client adapts —
including the two different search paging models (`nextPageToken` vs `startAt`).

## Actions

| Method | Title |
|--------|-------|
| `jira.issue.create` | Create Issue |
| `jira.issue.get` | Get Issue |
| `jira.issue.update` | Update Issue |
| `jira.issue.delete` | Delete Issue |
| `jira.issue.search` | Search Issues (JQL) |
| `jira.issue.transition` | Transition Issue |
| `jira.issue.assign` | Assign Issue |
| `jira.issue.comment.add` | Add Comment |
| `jira.issue.comment.list` | List Comments |
| `jira.issue.link` | Link Issues |
| `jira.issue.worklog.add` | Log Work |
| `jira.issue.attachment.add` | Add Attachment |
| `jira.project.list` | List Projects |
| `jira.user.search` | Search Users |

Meta RPCs: `jira.meta.ping`, `jira.meta.projects`, `jira.meta.issuetypes`,
`jira.meta.transitions`.

## Connection

The plugin stores no Jira credentials and reads no Jira environment variables. It
declares a settings form — site URL, deployment, account e-mail, API token — and
the platform ships the bound profile with every call as `body.settings`. Bind a
profile in the node drawer; one running plugin can serve many Jira sites, and
rotating a token needs no restart.

## Install

```bash
git clone https://github.com/mehdi-shokohi/jira-plugin
cd jira-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).
