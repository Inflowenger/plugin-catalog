# Agent skills

Instructions for AI coding agents building plugins against this catalog's
knowledge base. Each skill is a directory with a `SKILL.md` — the format Claude
Code, Codex and similar agents load — and it is the operational checklist, not
the reference: the reference is [`docs/`](../docs/) and the SDK's own docs.

| Skill | Use it for |
|-------|------------|
| [`oc-plugin`](oc-plugin/SKILL.md) | Building an **`-oc` plugin**: a node whose actions are executed by oomol **OpenConnector** through FloMorphic → Connect, so the plugin holds no provider credential. |

The SDKs ship their own language-level skill — the Go SDK's
[`skills/inflow-plugin`](https://github.com/Inflowenger/go-plugin-sdk/tree/main/skills/inflow-plugin)
covers `sdkv1`'s API, forms and job lifecycle. These are complementary: load the
SDK's skill for *how to write a plugin*, and `oc-plugin` for *what is different
about an OpenConnector-backed one*.

## Using one

Copy the directory into the plugin project you are building, where the agent
picks it up automatically:

```bash
mkdir -p .claude/skills
cp -r path/to/plugin-catalog/skills/oc-plugin .claude/skills/
```

Or point the agent at the raw file in this repo for a one-off. Either way, read
it before the first action, not after the first failing call — `oc-plugin`
exists because an agent that guesses OpenConnector action names and parameter
spellings produces a plugin that 400s on every node.

## Why `oc-plugin` exists

OpenConnector covers a thousand-plus services, and each one's actions and
parameter names are declared in a JSON Schema the API will hand you:

```bash
export OC_TOKEN='api-<key-from-the-panel>'   # exactly as the oomol web panel issues it
curl -s -H "authorization: $OC_TOKEN" \
  "https://connector.oomol.com/v1/actions?service=github"
```

With that response in context, an agent writes correct actions. Without it, it
invents field names that OpenConnector rejects outright, because every curated
input is declared `additionalProperties: false` with camelCase names. The skill
turns that into a procedure — get a token, pull the catalog, map it to canvas
actions — and ships
[`scripts/oc_catalog.py`](oc-plugin/scripts/oc_catalog.py) to keep the output
small enough to work with on a provider with 140+ actions.

## Adding a skill

Same bar as the docs ([CONTRIBUTING](../CONTRIBUTING.md)): verify against the
SDK or the upstream API before documenting it, link rather than duplicate, and
keep it a checklist an agent can follow top to bottom. Frontmatter needs `name`
and a `description` that says *when* to load the skill, since that line is all
an agent sees when deciding.
