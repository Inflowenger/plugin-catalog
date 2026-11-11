# Redis

> The Redis data types on the canvas — strings and counters, hashes, lists as queues, sets, sorted sets, streams and pub/sub, plus one raw-command node.

| | |
|---|---|
| **Repository** | https://github.com/Inflowenger/redis-plugin |
| **Node name** | `REDIS` |
| **Author** | [@FloMorphic](https://github.com/FloMorphic) |
| **SDK** | Node.js — [`@inflowenger/node-plugin-sdk`](https://github.com/Inflowenger/node-plugin-sdk) (`inflowv1`) |
| **Version** | v0.1.0 |
| **Categories** | `database` |
| **Runs on** | Any `inflowv1` host |
| **License** | See repository |
| **Status** | Review — 22 actions are implemented and the offline suites are green, but the plugin has not yet been run against a live Infra + Fractal. Read it, try it, report what breaks. |

## What it does

Puts Redis (and Valkey) on the canvas as its data types rather than as a
command line. Twenty-two nodes cover the keyspace — get, set, delete, scan,
expire, inspect — counters, hashes, lists used as queues, sets, sorted sets,
streams with consumer groups, and `PUBLISH`; a **Run command** node takes
anything else, modules included; and **Server info** returns a parsed `INFO`
with `DBSIZE`. Built on [`ioredis`](https://github.com/redis/ioredis), against
Redis 6+ or Valkey.

Each action carries a `class` — `keys`, `hash`, `list`, `set`, `sorted-set`,
`stream`, `pubsub`, `server` — so the canvas groups them instead of showing one
flat list of twenty-two.

Values are typed on the way in and out. **Writing**: a string goes as typed, a
number or boolean is rendered, an object or array is stored as JSON — so
`{{$.order}}` in a value field writes the whole upstream record. **Reading**: a
**Value decoding** field chooses `auto` (parse a plain JSON object or array,
leave everything else as text, so `007` stays `007`), `text` (never parse) or
`json` (insist). Every string input resolves `{{$.path}}` and `{{$this.id}}`
tokens against the flow scope first, in keys, values, patterns, channels and
members alike.

What it will not do is as deliberate as what it will. There is **no `KEYS`** —
listing is always `SCAN` with a cursor and a cap. There is **no `SUBSCRIBE`,
`PSUBSCRIBE` or `MONITOR`**: they take the connection out of request/reply mode,
and an action is one request and one reply, so they are refused with an
explanation rather than left hanging the node — publish from here, and read a
**stream** when the messages have to survive. A pattern delete needs the
confirmation checkbox and is never accepted for `*`. And it speaks to a single
server, primary or replica: **no cluster yet**, since a cluster answers `MOVED`
for a key that lives on another node.

## Actions

| Method | Title |
|--------|-------|
| `redis.key.get` | Get value |
| `redis.key.set` | Set value |
| `redis.key.delete` | Delete keys |
| `redis.key.scan` | Scan keys |
| `redis.key.expire` | Set or clear expiry |
| `redis.key.inspect` | Inspect keys |
| `redis.counter.increment` | Increment counter |
| `redis.hash.get` | Read hash |
| `redis.hash.set` | Write hash fields |
| `redis.list.push` | Push to list |
| `redis.list.pop` | Pop from list |
| `redis.list.range` | Read list range |
| `redis.set.add` | Add set members |
| `redis.set.remove` | Remove set members |
| `redis.set.members` | Read set members |
| `redis.zset.add` | Add scored members |
| `redis.zset.range` | Read sorted-set range |
| `redis.stream.add` | Append to stream |
| `redis.stream.read` | Read from stream |
| `redis.pubsub.publish` | Publish message |
| `redis.command` | Run command |
| `redis.server.info` | Server info |

Meta RPCs: `redis.meta.ping.check` (the settings form's **Test connection**
button and its submit validation) and `redis.meta.key.pick` (the ↻ keyspace
search behind every **Key** field).

## Connection

The plugin holds no server credentials. It declares a settings form, the
platform stores the filled-in form as a named settings profile, and ships the
values with every call as `body.settings` — so one running plugin serves many
Redis servers and rotating a password needs no redeploy.

| Key | Required | What it is |
|-----|----------|------------|
| `url` | no | `redis://user:password@host:6379/0`, or `rediss://` for TLS. Wins over the fields below; they fill in what it omits. |
| `host` / `port` | no | Default `localhost` and `6379`. |
| `db` | no | Logical database index (`SELECT`). 0 unless you partition by index. |
| `username` / `password` | no | A Redis 6+ ACL user, or a password-only server. |
| `tls` | no | Connect over TLS — implied by `rediss://`. |
| `tlsInsecure` | no | Accept a self-signed or mismatched certificate. Off by default. |

Keys are matched leniently — case, spaces, dashes and underscores are ignored
and the usual synonyms accepted (`uri`/`dsn` for `url`, `pass`/`secret` for
`password`, `dbIndex` for `db`, `ssl`/`secure` for `tls`) — so a hand-typed
profile works. A profile that is clearly for another plugin fails with the keys
it *did* contain. One connection is pooled per distinct profile, and no
credential is logged or stored.

## Install

```bash
git clone https://github.com/Inflowenger/redis-plugin
cd redis-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL

npm install && npm run build && npm start
```

Node 20+. `npm run dev` runs the TypeScript directly through `tsx` during
development. The SDK logs each subscribed subject on startup — that line is how
you tell "registered" from "silently misconfigured".

The plugin must already be provisioned in a space — that is where `PLUGIN_ID`,
`INFRA_CRED` and `INFRA_URL` come from. See
[docs/build-a-plugin.md § Provision](../docs/build-a-plugin.md#1-provision-the-plugin).

**From FloMorphic:** define the plugin under **Extensions**, then either
download the filled-in `.env.inflow` and run the commands above, or run the
generated one-liner — it clones, starts, and injects `./plugin.sh` for
`start / stop / restart / status / logs / update`. See
[docs/run-a-plugin.md § Start from FloMorphic](../docs/run-a-plugin.md#start-from-flomorphic).

## Notes

- **`REQ_TIMEOUT` has to clear the blocking reads.** The plugin raises its own
  NATS send deadline to 130s because `BLPOP` / `BRPOP` and a blocking stream
  read can legitimately sit there; the forms cap that at 60s. Override
  `REQ_TIMEOUT` (seconds) only upwards.
- **A blocking pop takes a connection of its own**, so it cannot stall the
  pooled one the other nodes share.
- **Some options need a newer server**, and each field says so in its own
  description: the `EXPIRE` conditions (`NX`/`XX`/`GT`/`LT`) are Redis 7+, and
  `ZRANGE` by score or reversed is 6.2+.
- **Deletes use `UNLINK`** rather than `DEL` where the server has it, so a large
  key is reclaimed off the main thread.
- **`src/redis/` imports nothing from the SDK**, so the Redis side is testable
  without NATS — the action suite runs the real handlers against a real server
  with only the `Job` faked (`REDIS_TEST_URL=redis://localhost:6399/9 npm test`).
  It works inside its own key prefix and deletes it afterwards, but it *does*
  write: point it at a scratch database, never a live one.
