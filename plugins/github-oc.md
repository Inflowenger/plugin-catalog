# GitHub (OpenConnector)

> Read GitHub — repositories, activity, search — and its security surface
> (Dependabot / secret-scanning / code-scanning alerts, branch protection, org
> members, repo settings) from the Inflowenger canvas, as a GitHub account
> connected centrally in FloMorphic → Connect.

| | |
|---|---|
| **Repository** | https://github.com/FloMorphic/github-oc |
| **Node name** | `GitHub (OpenConnector)` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Python — [`inflowenger-plugin-sdk`](https://pypi.org/project/inflowenger-plugin-sdk/) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `devops` |
| **Runs on** | **FloMorphic only ★** — needs FloMorphic's Connect / OpenConnector proxy (`flomorphic.svc.oc.*`); not portable to a bare `inflowv1` host. |
| **License** | See repository |
| **Status** | Beta |

## What it does

Puts GitHub on the canvas as thirteen **read-only** actions — the security
collector planned in the
[security collectors plan](../docs/security-collectors-plan.md) — without ever
holding a GitHub token or calling GitHub directly. It is a *request builder*: a
GitHub account is connected **once, centrally**, in **FloMorphic → Connect** (via
OpenConnector / oomol), and this node picks which connected account to act as and
asks the FloMorphic backend to run each request for it. It is the catalog's first
`-oc` plugin on the **Python SDK**, and the first to use oomol's **provider
proxy** next to its curated actions.

The backend is a generic proxy: it stores the OpenConnector token and forwards
requests over one NATS subject (`flomorphic.svc.oc.proxy`), injecting the auth
header. All GitHub knowledge lives in the plugin, which reaches the gateway two
ways:

- **Curated OpenConnector actions** (`POST /v1/actions/github.<action>`) for the
  surface oomol curates — used only where the input schema was confirmed against
  the live catalog (`list_my_repositories`, `get_repository`, `list_commits`,
  `get_current_user`), since oomol declares inputs with `additionalProperties:
  false` and camelCase names. The plugin reads each action's definition live and
  prunes its input to the declared properties.
- **oomol's provider proxy** (`POST /v1/proxy/github {endpoint, method, query,
  body}`) — a signed passthrough to `api.github.com` — for everything oomol does
  not curate: the alert feeds, branch protection & rulesets, org members and 2FA,
  deploy keys / webhooks / Actions settings, collaborators, workflow runs, search,
  and a **Raw GitHub request** escape hatch.

String inputs accept `{{$.path}}` tokens resolved against the flow scope.

## Actions

| Method | Title | Backed by |
|--------|-------|-----------|
| `github.repos.list` | List repositories | curated (own) · proxy (org) |
| `github.repo.get` | Get repository | curated |
| `github.repo.collaborators` | List collaborators | proxy |
| `github.repo.contents` | Get contents | proxy |
| `github.activity.list` | List activity (commits / workflow runs) | curated · proxy |
| `github.search` | Search GitHub | proxy |
| `github.repo.protection` | Branch protection & rulesets | proxy |
| `github.alerts.dependabot` | Dependabot alerts | proxy |
| `github.alerts.secret_scanning` | Secret-scanning alerts | proxy |
| `github.alerts.code_scanning` | Code-scanning alerts | proxy |
| `github.org.members` | Org members / 2FA / outside collaborators | proxy |
| `github.repo.settings` | Deploy keys, webhooks, Actions permissions & secret names | proxy |
| `github.request` | Raw GitHub request | proxy |

Meta RPCs power the settings dialog, the repo pickers and the in-app manual's
live **Run** buttons: `github.meta.account.list`, `github.meta.account.test`,
`github.meta.user.info`, `github.meta.org.list`, `github.meta.repo.list`.

## Connection

The plugin stores **no** GitHub credentials — there is no token, alias, or config
to paste. The settings profile holds two things:

- **GitHub account** — press **Load accounts** to populate the drop-down live from
  Connect and **pick** the connected account (or leave the default).
- **Organization / owner** — the org every action of this profile targets.
  **No action form has an Owner or Organization input.** An OpenConnector GitHub
  connection is granted to an account and, typically, to *one* organization, so
  the org belongs to the connection, not to a single action: it is set once here
  and every action reads it. Press **Load orgs** if the token can enumerate its
  orgs; a connection granted to one specific org in oomol cannot (GitHub returns
  none), so you type the org it was granted to. A token that spans several orgs
  gets one profile per org.

**Test account** and **Check identity** (login + granted scopes) validate the
profile before **Save**; the platform then supplies it on every call as
`body.settings`. The optional **Gateway** field pins to one Connect connection
when several are configured; leave it empty to span all.

## Install

```bash
git clone https://github.com/FloMorphic/github-oc
cd github-oc
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED (OPEN cred) / INFRA_URL
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).
`pytest -q` runs the unit suite against an in-process fake gateway (no NATS).

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **Central auth, no GitHub token in the plugin.** The `-oc` suffix marks this as
  the OpenConnector-backed GitHub node; a future direct-PAT `github` plugin for
  bare `inflowv1` hosts could coexist.
- **Runtime credential.** Because the plugin publishes on `flomorphic.svc.oc.*`,
  `INFRA_CRED` must be an **OPEN (multi)** runtime credential; a strict,
  plugin-scoped credential cannot publish on `flomorphic.>` and every action
  fails with a NATS no-responders/timeout.
- **Provider proxy — confirmed.** FloMorphic's `flomorphic.svc.oc.proxy` forwards
  `/v1/proxy/github` as it does `/v1/actions/*` (the feasibility note's open
  question); the security actions need no backend change.
- **Token scopes.** The alert feeds need `security_events`, org members / the 2FA
  filter `read:org`, private repos and branch protection `repo`, webhooks
  `admin:repo_hook` — or the fine-grained-PAT equivalents. The plugin does not
  pre-check these (a connection's reported scopes use oomol's own vocabulary,
  `github.repo.read`); GitHub's 403 message surfaces on the node instead.
- **Rate limits & volume.** Org-wide alert listing uses the one-call-per-org
  `/orgs/{org}/…/alerts` endpoints; every list action exposes state / severity
  filters and paging. Large orgs still return many rows.
- **GitHub Enterprise Server.** oomol's proxy base URL is `api.github.com`; GHES
  needs a per-connection base URL on the OpenConnector side.
- **Request timeout.** 30s in code (NATS hop → backend → oomol → GitHub);
  override per deployment with `REQ_TIMEOUT` (seconds) in `.env.inflow`.
