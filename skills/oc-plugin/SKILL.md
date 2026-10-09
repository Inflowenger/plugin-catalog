---
name: oc-plugin
description: Build an Inflowenger `-oc` plugin — a node whose actions are executed by oomol OpenConnector through FloMorphic → Connect, so the plugin holds no provider credential. Use when the task is to create, scaffold, or extend a plugin for a service OpenConnector already covers (Jira, Slack, Notion, Qwen, Stripe, GitLab, HubSpot, … a thousand-plus providers), when a plugin name ends in `-oc`, or when the user mentions OpenConnector / oomol / Connect / `flomorphic.svc.oc.*`. Its first rule: pull the service's live action catalog from the OpenConnector API before writing a single action — never guess an action id or a parameter name.
---

# Building an Inflowenger `-oc` plugin

An `-oc` plugin is a **request builder**. It holds no provider credential and
makes no provider API call. The account is connected once, centrally, in
**FloMorphic → Connect** (which runs oomol **OpenConnector**), and the plugin
asks the FloMorphic backend to run each OpenConnector action as that account.

```
canvas node → NATS flomorphic.svc.oc.proxy → FloMorphic backend (holds the OC token)
            → OpenConnector /v1/* → the provider's API
```

The backend is generic: it injects the auth header and forwards. **Every piece of
knowledge about the service lives in your plugin** — which actions exist, what
each one's input is called, which endpoint to hit. That is why this skill exists:
get that knowledge from the API, not from memory.

Read this skill **together with** the SDK's own `inflow-plugin` skill (or
[`build-a-plugin.md`](https://github.com/Inflowenger/plugin-catalog/blob/main/docs/build-a-plugin.md)),
which covers the parts common to every plugin — `Done`/`DoneWithError`, forms,
settings, meta RPCs, blocking after `Start()`. This file covers only what is
different about `-oc`.

## Rule zero — never invent an action id or a parameter name

OpenConnector declares every curated action's input with **`additionalProperties:
false`** and **camelCase** property names (`perPage`, `issueNumber`, not
`per_page` or `issue_number`). A plausible-looking field name is not a near miss;
it is a hard `400 invalid_input`. An action id you half-remember is `404
unknown_action`.

So: **before writing any action code, fetch the service's action catalog and work
from it.** If you cannot fetch it — no token yet — stop and get one (next
section) rather than writing actions you intend to fix later. This is the single
difference between an `-oc` plugin that works on the first run and one that
returns 400s on every node.

Nor is the curated surface the size you expect. On hosted oomol today `github`
has 147 actions but `jira` has **7** — `list_projects`, `get_project`,
`search_issues`, `get_issue`, `create_issue`, `list_issue_comments`,
`add_comment` — and `jira.create_issue` requires only `summary`, not the
`projectKey` the REST API would make you think. Count the actions before
promising a surface, and expect to need the proxy for the rest.

Do not skip this because the service or its REST API is familiar. oomol's names
are oomol's: it renames the provider's parameters to its own camelCase house
style (GitHub's `per_page` and `issue_number` are declared `perPage` and
`issueNumber`), and its action ids are its own too — `github.list_my_repositories`
is one action, and nothing is called `github.repos.list`.

## Step 1 — the developer must create an access token

The catalog API is authenticated even for discovery: listing actions needs a
token just as running one does. Without one, every call answers `401 token not
found`.

**Ask the developer to do this; do not try to work around it.** Say, in these
words if it helps:

> I need an OpenConnector runtime access token before I can define the actions.
> In the oomol web panel (the Connect / OpenConnector console):
> 1. Connect the **<service>** account you want the plugin to act as.
> 2. Open the runtime-tokens page and **create an access token**.
> 3. Give me the token, or better, export it in the shell I am running in:
>    `export OC_TOKEN='<token>'`
>
> If the plugin's actions will use the **provider proxy** as well as curated
> actions, the token needs `allowedProxies` to include `<service>` (or `*`) —
> it is **empty by default**, which denies all proxy calls.

Then:

```bash
export OC_TOKEN='api-<key-from-the-panel>'                  # never commit this
export OC_BASE_URL='https://connector.oomol.com' # or the self-hosted origin
```

**The header form is not the same on every deployment — do not assume `Bearer`.**

```bash
# hosted oomol: the panel documents the token bare, and it issues api-… keys
curl -s -H "authorization: $OC_TOKEN" "$OC_BASE_URL/v1/actions?service=github"
```

On hosted oomol an `api-…` key is verified against the oomol account service,
and it is reached **either** bare **or** behind `Bearer` — the `api-` prefix on
the token is what selects that path, not the scheme. A self-hosted open-source
runtime is the opposite: it parses the header's scheme and reads no token at all
without a recognized `Bearer `, so there the prefix is required. `oc_catalog.py`
tries the right form first for the token it is given and falls back to the other.

Token hygiene, which applies to you as much as to the developer:

- It is a live credential. Keep it in the environment. Never write it into a
  file in the repo, a committed example, a test fixture, or a log line.
- Never put it in the plugin either — see **Step 4**. The plugin gets its access
  through NATS; a token inside an `-oc` plugin is a design error, not a shortcut.
- A token granted `allowedConnections` is pinned to specific connection IDs;
  omitting an alias then selects `default` and fails with `403
  connection_not_allowed` unless that one is granted.

## Step 2 — pull the catalog and read it

The helper script makes the calls you need and prints something small enough to
reason about (a large provider has >140 actions; do not dump them all raw):

```bash
scripts/oc_catalog.py services                   # every service the token can see
scripts/oc_catalog.py list github --type read    # one line per action: id, type, required input
scripts/oc_catalog.py search github "create issue"
scripts/oc_catalog.py show github.create_issue   # full inputSchema + scopes + output keys
scripts/oc_catalog.py save github -o oc/catalog  # raw JSON to disk, for diffing later
```

Plain `curl` is equivalent — the script only formats:

| Call | Returns |
|------|---------|
| `GET /v1/actions` | `data`: `[{ "service": "github" }, …]` — the services that have actions |
| `GET /v1/actions?service=<svc>` | `data`: **a bare array** of action metadata (below) |
| `GET /v1/actions/<actionId>` | `data`: one action metadata object |
| `GET /v1/actions/search?q=<q>&service=<svc>&limit=10` | ranked matches — use this on a big provider instead of listing everything |
| `GET /v1/apps` · `GET /v1/apps/services/<svc>` | the connected accounts: `alias`, `isDefault`, `authType`, `status`, `accountLabel`, and the grants as both `scopes` and `providerScopes` |

All `/v1` responses share one envelope — `{"success", "message", "data", "meta"}`
on success, `{"success": false, "errorCode", "message", "data", "meta"}` on
failure. Unwrap `data`; read `errorCode`, not just the HTTP status.

**Trust the response over the upstream docs.** Hosted connector.oomol.com runs
a different build from `oomol-lab/open-connector@main`: it omits metadata fields
the source serialises, and it does not serve the admin console routes at all.
When the two disagree, the deployment you are targeting wins — which is the
whole argument for fetching rather than remembering.

Each action in `data` carries:

| Field | Use it for |
|-------|-----------|
| `id` | the exact string to call — `<service>.<name>` |
| `name`, `description` | the canvas action's Title and Description |
| `operationType` | `read` · `write` · `destructive` — gate on it (**Step 3**) |
| `inputSchema` | **the contract.** Its `properties`, `required` and `additionalProperties` are what you may send |
| `outputSchema` | what downstream nodes can read out of your `Done` payload |
| `requiredScopes` | oomol's own scope vocabulary (`github.repo.read`), for the scope check |
| `providerPermissions` | the provider's native permission names, for the docs and error messages |

The open-source runtime adds three more fields. **Hosted connector.oomol.com
does not return them today** (its action metadata is exactly the nine above —
checked across all 147 `github` actions), so treat them as present-if-present
and never make the build depend on them:

| Field | Use it for |
|-------|------------|
| `followUpActions` | the actions oomol expects to be chained after this one — often the right second action to expose |
| `asyncLifecycle` | non-null means the action is long-running: `{startActionId, statusActionId, cancelActionId?}`. Start, then poll — not one call. A `cancelActionId` is what a cancelable handler should call when the flow is stopped |
| `execution` | `{locallyExecutable, catalogOnly, requiredAuthTypes, noAuthRunnable, needsCredential}` — `catalogOnly: true` means schemas exist but nothing can run it, so do not expose those |

Write the shortlist down before coding. A table of *chosen oomol action id → your
canvas method → required input properties*, in the plugin's README or a
`docs/oc-actions.md`, is what stops the mapping drifting as the plugin grows —
and it is the one artifact a reviewer can check against the live catalog.

oomol's own runtime also renders an agent-readable guide per action — input
schema, scopes, provider permissions, the connection identity it would run as,
and request examples. **It is oomol's endpoint, on the OpenConnector origin, and
FloMorphic does not forward it**: the Connect proxy carries `/v1/actions/*` and
`/v1/proxy/*`, so a plugin can never reach this at runtime. It is a design-time
convenience for you and the developer, and only if you can authenticate to it:

- `GET /api/actions/<actionId>/agent.md` — on a **self-hosted** runtime. Note
  the path: `/api/`, **never** `/v1/` (there is no `agent.md` route under `/v1`,
  where `:actionId` matches a single segment, so `/v1/actions/<id>/agent.md` is
  a `404`). It is the admin surface, so it wants `OOMOL_CONNECT_ADMIN_TOKEN` or
  a console session, not the runtime token from Step 1. **On hosted
  connector.oomol.com this route does not exist at all** — it answers `404 Not
  Found` even with a valid token, so do not read a 404 here as a bad action id.
- The **MCP** tool `get_action_guide` (on `POST /mcp`, runtime scope) renders the
  same guide from the same code, with an `execute_action` example instead of
  curl. If the agent host can speak MCP, this is the way to read it with the
  token you already have.

Neither is required. `GET /v1/actions/<actionId>` carries the same contract as
data, which is what `oc_catalog.py show` prints.

## Step 3 — choose the canvas action surface

oomol's curated list is not your action list. Translate it.

- **Fewer, task-shaped actions.** ~147 curated GitHub actions became 13 canvas
  actions in [github-oc](https://github.com/FloMorphic/github-oc); 30 Google
  actions stayed 1:1 in
  [google-office-oc-plugin](https://github.com/FloMorphic/google-office-oc-plugin)
  because each was already one concrete operation. Collapse where several oomol
  actions are one user intent (list-own + list-org repos → one **List
  repositories**); keep 1:1 where they are genuinely different jobs.
- **Read-only first.** Ship `operationType: read` actions, then add writes when a
  workflow needs them. Never expose a `destructive` action unless the settings
  profile explicitly opts in — and say so in the action's description.
- **Group with `Tags["class"]`** when one plugin spans several products, so the
  canvas palette groups them (`sheets`, `docs`, `drive`, `calendar`).
- **Curated action, or provider proxy?** Prefer the curated action whenever one
  covers the need and you have confirmed its `inputSchema`. Reach for
  `POST /v1/proxy/<service>` only for what oomol does not curate — and expect to
  need it: github-oc ended up mostly proxy, because the security endpoints
  (alerts, branch protection, org members) have no curated action.
- **One escape hatch, at most.** A `*.request` action taking a raw
  `{endpoint, method, query, body}` is worth shipping once per plugin. It is not
  a substitute for modelling the common cases.

## Step 4 — build the request

The plugin publishes on `flomorphic.svc.oc.proxy`; the backend adds the auth
header. Your job is only to compose the HTTP request that the backend will make.

**Run a curated action.** The input goes under an `input` key — not at the top
level:

```jsonc
// POST /v1/actions/github.create_issue
// properties and required names copied from this action's inputSchema
{ "input": { "owner": "acme", "repo": "api", "title": "…", "labels": ["bug"] } }
```

Select the account with the `x-oo-connector-alias` header (or `alias` /
`connectionName` in the query or body); omitting it uses that provider's
`default` connection. An `idempotency-key` header makes a retry safe on a write.

The reply is the same envelope, with `meta` naming the run —
`{executionId, service, actionId, appId}` — and **`data` carrying the
provider's own payload, unnormalised**: a GitHub action answers with GitHub's
snake_case JSON (`login`, `node_id`, `html_url`), not with oomol-style names.
`outputSchema` describes that payload; commit it as the node's output so a flow
can read fields out of it.

**Prune the input to the declared properties before sending.** Read the action's
`inputSchema` live (same NATS subject, `GET /v1/actions/<id>`) and drop anything
it does not declare; `additionalProperties: false` turns one stray key into a
400 for the whole call. github-oc does exactly this.

**Call the provider proxy** for uncurated endpoints:

```jsonc
// POST /v1/proxy/github
{ "endpoint": "/repos/acme/api/dependabot/alerts",  // relative, must start with "/"
  "method": "GET",
  "query": { "state": "open" },
  "headers": { "accept": "application/vnd.github+json" },
  "body": null }
```

Absolute URLs are rejected. The success envelope nests the real response:
`data.status`, `data.headers`, `data.data` — unwrap both layers. A provider with
no proxy executor answers `proxy_not_supported`. Most proxies share the same 30s
budget as actions; a slow upstream comes back as HTTP 500 with `errorCode:
provider_error` and `data.status: 504`.

**Check scopes against the right field.** A connection from `/v1/apps` reports
its grants twice, in two different vocabularies, and only one of them is
comparable to an action's `requiredScopes`:

| Connection field | Example | Compare to `requiredScopes`? |
|------------------|---------|------------------------------|
| `scopes` | `github.issue.write`, `github.repo.read` | **yes** — same vocabulary as the action |
| `providerScopes` | `repo`, `read:user`, `user:email` | **no** — the provider's own names; comparing these denies everything |

So the check is `set(action.requiredScopes) ⊆ set(connection.scopes)`, and it is
worth doing on curated actions. Skip it when `scopes` is empty — an api-key
connection often reports none, and that is not a failure — and skip it for
every **proxy** call, where oomol has no declared scope and the provider's own
403 is the only real answer. Surface that 403 on the node rather than guessing.

**Resolve `{{$.path}}` tokens** in string inputs against the flow scope, so a
`chatId` or `issueKey` can come from an upstream node.

## Step 5 — the connection lives on the settings profile

No action form may contain a credential, a base URL, an account, or a value that
belongs to the connection. Those arrive as `body.settings`.

The `-oc` settings profile holds, typically:

- **Account** — a picker filled by a meta RPC off `/v1/apps`, with **Load
  accounts** and **Test account** buttons. Leave blank to mean `default`.
- **Gateway** (optional) — pins to one Connect connection when several are
  configured (hosted oomol vs self-hosted); empty spans all.
- **Per-connection constants.** This is the `-oc`-specific trap. An OpenConnector
  connection is often granted to exactly one tenant — one GitHub org, one Jira
  site, one Slack workspace — and a connection scoped that way frequently
  *cannot enumerate* its own tenants (GitHub returns nothing from `/user/orgs`).
  Such a value belongs on the profile, set once, with a picker that degrades to a
  typed field — **not** on every action form. One profile per tenant when a token
  spans several. github-oc puts the org here and no action form has an Owner
  input.

## Step 6 — forms, from the schema but not of it

Generate each action form from the oomol `inputSchema` — then edit it. A raw
provider schema is a bad form: it has no titles, no field order, exposes paging
internals, and offers fields a canvas user has no way to fill.

- Keep the property **names** exactly as oomol declares them, so no translation
  layer is needed at call time.
- Add `title` and `description` per field; mark `required` to match the schema.
- Any field a user cannot type from memory (an id valid only inside another
  selection) gets a meta RPC behind a button. A form action cannot inject a
  runtime `enum`, so model a picker as free text plus a **Find** button, or as an
  array field filled from a lookup. See
  [`dependent-fields.md`](https://github.com/Inflowenger/plugin-catalog/blob/main/docs/dependent-fields.md).
- Drop what the plugin should decide itself (`page` on an action that pages
  internally).

## Step 7 — the meta RPCs every `-oc` plugin wants

| Method | Purpose |
|--------|---------|
| `<svc>.meta.account.list` | fill the account drop-down from `/v1/apps` |
| `<svc>.meta.account.test` | the settings dialog's connection test — run the cheapest `read` action (`get_current_user` and friends) |
| `<svc>.meta.<identity>` | who the connection acts as, and its granted scopes — the fastest answer to "why 403?" |
| `<svc>.meta.<thing>.list` | the dependent pickers (repos, projects, channels, boards) |

Meta requests arrive **flat** (fields plus `settings` at the top level), not in
the action envelope; decode tolerantly and return a **patch object**, not the
SDK's response envelope. Register them all before `Start()`.

## Step 8 — list it in the catalog

An `-oc` plugin is not portable, and the catalog records that:

- Name the repo and the entry with the **`-oc` suffix**; node name reads
  `<Service> (OpenConnector)`.
- **Runs on** is `FloMorphic only ★`, because it needs the
  `flomorphic.svc.oc.*` subjects.
- `plugins/index.json` gets a `hostDependency`:
  `{"platform": "flomorphic", "service": "Connect / OpenConnector proxy",
  "subjects": ["flomorphic.svc.oc.*"]}`.
- The entry's **Connection** section says plainly that the plugin stores no
  provider credential and there is nothing to paste.

Follow [`templates/plugin-entry.md`](https://github.com/Inflowenger/plugin-catalog/blob/main/templates/plugin-entry.md)
and [`publishing.md`](https://github.com/Inflowenger/plugin-catalog/blob/main/docs/publishing.md).

## When it fails

| Symptom | Cause |
|---------|-------|
| `401` · body `token not found` | no `authorization` header at all — discovery needs the token too |
| `401` · body `invalid token` | the header carried a token this deployment does not know. On hosted oomol this is also what a non-`api-` token reads as |
| `401` · `CREDENTIALS_INVALID` / `Failed to verify api key` | hosted oomol recognised an `api-…` key and its account service rejected it: wrong, revoked, or from another account |
| `401` on a self-hosted runtime with a token you know is right | the header has no `Bearer ` scheme, so the server read no token. Send `authorization: Bearer <token>` |
| `404 unknown_action` | the action id does not exist — you guessed it; re-list the service |
| `400 invalid_input` | a property oomol does not declare, snake_case where it wants camelCase, or a missing `required` field. Re-read `inputSchema` and prune |
| `403 connection_not_allowed` | the token's `allowedConnections` does not grant the selected (or default) connection |
| `proxy_not_supported` | that provider has no proxy executor — use curated actions only |
| proxy denied although the path is right | the token's `allowedProxies` is empty (the default) or policy blocks the service |
| provider `403` with a scope message | the connected account lacks a provider permission. Fix it in Connect, not in code |
| `errorCode: provider_error`, `data.status: 504` | upstream exceeded the 30s budget; use the provider's async endpoints |
| NATS no-responders / timeout on **every** action | `INFRA_CRED` is a strict plugin-scoped credential. `-oc` plugins publish on `flomorphic.>` and need an **OPEN (multi)** runtime credential |
| bare `TIMEOUT` on the node | the NATS→backend→oomol→provider chain exceeded the plugin's deadline. Set `REQ_TIMEOUT` (seconds) in `.env.inflow`; `-oc` plugins set ~30s in code, above the SDK's 5s default |

## Verify before finishing

- [ ] Every oomol action id used appears in a `GET /v1/actions?service=<svc>`
      response you actually fetched in this session — none from memory.
- [ ] Every input property name is copied from that action's `inputSchema`, and
      input is pruned to the declared properties before the call.
- [ ] Curated action bodies are `{"input": {…}}`; proxy bodies are
      `{endpoint, method, query, headers, body}` with a relative `endpoint`.
- [ ] No `destructive` action without an explicit opt-in, and — where the
      deployment reports `execution` at all — no `catalogOnly` action exposed.
- [ ] Both response envelopes are unwrapped — `data` for actions, `data.data`
      for proxy calls — and `errorCode` is surfaced in the node's error message.
- [ ] No OpenConnector token and no provider credential anywhere in the source,
      a committed example, a test fixture, or a log line.
- [ ] No account, gateway, base URL or other connection value on an action
      form — the platform supplies them as `body.settings`.
- [ ] Account / gateway / per-connection constants are on the settings profile,
      and no action form duplicates them.
- [ ] `meta.account.list` and `meta.account.test` exist and are registered
      before `Start()`.
- [ ] The action-mapping table (oomol id → canvas method) is written down.
- [ ] Catalog entry carries the `-oc` suffix, `FloMorphic only ★`, and
      `hostDependency`.
- [ ] And every rule from the SDK skill: one terminal `Done`/`DoneWithError` per
      path, `main` blocks after `Start()`, forms match the input structs.

## Worked examples

Read one before starting; they are the same shape in three languages.

| Plugin | SDK | Why look |
|--------|-----|----------|
| [github-oc](https://github.com/FloMorphic/github-oc) | Python | curated + proxy together, live schema pruning, per-connection org on the profile |
| [google-office-oc-plugin](https://github.com/FloMorphic/google-office-oc-plugin) | Go | 30 actions, four products in one plugin, `Tags["class"]` grouping, dependent pickers |
| [gmail-oc-plugin](https://github.com/FloMorphic/gmail-oc-plugin) | Node | the smallest complete example, with a live scope check |
| [telegram-oc-plugin](https://github.com/mehdi-shokohi/telegram-oc-plugin) | Go | api-key connection that reports no scopes |

Catalog entries: [`plugins/`](https://github.com/Inflowenger/plugin-catalog/tree/main/plugins).
Upstream API reference:
[`runtime-api.md`](https://github.com/oomol-lab/open-connector/blob/main/docs/runtime-api.md),
[`credentials.md`](https://github.com/oomol-lab/open-connector/blob/main/docs/credentials.md),
[`catalog-format.md`](https://github.com/oomol-lab/open-connector/blob/main/docs/catalog-format.md).
A provider's definitions are the source of truth for its schemas:
`src/providers/<service>/{definition,actions,executors}.ts`.
