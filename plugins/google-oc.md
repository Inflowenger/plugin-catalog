# Google Workspace (OpenConnector)

> Sheets, Docs, Drive, and Calendar on the Inflowenger canvas, as a Google
> account connected centrally in FloMorphic → Connect.

| | |
|---|---|
| **Repository** | https://github.com/FloMorphic/google-office-oc-plugin |
| **Node name** | `Google Workspace (OpenConnector)` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Go — [`github.com/Inflowenger/go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) `sdkv1` (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `storage`, `utility` |
| **Runs on** | **FloMorphic only ★** — needs FloMorphic's Connect / OpenConnector proxy (`flomorphic.svc.oc.*`); not portable to a bare `inflowv1` host. |
| **License** | See repository |
| **Status** | Beta |

## What it does

Puts four Google Workspace products on the canvas from one plugin binary —
**Sheets**, **Docs**, **Drive**, and **Calendar** — as **30 actions**, one per
concrete operation, without ever holding a Google credential or making a Google
API call. It is a *request builder*: a Google account is connected **once,
centrally**, in **FloMorphic → Connect** (via OpenConnector / oomol, which grants
the Workspace scopes), and each node just picks which connected account to act
as and asks the FloMorphic backend to run the matching OpenConnector action for
it.

The backend is a generic proxy: it stores the OpenConnector token and forwards
requests over one NATS subject (`flomorphic.svc.oc.proxy`), injecting the auth
header. Every action carries `Tags["class"]` — `sheets`, `docs`, `drive`, or
`calendar` — so the canvas palette groups each product's ports together even
though they ship in one plugin. Inputs accept `{{$.path}}` tokens resolved
against the flow scope, and dependent-field pickers let you choose files,
folders, and sheet tabs from a drop-down populated live from the account.

## Actions

**Sheets** (5)

| Method | Title |
|--------|-------|
| `googlesheets.create_spreadsheet` | Create spreadsheet |
| `googlesheets.add_sheet` | Add sheet |
| `googlesheets.get_values` | Get values |
| `googlesheets.clear_values` | Clear values |
| `googlesheets.aggregate_column_data` | Aggregate column |

**Docs** (5)

| Method | Title |
|--------|-------|
| `googledocs.create_document` | Create document |
| `googledocs.get_document_plaintext` | Get document text |
| `googledocs.insert_text_action` | Insert text |
| `googledocs.copy_document` | Copy document |
| `googledocs.export_document_as_pdf` | Export as PDF |

**Drive** (9)

| Method | Title |
|--------|-------|
| `googledrive.files.list` | List files |
| `googledrive.files.get` | Get file |
| `googledrive.create_folder` | Create folder |
| `googledrive.files.copy` | Copy file |
| `googledrive.move_file` | Move file |
| `googledrive.rename_file` | Rename file |
| `googledrive.delete_file` | Delete file |
| `googledrive.share_file` | Share file |
| `googledrive.export_file` | Export file |

**Calendar** (11)

| Method | Title |
|--------|-------|
| `googlecalendar.list_calendars` | List calendars |
| `googlecalendar.list_events` | List events |
| `googlecalendar.get_event` | Get event |
| `googlecalendar.create_event` | Create event |
| `googlecalendar.quick_add_event` | Quick add event |
| `googlecalendar.patch_event` | Update event |
| `googlecalendar.delete_event` | Delete event |
| `googlecalendar.move_event` | Move event |
| `googlecalendar.find_free_slots` | Find free/busy |
| `googlecalendar.add_attendee` | Add attendee |
| `googlecalendar.remove_attendee` | Remove attendee |

Each canvas action maps to an OpenConnector action under the `googlesheets`,
`googledocs`, `googledrive`, or `googlecalendar` service that the backend runs as
the connected account. The gateway stays the authoritative gate: each action
declares its own `requiredScopes`, and an under-scoped account fails with the
gateway's error surfaced on the node.

## Connection

The plugin stores **no** Google credentials and reads no Google environment
variables — there is no credentials JSON, OAuth consent, alias, or token to
paste. In the node's **settings** form, press **Load accounts** to populate the
drop-down live from Connect, **pick** your connected Google account (or leave
the default), **Test account**, and **Save**; the platform stores this as a
reusable **settings profile** supplied on every call as `body.settings`. The
optional **Gateway** field pins to one Connect connection when several are
configured (hosted oomol vs self-hosted); leave it empty to span all. One
connected account can be shared by every node across all four products, and
rotating it happens in the Connect page with no plugin redeploy.

## Install

```bash
git clone https://github.com/FloMorphic/google-office-oc-plugin
cd google-office-oc-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go mod tidy
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

- **Central auth, no Google token in the plugin.** The plugin never sees a Google
  token; the FloMorphic backend holds the OpenConnector credential and performs
  the call. The `-oc` suffix marks this as the OpenConnector-backed Google node —
  a future direct-OAuth `google` plugin could coexist.
- **Runtime credential.** The plugin publishes on `flomorphic.svc.oc.*`, so
  `INFRA_CRED` must be an **OPEN (multi)** runtime credential (FloMorphic →
  Settings → MultiPlugin Credential, or the installer's multi option). A strict,
  plugin-scoped credential cannot publish on `flomorphic.>` and every action
  fails with a NATS no-responders/timeout.
- **Request timeout.** Every action is a NATS round-trip to the backend, which
  then calls OpenConnector; the node sets **30s** in code (above the SDK's 5s
  default). Override per deployment with `REQ_TIMEOUT=<seconds>` in
  `.env.inflow`. A bare `TIMEOUT` on the node means the deadline was exceeded —
  raise `REQ_TIMEOUT`.
- **Beta.** Docs, Drive, and Calendar are feature-complete; Sheets is the
  thinnest surface so far and the action set is still growing.
