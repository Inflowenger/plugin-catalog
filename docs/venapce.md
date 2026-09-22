# Venapce

> **Venapce** is a security-posture product built on Inflowenger. Its plugins
> **collect** from the systems it watches, and **FloMorphic** is both its backend
> and its dynamic layer: every Venapce feature is a workflow graph over the
> frames those plugins return, not code baked into a plugin.
>
> This page is the catalog's **roadmap** as seen from Venapce: what is already
> shaped, what the feasibility studies concluded, and which plugins are under
> study next. Dates and scope may shift. It shows where the catalog is heading
> and does not commit to any of it.

---

## TL;DR

- **Shape.** Resources → **collector plugins** → FloMorphic workflow (store →
  evaluate → recommend) → Venapce feature. A plugin only accesses a system and
  returns data frames; storage, evaluation and the LLM node live downstream in
  the graph.
- **Already shaped.** The host layer runs on **osquery → osctrl** through the
  `OSCTRL` plugin, and network devices are reached through
  **[Scrapli](../plugins/scrapli.md)**. Code, storage and response come
  from plugins already in [the catalog](../README.md#the-catalog).
- **Studies that finished.** [osctrl](osctrl-feasibility.md) → shipped.
  [GitHub (OpenConnector)](github-oc-feasibility.md) → shipped (beta). The
  network-device study's need for Python drove the **Python SDK** → Scrapli
  shipped (beta) on it.
- **Next.** The three clouds (`AWS` · `AZURE` · `GCP`, AWS first) lead wave 1
  of the [security collectors plan](security-collectors-plan.md), followed by
  `OPENSEARCH`, `LDAP`, `VULNINTEL`, `WAZUH` and `NETBOX`.

---

## How Venapce is put together

```
 hosts ── osquery ──▶ osctrl ─┐
 network devices ─────────────┤
 code (GitHub) ───────────────┤   collector plugins          FloMorphic workflow            Venapce
 identity, clouds, logs (plan)┼──▶ OSCTRL · SCRAPLI · …  ──▶  store → evaluate → LLM node ──▶ features
 …                         ───┘   (access + data frames)     (backend + dynamic layer)
```

- **Plugins collect and investigate.** Each one declares a settings form for
  access, exposes the target's API as actions, and returns frames. Every frame is
  labelled **inventory** (what exists), **findings** (what a tool judged wrong)
  or **events** (what happened). The envelope is described in the
  [security collectors plan § 11](security-collectors-plan.md#11-conventions-every-collector-follows).
- **FloMorphic is the backend.** It holds the settings profiles (a plugin keeps
  no credentials) and runs the workflows. For SaaS it also hosts the Connect /
  OpenConnector proxy that `-oc` plugins go through.
- **FloMorphic is also the dynamic layer.** A new Venapce feature is a new
  workflow over existing collectors, such as a daily exposure report, an
  "unknown host on the subnet" diff or a CVE triage with LLM recommendations.
  Most features need no new plugin and no redeploy.

---

## What is already shaped

| Layer | Plugin | Role in Venapce | Status |
|-------|--------|-----------------|--------|
| Host state & config | `OSCTRL` (osquery → osctrl) | The host **vein**: one SQL query fans out to every enrolled host and returns processes, ports, packages, users, firewall rules, sudoers, SSH keys, parsed configs. Run → poll → collect as an async job | **Shipped**, internal (Venapce) |
| Network devices | [Scrapli](../plugins/scrapli.md) | Show/exec commands and config push over SSH/Telnet, with TextFSM parsing to structured data. Covers Cisco IOS-XE/NX-OS/IOS-XR, Arista EOS and Juniper JunOS | **Beta** |
| Code & supply chain | [GitHub (OpenConnector)](../plugins/github-oc.md) | Repos, branch protection, Dependabot / secret-scanning / code-scanning alerts, org members & 2FA, deploy keys | **Beta** |
| Logs, flows, inventory by SQL | [ClickHouse](../plugins/clickhouse.md) · [Postgres](../plugins/postgres.md) | ClickHouse reads NetFlow landed by goflow2/akvorado. Postgres queries Steampipe for cloud inventory until the native cloud plugins ship | Shipped |
| Storage & retrieval | [MongoDB](../plugins/mongodb.md) · [Qdrant](../plugins/qdrant.md) | Candidates for the doc store the frames land in, and for the vector search that feeds the LLM node | Shipped |
| Response & reporting | [Jira](../plugins/jira.md) · [Telegram (OpenConnector)](../plugins/telegram-oc.md) · [Gmail (OpenConnector)](../plugins/gmail-oc.md) · [Google Workspace (OpenConnector)](../plugins/google-oc.md) | Where findings and recommendations go: a ticket, a chat alert, an email, or a report in Sheets/Docs. Workspace is not yet an identity source; admin users and 2SV are a planned extension | Shipped · Workspace beta |

---

## Feasibility studies: outcomes

| Study | Question | Outcome |
|-------|----------|---------|
| [osctrl](osctrl-feasibility.md) | Can Venapce reach osquery hosts through osctrl, and should it ship its own osctrl? | **Plugin shipped** (Track A): four actions on `osctrl-api` with token auth and an async run → poll → collect flow. **"Easy osctrl"** (Track B), a repackaged all-in-one image, is a separate product track and still open. `osctrl-tls` must remain publicly reachable over TLS by every agent |
| Network devices (`NETDEVICE`) | Which connection layer for multivendor routers, switches and firewalls? | NAPALM/scrapli's structured getters needed Python, and that requirement drove the **[Python SDK](sdks.md)**, now on PyPI. **[Scrapli](../plugins/scrapli.md) shipped (beta)** on it. A full normalised `NETDEVICE` node is still under study (below) |
| [GitHub (OpenConnector)](github-oc-feasibility.md) | Can source-code posture come through oomol's connector? | **Shipped (beta).** The provider proxy forwards the security endpoints. The org lives on the settings profile. Built on the Python SDK. GitLab follows on the same code path |
| [Security collectors](security-collectors-plan.md) | What does a security-posture agent need beyond osquery? | A layered plan covering nine layers, three frame kinds and three waves, with shared conventions. Wave 1 is listed below |

---

## Under study

These candidates are under evaluation and **not yet committed**. Each is
assessed for how well it maps onto the `inflowv1` model and onto Venapce's
needs, and for how much work it takes with the current SDKs. Any item **may be
cancelled or reshaped**. *Effort* is a first estimate of quick win vs. hard win
and is not a promise.

Each item is a **collector**. The logic on top (doc store, evaluation, LLM
recommendations) is built downstream in FloMorphic.

| Plugin | Node | What it would do | Approach under review | Effort | Status |
|--------|------|------------------|-----------------------|--------|--------|
| Cloud providers **(priority)** | `AWS` · `AZURE` · `GCP` | Pull resource inventory and deployment status, and read each cloud's native security findings. The result is a Wiz-style trace of what's deployed and what's misconfigured. AWS first | First-class **Go** SDKs. Credentials come from the settings profile: an AWS key or role, an Azure service principal, or a GCP service-account JSON. oomol has no AWS/Azure/GCP connector, so these are not `-oc` plugins. Each plugin collects ① inventory + status (CloudFormation/Config · Resource Graph · Cloud Asset Inventory) and ② the cloud's own posture findings (**Security Hub** · **Defender for Cloud** · **Security Command Center**). One node per provider | **Hard win**: three providers, phased. ① is tractable and ② rides native findings | In study |
| Network devices | `NETDEVICE` | Collect facts, interfaces, IPs and BGP/ARP/LLDP neighbours from routers, switches and firewalls across vendors | Either **[scrapligo](https://github.com/scrapli/scrapligo)** on the Go SDK (SSH/NETCONF, structured transports where offered, CLI + ntc-templates otherwise, normalised to JSON) or building on the shipped [Scrapli](../plugins/scrapli.md) plugin with the Python SDK | **Hard win** | In study |
| ManageEngine | `MANAGEENGINE` | Read and write through a ManageEngine product's REST API (ServiceDesk Plus, Endpoint Central, OpManager or ADManager Plus) | Standard REST + API key/OAuth. Fits the Go or Node SDK directly, close to the Jira plugin. **Which product** is still open, and that choice decides the whole node | **Quick win** once the product is chosen | In study |

### Wave 1 after the clouds

From the [security collectors plan § 10](security-collectors-plan.md#10-waves).
Each item gets its own short feasibility note, modelled on the osctrl one,
before it joins the table above:

| Node | Why Venapce wants it |
|------|----------------------|
| `OPENSEARCH` | Opens up Wazuh vulnerabilities, Suricata/Zeek and auth logs through one plugin. With osctrl it gives the first end-to-end host state → logs chain |
| `LDAP` | Privileged, stale and never-expiring accounts. Highest signal per frame |
| `VULNINTEL` | NVD, OSV, EPSS and CISA KEV, which turn a CVE list into a fix-first order. The LLM node's best input |
| `WAZUH` | SCA/CIS, FIM and rootcheck. A second host lens, the same shape as osctrl |
| `NETBOX` | The intended network, to diff against osquery's host list |

Waves 2 and 3 (`NMAP`, `LINUXHOST`, `K8S`, `TRIVY`, firewalls, threat intel,
and more) are in the [plan](security-collectors-plan.md#10-waves).

---

## Requested

These plugins have been requested but nobody has claimed them yet. To build
one, or to request another, open an issue, or see
**[Get your plugin listed](../README.md#get-your-plugin-listed)**.

_Nothing open right now._
