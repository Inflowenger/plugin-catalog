# Telegram (OpenConnector)

> Send Telegram messages, photos and documents — and read updates and chats —
> from the Inflowenger canvas, as a bot connected centrally in FloMorphic →
> Connect.

| | |
|---|---|
| **Repository** | https://github.com/mehdi-shokohi/telegram-oc-plugin |
| **Node name** | `Telegram (OpenConnector)` |
| **Author** | [@mehdi-shokohi](https://github.com/mehdi-shokohi) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `communication` |
| **Runs on** | **FloMorphic only ★** — needs FloMorphic's Connect / OpenConnector proxy (`flomorphic.svc.oc.*`); not portable to a bare `inflowv1` host. |
| **License** | See repository |
| **Status** | Active |

## What it does

Puts Telegram on the canvas as five actions — **Send message**, **Send photo**,
**Send document**, **Get updates**, and **Get chat** — without ever holding a
Telegram bot token or making a Telegram Bot API call. It is a *request builder*:
a Telegram bot is connected **once, centrally**, in **FloMorphic → Connect** (via
OpenConnector / oomol), and this node just picks which connected bot to act as
and asks the FloMorphic backend to run each action for it.

The backend is a generic proxy: it stores the OpenConnector token and forwards
requests over one NATS subject (`flomorphic.svc.oc.proxy`), injecting the auth
header. All Telegram knowledge — which bots exist, what an action needs, which
OpenConnector endpoint to call — lives in the plugin. Before running, the plugin
reads each action's required scopes **live from oomol**
(`GET /v1/actions/telegram.<action>`) and checks the chosen account's scopes
against them; Telegram is an API-key connection (the bot token) that typically
reports no scopes, so the check skips and oomol stays the authoritative gate.
String inputs accept `{{$.path}}` tokens resolved against the flow scope, so a
`chatId`, `text` or `caption` can reference upstream data.

## Actions

| Method | Title |
|--------|-------|
| `telegram.send` | Send message |
| `telegram.send_photo` | Send photo |
| `telegram.send_document` | Send document |
| `telegram.get_updates` | Get updates |
| `telegram.get_chat` | Get chat |

Each canvas action maps to an OpenConnector action name that the backend runs as
the connected bot. Meta RPCs power the settings dialog and the in-app manual's
live **Run** buttons: `telegram.meta.account.list`, `telegram.meta.account.test`,
`telegram.meta.bot.info`, `telegram.meta.webhook.info`, `telegram.meta.chat.list`.

## Connection

The plugin stores **no** Telegram credentials and reads no Telegram environment
variables — there is no bot token, alias, or config to paste. In the node's
**settings** form, press **Load accounts** to populate the drop-down live from
Connect, **pick** your connected bot (or leave the default), **Test account**,
and **Save**; the platform stores this as a reusable **settings profile** supplied
on every call as `body.settings`. The optional **Gateway** field pins to one
Connect connection when several are configured (hosted oomol vs self-hosted);
leave it empty to span all. One connected bot can be shared by many nodes, and
rotating it happens in the Connect page with no plugin redeploy.

## Install

```bash
git clone https://github.com/mehdi-shokohi/telegram-oc-plugin
cd telegram-oc-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

- **Central auth, no Telegram token in the plugin.** The plugin never sees the
  bot token; the FloMorphic backend holds the OpenConnector credential and
  performs the call. The `-oc` suffix marks this as the OpenConnector-backed
  Telegram node — a future direct-Bot-API `telegram` plugin could coexist.
- **Runtime credential.** Because the plugin publishes on `flomorphic.svc.oc.*`,
  `INFRA_CRED` must be an **OPEN (multi)** runtime credential; a strict,
  plugin-scoped credential cannot publish on `flomorphic.>` and every action
  fails with a NATS no-responders/timeout.
- **Request timeout.** Each action is a NATS round-trip to the backend, which
  then calls OpenConnector. The node sets 30s in code and can be overridden per
  deployment with `REQ_TIMEOUT` (seconds) in `.env.inflow`.
- **Verify the catalog.** The OpenConnector action names and input field keys are
  the natural Telegram Bot API names but were not verified against a live gateway;
  confirm with `GET /v1/actions?service=telegram` and adjust the plugin's
  `ocAction` bindings if your catalog differs. Required scopes are read live, so
  only names/keys need touching.
