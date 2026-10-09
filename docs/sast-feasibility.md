# Joern, CodeQL & Semgrep — feasibility & requirements assessment

> Investigation of whether source-code analysis (SAST) can ship as a catalog
> plugin with **embedded dependencies** and a near-zero-knowledge install, the
> way [Nuclei](../plugins/nuclei.md) embeds its engine. Joern was the candidate;
> CodeQL was evaluated as the fallback.
>
> Status: **assessment** — no plugin committed. Not a build spec.
> Measured against **Joern 4.0.645** (2026-10-02), **CodeQL CLI 2.27.1**
> (2026-09-22), **Semgrep 1.179.0** (2026-10-02) and **Opengrep 1.30.0**
> (2026-09-07).

---

## TL;DR

- **The 1.8 GB number is misleading.** Joern's official distribution zip is
  1.80 GB, but that is the *CLI distribution* — every language frontend, every
  native AST generator for every OS/arch, and Ghidra. The **engine as a library
  is 143 MB of jars** for an eight-language embed (measured, §2.1). That is
  *smaller* than the nuclei plugin's own ~150–200 MB binary. Embedding Joern is
  not a size problem.
- **It is a runtime problem.** Joern is Scala 3 on the JVM. An embed is a **JVM
  embed** — the Go, Node and Python SDKs cannot hold it. Shipping it embedded
  means a **fourth SDK** (Scala/Java against `inflowv1`), which also breaks the
  catalog's one-line standard-command rule. Keeping the existing SDKs means
  *not* embedding: driving an external 1.8 GB install or the Docker image.
- **Joern's CLI cannot be embedded, only its engine.** Verified: a frontend
  (`javasrc2cpg`) builds a CPG from a bare Maven classpath, but `joern-scan`
  and `importCode` fail — the console layer requires an installation layout
  (`.installation_root` marker) and **shells out to frontend launcher scripts**,
  and it compiles Scala at runtime. An embed must call the engine's own API, as
  [`joernio/standalone-ext`](https://github.com/joernio/standalone-ext) does.
- **The real blocker is not packaging — it is that Joern is not a scanner.**
  Its stock query database holds **58 queries**: C 27, Android 10, PHP 9,
  Java 7, Kotlin 3, Ghidra 2 — and **nothing for Python, JavaScript/TypeScript,
  Go, C#, Ruby or Swift**. Joern's value is its query language. A node a user
  can run "knowing nothing about the plugin" is directly at odds with the tool.
- **CodeQL is out, and not for technical reasons.** Its licence forbids use on
  any codebase that is not OSI-licensed, and forbids generating a database
  "for or during automated analysis, CI or CD", unless the user holds a paid
  **GitHub Advanced Security** licence. A Venapce customer scanning their own
  private repositories on a schedule is exactly the prohibited case. It is also
  CLI-only — there is no library to embed.
- **Semgrep fills the slot, with one constraint: the rules, not the engine, are
  licensed.** Both engines are LGPL-2.1 — **Opengrep** even ships the single
  signed static binary (46.5 MB, glibc *and* musl) that Semgrep itself does not
  (Semgrep is a 71 MB wheel around a 257 MB core, needing Python ≥ 3.10). But
  `semgrep-rules` is under the **Semgrep Rules License v1.0** ("internal
  business purposes" only, no distribution, not "available to others as a
  service"), and even the pre-fork `opengrep-rules` carries **LGPL-2.1 +
  Commons Clause**. So the plugin ships the **engine and a rule loader, never
  the rules** — the same shape nuclei already uses for its template catalog
  (§7.2).
- **And Joern is not simply the weaker tool.** Semgrep OSS/Opengrep taint
  analysis is **intraprocedural**; cross-file taint is the **paid** Pro Engine.
  Joern does whole-program interprocedural dataflow under Apache-2.0 for free.
  Semgrep wins breadth, authoring cost and rule supply; Joern wins depth per
  dollar. Side-by-side table in §7.4.
- **Recommendation (§10):** do not make Joern the zero-knowledge SAST node. Fill
  that slot with **`SEMGREP`** on the Python SDK (or Opengrep on Go), engine
  embedded and rules fetched by the user, and keep Joern as a later, explicitly
  **expert** node — "run a CPG query / taint trace" — if and when a JVM SDK is
  justified on its own merits.

---

## 1. What Joern is, and how it is built

**Joern** (`joernio/joern`, **Apache-2.0**, Scala 3) turns source, bytecode or
binaries into a **Code Property Graph** (CPG) — AST + control flow + data flow in
one graph — stored in its own graph database (flatgraph since v4.0.0), and
queried with a **Scala-embedded DSL** (CPGQL). It is a program-analysis
workbench, not a rule scanner. Releases are cut **daily** and published both to
GitHub and to Maven Central (`io.joern`), which makes the library path
first-class rather than incidental.

Four layers matter for packaging, and they have very different properties:

| Layer | Artifacts | Embeddable? |
|-------|-----------|-------------|
| **Frontends** (`x2cpg` + one per language) | `javasrc2cpg`, `c2cpg`, `pysrc2cpg`, `jssrc2cpg`, … | Yes — some need a native helper (§3) |
| **Engine** | `semanticcpg`, `dataflowengineoss`, `codepropertygraph` | Yes, pure JVM |
| **Query database** | `querydb` | Yes — queries are compiled Scala |
| **Console / CLI** | `console`, `joern-cli` (the `joern` REPL, `joern-scan`, `importCode`, `--server`) | **No** — install-layout bound (§2.1) |

```
source ──▶ frontend (x2cpg) ──▶ cpg.bin ──▶ engine + querydb ──▶ Finding nodes
                                    ▲
                        console / REPL / --server  (needs an install, not a classpath)
```

---

## 2. The three ways to ship it — measured

### 2.1 Embedded as a library (the attractive option)

Joern publishes every module to Maven Central, and upstream documents the
pattern in [`joernio/standalone-ext`](https://github.com/joernio/standalone-ext)
("Minimal example of a standalone program that depends on Joern") — a `sbt
assembly` fat jar depending on `io.joern::joern-cli`, `x2cpg`, `semanticcpg` and
one frontend.

**Measured footprint** (coursier resolve, v4.0.645, jar bytes on disk):

| Embed | Jars | Size |
|-------|-----:|-----:|
| `joern-cli` (engine + console, **no frontends**) | 92 | **111.1 MB** |
| `querydb` (pulls the engine) | 89 | 110.8 MB |
| Engine + 8 frontends: Java · Python · JS/TS · C/C++ · PHP · Go · C# + querydb | 134 | **142.7 MB** |
| `+ rubysrc2cpg` | | +43.6 MB (bundles a JRuby AST generator with native `libprism`) |
| `+ kotlin2cpg` | | +85.2 MB (`kotlin-compiler-embeddable`) |
| `+ ghidra2cpg` (binaries) | | **+243.7 MB** |

Reproduce:

```bash
cs fetch --classpath \
  -r https://repo.gradle.org/gradle/libs-releases \
  io.joern::joern-cli:4.0.645 io.joern::querydb:4.0.645 \
  io.joern::javasrc2cpg:4.0.645 io.joern::pysrc2cpg:4.0.645 \
  io.joern::jssrc2cpg:4.0.645 io.joern::c2cpg:4.0.645 \
  io.joern::php2cpg:4.0.645 io.joern::gosrc2cpg:4.0.645 \
  io.joern::csharpsrc2cpg:4.0.645
```

So **143 MB, not 1.8 GB**. The distribution zip is large because it carries all
~14 frontends, the native AST generators for all six OS/arch combinations, and
Ghidra. A plugin picks the frontends it wants and pays only for those.

Two findings from actually running it (JDK 25, bare classpath, no Joern
installed anywhere):

- **The frontends work standalone.** `java -cp <classpath>
  io.joern.javasrc2cpg.Main --output vuln.cpg testsrc` produced a valid CPG.
  No install, no `JOERN_HOME`, no 1.8 GB zip.
- **The console layer does not.** `io.joern.joerncli.JoernScan` fails with
  `unable to find root installation directory … tried to find marker file
  '.installation_root'`. Creating that marker gets one step further, then:
  `CPG generator does not exist at: <cwd>/javasrc2cpg` — the console **shells
  out to frontend launcher scripts** in the install directory, and compiles its
  work as a Scala script at runtime (`replpp.scripting`). This is why
  `standalone-ext` keeps an `.installation_root` file in its repo root.

**Consequence:** an embedded plugin cannot wrap Joern's CLI. It must call the
engine API itself — build the CPG with the frontend class, run queries from
`querydb` (or its own compiled queries) against it, and read `cpg.finding`.
That is a genuine Scala development effort, not a subprocess wrapper. The
upside is that it is also the *better* plugin: findings come back as objects to
turn into frames, with no table-scraping.

### 2.2 External install, driven over the CPGQL server

Joern ships a server mode — `joern --server [--server-host H --server-port P]
[--server-auth-username U --server-auth-password P]` — with `POST /query`,
`POST /query-sync`, `GET /result/{uuid}` and a `ws://host:8080/connect`
websocket that pushes completion UUIDs instead of polling. Official clients
exist for **Python** (`cpgqls-client-python`) and **JavaScript**
(`cpgqls-client-js`); **there is no Go client**.

This keeps the plugin on an existing SDK — Node or Python — at the cost of the
host needing **JDK 21** plus the **1.8 GB** install. The plugin can bootstrap
both (download the platform zip, and a Temurin JRE, on a meta RPC with
progress), which is precisely the pattern [Playwright](../plugins/playwright.md)
already uses for browser engines and [Nuclei](../plugins/nuclei.md) for its
template catalog. "Minimum knowledge" is reachable this way — but through a
bootstrap action, not through embedding.

One hard caveat, upstream's own words: *"the server exclusively implements
remote access to an interpreter, it does not implement sandboxing."* A node that
accepts a CPGQL string is **arbitrary code execution on the plugin host**, by
design — the same class of exposure as nuclei's *allow code templates* gate and
Playwright's *Evaluate JavaScript* note, and it must be gated and documented the
same way.

### 2.3 The Docker image

`ghcr.io/joernio/joern:master` (and `joern-alma8` for CPUs without SSE4.2) runs
the CLI or `joern --server` directly. Lowest effort, but it puts a Docker daemon
between the user and the plugin, which no catalog plugin currently requires and
which the `./plugin.sh` install path does not cover.

---

## 3. Per-frontend dependency tiers

Measured from the published jars. This decides which languages an embedded
plugin can offer with *nothing* extra on the host:

| Tier | Languages | What it needs |
|------|-----------|---------------|
| **1 — pure JVM, zero external deps** | **Java** (javaparser) · **C/C++** (Eclipse CDT) · **Python** · **Kotlin** · **JVM bytecode** (jimple2cpg) · **Ruby** (bundles its own JRuby AST generator, +43.6 MB) | Nothing. `gcc`/`g++` optional for C/C++ system-header discovery |
| **2 — needs a native helper binary** | **JS/TS** (`astgen`) · **Go** (`goastgen`) · **C#** (`DotNetAstGen`) · **Swift** (`SwiftAstGen`) | A per-OS/arch binary shipped alongside. `x2cpg`'s `AstGenRunner` locates it relative to the jar's code source, with an env-var override (e.g. `ASTGEN_BIN`) — so shipping them in the plugin repo is clean |
| **3 — needs an external interpreter or toolkit** | **PHP** (`php-cli` on `PATH`) · **Binaries** (Ghidra, +243.7 MB) | Host-installed dependency |
| — | **Java/Kotlin build-aware analysis** | `gradle-tooling-api` is resolved from `repo.gradle.org`, not Maven Central — the build must add that resolver |

Tier 1 alone covers Java, C/C++, Python, Kotlin, JVM bytecode and Ruby with a
single self-contained artifact. That is a defensible v1 language set.

---

## 4. The SDK problem

The catalog's install rule is that every plugin starts with one standard command
for its language ([run-a-plugin.md](run-a-plugin.md)). Joern's two shapes land
on opposite sides of it:

| Shape | SDK | Standard command | Embedded? | Cost |
|-------|-----|------------------|-----------|------|
| Scala/Java plugin, engine as a library | **none exists** — hand-rolled `inflowv1` over NATS (six subjects, [sdks.md](sdks.md#writing-an-sdk-in-another-language)) | new: `java -jar` / `sbt run` | **Yes** (143 MB) | A fourth SDK + a new catalog rule |
| Node (or Python) plugin, drives `joern --server` | Node SDK, `cpgqls-client-js` | `npm install && npm run build && npm start` | No — JDK 21 + 1.8 GB install, bootstrapped | Fits today's rules |

A JVM SDK is not unreasonable on its own — `inflowv1` is a plain NATS protocol
and the surface is six subjects — and it would open Java/Kotlin/Scala plugins
generally. But it is a platform decision, and it should be taken for its own
reasons, not to make one node 1.6 GB smaller. Self-contained JVM packaging
(`jlink`/`jpackage`) could even remove the JDK requirement for the user; GraalVM
`native-image` is not realistic for Scala 3 plus this much reflection.

---

## 5. Why "minimum knowledge" does not fit Joern

This is the finding that decides the study.

- **The stock query database is 58 queries** (`querydb.json`, a release asset):
  C 27 · Android 10 · PHP 9 · Java 7 · Kotlin 3 · Ghidra 2. Tags are shallow —
  `default` (32), `badfn` (11), `android` (13), `metrics` (6), the rest in ones
  and twos. By comparison the nuclei node selects from 13,000+ templates.
- **Whole languages have no queries at all** — Python, JS/TS, Go, C#, Ruby,
  Swift. Joern can *parse* them; it ships nothing to *find* in them. A typical
  modern service repo would come back empty.
- **`joern-scan`'s filters are the right shape** — `--names`, `--tags`,
  `--language`, `--depth`, `--list-query-names` map cleanly onto a nuclei-style
  filter form — but there is almost nothing behind them to filter.
- **The value is the query language.** A useful `JOERN` node is "give me the
  call sites reaching this sink", "trace taint from this parameter", "export the
  CPG" — which asks the *user* to know CPGQL, i.e. Scala. That is the opposite
  of a node someone runs knowing nothing about it.
- **No SARIF/JSON findings format.** Findings are `Finding` nodes in the CPG;
  the plugin would define the frame shape itself (fine — but it is work, and it
  is ours to maintain).

Joern remains a strong fit for an *investigation* node — the "pull the thread"
half of Venapce, reached after something else flagged a repo. It is a poor fit
for the "scan everything nightly" half.

---

## 6. CodeQL — assessed, and ruled out

**The licence makes it unusable for this product.** The CodeQL CLI is not open
source. Its terms permit academic research, demonstration, and analysis of an
**Open Source Codebase** — defined as "a codebase that is released under an
OSI-approved License" — and otherwise forbid using it

> "in connection with any codebase that is not an Open Source Codebase (e.g.,
> code in a private repo in GitHub)"

and forbid using it

> "To otherwise or in any other context generate any CodeQL database for or
> during automated analysis, CI or CD"

with the restrictions lifted only "if your use of the Software is under a paid
customer license for GitHub Advanced Security". A Venapce customer scanning
their own private repositories on a schedule is both prohibited cases at once.
A plugin whose lawful operation depends on each user holding a per-committer
GHAS licence is not a catalog plugin; at most it is a thin client of **GitHub's
code-scanning API**, which [GitHub (OpenConnector)](../plugins/github-oc.md)
already exposes (`GET /repos/{o}/{r}/code-scanning/alerts`) — the analysis then
runs on GitHub's side, under the customer's own licence. **That path is already
shipped, and it is the right one.**

For completeness, the technical picture if the licence ever changed:

| | CodeQL |
|---|---|
| **Embeddable** | **No.** CLI only; no library API, no server mode. Everything is `codeql database create` / `database analyze` subprocesses |
| **Size** | CLI 416 MB (linux64 zip); CLI + precompiled query packs 692 MB (`.tar.gz`) / 557 MB (`.tar.zst`); per-language bundles 97–279 MB |
| **Self-contained** | Largely — the bundle ships its own tooling. Not glibc-free: incompatible with musl/Alpine |
| **DB creation** | `--build-mode none` now covers all interpreted languages plus C/C++, C#, Java and Rust (Java from CLI 2.16.5, C# from 2.17.6). Mixed Java/Kotlin still needs a working build |
| **Output** | SARIF (`--format=sarif-latest`) — a real advantage over Joern |
| **Rules** | Mature, maintained, broad CWE coverage per language — exactly what Joern lacks |

So the two tools fail in opposite places: **Joern is installable but not
usable out of the box; CodeQL is usable out of the box but not licensable.**

---

## 7. Semgrep / Opengrep — the slot filler, and its one real constraint

### 7.1 How it actually ships

**Semgrep** (`semgrep/semgrep`, **LGPL-2.1**, OCaml core + Python CLI, 1.179.0
released 2026-10-02) is *not* a single static binary. It ships as **PyPI
platform wheels** — 70.8 MB for linux x86_64 — which unpack to a **257 MB**
native `semgrep-core` plus bundled shared libraries, and it needs **Python
≥ 3.10**. The natural shape is therefore a **Python SDK** plugin, where
`pip install -r requirements.txt` — already the catalog's Python standard
command — genuinely does embed the engine in the venv. One step, no JVM.

**Opengrep** (`opengrep/opengrep`, **LGPL-2.1**, 3.1k stars, pushed daily) is
the consortium fork of the Semgrep OSS engine, and it ships what the brief asked
for: **one signed static binary**, `opengrep_manylinux_x86` at **46.5 MB**, with
**musllinux** builds as well as glibc (Alpine works — CodeQL explicitly does
not), each with a cosign `.sig`/`.cert`. A **Go SDK** plugin can ship or fetch
that binary and exec it, which is the closest thing in this whole study to
"embedded dependencies, seamless".

| | Semgrep | Opengrep |
|---|---|---|
| Engine licence | LGPL-2.1 | LGPL-2.1 |
| Artifact | PyPI wheel, 70.8 MB → 257 MB core | Single static binary, 46.5 MB |
| Runtime prereq | Python ≥ 3.10 | none |
| musl / Alpine | no | **yes** |
| Signed releases | — | cosign |
| Natural SDK | **Python** | **Go** |

### 7.2 The rules are the licensed asset — not the engine

This is the constraint, and it is the thing to decide before writing code.

- **`semgrep/semgrep-rules`** — 2,094 rule files across 28 language/area trees
  (Terraform 364 · Python 337 · generic 257 · JS 173 · AI 131 · Java 124 ·
  Ruby 94 · YAML 94 · Go 78 · PHP 65 · C# 52 · Solidity 50 · …) — is **not**
  LGPL. It is under the **Semgrep Rules License v1.0**: *"You may use the rules
  only for your own internal business purposes"*, and it *"does not allow you to
  distribute the rules, or to make them available to others as a service."*
- The pre-change snapshot (**`opengrep/opengrep-rules`**, forked 2024-12-13) is
  **LGPL-2.1 + Commons Clause** — no right to *"Sell"*, defined as providing to
  third parties for a fee *"a product or service whose value derives, entirely
  or substantially, from the functionality of the Software."* It is also stale
  (last push 2025-11-28).

So **neither large ruleset can be bundled into a commercial Venapce and sold.**
That shapes the plugin; it does not block it.

| Rule source | Licence | Bundle in the plugin? |
|---|---|---|
| Semgrep Registry / `semgrep-rules` | Semgrep Rules License v1.0 | **No** — user's own internal use, fetched by the user on their own host |
| `opengrep/opengrep-rules` | LGPL-2.1 + **Commons Clause** | **No** for a paid product |
| `0xdea/semgrep-rules` (C/C++) | **MIT** | Yes |
| `elttam/semgrep-rules` | **MIT** | Yes |
| `dgryski/semgrep-go` | **MIT** | Yes |
| `trailofbits/semgrep-rules` | AGPL-3.0 | Only with the AGPL consequences understood |
| Rules we write | ours | Yes |

**The design rule that follows:** the plugin ships the **engine and a rule
*loader*, never the rules.** A `semgrep.rules.fetch` action the user runs on
their own host, plus a `rulesDir` / `config` setting pointing at whatever they
are entitled to use. That is exactly the shape
[Nuclei](../plugins/nuclei.md) already documents — *"run Update Templates once,
or point `templatesDir` at an existing checkout"* — and it extends the
catalog's "a plugin holds no user credentials" principle to licensed content.

One question for a lawyer rather than this document: a plugin the **customer**
runs on their **own** host against their **own** code is a far more defensible
reading of "internal business purposes" than Venapce running scans centrally and
selling the result. The catalog's architecture already puts every plugin on the
user's host — for this node, keep it there deliberately.

### 7.3 Depth: where Joern is not the loser

Semgrep OSS and Opengrep do taint analysis **intraprocedurally** — within one
function, in one file. **Cross-function and cross-file (interfile) taint is the
paid Pro Engine**, available for C, C++, C#, Go, Java, JS/TS, Kotlin and Python.
Published comparisons put cross-file flows at roughly a quarter to a third of
taint findings, so the gap is real.

**Joern does whole-program interprocedural dataflow under Apache-2.0, for
free.** On depth-per-dollar Joern wins outright. On breadth, authoring cost and
rule supply, Semgrep wins outright. They fail in different directions, which is
why §10 keeps both.

### 7.4 Side by side

| | **Semgrep / Opengrep** | **Joern** |
|---|---|---|
| **Model** | Pattern match on syntax (tree-sitter per language) + dataflow | Code Property Graph (AST + CFG + data dependence) in a graph DB |
| **Query language** | YAML patterns that *look like the code* | Scala DSL (CPGQL) over a graph |
| **Who can author** | Any developer, in minutes | Program-analysis expertise |
| **Dataflow reach** | Intraprocedural free; **interfile is paid** | **Whole-program interprocedural, free** |
| **Rules shipped** | 2,094 rule files, 28 language/area trees — **licence-encumbered** | **58 queries**, 6 languages — Apache-2.0 |
| **Language breadth** | ~30, incl. IaC/config (Terraform, Dockerfile, YAML) | ~14 source languages, **plus binaries** (Ghidra) |
| **Pre-pass** | None — streams file by file | **Must build a CPG first** (minutes, GBs of heap, `cpg.bin` on disk) |
| **Run cost** | Seconds to minutes per repo | Minutes+ per repo, memory-hungry |
| **Output** | **SARIF / JSON** native, severity + CWE/OWASP metadata | `Finding` nodes; frame shape is ours to define |
| **Install** | `pip install` (71 MB wheel) or one 46.5 MB binary | 143 MB of jars + a JVM, or 1.8 GB + JDK 21 |
| **SDK available** | **Python** / **Go** — both exist | **none** — needs a JVM SDK |
| **Licence risk** | Engine clean; **rules are the problem** | **None** — Apache-2.0 throughout |
| **Best at** | Known bug classes across many repos, nightly, IaC included | One codebase, deeply: reachability, taint traces, call paths, slicing, binaries |
| **Venapce fit** | The **scanner** — findings frames on a schedule | The **investigation** node — reached from a finding |

---

## 8. Requirements & dependency matrix

| Requirement | Needed by | Notes |
|-------------|-----------|-------|
| JVM at runtime (JDK 21 per upstream; JDK 25 worked in test) | Any Joern shape | Removable only via `jlink`/`jpackage` self-contained packaging |
| 143 MB of jars (8 languages) | Embedded shape | Measured; vs ~150–200 MB for the nuclei plugin binary |
| 1.8 GB platform zip + JDK | External/server shape | Bootstrappable by a meta RPC, Playwright-style |
| Native AST generator per OS/arch | JS/TS, Go, C#, Swift | `ASTGEN_BIN`-style env override makes this tidy |
| `php-cli` on `PATH` | PHP frontend | Host dependency |
| `repo.gradle.org` resolver | Java/Kotlin frontends | `gradle-tooling-api` is not on Maven Central |
| A JVM `inflowv1` SDK | Embedded shape only | Does not exist; six subjects to implement |
| Source checkout on the plugin host | Both | A `GIT_CLONE`-style step, or reuse the GitHub plugin to fetch |
| Heap headroom (`-J-Xmx`) + disk for `cpg.bin` | Both | Large repos are memory-hungry; needs a cap and a timeout |
| Python ≥ 3.10 | **Semgrep** | Wheel bundles a 257 MB native core; no JVM |
| Nothing | **Opengrep** | One 46.5 MB signed static binary, glibc **or** musl |
| A rule source the user is entitled to use | **Semgrep/Opengrep** | The plugin must not bundle the registry rules (§7.2) |
| Paid GitHub Advanced Security licence per user | **CodeQL** | The reason CodeQL is out |

---

## 9. Risks & open questions

- **Arbitrary code execution is intrinsic.** Any node that takes a CPGQL string
  runs Scala on the plugin host, unsandboxed by upstream's own admission. Either
  restrict the node to a precompiled query set (safe, and it needs no Scala
  compiler at runtime) or gate free-form queries behind an explicit setting,
  defaulting off — the nuclei *allow code templates* precedent.
- **Daily releases, no LTS.** 1,077 published versions of `joern-cli_3`. Pinning
  policy and upgrade cadence need a decision; the library path means version
  skew between frontends and engine is a real failure mode.
- **Resource ceilings.** CPG construction on a large monorepo can exhaust heap
  and disk. Needs a measured ceiling, a timeout, and an `OnSignal` abort — the
  nuclei plugin already sets that pattern.
- **Where does the code come from?** Neither tool helps here. Cloning private
  repos means a credential on the plugin host, or a handoff from the GitHub
  plugin. Decide before designing actions.
- **Unmeasured:** fat-jar size after `sbt assembly` dedup (expected below the
  143 MB classpath sum), CPG build time and peak RSS on a real repo, and whether
  JDK 25 is safe for sustained use when upstream tests only JDK 21.
- **Query coverage is ours to fix if we pick Joern.** Writing and maintaining
  CPGQL queries for the languages Venapce cares about becomes a standing cost.
  That is a research programme, not a plugin task.

---

## 10. Recommendation

1. **Do not build Joern as the zero-knowledge SAST node.** It can be embedded
   far more cheaply than the 1.8 GB distribution suggests — 143 MB of jars, and
   the frontends verifiably run from a bare classpath — but it ships 58 queries
   and none for most modern languages. The packaging question was answerable;
   the product question is the one that fails.
2. **Rule CodeQL out on licence, not on merit.** Its terms forbid private-code
   and CI/CD use without paid GitHub Advanced Security. Where a customer *does*
   hold GHAS, Venapce already reads the results through
   [GitHub (OpenConnector)](../plugins/github-oc.md)'s code-scanning alerts —
   analysis stays on GitHub's side, under the customer's own licence. Keep that
   path; do not ship a CodeQL plugin.
3. **Fill the slot with `SEMGREP` instead — engine embedded, rules not.** It is
   what the brief actually described: no JVM, no 1.8 GB, rule selection by
   ruleset/severity/language (a near-exact analogue of the nuclei node), and
   SARIF/JSON output that maps straight onto **findings** frames. Two open
   choices, both small:
   - **Which engine.** **Semgrep** on the **Python SDK** — `pip install -r
     requirements.txt` is already the standard command, so the 257 MB core
     genuinely lands in the venv — or **Opengrep** on the **Go SDK**, one
     signed 46.5 MB static binary, glibc or musl, no Python. Opengrep is the
     better fit for "embedded and seamless"; Semgrep is the better fit for
     staying close to upstream and the registry.
   - **Where rules come from.** Ship a `rules.fetch` action and a `rulesDir` /
     `config` setting; ship **no** registry rules in the repo (§7.2). Seed with
     the MIT sets (`0xdea`, `elttam`, `dgryski/semgrep-go`) and our own rules,
     and let the user point at whatever else they are entitled to use. Get the
     "internal business purposes" reading confirmed by a lawyer for the
     customer-hosted case before the node is sold, not after.
4. **Keep Joern on the roadmap as an expert node, not a scanner.** If it ships,
   it ships as `JOERN` — "build a CPG, run a query, trace a flow, export the
   graph" — explicitly labelled expert-level, with a precompiled query set by
   default and free-form CPGQL behind a gate that defaults off. Reach it from a
   finding, not from a schedule.
5. **Decide a JVM SDK on its own merits.** A Scala/Java `inflowv1` SDK is the
   only way to ship Joern genuinely embedded, and it would open the whole JVM
   ecosystem to the catalog. That is a platform call worth making deliberately —
   not a side effect of one node. Until it exists, a Joern plugin is a **Node
   SDK** plugin that bootstraps a JDK and the distribution zip on first run and
   talks to `joern --server`, Playwright-style.
