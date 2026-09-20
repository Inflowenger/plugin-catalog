# Run a plugin

How a plugin process gets started — by hand in each of the three SDK languages,
and by the one-liner that FloMorphic generates from its **Extensions** menu. This
page is also the **rule** every listed plugin follows so that both paths work on
every repository the same way.

A plugin is an ordinary long-running process. Whatever the language, it needs
exactly three values — `PLUGIN_ID`, `INFRA_CRED`, `INFRA_URL` — in a `.env.inflow`
file (or the environment), outbound network access, and nothing else. Where the
three values come from is in
[build-a-plugin.md § Provision](build-a-plugin.md#1-provision-the-plugin).

---

## The rule

Every plugin repository, whichever SDK it uses:

1. **Has `.env.inflow.example` at the repository root** and gitignores
   `.env.inflow`. The plugin reads `.env.inflow` from the working directory
   (`INFLOW_ENV_FILE` overrides the path).
2. **Starts with the standard command for its language** — the table below —
   from the repository root, with no extra flags, arguments, or environment
   variables beyond the three above. Anything the plugin needs on top is
   optional and has a default.
3. **Has a `## Run` section in its README** that shows that command verbatim,
   plus the FloMorphic one-liner paragraph, in the shape of
   [the template](../templates/plugin-entry.md#install).
4. **Any other Markdown that tells someone how to start the plugin — `SKILL.md`,
   `MANUAL.md`, `docs/*.md`, an agent instruction file — links to README § Run
   instead of restating a different command.** One source of truth: a human, an
   AI coding agent, and the installer all start the plugin the same way.
5. **Logs the subject subscriptions at startup.** That line is how you — and
   `./plugin.sh status` — tell "registered" from "silently misconfigured".

A repository that follows this rule is what the installer expects; one that
doesn't will fail the one-liner and, for the catalog, fail the
[listing bar](../CONTRIBUTING.md#the-bar).

---

## Start by hand

Clone, copy the example env, fill in the three values, run. Only the last line
changes per language.

### Go

Requirements: Go 1.26+. A `main` package at the repository root.

```bash
git clone https://github.com/<you>/<repo>-plugin
cd <repo>-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
go run .
```

For a deployable binary, `go build -o plugin .` and run `./plugin` from the same
directory so `.env.inflow` is found.

### Node.js / TypeScript

Requirements: Node 18+ (check the entry — some plugins need 20+). A
`package.json` at the root with a `start` script, and a `build` script when the
source is TypeScript.

```bash
git clone https://github.com/<you>/<repo>-plugin
cd <repo>-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
npm install
npm run build        # only if the repo has a build script
npm start
```

### Python

Requirements: Python 3.11+. A `main.py` at the root and a `requirements.txt`
(a `pyproject.toml` is fine too — then `pip install .` replaces the requirements
line).

```bash
git clone https://github.com/<you>/<repo>-plugin
cd <repo>-plugin
cp .env.inflow.example .env.inflow   # PLUGIN_ID / INFRA_CRED / INFRA_URL
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python main.py
```

In all three cases the process must stay in the foreground — `Start()` only
wires the subscriptions. The startup log listing
`inflow.v1.<PLUGIN_ID>.*` subjects is the confirmation the plugin registered.

---

## Start from FloMorphic

FloMorphic — the product built on Inflowenger — exposes plugins as
**extensions**. The **Extensions** menu is where you define one and get
everything needed to run it, so you never touch Infra directly.

### 1. Define the plugin

**Extensions → New extension.** Give it a name and the repository URL (from the
[catalog](../plugins/), or your own). FloMorphic provisions the plugin in a
space, which is what creates its `PLUGIN_ID` and credential.

### 2. Get the `.env.inflow`

The extension page offers the filled-in **`.env.inflow`** for download — the
three values, already set. Drop it at the root of the cloned repository and
[start by hand](#start-by-hand), or skip to the one-liner, which writes it for
you.

### 3. Run the one-liner

The same page shows an **Install** command. It is generated per extension and
carries the plugin's identity, so copy it from the page rather than from this
doc — the shape is:

```bash
curl -fsSL "https://<your-flomorphic>/…/install.sh" | bash
```

> The command embeds a live credential. Treat it like a password: don't paste
> it into issues, chat, or a script you commit.

Run it on the machine that will host the plugin. It does, in order:

1. **Clones the repository** into the current directory (or `cd`s into it if it
   is already there and pulls the tagged release).
2. **Writes `.env.inflow`** at the repository root.
3. **Detects the language** from what is at the root — `go.mod`,
   `package.json`, or `main.py` + `requirements.txt` / `pyproject.toml` — and
   runs the [standard command](#start-by-hand) for it: installs dependencies,
   builds if there is a build step, and starts the process in the background.
4. **Injects `plugin.sh`** — the process helper below — next to `.env.inflow`,
   and prints the startup log so you see the subscriptions register.

Nothing in the repository is modified; `.env.inflow` and `plugin.sh` are both
in the standard `.gitignore` (and if yours doesn't list `plugin.sh` yet, add
it).

### 4. The process helper

`plugin.sh` is a small bash script that wraps the running process so you don't
need to remember the language's start command, a PID, or a log path:

| Command | What it does |
|---------|--------------|
| `./plugin.sh start` | Starts the plugin in the background with the language's standard command, using the `.env.inflow` beside it. No-op if already running. |
| `./plugin.sh stop` | Sends `SIGTERM`, waits, then `SIGKILL` if it doesn't exit. |
| `./plugin.sh restart` | `stop` then `start`. Use it after editing `.env.inflow` or pulling a new version. |
| `./plugin.sh status` | Running or not, PID, uptime, and whether the last startup logged its `inflow.v1.<PLUGIN_ID>.*` subscriptions. |
| `./plugin.sh logs` | Prints the log; `logs -f` follows it. Stdout and stderr go to `.inflow/plugin.log` next to the script. |
| `./plugin.sh update` | Pulls the latest tagged release, reinstalls dependencies, rebuilds, restarts. |

Under the hood it is only the standard command for the language plus `nohup`, a
PID file in `.inflow/`, and log redirection — so if you'd rather run the plugin
under systemd, Docker, or Kubernetes, read the script for the exact command it
uses and lift it into your unit or image. See
[publishing.md § Deploying](publishing.md#deploying).

---

## Where things live

```
<repo>-plugin/
├── .env.inflow.example     committed — the three keys, empty
├── .env.inflow             gitignored — written by you or by the one-liner
├── plugin.sh               gitignored — injected by the one-liner
├── .inflow/                gitignored — plugin.pid, plugin.log
├── go.mod | package.json | main.py + requirements.txt
└── README.md               § Run — the standard command, verbatim
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| Starts, then exits immediately | `.env.inflow` missing or not at the root. Run from the repository root, or set `INFLOW_ENV_FILE`. |
| Starts, no subscription log | Wrong `INFRA_URL`, or `INFRA_CRED` from a different space. Check `./plugin.sh logs` for the NATS connect error. |
| Registered, node not on the canvas | The plugin is provisioned in a space the workspace doesn't load. Check the extension's space in FloMorphic. |
| One-liner fails at "detect language" | The repository doesn't follow [the rule](#the-rule) — no `go.mod` / `package.json` / `main.py` at the root. |
| Node not found by `npm start` | Missing `start` script in `package.json`, or `build` was skipped for a TypeScript repo. |
