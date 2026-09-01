# Gmail (OpenConnector)

> Send, search, read, and label Gmail messages from the Inflowenger canvas, as an
> account connected centrally in FloMorphic → Connect.

| | |
|---|---|
| **Repository** | https://github.com/FloMorphic/gmail-oc-plugin |
| **Node name** | `Gmail (OpenConnector)` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Node.js — [`@inflowenger/node-plugin-sdk`](https://www.npmjs.com/package/@inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.2.0 |
| **Categories** | `communication` |
| **Runs on** | **FloMorphic only ★** — needs FloMorphic's Connect / OpenConnector proxy (`flomorphic.svc.oc.*`); not portable to a bare `inflowv1` host. |
| **License** | See repository |
| **Status** | Active |

## What it does

Puts Gmail on the canvas as four actions — **Send email**, **Search messages**,
**Get message**, and **Modify labels** — without ever holding a Google
credential or making a Google API call. It is a *request builder*: a Gmail
account is connected **once, centrally**, in **FloMorphic → Connect** (via
OpenConnector / oomol), and this node just picks which connected account to act
as and asks the FloMorphic backend to run each action for it.

The backend is a generic proxy: it stores the OpenConnector token and forwards
requests over one NATS subject (`flomorphic.svc.oc.proxy`), injecting the auth
header. All Gmail knowledge — which accounts exist, what an action needs, which
OpenConnector endpoint to call — lives in the plugin. Before running, the plugin
reads each action's required scopes **live from oomol**
(`GET /v1/actions/gmail.<action>`) and checks the chosen account's scopes against
them, so an under-scoped account fails with a clear message and oomol stays the
authoritative gate. Inputs accept `{{$.path}}` tokens resolved against the flow
scope.

## Actions

| Method | Title |
|--------|-------|
| `gmail.send` | Send email |
| `gmail.search` | Search messages |
| `gmail.get` | Get message |
| `gmail.modify` | Modify labels |

Each canvas action maps to an OpenConnector action (`gmail.send_email`,
`gmail.fetch_emails`, `gmail.get_message`, `gmail.modify_message_labels`) that
the backend runs as the connected account.

## Connection

The plugin stores **no** Google credentials and reads no Google environment
variables — there is no credentials JSON, OAuth consent, alias, or token to
paste. In the node's **settings** form, press **Load accounts** to populate the
drop-down live from Connect, **pick** your connected Gmail account (or leave the
default), **Test account**, and **Save**; the platform stores this as a reusable
**settings profile** supplied on every call as `body.settings`. The optional
**Gateway** field pins to one Connect connection when several are configured
(hosted oomol vs self-hosted); leave it empty to span all. One connected account
can be shared by many nodes, and rotating it happens in the Connect page with no
plugin redeploy.

## Install

```bash
git clone https://github.com/FloMorphic/gmail-oc-plugin
cd gmail-oc-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install
npm run build
npm start
```

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

## Notes

- **Central auth, no Google token in the plugin.** The plugin never sees a Google
  token; the FloMorphic backend holds the OpenConnector credential and performs
  the call. The `-oc` suffix marks this as the OpenConnector-backed Gmail node —
  a future direct-OAuth `gmail` plugin could coexist.
- **Runtime credential.** The plugin publishes on `flomorphic.svc.oc.*`. The NATS
  token grants `flomorphic.svc.>`, so a normal strict, plugin-scoped runtime
  credential can reach these subjects — an open (multi) credential is not
  required.
- **Modify labels.** The OpenConnector action name and inputs for label
  modification were not in the confirmed catalog dump; verify against
  `GET /v1/actions?service=gmail` if the action errors. Required scopes are read
  live like the other actions.
