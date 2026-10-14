# Claude Agent

> Runs Claude as an agent on the plugin's own host — one durable Claude Code
> session per call site, with a port for the questions it cannot answer alone.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/claude-agent-plugin |
| **Node name** | `CLAUDE AGENT` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Node — [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `ai`, `utility` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Active |

## What it does

Adds a `CLAUDE AGENT` node that gives a flow a coding agent: it reads and writes files,
runs commands, and answers in prose or in a schema you define. It is built on
[`@anthropic-ai/claude-agent-sdk`](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk)
and drives the Claude Code installed on the plugin's host, so the agent works in
a real working tree on real disk rather than through an API wrapper.

It is not an LLM node. A model node sends a prompt and returns a completion; this
one hands work to an agent that decides its own steps, uses tools, keeps a
session between runs, and can come back with a question. Reach for it when the
task is *do this in this repo*, not *answer this*.

Two things separate it from a normal request/response plugin.

**It holds a conversation, not a request.** Each run of the node is one *turn* of
a durable Claude Code session. The session id is the inflow job id, so the
engine's own memory of the node's last run (`_registry.jobId`) is the handle on
that conversation — no database, no in-memory map, and nothing lost when the
plugin restarts.

**It can stop and ask.** When Claude needs a decision the flow did not give it,
the turn ends deliberately and the node fires its **Needs a human** port, with the
question already turned into prose for a person. Wire that port to a Human in the
Loop node (park mode) and bring the reply back into the same node: the session
resumes with the person's words delivered as the answer to the question Claude
was mid-way through asking, context intact, for as many rounds as the work takes.
Nothing is held open between the two runs — no process, no connection, no node
sitting at 40%; the transcript waits on disk. This is the catalog's first plugin
to declare [outbound ports](#ports), and an instance of the Node SDK's
[detached-work](https://github.com/Inflowenger/node-plugin-sdk/blob/main/docs/detached-work.md)
pattern.

Turn on **Return structured data** and give the node a JSON Schema, and the
turn's answer conforms to it — committed as `output`, so downstream nodes read
`{{$.claudeAgent.output.verdict}}` instead of parsing prose.

## Actions

| Method | Title |
|--------|-------|
| `claude.agent.run` | Run Claude |

Meta RPCs: `claude.meta.ping` (CLI version, which credential is in use, default
model, workspace — also the settings form's `submitTo`, so saving a profile tests
it), `claude.meta.models` (the models *this host* offers, re-rendering the open
form's model field as a drop-down), `claude.meta.sessions` (the sessions already
on the host for that workspace). All three answer from the agent's own process
**without sending a token to a model**, so they are free to run.

### Ports

An action with ports has no default handle, so every edge leaving the node names
one, and the branches are not editable in the drawer — their shape belongs to the
plugin.

| Port | Tag | Fires when |
|---|---|---|
| Answer | `done` | The turn finished. `text`, plus `output` when a schema was set. |
| Needs a human | `ask` | Claude asked. The session is parked mid-question — a *successful* job, not a failure. |
| Limit reached | `limit` | Out of turns or budget with work left. Run the node again to continue. |
| Failed | `_exception` | Claude could not run, or ended in error. |

## Connection

The settings profile is as much policy as credential. It holds no secret of its
own beyond the optional key, and the platform supplies it per call as
`body.settings` — nothing is stored by the plugin, and no credential reaches a
form, a log line or the node's output.

| Field | Required | Meaning |
|---|---|---|
| `apiKey` | no | Anthropic API key. Empty means the agent runs as whatever the host's own `claude` is logged in as. |
| `baseUrl` | no | A gateway or proxy instead of the public API. |
| `model` | no | Default model for nodes that name none. |
| `workspaceRoot` | no | The tree nodes may be pointed at; a node outside it fails before Claude starts. Empty means unrestricted. See [Notes](#notes) — it is organisation, not a sandbox. |

Keys are matched leniently (case, spaces, dashes, underscores and the obvious
synonyms), because profiles are typed by hand. An API key comes from
[console.anthropic.com](https://console.anthropic.com/settings/keys); a host login
comes from running `claude` once on the host.

## Install

```bash
git clone https://github.com/Inflowenger/claude-agent-plugin
cd claude-agent-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install && npm run build && npm start
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**Requirements on the host:** Node 20+, and Claude Code installed and either
logged in or reachable with an API key. `CLAUDE_EXECUTABLE` points at it when it
is not on `PATH`; `CLAUDE_WORKSPACE_ROOT` is the default fence when no profile
sets one. On startup the plugin logs what the host's Claude actually is — version,
default model, credential source — so a misconfigured host is obvious in the log
rather than on the first flow run.

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **The workspace root fences the node, not yet the agent.** Containment is
  checked before Claude starts — a node pointed outside the root fails, and
  traversal and prefix tricks are rejected (`/srv/ws-evil` is not inside
  `/srv/ws`). But `cwd` is not a sandbox: Claude Code resolves its *project* from
  the git root above `cwd`, so its Read/Grep tools can reach files outside the
  workspace, including the plugin's own `.env.inflow`. Run the plugin as a user
  that cannot read what the agent must not see, and keep `.env.inflow` outside any
  tree the agent works in.
- **The agent runs commands on your host.** `bypassPermissions` approves
  everything — use it only in a workspace you are willing to lose. The default
  `auto` mode has a classifier judge each tool call and asks a person when it
  cannot decide; `plan` explores without changing anything.
- **A turn stops with its flow.** The action carries `jobstop`, so a stopped run
  aborts the subprocess instead of leaving an agent writing to someone's disk. The
  conversation survives — the transcript is on disk and the next run resumes it.
- **Turns cost money.** *Max turns* (30 by default) and *Max spend* are per-turn
  ceilings, and a run that hits one fires `limit` rather than failing. Each run
  commits `costUsd`, `turns`, `model` and `usage`.
- **The human loop needs a host that renders outbound ports** and offers a Human
  in the Loop node in park mode. The plugin itself is portable — it speaks only
  `inflowv1` and needs no host-specific service — but on a host without those,
  the `ask` branch has nowhere to go and the node is a one-shot agent.
- **Sessions are kept by Claude Code**, not by the plugin: ~30 days on disk by
  default. A session that has expired cannot be resumed, so a flow parked at a
  human for longer than that starts fresh.
