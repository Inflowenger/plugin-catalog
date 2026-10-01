# Playwright

> Drive a real browser — Chromium, Firefox or WebKit — from the Inflowenger canvas.

| | |
|---|---|
| **Repository** | https://github.com/Venapce/playwright |
| **Node name** | `Playwright` |
| **Author** | [@Venapce](https://github.com/Venapce) |
| **SDK** | Node — [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `utility`, `protocol` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Beta |

## What it does

Adds a `Playwright` node that opens pages that need JavaScript to render and reads
them as structured data, screenshots them, prints them to PDF, evaluates scripts in
them, or runs a whole scripted session (sign in, fill a form, page through a table)
as one node. Flows can be recorded with Playwright's codegen and converted to
steps. A browser is launched once per profile and kept warm; every job gets its own
isolated context.

> **Beta.** The plugin is not yet fully tested. Verify it against your own sites
> and browser setup before relying on it.

## Actions

| Method | Title |
|--------|-------|
| `playwright.page.open` | Open page |
| `playwright.page.screenshot` | Screenshot |
| `playwright.page.pdf` | Print to PDF (Chromium only) |
| `playwright.page.evaluate` | Evaluate JavaScript |
| `playwright.flow.run` | Run browser flow |

Meta RPCs: browser status, install (with progress) and a browser check — so
engines can be installed from the plugin's page without a terminal.

## Connection

No credentials in the plugin. A **browser profile** settings form (engine, remote
browser endpoint, storage state, JavaScript on/off, proxy, headers, locale,
timezone, viewport, timeouts) is shipped with every call as `body.settings`.
Pointing the profile at a remote browser endpoint means nothing is installed or
launched locally.

## Install

```bash
git clone https://github.com/Venapce/playwright
cd playwright
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install && npm run build && npm start
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).
Requires Node 20+.

**From FloMorphic:** define the plugin under **Extensions**, then either download
the filled-in `.env.inflow` and run the commands above, or run the generated
one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- Browsers are a separate dependency: run `npm run browsers` once on the host, use
  the install buttons on the plugin's page, or use a remote browser endpoint.
- **Evaluate JavaScript** runs arbitrary script inside the page; it is as trusted
  as whoever can edit the flow.
