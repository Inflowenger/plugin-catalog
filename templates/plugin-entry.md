# <Plugin name>

> One sentence: what this plugin puts on the canvas.

| | |
|---|---|
| **Repository** | https://github.com/<you>/<repo> |
| **Node name** | `<PluginIntro.Name>` |
| **Author** | [@<you>](https://github.com/<you>) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `<category>` |
| **Runs on** | Any `inflowv1` host — *or* `<Platform> ★` if it needs a host-specific service (see below) |
| **License** | See repository |
| **Status** | Active / Experimental / Unmaintained |

## What it does

A short paragraph. What can a flow author do with this node that they couldn't
before? Name the service and the versions or flavours you support — and the ones
you don't.

## Actions

| Method | Title |
|--------|-------|
| `<domain>.<object>.<verb>` | <Title> |

Meta RPCs, if any: `<domain>.meta.ping`, …

## Connection

Which settings profile keys the plugin expects, which are required, and where a
user gets them (API token page, service account, connection string). State that
the plugin stores no credentials — the platform supplies them per call as
`body.settings`.

## Install

```bash
git clone https://github.com/<you>/<repo>
cd <repo>
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

Optional. Upstream API quirks, rate limits, anything a user will hit on day two.

If your plugin needs a **host-specific service** on top of `inflowv1` (a proxy,
an internal subject, a platform-only capability) and therefore runs on one
platform only, say so here, put `<Platform> ★` in the **Runs on** row above, and
add a `hostDependency` object to your `index.json` entry:

```json
"hostDependency": {
  "platform": "<platform>",
  "service": "<the service you depend on>",
  "subjects": ["<nats.subjects.you.use.*>"]
}
```

Omit `hostDependency` entirely if the plugin runs on any `inflowv1` host.
