# Scrapli

> Run CLI commands and push configuration to network devices from the Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/scrapli-plugin |
| **Node name** | `SCRAPLI` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Python — [`inflowenger-plugin-sdk`](https://pypi.org/project/inflowenger-plugin-sdk/) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `devops`, `utility` |
| **License** | See repository |
| **Status** | Beta |

## What it does

Adds a `SCRAPLI` node that talks to network devices over SSH/Telnet using
[scrapli](https://github.com/carlmontanari/scrapli): send show/exec commands and
read their output, or push configuration lines in config mode. Commands can be
parsed to structured data with TextFSM via
[ntc-templates](https://github.com/networktocode/ntc-templates) when the "Parse
output" toggle is on.

Supported platforms are Cisco IOS-XE / NX-OS / IOS-XR, Arista EOS, and Juniper
JunOS. A failed command does not stop the flow — the error is committed as
output, so downstream nodes can branch on it.

This is the catalog's **first plugin built on the Python SDK** (the Python port of
the reference Go SDK).

> **Beta.** The plugin works and its settings/form logic is covered by an offline
> test suite, but it has **not yet been exercised end-to-end against every listed
> platform** (e.g. Cisco NX-OS). Treat platform coverage as provisional and
> verify against your own devices before relying on it in production.

## Actions

| Method | Title |
|--------|-------|
| `scrapli.command.send` | Send Commands |
| `scrapli.config.send` | Send Config |

Meta RPC: a connection test bound to the settings form's submit — it opens the
device and reads its prompt to confirm the profile is valid.

## Connection

The plugin stores no device credentials. It declares a **Scrapli Device** settings
form — `host`, `platform`, `transport` (SSH/Telnet), `port`, `username`,
`password`, `enable` (enable secret), and `strict_key` (host-key verification) —
and the platform ships the bound profile with every call as `body.settings`.
Create one profile per device, then bind it on the node. One running plugin can
serve many devices.

## Install

```bash
git clone https://github.com/Inflowenger/scrapli-plugin
cd scrapli-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
pip install -r requirements.txt
python main.py
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. Device credentials never go in
`.env.inflow`; they are a settings profile. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).
Requires Python 3.11+.

## Notes

- TextFSM parsing is optional — install the `parse` extra (`ntc-templates`) to use
  the "Parse output" toggle on **Send Commands**; without it, output is returned
  as raw text.
- Transport is asyncssh (`scrapli[asyncssh]`). Set `strict_key` per your host-key
  policy — disabling it skips known-hosts verification.
