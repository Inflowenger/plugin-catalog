# Codex Agent

> Runs OpenAI Codex as an agent on the plugin's own host — one durable Codex
> thread per call site, fenced by the operating system's own sandbox, with a port
> for the approvals and questions it cannot settle alone.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/codex-agent-plugin |
| **Node name** | `CODEX AGENT` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Python — [`inflowenger-plugin-sdk`](https://pypi.org/project/inflowenger-plugin-sdk/) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `ai`, `utility` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Beta — see [Notes](#notes) |

## What it does

Adds a `CODEX AGENT` node that gives a flow a coding agent: it reads and writes
files, runs commands, and answers in prose or in a schema you define. It is built
on [`openai-codex`](https://pypi.org/project/openai-codex/), the Codex Python SDK
that drives the Codex app-server over JSON-RPC, so the agent works in a real
working tree on real disk rather than through an API wrapper.

It is not an LLM node. A model node sends a prompt and returns a completion; this
one hands work to an agent that decides its own steps, uses tools, keeps a thread
between runs, and can come back with a question. Reach for it when the task is
*do this in this repo*, not *answer this*.

It is the sibling of [Claude Agent](claude-agent.md) — same node shape, same four
ports, same human loop — over a different agent. Three things separate both from
a normal request/response plugin.

**It holds a conversation, not a request.** Each run of the node is one *turn* of
a durable Codex thread. Codex mints its own thread id, so the node adopts that id
as the inflow job id — which makes the engine's own memory of the node's last run
(`_registry.jobId`) the handle on that conversation, with no database, no
in-memory map, and nothing lost when the plugin restarts.

**It can stop and ask.** When Codex wants to step outside its sandbox, the
app-server sends the *client* a JSON-RPC approval request. The node refuses it —
so nothing proceeds on a decision nobody made — ends the turn, and fires its
**Needs a human** port with the request already turned into prose for a person.
Wire that port to a Human in the Loop node (park mode) and bring the reply back
into the same node: **approve** accepts the next approval the turn raises,
**decline** refuses it, and anything else is passed to Codex as instructions. The
thread resumes with its context intact, for as many rounds as the work takes.
Nothing is held open between the two runs — no process, no connection, no node
sitting at 40%; the thread waits on disk. An instance of the SDK's detached-work
pattern, where the plugin reports state and ends and the flow is the observer.

**The fence is the operating system's.** `read-only` and `workspace-write` are
enforced by Seatbelt (macOS) or bubblewrap (Linux), not by the model's good
behaviour, so the workspace is a boundary the agent cannot talk its way around.

Turn on **Return structured data** and give the node a JSON Schema, and the
turn's answer conforms to it — committed as `output`, so downstream nodes read
`{{$.codex.output.verdict}}` instead of parsing prose.

## Actions

| Method | Title |
|--------|-------|
| `codex.agent.run` | Run Codex |

Meta RPCs: `codex.meta.ping` (runtime version, which credential is in use,
workspace root — also the settings form's `submitTo`, so saving a profile tests
it), `codex.meta.models` (the models *this host* offers, re-rendering the open
form's model field as a drop-down), `codex.meta.dirs` (the directories under the
workspace root, as rows for *Also writable*), `codex.meta.threads` (the threads
already on this host). All four answer from the Codex app-server **without
sending a token to a model**, so they are free to run.

### Ports

An action with ports has no default handle, so every edge leaving the node names
one, and the branches are not editable in the drawer — their shape belongs to the
plugin.

| Port | Tag | Fires when |
|---|---|---|
| Answer | `done` | The turn finished. `text`, plus `output` when a schema was set. |
| Needs a human | `ask` | Codex needs a decision. The thread is parked on the question — a *successful* job, not a failure. |
| Limit reached | `limit` | The node's own token or time budget cut the turn short. Run the node again to continue. |
| Failed | `_exception` | Codex could not run, or the turn ended in error. |

## Connection

The settings profile is as much policy as credential. It holds no secret of its
own beyond the optional key, and the platform supplies it per call as
`body.settings` — nothing is stored by the plugin, and no credential reaches a
form, a log line or the node's output.

| Field | Required | Meaning |
|---|---|---|
| `apiKey` | no | OpenAI API key. Empty means the agent runs as whatever the host's own `codex login` is authenticated as. |
| `baseUrl` | no | A gateway or proxy instead of the public API. |
| `model` | no | Default model for nodes that name none. |
| `workspaceRoot` | no | The tree nodes may be pointed at; a node outside it fails before Codex starts. Empty means unrestricted. |

Keys are matched leniently (case, spaces, dashes, underscores and the obvious
synonyms), because profiles are typed by hand. An API key comes from
[platform.openai.com](https://platform.openai.com/api-keys); a host login comes
from running `codex login` once on the host.

## Install

```bash
git clone https://github.com/Inflowenger/codex-agent-plugin
cd codex-agent-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
pip install -r requirements.txt && python main.py
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**Requirements on the host:** Python 3.11+, and Codex reachable — the runtime
bundled with `openai-codex` serves, or `CODEX_EXECUTABLE` points at another build
— and either logged in or reachable with an API key. On Linux the sandbox wants
`bubblewrap` (`bwrap`) on `PATH`. `CODEX_WORKSPACE_ROOT` is the default fence
when no profile sets one. On startup the plugin logs what the host's Codex
actually is — version and credential — so a misconfigured host is obvious in the
log rather than on the first flow run.

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **Beta: the model call is unverified.** The plugin is verified live against
  Codex 0.162.1 on a real host — runtime boot, the zero-token probe, thread
  minting (0.85s, a UUIDv7 usable as a job id), client configuration and config
  overrides, the notification stream, and error mapping — and 47 unit tests pass.
  But the author has no funded OpenAI credential, so **a full turn, the approval
  park and the resume have not been exercised against a live model**. Treat the
  conversation and human-loop paths as untested until you have run them on your
  own host. [Claude Agent](claude-agent.md) is the end-to-end-verified sibling.
- **The agent runs commands on your host.** `danger-full-access` removes the
  sandbox entirely — use it only in a workspace you are willing to lose.
  `workspace-write` is the default and `read-only` explores without changing
  anything; both are enforced by the OS, so they hold even when the model is
  wrong about what it may do.
- **"Also writable" grants write, not read.** Those rows widen the sandbox, and
  they are fenced by the same workspace root as the workspace itself — otherwise
  the fence would leak through a field nobody thinks of as a path.
- **The approval handler fails closed.** Without it the SDK's default answers
  *accept* to every approval request. If a future `openai-codex` moves it, the
  node refuses to run anything but `read-only` rather than silently
  auto-approving.
- **Codex will not run outside a git repository** unless *Allow a non-git
  workspace* is ticked, because without one it cannot show or undo what it
  changed.
- **Budgets are the node's, not Codex's.** Codex enforces no turn cap and no
  spend cap, and reports tokens rather than dollars. *Token budget* and *Time
  budget* are watched as the turn streams, and breaching one fires `limit` rather
  than failing. Each run commits `tokens`, `commands`, `filesChanged` and
  `durationMs`.
- **A turn stops with its flow.** The action carries `jobstop`, so a stopped run
  ends the turn instead of leaving an agent writing to someone's disk. The
  conversation survives — the thread is on disk and the next run resumes it.
- **The human loop needs a host that renders outbound ports** and offers a Human
  in the Loop node in park mode. The plugin itself is portable — it speaks only
  `inflowv1` and needs no host-specific service — but on a host without those,
  the `ask` branch has nowhere to go and the node is a one-shot agent.
- **Threads are kept by Codex**, not by the plugin: they live in
  `~/.codex/sessions` on the host. A thread that has been cleared cannot be
  resumed, so a flow parked at a human for long enough starts fresh.
