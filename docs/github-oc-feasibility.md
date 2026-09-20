# GitHub (OpenConnector) — feasibility & requirements

> What a **`GitHub (OpenConnector)`** plugin needs: the oomol connector's
> action surface, where the security-relevant endpoints are, and the canvas
> actions to build. Scope: source-code managers via FloMorphic → Connect, as a
> **collector** for the [security collectors plan](security-collectors-plan.md).
>
> Status: **built** — listed as [GitHub (OpenConnector)](../plugins/github-oc.md)
> (beta). Same shape as [Gmail (OpenConnector)](../plugins/gmail-oc.md) and
> [Telegram (OpenConnector)](../plugins/telegram-oc.md), on the Python SDK.
> The study below is kept as written; **§ 0** records what building it found.

---

## 0. Outcome (what the build settled)

| Question in this note | Answer |
|-----------------------|--------|
| Does `flomorphic.svc.oc.proxy` forward `/v1/proxy/github`? | **Yes.** Proxied GitHub calls return through the same NATS subject as `/v1/actions/*`; no backend change was needed, so the security actions shipped in the first cut. |
| Curated where possible, proxy for the rest? | **Mostly proxy.** oomol declares every curated input with `additionalProperties: false` and **camelCase** names (`perPage`, `issueNumber`), so an unconfirmed field name is a hard 400. Only actions whose `inputSchema` was checked against the live catalog are called curated (`list_my_repositories`, `get_repository`, `list_commits`, `get_current_user`), and the plugin prunes input to the live schema at runtime. Collaborators, workflow runs, search and org repos go through exact REST paths. |
| Where does the organization live? | **On the settings profile, not on actions.** An OpenConnector GitHub connection is granted to an account and typically to one org; a token scoped that way cannot even enumerate orgs (`/user/orgs` is empty). So the org is set once per profile — picker if the token can list, typed otherwise — and **no action form has an Owner / Organization input**. One profile per org when a token spans several. |
| Scope check as in gmail-oc? | **Curated only, same-vocabulary only.** `requiredScopes` are oomol's (`github.repo.read`), while a connection may report GitHub OAuth scopes (`repo`); comparing across vocabularies would deny everything. The proxy actions are not pre-checked — GitHub's own 403 surfaces on the node. |
| oomol reply shape | `{success, message, data}` on the REST API (and `{status, headers, data}` on the proxy) — the client unwraps both. |
| SDK | **Python** (`inflowenger-plugin-sdk`), not Go — the first `-oc` plugin on it. |
| Actions built | The 13 proposed in § 3, read-only, plus `github.meta.{account.list,account.test,user.info,org.list,repo.list}`. `github.request` expands `{org}` to the profile org. |

---

## TL;DR

- **Shape is settled.** An `-oc` request builder: no GitHub token in the plugin,
  the account is connected once in FloMorphic → Connect, the settings form
  offers **Load accounts** / **Test account**, and every action is proxied over
  `flomorphic.svc.oc.proxy`. Node/Go SDK, `hostDependency` on FloMorphic.
- **oomol's GitHub connector is large but not security-shaped.** It curates
  ~147 actions (81 `read`, 36 `write`, 30 `destructive`) across repos,
  branches, commits, contents, issues, PRs, checks, workflows, releases, events,
  search and collaborators. It has **no** action for Dependabot, secret-scanning
  or code-scanning alerts, branch protection / rulesets, org members, or 2FA.
- **The security endpoints are still reachable through Connect** via oomol's
  **provider proxy** — `POST /v1/proxy/github` with `{endpoint, method, query,
  body}` — which signs any GitHub REST path with the connected credential. The
  plugin uses curated actions where they exist and the proxy for the rest.
- **One open question decides the build:** does FloMorphic's
  `flomorphic.svc.oc.proxy` forward `/v1/proxy/:service` as well as
  `/v1/actions/:id`, and does the runtime token carry an `allowedProxies` grant
  for `github`? *(Resolved — yes, see § 0.)*

---

## 1. What oomol provides

Source: [`oomol-lab/open-connector`](https://github.com/oomol-lab/open-connector),
`src/providers/github/` (`definition.ts`, `actions.ts`, `executors.ts`).

| Surface | What it is | Plugin use |
|---------|------------|------------|
| **Auth** | `oauth2` (own GitHub OAuth app; scopes `read:user`, `user:email`, `repo`, `workflow`, `delete_repo` selectable) or `api_key` (PAT, fine-grained recommended). Several named connections per provider (`default`, `work`, …) | Account picker in the settings form; alias passed per call |
| **Curated actions** | `GET /v1/actions?service=github`, `POST /v1/actions/github.<name>`. Each declares `operationType` (`read`/`write`/`destructive`), `requiredScopes`, JSON input/output schemas | Read live at startup — the action's schema seeds the form, `requiredScopes` drives the scope check, as gmail-oc does |
| **Provider proxy** | `POST /v1/proxy/github` → `https://api.github.com/<endpoint>` with bearer auth, `accept: application/vnd.github+json`, `x-github-api-version` set by oomol | Everything the curated list lacks |
| **Policy** | `OOMOL_CONNECT_ALLOWED_ACTIONS` / `BLOCKED_ACTIONS` (e.g. `github.*` minus `github.delete_repository`), and independent `ALLOWED_PROXIES` / `BLOCKED_PROXIES`; persistent tokens carry `allowedProxies` (empty by default) | Operators can pin the plugin to read-only actions and grant only the `github` proxy |

Curated actions grouped (names are oomol's, prefix `github.`):

| Group | Read | Write / destructive |
|-------|------|---------------------|
| User / org | `get_current_user`, `get_user`, `list_my_repositories`, `list_organization_repositories`, `list_user_repositories`, `search_users` | — |
| Repository | `get_repository`, `list_branches`, `get_branch`, `list_repository_tags`, `list_repository_languages`, `list_repository_contributors`, `list_repository_topics`, `get_repository_readme`, `list_repository_forks`, `list_repository_watchers`, `list_repository_stargazers`, `search_repositories` | `create_repository`, `update_repository`, `delete_repository`, `fork_repository`, `replace_repository_topics`, star/unstar |
| Collaborators | `list_repository_collaborators`, `get_repository_permission_for_user` | `add_repository_collaborator`, `remove_repository_collaborator` |
| Contents / refs / commits | `list_directory_contents`, `get_file_contents`, `list_commits`, `get_commit`, `compare_commits`, `get_ref`, `list_matching_refs`, `search_code`, `search_commits`, commit comments/statuses | `create_or_update_file`, `delete_file`, `create_ref`, `update_ref`, `delete_ref`, `merge_branch`, `rename_branch`, `sync_fork_branch_with_upstream`, `create_commit_status` |
| Issues / labels / milestones | list/get issues, comments, labels, milestones, events, timeline, `search_issues_and_pull_requests` | create/update/lock issues, comments, labels, milestones, assignees, reactions |
| Pull requests | list/get PRs, files, commits, reviewers, reviews, review comments, `check_pull_request_merged` | create/update/merge PRs, request/remove reviewers, create/submit/dismiss reviews, review comments |
| Checks / Actions | `list_check_runs_for_ref`, `get_commit_statuses`, `list_repository_workflows`, `get_workflow`, `list_workflow_runs`, `get_workflow_run`, `list_workflow_run_jobs`, `get_workflow_job_logs`, `list_workflow_run_artifacts`, `download_workflow_artifact` | `dispatch_workflow`, `rerun_workflow`, `rerun_failed_jobs`, `cancel_workflow_run`, enable/disable workflow, re-request check run/suite |
| Releases | `list_releases`, `get_release`, `get_latest_release`, `get_release_by_tag`, `list_release_assets`, `get_release_asset` | create/update/delete release, `generate_release_notes`, delete asset |
| Events | repository / public / user / authenticated-user event feeds | — |

---

## 2. What the security workflow needs, and where it comes from

| Need | Frame kind | Source through Connect |
|------|------------|------------------------|
| Repo inventory (visibility, default branch, archived, languages, topics) | inventory | curated `list_organization_repositories`, `get_repository` |
| Who can push (collaborators, permission level) | inventory | curated `list_repository_collaborators`, `get_repository_permission_for_user` |
| **Branch protection / rulesets** on the default branch | inventory | **proxy** `GET /repos/{o}/{r}/branches/{b}/protection`, `GET /repos/{o}/{r}/rules/branches/{b}` |
| **Dependabot alerts** (vulnerable dependencies) | findings | **proxy** `GET /repos/{o}/{r}/dependabot/alerts`, org-wide `GET /orgs/{org}/dependabot/alerts` |
| **Secret-scanning alerts** (leaked credentials) | findings | **proxy** `GET /repos/{o}/{r}/secret-scanning/alerts`, `GET /orgs/{org}/secret-scanning/alerts` |
| **Code-scanning alerts** (SAST) | findings | **proxy** `GET /repos/{o}/{r}/code-scanning/alerts`, `GET /orgs/{org}/code-scanning/alerts` |
| **Org members without 2FA**, outside collaborators, owners | inventory | **proxy** `GET /orgs/{org}/members?filter=2fa_disabled`, `?role=admin`, `GET /orgs/{org}/outside_collaborators` |
| Deploy keys, webhooks, Actions secret *names*, workflow permissions | inventory | **proxy** `GET /repos/{o}/{r}/keys`, `/hooks`, `/actions/secrets`, `/actions/permissions` |
| Recent activity (pushes, releases, workflow runs) | events | curated event feeds, `list_workflow_runs`, `list_commits` |
| Security policy / SECURITY.md, CODEOWNERS present | inventory | curated `get_file_contents` |
| Org audit log (Enterprise) | events | **proxy** `GET /orgs/{org}/audit-log` |

Required token scopes for the proxy paths: `security_events` (alerts),
`read:org` (members, 2FA filter), `repo` (private repos, protection), `admin:repo_hook`
(webhooks), `admin:org` (audit log). Fine-grained PAT equivalents:
*Dependabot alerts: read*, *Secret scanning alerts: read*, *Code scanning alerts:
read*, *Administration: read*, *Members: read*. The plugin should check the
connected account's scopes before running, as gmail-oc does, and fail with a
clear message when a proxy path needs a scope the account lacks.

---

## 3. Proposed canvas actions

Read-only first (see [plan § 13](security-collectors-plan.md#13-decisions-needed-before-wave-1)).
Every list action takes `owner`/`org`, optional `repo`, `page`/`per_page`, and
accepts `{{$.path}}` tokens; org-wide actions fan out per repo with a
`Progress` frame each and a server-side cap.

| Method | Title | Backed by |
|--------|-------|-----------|
| `github.repos.list` | List repositories (org or user) | curated |
| `github.repo.get` | Get repository | curated |
| `github.repo.collaborators` | List collaborators & permissions | curated |
| `github.repo.protection` | Get branch protection & rulesets | proxy |
| `github.alerts.dependabot` | List Dependabot alerts (repo or org) | proxy |
| `github.alerts.secret_scanning` | List secret-scanning alerts (repo or org) | proxy |
| `github.alerts.code_scanning` | List code-scanning alerts (repo or org) | proxy |
| `github.org.members` | List org members (filter: 2FA disabled / admins / outside collaborators) | proxy |
| `github.repo.settings` | Deploy keys, webhooks, Actions secret names & permissions | proxy |
| `github.repo.contents` | Get file / directory contents (CODEOWNERS, SECURITY.md, workflows) | curated |
| `github.activity.list` | Commits / workflow runs / events for a window | curated |
| `github.search` | Search code / issues / repos | curated |
| `github.request` | Raw GitHub REST request through the proxy — escape hatch, gated by a profile flag | proxy |

Writes (`github.issue.create`, `github.pr.comment`) only if a workflow needs to
file findings back; they are curated actions and cheap to add later.

Meta RPCs, mirroring telegram-oc: `github.meta.account.list`,
`github.meta.account.test`, `github.meta.org.list`, `github.meta.repo.list`
(the last two feed dependent pickers — see
[dependent-fields.md](dependent-fields.md)).

---

## 4. Requirements & dependencies

| Requirement | Needed by | Notes |
|-------------|-----------|-------|
| GitHub account connected in FloMorphic → Connect | User | OAuth app **or** a fine-grained PAT; PAT is simpler for org security reads |
| `flomorphic.svc.oc.proxy` forwards `/v1/actions/*` | Plugin | Already true — gmail-oc and telegram-oc rely on it |
| `flomorphic.svc.oc.proxy` forwards `/v1/proxy/github` **and** the runtime token grants `allowedProxies: ["github"]` | Plugin (security actions) | **Confirmed** (§ 0) |
| Node, Go or Python SDK | Build | Built on the **Python SDK** (first `-oc` plugin on it) |
| GitHub token scopes | User | `security_events`, `read:org`, `repo` — checked live per action |

---

## 5. Risks & open questions

- **Proxy reachability** (above) — the single item that changes the effort.
  *(Resolved: reachable.)*
- **Curated input schemas are strict.** `additionalProperties: false` + camelCase
  — never guess a curated field name; read `GET /v1/actions?service=github`
  first, or use the proxy. *(Found while building.)*
- **Single-org grants can't list orgs.** A connection granted to one organization
  gets nothing from `/user/orgs`, so an org picker on an action form is dead
  weight — the org belongs on the settings profile. *(Found while testing.)*
- **Rate limits.** Org-wide alert listing over hundreds of repos burns the
  5,000 req/h REST budget; use the `/orgs/{org}/…/alerts` endpoints where they
  exist (one call per org) and cache repo lists per job.
- **GitHub Enterprise Server.** oomol's proxy base URL is `api.github.com`;
  GHES needs a per-connection base URL — check whether oomol's `api_key`
  connection supports it before promising GHES.
- **Alert volume.** Dependabot alerts on a large org run to tens of thousands
  of rows; enforce a cap and expose `state=open` / severity filters in the form.
- **operationType as a guard.** oomol tags every curated action `read` /
  `write` / `destructive`; the plugin should refuse to expose `destructive`
  actions unless the settings profile opts in, and operators can also block
  them with `OOMOL_CONNECT_BLOCKED_ACTIONS`.

---

## 6. Recommendation

1. Confirm proxy forwarding in the FloMorphic backend (one question, one
   afternoon if it needs adding).
2. Build the plugin read-only: 12 actions above, curated where possible, proxy
   for alerts / protection / org members. Go SDK, patterned on telegram-oc.
   *(Done — Python SDK, and more proxy than curated; see § 0.)*
3. List as `github-oc` with `hostDependency` on FloMorphic; the `-oc` suffix
   leaves room for a direct-PAT `github` plugin on bare `inflowv1` hosts later.
4. GitLab follows on the same code path — oomol has a `gitlab` connector with
   the same proxy mechanism — so the second SCM is mostly a provider swap.

---

*Sources: [oomol-lab/open-connector](https://github.com/oomol-lab/open-connector)
— `src/providers/github/{definition,actions,executors}.ts`,
`docs/runtime-api.md`, `docs/credentials.md`; GitHub REST API docs for
Dependabot, secret scanning, code scanning, branch protection, organizations.*
