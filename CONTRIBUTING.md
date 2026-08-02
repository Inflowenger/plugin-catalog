# Contributing

Two kinds of contribution: **listing a plugin** and **improving the docs**. Both
are PRs.

---

## Listing a plugin

Your plugin stays in your account or org — the catalog links to it, it does not
host it. You keep the issues, the releases, and the license.

### The bar

Deliberately low. The catalog is a map, not a gate.

- **It runs.** Tested against a real Infra + Fractal, not only compiled.
- **Public repository** with a `LICENSE` file.
- **A README** covering what it does, how to run it, and how the connection is
  supplied. See [docs/publishing.md § README](docs/publishing.md#readme).
- **A tagged release** whose version matches `PluginIntro.Version`.
- **No credentials in action forms** and none in logs or committed output —
  connections come from settings profiles.
- **Speaks `inflowv1`.** Any SDK, or none.

Experimental and half-finished are fine — mark `status` as `experimental` and say
so in the entry. What is not fine is a plugin that mishandles other people's
credentials.

### Steps

1. Copy [`templates/plugin-entry.md`](templates/plugin-entry.md) to
   `plugins/<slug>.md`. The slug is lowercase and hyphenated: `jira`,
   `google-sheets`.
2. Fill it in. Keep the description to one or two sentences of plain text.
3. Add the plugin to [`plugins/index.json`](plugins/index.json), matching
   [`index.schema.json`](plugins/index.schema.json).
4. Add one row to **both** tables — [`plugins/README.md`](plugins/README.md) and
   the root [README.md](README.md). Keep them alphabetical.
5. Open a PR titled `Add <name> plugin`.

Prefer not to write the files yourself? Open an
[Add a plugin issue](.github/ISSUE_TEMPLATE/add-plugin.yml) instead and someone
will prepare the entry.

### Keeping an entry current

Also a PR — new version, new actions, a moved repository, or a status change.

If a plugin stops being maintained, set `status` to `unmaintained` rather than
deleting the entry: people already running it need to be able to find out. Entries
are only removed when the repository disappears or the author asks.

---

## Trust and safety

**A listing is not an endorsement, an audit, or a security review.** Every plugin
is third-party code that runs as a process on your infrastructure, holding
credentials the platform hands it. Before running one you did not write:

- Read its source, or at least its settings handling and its network calls.
- Check its license.
- Give it its own space (NATS account) when the plugin is not yours, so its
  credentials only reach what that account permits.
- Prefer a tagged release over `main`.

Found a plugin behaving badly — leaking credentials, calling somewhere it should
not? Open an issue here **and** on the plugin's own repository. Genuine abuse gets
delisted.

---

## Improving the docs

Corrections and clarifications are welcome, especially:

- Anything in [`docs/`](docs/) that no longer matches the SDK. The SDK is the
  source of truth; when they disagree, this repo is wrong.
- Gotchas you hit while building a plugin that nobody wrote down.
- A worked example of something the docs only describe.

Two rules:

- **Verify against the SDK before documenting an API.** No signatures from
  memory. Check the version you are describing, and say which version if it
  matters.
- **Don't duplicate the SDK docs.** Link to them. This repo covers what a plugin
  *author* needs across the whole lifecycle — build, publish, list — and points at
  the SDK for the normative detail.

---

## Style

- Sentence case in headings. Plain language.
- Code that compiles. If you can't run it, mark it as a sketch.
- Relative links inside the repo, absolute links to the SDK and to plugins.
- One topic per PR — a listing and a docs rewrite are two PRs.
