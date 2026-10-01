# Nuclei

> Template-based vulnerability scanning on the Inflowenger canvas, powered by the embedded nuclei engine.

| | |
|---|---|
| **Repository** | https://github.com/Venapce/nuclei |
| **Node name** | `NUCLEI` |
| **Author** | [@Venapce](https://github.com/Venapce) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `devops`, `utility` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Beta |

## What it does

Adds a `NUCLEI` node that runs [nuclei](https://github.com/projectdiscovery/nuclei)
(ProjectDiscovery, MIT) in-process against targets a flow provides. Templates are
chosen by **filter** — profile, severity, protocol, tags, authors, IDs, or a DSL
condition — rather than one by one, so a single node covers the whole 13,000+
template catalog. Findings stream out as they match.

> **Beta.** The plugin is not yet fully tested. Verify it against your own
> targets before relying on it.

> **Active scanning.** The node scans whatever targets it is given. Authorisation
> to scan them is your responsibility.

## Actions

| Method | Title |
|--------|-------|
| `nuclei.scan.run` | Run Scan |
| `nuclei.templates.select` | Preview Selection |
| `nuclei.templates.search` | Search Templates |
| `nuclei.templates.update` | Update Templates |
| `nuclei.template.validate` | Validate Template |
| `nuclei.workflow.run` | Run Workflow |

Meta RPCs: `nuclei.meta.ping`, `.profiles`, `.tags`, `.templates.search` — back
the connection test and the form's browse/search buttons.

## Connection

No scan credential is needed. The settings profile carries deployment policy: the
templates directory, rate limit / concurrency / timeout, and the safety gates —
block local/private networks (on by default), allow intrusive templates, allow
code templates (execute shell on the plugin host), allow DAST / headless / local
file access. Every gate defaults to the safe setting.

## Install

```bash
git clone https://github.com/Venapce/nuclei
cd nuclei
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- A cancelled node stops its in-flight scan: the plugin registers an `OnSignal`
  handler and aborts the job when the runtime reports a cancel / timeout.

- The first scan needs a template catalog: run **Update Templates** once, or point
  `templatesDir` at an existing nuclei-templates checkout.
- The binary embeds the nuclei engine (~150–200 MB); no external `nuclei` binary
  is required.
