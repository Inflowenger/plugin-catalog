# osctrl — feasibility & requirements assessment

> Investigation of what an **`OSCTRL`** plugin needs, and whether Venapce should
> ship its own repackaged, all-in-one osctrl. Scope: dependencies and runtime
> requirements of the osquery → osctrl "vein" that feeds Venapce collectors.
>
> Status: **assessment** — the plugin it describes has since shipped and is listed
> in [the catalog](../README.md#the-catalog). Not a build spec.

---

## TL;DR

- **The plugin is a quick win.** It needs exactly **four API calls** against
  `osctrl-api`, all already exposed: run a distributed query, read its results,
  list nodes, list environments. No forking required to ship the plugin.
- **The hard part is not the plugin — it is giving a Venapce user a running
  osctrl.** osctrl's own deployment is a multi-container stack (TLS ingest +
  API + web + PostgreSQL + Redis). That is the friction the user is reacting to.
- **Decouple the two.** (A) the plugin ships now against any osctrl. (B) an
  "easy osctrl" — a repackaged all-in-one image and a thin front over the
  existing API — is a **separate product effort** that the plugin does not
  depend on.
- **One thing cannot be collapsed away:** `osctrl-tls` must stay, and it must be
  publicly reachable over TLS by every osquery agent. That requirement is
  intrinsic to osquery's remote (TLS) mode — it is the vein itself, not
  packaging overhead.

---

## 1. The vein: osquery and osctrl

**osquery** (Meta, Apache-2.0) exposes an operating system as a relational
database. It installs as a host agent on Linux/macOS/Windows and answers SQL
against ~250 virtual tables (`processes`, `listening_ports`, `users`,
`kernel_info`, `rpm_packages`, …). Two modes matter here:

- **Scheduled** — the agent runs a query pack on a timer and ships results out.
- **Distributed** — a control server hands the agent an ad-hoc query and
  collects the answer. This is the "run a query now, get the result" path a
  Venapce collector wants.

osquery in remote mode does **not** connect to a database directly; it speaks its
own **TLS remote API** to a control server. That server is **osctrl**.

**osctrl** (`jmpsec/osctrl`, **MIT**, Go + React) is that control server: it
terminates the osquery TLS remote API, enrolls agents, groups them into
**environments** (osctrl's tenant boundary), pushes distributed queries, and
stores results. For Venapce, osctrl is the **hive** — one endpoint that fans a
single SQL query out to N enrolled hosts and returns rows. The plugin is a thin
client of osctrl's REST API; it never talks to osquery directly.

```
osquery agent  ──TLS remote API──▶  osctrl-tls  ──▶  Postgres/Redis
   (per host)                          │
                                    osctrl-api  ◀──REST──  OSCTRL plugin ◀── Venapce workflow
```

---

## 2. osctrl as it ships today

Current `main` (Go 1.26, Node 22, osquery 5.23 schema) is three Go services plus
a React SPA, backed by two datastores:

| Component | Role | Must the plugin reach it? |
|-----------|------|---------------------------|
| **osctrl-tls** | Terminates the osquery TLS remote API; enrollment, config, log/result ingest. Must be reachable by every agent. | No (agents do) |
| **osctrl-api** | REST API for operators — queries, nodes, environments. Token auth. | **Yes — the only surface the plugin uses** |
| **osctrl-cli** | Admin/automation CLI; can also mint API tokens. | No (used once, to get a token) |
| **Frontend** | React/TS SPA (Vite, Tailwind, Monaco) served over TLS (dev: `https://localhost:8444`), talks to `osctrl-api`. | No |
| **PostgreSQL** | Primary store (GORM). MySQL/SQLite also supported. | No (osctrl does) |
| **Redis** | Cache + activity/session tracking. | No |

Optional integrations compiled in but off by default: JWT/SAML/OIDC + WebAuthn
auth, Kafka / Elasticsearch v8 log shippers, AWS SDK, MaxMind GeoIP enrichment.
None are required for the plugin path.

> The "~5 containers" recollection matches older/full topologies where a
> reverse proxy (nginx, for TLS termination) and a separate `osctrl-admin` web
> service were their own containers. Current `main` folds admin into the SPA +
> `osctrl-api`, so the realistic minimum is **tls + api + postgres + redis**
> (+ the SPA if you want the stock UI).

**Sources:** [jmpsec/osctrl](https://github.com/jmpsec/osctrl) ·
[osctrl-api.yaml](https://github.com/jmpsec/osctrl/blob/main/osctrl-api.yaml) ·
[osctrl.net](https://osctrl.net/).

---

## 3. What the plugin actually needs

The requested actions map one-to-one onto existing `osctrl-api` endpoints. Base
path `/{...}/api/v1`, auth is a **token in the request header** (osctrl issues a
JWT; header carries `ApiKeyAuth`, i.e. `Authorization: Bearer <token>` — confirm
exact header against the running build). Every query/node route is scoped by
`{env}`.

| Plugin action | Method & path | Notes |
|---------------|---------------|-------|
| **List environments** (tenants) | `GET /api/v1/environments` | Backs an env picker; returns the tenant list |
| **List instances** (nodes) | `GET /api/v1/nodes/{env}` | Paged (`page`, `page_size`, `q`); also `/all`, `/active`, `/inactive` |
| **Run query** | `POST /api/v1/queries/{env}` | Body: `{ query, environment_list[], platform_list[], uuid_list[], host_list[] }`. Returns the created query's name/id |
| **Get result** | `GET /api/v1/queries/{env}/{name}` | Result detail; CSV at `/queries/{env}/results/csv/{name}` |

Two structural facts that shape the plugin:

1. **Distributed queries are asynchronous.** `POST …/queries` *dispatches*; each
   agent answers on its own next check-in. So "run query" returns a handle and
   "get result" is **polled** until the target nodes have reported. The plugin
   should model this as run → (poll) → collect, not a single blocking call. This
   fits the SDK's long-lived job + `Progress` model cleanly.
2. **Targeting is by env / platform / UUID / hostname**, not free-form. The run
   form should surface those as fields, ideally with the node list feeding a
   picker (a dependent field — see [dependent-fields.md](dependent-fields.md)).

Mapped to the catalog's shape this is a **~4-action, Go-SDK, token-auth REST
plugin** — the same family as [Jira](../plugins/jira.md), and simpler than it.
The settings profile holds `{ base URL, API token, optional default env }`; no
osquery/osctrl credentials live in `.env.inflow`.

---

## 4. The real question: how does a user get an osctrl?

The plugin assumes "an installed osctrl and connected osquery hosts." That
assumption is the entire cost. Two independent tracks:

### Track A — the plugin (ship now)

Nothing here is blocked. The plugin talks to `osctrl-api`; whether that osctrl is
the stock stack, a managed instance, or a Venapce-repackaged image is invisible
to the plugin. **Recommendation: build and list the plugin against stock
osctrl.** It is feasible today and confirms the vein end-to-end.

### Track B — "easy osctrl" (the repackaging idea)

The proposal — one all-in-one image + a thin front written against the existing
osctrl API — is **sound and low-risk in principle** (MIT license permits it; the
API is small and stable), with important caveats:

**What *can* collapse into one image**

- `osctrl-tls` + `osctrl-api` + `osctrl-cli` are all one Go codebase — a single
  multi-process image (or supervisor) is straightforward.
- Postgres + Redis can be embedded in the same compose/image for a
  single-tenant, single-host deployment. (SQLite is supported and removes
  Postgres for the smallest footprint — validate it against the features you
  use.)
- A custom front is genuinely optional: the plugin does not need it, and the
  existing API is small enough that a thin replacement UI is a modest project.
  **But note that "own front over existing API" delivers no value to the plugin
  path** — spend that effort only if humans need to operate the instance.

**What *cannot* be simplified away**

- **`osctrl-tls` must remain and must be publicly reachable over TLS** by every
  osquery agent, with a certificate the agents trust. This is osquery's remote
  mode, not osctrl overhead. An all-in-one image still needs an ingress, a
  hostname, and a cert (Let's Encrypt / provided). This is the single biggest
  requirement to design around.
- **Enrollment is still per-host.** Each osquery agent needs a config pointing at
  your `osctrl-tls` URL + an enroll secret. Packaging osctrl does not package the
  fleet; agent rollout stays the user's job (though osctrl can generate the
  enroll packages).
- **Forking = maintenance.** A Venapce fork/front pins to osctrl's API shape and
  inherits its upgrade treadmill (osquery schema bumps, security fixes). Prefer
  *repackaging* (own Dockerfile/compose over upstream binaries) over *forking the
  source*, so you inherit upstream fixes for free.

---

## 5. Requirements & dependency matrix

| Requirement | Needed by | Notes |
|-------------|-----------|-------|
| osctrl-api reachable + API token | **Plugin** | The only hard dependency of the plugin |
| osctrl-tls, publicly reachable over TLS + cert | osctrl / agents | Intrinsic to osquery remote mode; cannot be removed |
| PostgreSQL (or MySQL/SQLite) | osctrl | SQLite is the lightest for an all-in-one; Postgres for real fleets |
| Redis | osctrl | Cache/activity; embed in the all-in-one |
| osquery installed + enrolled per host | The fleet | Per-host config + enroll secret; osctrl generates packages |
| Go 1.26 / Node 22 toolchain | Only to build osctrl / an all-in-one image | Not a runtime dep for the plugin |
| Inflowenger Go SDK, token-auth REST | **Plugin build** | Same class as the Jira plugin |

---

## 6. Risks & open questions

- **Async result collection.** Confirm the exact poll/complete semantics of
  `GET …/queries/{env}/{name}` (per-node status, when a query is "done", how
  partial results appear) before finalizing the run→poll→collect handler.
- **Auth header specifics.** Confirm header name and token lifetime (JWT default
  ~3h expiry was observed) — a short-lived token forces a refresh story; a
  long-lived API token in the settings profile is preferable for a plugin.
- **Result size / pagination.** Fleet-wide queries can return large result sets.
  Decide a cap (cf. ClickHouse's 100-row server-side cap) and whether to expose
  paging or CSV.
- **SQLite fitness.** Verify the all-in-one on SQLite covers the features Venapce
  needs; drop back to embedded Postgres if not.
- **Ingress in the all-in-one.** The one genuinely fiddly piece is TLS ingress
  for `osctrl-tls`; design the image's cert/hostname story explicitly.

---

## 7. Recommendation

1. **Ship the `OSCTRL` plugin now** (Track A) against stock osctrl — four
   actions, Go SDK, token auth. Model run/result as an async job. This is the
   catalog deliverable and it is a quick win.
2. **Treat "easy osctrl" as a separate product track** (Track B). Prefer a
   **repackaged all-in-one image over upstream binaries** (tls+api+cli, embedded
   store + Redis, SQLite option) to *forking source*. Build a custom front only
   if operators need a UI — the plugin does not.
3. **Keep the two decoupled** so the plugin is never blocked on the packaging
   work, and so a Venapce instance and a stock instance are interchangeable to
   the plugin.

---

*Sources: [jmpsec/osctrl](https://github.com/jmpsec/osctrl),
[osctrl-api.yaml](https://github.com/jmpsec/osctrl/blob/main/osctrl-api.yaml),
[osctrl.net](https://osctrl.net/), osquery remote/TLS mode.*
