# Security collectors — plugin plan

> A layered plan for the **collector plugins** a security-posture workflow needs
> beyond osquery/osctrl: which systems to read, what frames to pull out of them,
> how each maps onto the SDKs, and in what order to build. Scope: the
> **security + AI-agent** domain (Venapce-style workflows: collect → store →
> evaluate → recommend).
>
> Status: **plan** — feeds the [Venapce roadmap](venapce.md). Companion to
> [osctrl-feasibility.md](osctrl-feasibility.md). Not a build spec; each wave-1
> item gets its own short feasibility note before it starts.

---

## TL;DR

- **osquery/osctrl covers the host layer well** — processes, ports, packages,
  users, iptables, sudoers, cron, systemd units, SSH keys and config files
  (`augeas`, carves) on every enrolled host. What it cannot see is *outside the
  host*: what the network exposes to unenrolled machines, what the cloud
  account exposes, who has admin in AD, what the code repos leak, or which CVEs
  are actually exploited in the wild. That is where the new collectors go.
- **Every plugin here is a collector.** It declares a settings form for access,
  exposes the target's API as actions, and returns data frames. It holds no
  database. Storage (doc store), evaluation, and recommendations (LLM node) are
  built downstream in the workflow graph — the same rule the
  [osctrl study](osctrl-feasibility.md) set.
- **SaaS goes through Connect (OpenConnector / oomol).** Where oomol has a
  connector for the service the plugin is an `-oc` request builder like
  [Gmail](../plugins/gmail-oc.md) and [Telegram](../plugins/telegram-oc.md):
  credentials live centrally in FloMorphic → Connect, the proxy injects auth.
  Checked against oomol's 1,517 providers (§1a): **GitHub, GitLab, Okta,
  Elasticsearch, Shodan, VirusTotal, AbuseIPDB, Censys, HIBP, Snyk, TheHive**
  are there. **AWS, Azure and GCP are not** (oomol has only `aws_s3` and
  `aws_sts`), so the cloud plugins — like LDAP, Wazuh, osctrl, NetBox — carry
  a read-only credential in a settings profile.
- **Three frame kinds**, and every collector labels which it emits:
  **inventory** (what exists), **findings** (what a tool judged wrong), and
  **events** (what happened). The AI agent consumes them differently.
- **Shipped: [GitHub (OpenConnector)](../plugins/github-oc.md)** (beta) —
  source-code managers via oomol, see
  [github-oc-feasibility.md](github-oc-feasibility.md). **Wave 1** next: the **three clouds** (`AWS` · `AZURE` · `GCP`, one node each — cloud
  inventory and native findings are a priority), then `OPENSEARCH`, `LDAP`,
  `VULNINTEL`, `WAZUH`, `NETBOX`.
- **Two accelerators need no new plugin:** Steampipe exposes AWS/Azure/GCP/
  GitHub/… over the Postgres wire protocol, so the existing
  [Postgres](../plugins/postgres.md) plugin can query cloud inventory while
  the native cloud plugins are built; and goflow2/akvorado land NetFlow in
  ClickHouse, which the existing [ClickHouse](../plugins/clickhouse.md) plugin
  already reads.

---

## 1. Coverage map

What a security-posture agent needs to see, per layer, and where we stand.

| # | Layer | Questions it answers | Have today | Gap |
|---|-------|----------------------|------------|-----|
| 1 | **Host state** | Processes, ports, packages, users, kernel, FIM | osquery → osctrl | Host audits (CIS), package CVEs |
| 2 | **Host services & config** | What does nginx/sshd/sudoers/iptables actually say? | osquery: `iptables`, `sudoers`, `crontab`, `systemd_units`, `ssh_configs`, `authorized_keys`, `augeas`, `file`/`hash`, carves | Only *merged/effective* views (`nginx -T`, `sshd -T`), nftables, audit-tool output |
| 3 | **Network** | What is reachable **from the network**, what the firewall allows, what should exist | osquery (`listening_ports` per enrolled host), Scrapli (device CLI), NETDEVICE (study) | Unenrolled hosts, firewall policy dumps, IPAM source of truth, flows, external surface |
| 4 | **Cloud** | What is deployed, what is public, what the provider's own posture tool flags | AWS/AZURE/GCP (study) | Everything — **priority, wave 1**; plus containers/Kubernetes |
| 5 | **Identity** | Who exists, who is privileged, who is stale, who has no MFA | [Google Workspace (OpenConnector)](../plugins/google-oc.md) (beta) | AD/LDAP, Entra, Okta |
| 6 | **Vulnerability & findings** | Which CVEs, on which assets, which are exploited | — | Scanner results, CVE enrichment (EPSS/KEV) |
| 7 | **Logs & telemetry** | What happened, when, from where | ClickHouse | SIEM/log search, metrics |
| 8 | **Code & supply chain** | Repo protection, leaked secrets, vulnerable dependencies, SBOM | [GitHub (OpenConnector)](../plugins/github-oc.md) (beta) | Repo protection, alerts, org 2FA, deploy keys covered; SBOM, GitLab |
| 9 | **Threat intel** | Is this IP/domain/hash known bad? Did our domain leak? | — | Everything |

The plan below fills the gaps layer by layer; §10 orders them into waves.

### 1a. What oomol already connects

Checked against `src/providers/` in
[oomol-lab/open-connector](https://github.com/oomol-lab/open-connector)
(1,517 providers). Where a connector exists the plugin is `-oc`; where it
doesn't, the plugin declares a settings profile.

| Plan item | oomol connector | Plugin path |
|-----------|-----------------|-------------|
| GitHub · GitLab · Bitbucket · Gitea | `github`, `gitlab`, `bitbucket`, `gitea` | **`-oc`** |
| AWS · Azure · GCP | only `aws_s3`, `aws_sts`; no Azure, no GCP (Google Workspace apps + `google_bigquery` only) | **settings profile** |
| Elasticsearch / OpenSearch | `elasticsearch` (check OpenSearch compatibility); `splunk_http_event_collector` is ingest-only | `-oc` for Elastic; profile for OpenSearch/self-hosted |
| Okta · JumpCloud · Auth0 | `okta`, `jumpcloud`, `auth0_management` | `-oc` |
| AD/LDAP · Entra ID | — (`microsoft_*` are Teams/To Do/Clarity, not Graph directory) | settings profile |
| Threat intel | `shodan`, `censys`, `virustotal`, `abuseipdb`, `urlscan`, `securitytrails`, `haveibeenpwned`, `hybrid_analysis`, `api_void` | **`-oc`** — one `THREATINTEL (OpenConnector)` node can front all of them |
| Code security | `snyk`, `sonarcloud` | `-oc` |
| Network | `cisco_meraki`, `juniper_mist`, `tailscale`, `cloudflare_dns` | `-oc` where used; NetBox, firewalls, SNMP → profile |
| Observability | `datadog`, `grafana`, `grafana_cloud`, `new_relic`, `sentry`, `dynatrace`, `honeycomb`, `axiom` | `-oc` |
| Sinks (response side) | `thehive`, `thehive5`, `pagerduty`, `opsgenie`, `incident_io`, `jira` | `-oc` |
| Wazuh · osctrl · NetBox · Nmap · Trivy · GVM · Tenable · DefectDojo · MISP · OpenCTI · Vault · Prometheus · Loki | — | settings profile |

Every oomol provider also exposes a **provider proxy** (`POST /v1/proxy/:service`)
that reaches API paths outside the curated action list — that is how the
GitHub plugin gets Dependabot/secret-scanning alerts ([details](github-oc-feasibility.md)).

---

## 2. Host services & config — osquery first, `LINUXHOST` for the residual

Most of this layer is **already an osquery table**, so the osctrl plugin
collects it with a SQL query and no new plugin:

| Question | osquery table(s) |
|----------|------------------|
| Firewall rules | `iptables` |
| Listening ports, sockets | `listening_ports`, `process_open_sockets` |
| sudo rights, cron, timers | `sudoers`, `crontab`, `systemd_units` |
| SSH config and keys | `ssh_configs`, `user_ssh_keys`, `authorized_keys` |
| Installed packages, sources | `deb_packages`, `rpm_packages`, `apt_sources`, `yum_sources`, `python_packages`, `npm_packages` |
| Users, groups, logins | `users`, `groups`, `shadow`, `logged_in_users`, `last` |
| Network config | `interface_addresses`, `routes`, `arp_cache`, `dns_resolvers`, `etc_hosts` |
| Parsed config files (nginx, sshd, …) | `augeas` (per-lens key/value view of the file) |
| Any file's metadata / hash / content | `file`, `hash`, **carves** (osctrl supports them) |
| Kernel, modules, MAC | `kernel_info`, `kernel_modules`, `selinux_settings`, `apparmor_profiles` |

What osquery does **not** give is the *merged, effective* view a service
computes from its config tree, and the output of audit tools:

| Residual need | Why osquery falls short | `LINUXHOST` action |
|---------------|-------------------------|--------------------|
| nginx effective config | `augeas` parses one file; `nginx -T` resolves every `include` and reports what is actually loaded | `host.nginx.dump` |
| sshd effective policy | `sshd -T` applies `Match` blocks and defaults; the file alone doesn't | `host.sshd.config` |
| nftables ruleset | no `nftables` table (only `iptables`) | `host.firewall.dump` (`nft list ruleset`) |
| HAProxy / Apache runtime | stats socket, `apachectl -S` | `host.haproxy.dump`, `host.apache.dump` |
| Host audits (CIS) | Lynis / OpenSCAP are tools, not tables | `host.audit.lynis`, `host.audit.openscap` → **findings** |
| Anything else | escape hatch | `host.command.run` |

**`LINUXHOST`** is therefore a small SSH collector (Go SDK,
`golang.org/x/crypto/ssh`, key/password in the settings profile) with those
recipes. It is **wave 2**, not wave 1: build it when a workflow actually needs
an effective config or an audit report, and keep everything osquery can answer
in osquery. If Wazuh is deployed, its SCA covers the CIS-audit case too (§6).

---

## 3. Network layer

| Plugin | Node | What it collects | Approach | Deps on plugin host | Effort | Frame kind |
|--------|------|------------------|----------|---------------------|--------|------------|
| **Nmap** | `NMAP` | The **outside-in** view: host discovery across a subnet, open ports, service/version, OS guess, `--script vuln`. osquery's `listening_ports` is the **inside** view of one enrolled host; Nmap finds the hosts that are *not* enrolled and what the network actually exposes after firewalls | Go SDK + [`Ullaakut/nmap`](https://github.com/Ullaakut/nmap) (runs the binary, parses XML). Long scans → async job with `Progress` | `nmap` binary (+ root for SYN/OS scans) | Quick win; **wave 2** — diff against osquery + NetBox is the payoff | inventory + findings |
| **NetBox** | `NETBOX` | Devices, interfaces, IP addresses, prefixes, VLANs, sites — the *intended* network, to diff against what Nmap finds | REST, `Authorization: Token …`, paged | none | **Quick win** | inventory |
| **Firewall policy** | `OPNSENSE` · `FORTIGATE` · `PANOS` · `CHECKPOINT` | Rule base, NAT, address/service objects, active sessions, interfaces, firmware version | OPNsense: REST key/secret. FortiGate: REST `/api/v2/cmdb/*` + `/monitor/*`, bearer token. PAN-OS: XML API `type=config` (REST since 9.0). Check Point: Management API `show-access-rulebase`. One node per vendor (each API is different enough) | none | **Quick win each**; *which vendor first* is the open question | inventory |
| **SNMP** | `SNMP` | Interface table, ARP/ND table, sysDescr, uptime — vendor-neutral for anything Scrapli/NETDEVICE can't reach | Go SDK + `gosnmp`, v2c/v3 | none | **Quick win** | inventory |
| **External surface** | `EXTSURFACE` | DNS records (A/AAAA/MX/TXT/SPF/DMARC), subdomains from cert transparency (crt.sh), TLS check per endpoint (chain, expiry, protocol/cipher) | Go SDK + `miekg/dns`, `crypto/tls` dial, crt.sh JSON — no credentials. Shodan/Censys go through `THREATINTEL (OpenConnector)` (§9) | none | **Quick win** | inventory + findings |
| **Flows** | *(none)* | NetFlow/sFlow/IPFIX top talkers, new external destinations | Run **goflow2** or **akvorado** → ClickHouse; query with the existing [ClickHouse](../plugins/clickhouse.md) plugin | collector process, not a plugin | **No plugin needed** | events |
| **IDS** | *(none)* | Suricata/Zeek alerts and connection logs | Ship EVE JSON / Zeek logs to OpenSearch; read with `OPENSEARCH` (§7) | log shipper | **No plugin needed** | events |
| Network devices | `NETDEVICE` | Facts, interfaces, neighbours | Already in [study](venapce.md#under-study); Scrapli ships today | — | Hard win | inventory |

---

## 4. Cloud & containers

### All three clouds — one node each, AWS built first

The roadmap lists `AWS · AZURE · GCP` as a study item; this plan promotes them
to **wave 1**. Each is a collector with two halves — ① **inventory** (what is
deployed and how it is configured) and ② the provider's **own posture
findings** — and the same async/paging conventions (§11).

**Auth path.** oomol has **no** general AWS, Azure or GCP connector (only
`aws_s3`/`aws_sts`; see §1a), so these are settings-profile plugins. The
profile holds a read-only credential: AWS access key or role ARN to assume
(`SecurityAudit` policy), Azure service principal with `Reader` +
`Security Reader`, GCP service-account JSON with `roles/viewer` +
`roles/securitycenter.findingsViewer`. The plugin never stores them; they
arrive as `body.settings` per call. If Connect-managed cloud credentials are
wanted later, the route is contributing `aws`/`azure`/`gcp` providers to oomol
(it has an add-provider workflow, and `aws_sts` shows SigV4 is already solved
there) — a separate effort the plugins should not wait on.

**AWS** (AWS SDK for Go v2):

| Action | API | Frame kind |
|--------|-----|------------|
| `aws.inventory.search` | Resource Explorer `Search` **or** Config `SelectResourceConfig` (SQL-like) | inventory |
| `aws.ec2.security_groups` | `DescribeSecurityGroups` (+ instances/ENIs they attach to) | inventory |
| `aws.s3.posture` | per bucket: `GetPublicAccessBlock`, `GetBucketPolicyStatus`, `GetBucketEncryption`, `GetBucketVersioning` | inventory |
| `aws.iam.credential_report` | `GenerateCredentialReport` → `GetCredentialReport` (async, poll) | inventory |
| `aws.iam.policies` | users/roles/groups + attached & inline policies | inventory |
| `aws.securityhub.findings` | `GetFindings` with filters, paged — AWS's own posture, in ASFF | findings |
| `aws.guardduty.findings` | `ListFindings` → `GetFindings` | findings |
| `aws.inspector.findings` | Inspector2 `ListFindings` (package CVEs on EC2/ECR/Lambda) | findings |
| `aws.accessanalyzer.findings` | `ListFindings` (external access to resources) | findings |
| `aws.cloudtrail.events` | `LookupEvents` (last 90 days; older → Athena/CloudTrail Lake later) | events |

**Azure** (`azure-sdk-for-go`):

| Action | API | Frame kind |
|--------|-----|------------|
| `azure.inventory.query` | Resource Graph `Resources` (KQL) — the whole tenant in one query | inventory |
| `azure.network.nsg_rules` | `armnetwork` NSGs + rules, public IPs | inventory |
| `azure.storage.posture` | storage accounts: public blob access, TLS min version, network rules | inventory |
| `azure.rbac.assignments` | `armauthorization` role assignments + definitions | inventory |
| `azure.defender.assessments` | Defender for Cloud `Assessments` + `SubAssessments` | findings |
| `azure.defender.alerts` | Defender for Cloud `Alerts` | findings |
| `azure.activity.events` | Activity Log (`armmonitor`) | events |

Identity (users, MFA, conditional access) is Entra → `ENTRA` in §5.

**GCP** (`cloud.google.com/go`):

| Action | API | Frame kind |
|--------|-----|------------|
| `gcp.inventory.search` | Cloud Asset Inventory `SearchAllResources` / `ExportAssets` | inventory |
| `gcp.iam.policies` | Cloud Asset `SearchAllIamPolicies` — who has what, org-wide | inventory |
| `gcp.network.firewalls` | Compute `Firewalls.List`, external IPs | inventory |
| `gcp.storage.posture` | buckets: IAM (allUsers/allAuthenticatedUsers), uniform access, public-access prevention | inventory |
| `gcp.scc.findings` | Security Command Center `ListFindings` | findings |
| `gcp.audit.events` | Cloud Logging `entries.list` filtered on audit logs | events |

**Order: AWS → Azure → GCP**, one node each, sharing one internal package for
the envelope, paging, and async export handling.

### The Steampipe shortcut — inventory without a new plugin

[Steampipe](https://steampipe.io) serves AWS, Azure, GCP, GitHub, Kubernetes,
net (DNS/TLS) and ~140 other sources as **Postgres tables** on
`localhost:9193`. Our [Postgres](../plugins/postgres.md) plugin can query it
today:

```sql
select group_id, ip_protocol, from_port, cidr_ip
from aws_vpc_security_group_rule
where cidr_ip = '0.0.0.0/0' and type = 'ingress';
```

This gives cloud **inventory** *now* (run `steampipe service start` next to
the plugin) while the native plugins are built, and stays useful afterwards for
ad-hoc SQL across all three clouds. The native `AWS`/`AZURE`/`GCP` plugins own
what Steampipe cannot do: provider **findings** (Security Hub, Defender, SCC),
async exports, multi-account/subscription/project fan-out, and a proper form
with pickers. Powerpipe runs CIS benchmarks on top and emits JSON
— a CLI-wrapper action. Note CloudQuery is a similar sync-to-Postgres/ClickHouse
tool but its license changed; check before adopting.

### Containers & IaC

| Plugin | Node | What it collects | Approach | Deps | Effort | Frame kind |
|--------|------|------------------|----------|------|--------|------------|
| **Kubernetes** | `K8S` | Namespaces, workloads, images, service accounts, RBAC bindings, network policies, secrets *metadata*, pod security context; Trivy Operator `VulnerabilityReport`/`ConfigAuditReport` CRDs if present | Go SDK + `client-go`, kubeconfig or token in the profile | none | Medium | inventory + findings |
| **kube-bench** | action on `K8S` | CIS Kubernetes benchmark | run as a Job, read JSON output | cluster access | Quick, once `K8S` exists | findings |
| **Docker host** | `DOCKER` | Containers, images, mounts, privileged/host-network flags, exposed ports | Docker Engine API over socket/TLS | none | Quick win | inventory |
| **Trivy** | `TRIVY` | CVEs in images, filesystems, SBOMs; misconfig in IaC (`trivy config`), secrets | CLI wrapper `--format json` (Go lib is not a stable API); or `trivy server` | `trivy` binary | Quick win | findings |
| **Terraform state** | `TFSTATE` | Desired state from a state backend (S3/GCS/HTTP) — to diff against cloud inventory | read + parse state JSON | none | Quick win | inventory |
| **IaC scanners** | action on `TRIVY` | Checkov/tfsec/`trivy config` findings on repos | CLI wrapper | binary | Quick | findings |

---

## 5. Identity & access

Highest signal-per-frame layer for an AI agent: privileged accounts, stale
accounts, missing MFA.

| Plugin | Node | What it collects | Approach | Effort | Frame kind |
|--------|------|------------------|----------|--------|------------|
| **AD / LDAP** | `LDAP` | Users, groups, computers, privileged groups (Domain Admins, `adminCount=1`), password-never-expires & disabled (`userAccountControl` bits), stale (`lastLogonTimestamp`), Kerberoastable (`servicePrincipalName` set), password policy, OU tree | Go SDK + `go-ldap/v3`, paged search; works for OpenLDAP/FreeIPA too | **Quick win** | inventory |
| **Entra ID** | `ENTRA` | Users, MFA registration (`userRegistrationDetails`), conditional-access policies, risky users/sign-ins, app registrations & consents, sign-in logs | Microsoft Graph (Go SDK), client-credential auth | Medium | inventory + events |
| **Okta (OpenConnector)** | `Okta (OpenConnector)` | Users, groups, apps, policies, system log | oomol `okta` connector → `-oc` | Quick win | inventory + events |
| **Keycloak** | `KEYCLOAK` | Realms, clients, users, roles, required actions (MFA) | Admin REST | Quick win | inventory |
| **Google Workspace** | `GOOGLE` | *(extend [Google Workspace (OpenConnector)](../plugins/google-oc.md))* admin users, 2SV status, login audit | Admin SDK Directory + Reports | Quick, incremental | inventory + events |
| **Vault** | `VAULT` | Auth methods, policies, leases, activity counters | REST, token | Quick win | inventory |

---

## 6. Vulnerability & findings

| Plugin | Node | What it collects | Approach | Effort | Frame kind |
|--------|------|------------------|----------|--------|------------|
| **Wazuh** | `WAZUH` | Agents, SCA (CIS) results, FIM changes, rootcheck, syscollector (packages/ports/processes) — a second host lens with built-in audits | REST on `:55000`, basic auth → JWT (short-lived; refresh in the plugin). **4.8+ moved vulnerability state to the indexer** (`wazuh-states-vulnerabilities-*`), so pair with `OPENSEARCH` | **Quick win** | inventory + findings |
| **Vuln intel** | `VULNINTEL` | Per CVE: CVSS/description (NVD 2.0), affected packages (OSV), exploit probability (EPSS), known-exploited (CISA KEV) | Four public REST/JSON sources, API key optional (NVD rate limit) | **Quick win** | enrichment |
| **Nuclei** | `NUCLEI` | Template-based web/service findings against a target list | Go SDK + `projectdiscovery/nuclei/v3/lib` (or CLI `-jsonl`) | Quick win | findings |
| **Greenbone / OpenVAS** | `GVM` | Scan results, hosts, tasks | GMP (XML over TLS/unix socket) → Python SDK + `python-gvm` | Medium | findings |
| **Tenable** | `TENABLE` | Scan results (async export → poll → download) | REST, `X-ApiKeys` | Medium | findings |
| **DefectDojo** | `DEFECTDOJO` | Findings across imported scanners; also a **sink** for what the agent produces | REST v2, token | Quick win | findings |
| **OWASP ZAP** | `ZAP` | Active/passive web scan alerts | ZAP daemon REST API | Medium | findings |

`VULNINTEL` is the one the LLM node leans on most: it turns "CVE-2025-1234 on
12 hosts" into "exploited in the wild, EPSS 0.93, fix first".

---

## 7. Logs & telemetry

State says what is; events say what happened. Every layer above eventually
ships logs here.

| Plugin | Node | What it collects | Approach | Effort |
|--------|------|------------------|----------|--------|
| **OpenSearch / Elasticsearch** | `OPENSEARCH` | Query DSL search, aggregations, index list — covers Wazuh indexer, Suricata/Zeek, Filebeat/auth logs | Node or Go client; same shape as the [ClickHouse](../plugins/clickhouse.md) plugin (row cap, mustache tokens). oomol has an `elasticsearch` connector — an `-oc` variant for Elastic Cloud; self-hosted OpenSearch (Wazuh) needs the profile path | **Quick win** |
| **Prometheus** | `PROMETHEUS` | PromQL instant/range queries — node_exporter, blackbox, cert expiry | HTTP API | Quick win |
| **Loki** | `LOKI` | LogQL range queries | HTTP API | Quick win |
| **Splunk** | `SPLUNK` | Saved/ad-hoc searches (async job → poll → results, like osctrl) | REST `search/jobs` | Medium |
| **Graylog** | `GRAYLOG` | Search API | REST | Quick win |

---

## 8. Code & supply chain — via OpenConnector

Source-code managers are SaaS with OAuth, and oomol connects them — so these
are **`-oc` plugins**: the credential is connected once in FloMorphic → Connect,
the plugin picks the connected account in its settings form, and each action is
proxied over `flomorphic.svc.oc.proxy`. Same shape as
[Gmail (OpenConnector)](../plugins/gmail-oc.md); `hostDependency` on FloMorphic.

| Plugin | Node | What it collects | Approach | Effort | Frame kind |
|--------|------|------------------|----------|--------|------------|
| **[GitHub (OpenConnector)](../plugins/github-oc.md)** — **shipped (beta)** | `GitHub (OpenConnector)` | Repos, collaborators, branch protection, Dependabot / secret-scanning / code-scanning alerts, org members & 2FA, deploy keys, Actions secrets *names*, workflow permissions, commits/PRs | oomol `github` connector (~147 curated actions, none security-specific) + oomol's **provider proxy** for the alert/protection/org endpoints. Details in [github-oc-feasibility.md](github-oc-feasibility.md) | **Done** — proxy forwarding confirmed; the org lives on the settings profile, not on actions (see the note's § 0) | inventory + findings |
| **GitLab (OpenConnector)** | `GitLab (OpenConnector)` | Projects, protected branches, vulnerability findings (Ultimate), members, CI variable *names* | oomol `gitlab` connector + proxy — same code path as GitHub | Quick win | inventory + findings |
| **Snyk / SonarCloud (OpenConnector)** | `Snyk (OpenConnector)` | Dependency/container/IaC issues per project; SonarCloud hotspots | oomol `snyk`, `sonarcloud` connectors | Quick win | findings |
| **Syft / SBOM** | action on `TRIVY` | SBOM per image/repo (CycloneDX/SPDX) | CLI wrapper | Quick | inventory |
| **Registry** | `HARBOR` | Projects, images, scan results | REST (self-hosted → settings profile) | Quick win | inventory + findings |
| **SonarQube** | `SONARQUBE` | Security hotspots, vulnerabilities, quality gate | REST, token (self-hosted → settings profile) | Quick win | findings |

---

## 9. Threat intel & enrichment

| Plugin | Node | What it collects | Approach | Effort |
|--------|------|------------------|----------|--------|
| **Threat intel (OpenConnector)** | `THREATINTEL (OpenConnector)` | IP/domain/hash/URL reputation: VirusTotal, AbuseIPDB, urlscan, SecurityTrails, Hybrid Analysis, APIVoid; Shodan/Censys host lookups | oomol has connectors for **all of these** → one `-oc` node, keys managed in Connect; batch with rate-limit handling | **Quick win** |
| **MISP** | `MISP` | IOC search (`attributes/restSearch`), events, feeds | REST, key | Quick win |
| **OpenCTI** | `OPENCTI` | Indicators, relationships, reports | GraphQL, token | Medium |
| **HIBP** | in `THREATINTEL (OpenConnector)` | Breached accounts for a verified domain, pastes | oomol `haveibeenpwned` connector | Quick win |
| **Shodan / Censys** | in `THREATINTEL (OpenConnector)` | Host/port exposure as seen from outside | oomol `shodan`, `censys` connectors | — |

Enrichment plugins are called *per record* from the flow (loop over IPs from
`OPENSEARCH`, look each up), so they should accept **batches** and honour
upstream rate limits with backoff rather than failing the job.

---

## 10. Waves

Ordered by value ÷ effort, and by dependency (e.g. `OPENSEARCH` before
`WAZUH` vulnerabilities).

### Shipped — GitHub (OpenConnector)

Source-code managers via oomol, on the Python SDK —
[plugin entry](../plugins/github-oc.md), feasibility note and build outcome in
[github-oc-feasibility.md](github-oc-feasibility.md). GitLab follows on the same
code path.

### Wave 1 — quick wins that close the biggest gaps

| Plugin | Node | SDK | Why now |
|--------|------|-----|---------|
| **AWS** | `AWS` | Go | Cloud is a priority: inventory + Security Hub/GuardDuty/Inspector findings + IAM credential report |
| **Azure** | `AZURE` | Go | Resource Graph inventory + Defender for Cloud assessments; Entra follows in §5 |
| **GCP** | `GCP` | Go | Cloud Asset Inventory + IAM policy search + Security Command Center findings |
| OpenSearch / Elasticsearch | `OPENSEARCH` | Node or Go | Unlocks Wazuh vulns, Suricata, auth logs — one plugin, many sources |
| AD / LDAP | `LDAP` | Go | Privileged/stale/no-expiry accounts — highest signal per frame |
| Vuln intel | `VULNINTEL` | Go | Makes every CVE list actionable (EPSS/KEV); the LLM node's best input |
| Wazuh | `WAZUH` | Go | SCA/FIM/CIS for hosts, same shape as the osctrl plugin |
| NetBox | `NETBOX` | Go | Source of truth to diff osquery's host list against — "unknown host on the subnet" |

Plus **no-plugin** enablers documented as recipes: osquery queries for the host
config layer (§2), Steampipe → Postgres plugin (cloud inventory),
goflow2/akvorado → ClickHouse plugin (flows).

### Wave 2 — outside-in views, containers, firewalls

`NMAP` (the network view osquery can't give), `LINUXHOST` (effective configs
and audits only), `K8S` (+kube-bench), `DOCKER`, `TRIVY`, one firewall vendor
(**pick one:** OPNsense is the fastest API; FortiGate the most common in
enterprise), `EXTSURFACE`, `PROMETHEUS`, `NUCLEI`, `DEFECTDOJO`, and the
`-oc` follow-ons that reuse the GitHub code path: GitLab, Okta, Threat intel
(Shodan / VirusTotal / AbuseIPDB / HIBP / Censys).

### Wave 3 — breadth

`ENTRA`, `OKTA`, `GVM`, `TENABLE`, `SPLUNK`, `MISP`,
`THREATINTEL`, `SNMP`, `TFSTATE`, `ANSIBLE`, `HARBOR`, `VAULT`, remaining
firewall vendors.

---

## 11. Conventions every collector follows

These are what make the frames usable by an AI agent downstream; agree on them
before wave 1 starts.

**Frame envelope.** Every frame a collector emits carries:

```json
{
  "collector": "NMAP",
  "kind": "inventory | findings | events | enrichment",
  "source": { "type": "nmap", "target": "10.0.0.0/24", "version": "7.95" },
  "collected_at": "2026-09-18T10:00:00Z",
  "asset": { "hostname": "web-01", "ip": "10.0.0.5", "cloud_id": null },
  "records": [ ... native shape ... ]
}
```

- **Native shape inside, common envelope outside.** Don't rewrite Nmap XML or
  Security Hub ASFF into a house schema — the LLM node reads either. Do add
  `asset` so records from different collectors join on host/IP/cloud ID in the
  doc store.
- **Findings may be normalised to OCSF** (Prowler and Security Hub emit it
  already; Vulnerability Finding `2002`, Compliance Finding `2003`, Detection
  Finding `2004`) so evaluation rules apply uniformly. Do this as a *separate*
  downstream node, not inside collectors, unless the source is OCSF-native.
- **Async by default for anything that scans or exports.** Nmap, Tenable
  exports, IAM credential reports, Splunk jobs, osctrl queries: run → `Progress`
  → poll → `Done`, never a single blocking call.
- **Caps and paging.** Fleet-wide queries and findings lists get large; every
  list action takes `limit`/`page` and the plugin enforces a server-side cap
  (cf. ClickHouse's 100-row cap), with the cap reported in the frame.
- **Connect first.** If oomol has a connector for the service (§1a), the
  plugin is an `-oc` request builder (settings form picks the connected
  account; proxy injects auth; `hostDependency` on FloMorphic), using curated
  actions where they exist and the provider proxy for the rest. A settings
  profile holds credentials only for systems oomol does not connect.
- **Read-only profiles.** A collector's settings profile should be satisfiable
  by a read-only credential (`SecurityAudit` in AWS, a read-only Wazuh user, a
  PAT with `security_events:read`). Actions that need more (`host.command.run`,
  `NUCLEI`, `NMAP` SYN scans) are gated by an explicit profile flag.
- **Binary dependencies are declared.** Nmap, Trivy, Lynis, OpenSCAP, kube-bench
  run a binary on the plugin host; the catalog entry's *Install* section lists
  it and the plugin's connection test (meta RPC) checks it is present, like
  Scrapli's prompt test.
- **Shared library, separate nodes.** The CLI wrappers share one internal Go
  package (exec + timeout + JSON/XML parse + envelope), but each tool stays its
  own node so its form, pickers, and settings profile make sense on the canvas.

---

## 12. The AI-agent side

Collectors feed the agent; two additions make the agent side itself cheaper:

- **`VULNINTEL` and `THREATINTEL` are enrichment nodes** — the agent calls them
  mid-reasoning ("is this CVE exploited?", "is this IP known bad?"), so they are
  designed for many small calls, not one bulk pull.
- **An `MCP` bridge plugin** (idea, not committed): connect to any MCP server and
  expose its tools as actions. MCP tools already describe their input as JSON
  Schema, which is exactly what a plugin action's form is — so the mapping is
  near mechanical, and it would surface the growing set of security MCP servers
  (Semgrep, GitHub, Shodan, VirusTotal, HIBP) on the canvas without a plugin
  each. Worth a feasibility note once the SDKs settle.

---

## 13. Decisions needed before wave 1

| Decision | Options | Default if nobody objects |
|----------|---------|---------------------------|
| Which firewall vendor first | OPNsense · FortiGate · PAN-OS · Check Point | **FortiGate** (most common where a "network report" is asked for); OPNsense if the lab runs it |
| Which SIEM/log store | OpenSearch · Elasticsearch · Splunk · Loki | **OpenSearch** (Wazuh ships it; Elasticsearch-compatible client) |
| Directory | AD/LDAP · Entra · Okta | **LDAP** first (works on-prem and for OpenLDAP/FreeIPA), Entra in wave 3 |
| Cloud order | AWS · Azure · GCP | All three in wave 1, **AWS → Azure → GCP**; Steampipe covers inventory for all three meanwhile |
| Cloud auth path | oomol connector (`-oc`) · settings-profile credential | **Settings profile** — confirmed: oomol has no AWS/Azure/GCP connector today (§1a) |
| Host audit tool | Lynis · OpenSCAP · Wazuh SCA | **Wazuh SCA** if Wazuh is deployed; else Lynis via `LINUXHOST` (wave 2) |
| GitHub scope | read-only collection · also write (issues, PR comments) | **Read-only** first; writes only if a workflow needs to file findings back |
| Scanner | Nmap · Nuclei · GVM · Tenable | **Nmap + Nuclei** (no server to run), GVM/Tenable if already licensed |

---

## 14. Next steps

1. ~~**GitHub (OpenConnector)** is next~~ — **built**
   ([plugin entry](../plugins/github-oc.md)); finish testing against a live
   org and promote it from beta.
2. Agree the wave-1 list and the §13 defaults.
3. Add the wave-1 rows to the **Under study** table in [venapce.md](venapce.md#under-study) (Node ·
   What it would do · Approach · Effort · Status), the same way osctrl was added.
4. Write a one-page feasibility note per wave-1 plugin (API surface, auth,
   async shape, caps) — the osctrl note is the template.
5. After GitHub, build `OPENSEARCH`: with osctrl it gives a host state → logs
   chain end to end, which is the first security workflow worth demoing.

---

*Sources: osquery schema, [jmpsec/osctrl](https://github.com/jmpsec/osctrl),
[Wazuh API](https://documentation.wazuh.com/current/user-manual/api/reference.html),
[Steampipe](https://steampipe.io), [Ullaakut/nmap](https://github.com/Ullaakut/nmap),
[NVD API 2.0](https://nvd.nist.gov/developers/vulnerabilities), [OSV](https://osv.dev),
[EPSS](https://www.first.org/epss/), [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog),
[OCSF](https://schema.ocsf.io), AWS SDK for Go v2, Microsoft Graph, NetBox REST API.*
