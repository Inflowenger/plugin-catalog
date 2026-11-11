# MinIO

> Buckets and objects on the canvas — one node for MinIO, AWS S3 and anything else that speaks S3.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/minio-plugin |
| **Node name** | `MINIO` |
| **Author** | [@Inflowenger](https://github.com/Inflowenger) |
| **SDK** | Go — [`go-plugin-sdk`](https://github.com/Inflowenger/go-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `storage` |
| **Runs on** | Any `inflowv1` host |
| **License** | Apache 2.0 |
| **Status** | Review — the twelve actions and the offline suite are complete, but the plugin has not yet been run against a live Infra + Fractal. Read it, try it, report what breaks. |

## What it does

Puts object storage where a flow can use it: list and inspect buckets, read and
write objects, copy or move them server-side, delete them under a guard, and
hand out presigned URLs so a browser or another service moves the bytes instead
of the flow.

It is built on [`minio-go`](https://github.com/minio/minio-go), which is an S3
client — so the same twelve actions drive a self-hosted **MinIO**, **AWS S3**,
**Ceph RGW**, **Cloudflare R2**, **Wasabi** and **Garage**, with no second
plugin and no second set of methods. What differs between those services is an
endpoint, a region and whether buckets are addressed in the path or the
hostname, and all three are fields on a settings profile: a flow written against
a MinIO in a lab runs against S3 in production by binding a different profile.

What it deliberately does not do is MinIO's **admin** API (`madmin`) — users,
policies, tiers, healing, server info. Those are MinIO-only, and leaving them
out is what lets one node serve both without lying about which half works
where.

Object storage has no undo, so the destructive actions ask: a prefix delete
needs a confirmation in the same form and can be dry-run first, removing a
bucket's contents needs the bucket's name typed again, and governance retention
is only bypassed when ticked. Reads into the flow are capped at 8 MiB, because
everything a node commits is held in memory and written to the platform's store
— past that, the plugin writes to a file, copies server-side, or presigns.

Any string input resolves double-brace `{{$.path}}` mustache tokens against the
flow scope, at any depth, so a bucket, a key, a prefix, a tag or an object's
whole content can come from an upstream node. A token the scope cannot supply
is left verbatim rather than resolved to nothing. On **Remove objects** one row
of *Keys* may be a token that resolves to a whole list, which is how a List
objects node's output is deleted without a loop.

## Actions

| Method | Title |
|--------|-------|
| `minio.bucket.list` | List buckets |
| `minio.bucket.create` | Create bucket |
| `minio.bucket.info` | Bucket info |
| `minio.bucket.remove` | Remove bucket |
| `minio.object.list` | List objects |
| `minio.object.stat` | Stat object |
| `minio.object.get` | Get object |
| `minio.object.put` | Put object |
| `minio.object.copy` | Copy object |
| `minio.object.remove` | Remove objects |
| `minio.object.presign` | Presigned URL |
| `minio.object.tag.set` | Set object tags |

Meta RPCs: `minio.meta.ping` (connects with the values in the open settings
dialog and reports which product answered, the buckets the keys can see and
whether the default bucket is there — backs the form's **Check** button and its
submit validation), `minio.meta.buckets` (the **List** button: turns a bucket
box into a drop-down) and `minio.meta.objects` (the **Browse** button: lists one
level of a bucket, using whatever is already in the box as the prefix).

## Connection

The plugin stores no endpoint and no credential. It declares a settings form and
the platform ships the bound profile with every call as `body.settings`, so one
running process serves many accounts and rotating a key needs no redeploy.

| Key | Required | What it is |
|-----|----------|------------|
| `endpoint` | yes | Host and port, no bucket: `minio.example.com:9000`, `s3.amazonaws.com`, `<account>.r2.cloudflarestorage.com`. A `http://` / `https://` prefix decides TLS and overrides `useSSL`. |
| `accessKey` / `secretKey` | no | Static credentials. Leave **both** empty to sign with the host's own identity — the `AWS_*`/`MINIO_*` environment variables, or an attached EC2/ECS/EKS IAM role. |
| `sessionToken` | no | For temporary STS / assume-role credentials. |
| `region` | no | Signing region. AWS needs the bucket's; MinIO usually needs none. |
| `useSSL` | no | HTTPS; on by default. |
| `pathStyle` | no | `endpoint/bucket` instead of `bucket.endpoint` — for a MinIO reached by IP or a single hostname. |
| `insecureSkipVerify` | no | Accept any TLS certificate; for an internal self-signed MinIO only. |
| `defaultBucket` | no | Pre-fills the node forms and gives the connection check something to prove access to. |

Keys are matched leniently — case, spaces, dashes and underscores ignored, usual
synonyms accepted — so a profile typed in AWS CLI spelling (`AWS_ACCESS_KEY_ID`)
or MinIO's (`MINIO_ACCESS_KEY`) is read as it stands. A key scoped to one bucket
is supported: the check reports "accepted but may not list buckets" instead of
failing, and only the pickers need `s3:ListAllMyBuckets`.

## Install

```bash
git clone https://github.com/Inflowenger/minio-plugin
cd minio-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL

go run .
```

Pure Go — no cgo, no C library, nothing to install beside it. `make build`
produces one static binary.

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either
download the filled-in `.env.inflow` and run the commands above, or run the
generated one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **Files are on the plugin's host, not the platform's.** *Write to file* on Get
  and *Upload file* on Put read and write wherever this process runs. That is
  the point of them — a large object never enters the flow's context — but it
  means a containerised plugin needs the path mounted.
- **A listing is data, not a file browser.** List objects returns at most 2000
  entries (200 by default) and reports `truncated` with a `startAfter` to
  continue from, because every entry is committed into the run's context.
- **Metadata is fixed at write time; tags are not.** Changing an object's user
  metadata means rewriting it — a Copy onto itself with *Replace user metadata*
  does exactly that. Tags can be set, merged and cleared in place, which is why
  lifecycle and replication rules filter on them.
- **Versioning is the service's, not the plugin's.** On a versioned bucket a
  plain delete leaves a delete marker; *Delete every version* is what frees
  space, and Stat, Get, Copy and the tag actions all take a version id.
- **`WithMetadata` on a listing is a MinIO extension.** AWS S3 ignores it and
  returns no tags or user metadata in a listing; use Stat object there.
- **Not every S3 implementation serves every call.** Bucket versioning, tagging
  and policies are declined by some gateways and older deployments; Bucket info
  reports those as notes and still succeeds rather than failing the node over an
  optional detail.
- **A presigned URL is a capability.** Anything holding it can do that one
  operation until it expires (7 days maximum, S3's own ceiling). It is committed
  into the flow's output like any other result, so treat the run's context as
  carrying a password in a link.
