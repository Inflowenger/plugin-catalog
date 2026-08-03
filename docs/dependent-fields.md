# Dependent fields — forms that fetch their own data

Most integrations have a field a user cannot type from memory. A Jira assignee is
an `accountId` like `5b10a2844c20165700ede21g`. A project is a key the user has
to go and look up. An issue type is only valid for one project. A transition only
exists on one issue, right now.

A static JSON Schema cannot express any of that, because none of it is knowable
when the plugin is compiled — it depends on the settings profile the node is
bound to, and on what the user picked in the field above.

The platform's answer is the **meta function** plus a **form button**: a control
in your form carries a button, the button calls one of your plugin's live RPCs
with the form's current contents and the bound settings profile, and what comes
back is patched into the form.

This document is the contract for that: the exact call, the exact answer shape,
what works today, and what does not.

> Read [concepts.md § Actions vs. meta RPCs](concepts.md#actions-vs-meta-rpcs)
> first if you have not — this doc assumes you know what a meta RPC is.

---

## The three pieces

| Piece | Where it lives | What it is |
|---|---|---|
| A **meta function** | Your plugin (`p.AddMeta`) | A synchronous RPC on `inflow.v1.<PLUGIN_ID>.<method>` that answers with live data. |
| An **`x-inflow-ui` button** | Your action's `Jsonui` | A button attached to one control, naming the function to call. |
| The **`pluginFn` host action** | The platform | The generic bridge that makes the call and applies the answer. You do not ship it. |

The host only knows how to *reach* a plugin function; it never knows what your
functions are. That is why this stays generic — no plugin ever needs the platform
to ship bespoke UI for it.

---

## 1. Mark up the control

```jsonc
{
  "type": "Control",
  "scope": "#/properties/projectKey",
  "x-inflow-ui": {
    "action": { "name": "pluginFn", "fn": "jira.meta.projects.resolve" },
    "button": { "position": "append", "label": "Find", "icon": "↻" }
  }
}
```

- **`action.name`** must be `pluginFn`. It is the only action the host registers,
  and it is all you need. An unknown name is inert — the button renders and does
  nothing.
- **`action.fn`** is your meta method name, exactly as passed to `AddMeta`.
- **`action.target`** (optional) — the data path the answer is written to when the
  answer is not an object. Defaults to the path of the control the button sits on.
- **`action.body`** (optional) — a static object merged into the request, for
  telling one shared meta function which caller it is serving.
- **`button.position`** — `append` | `prepend` | `above` | `below`, relative to
  the control that would have rendered anyway. Defaults to `append`.
- **`button.icon`** is rendered as **literal text**, not looked up in an icon
  font. Use a character (`↻`, `🔍`), not `mdi-refresh`.

Controls without `x-inflow-ui` are untouched and render exactly as they would
otherwise, so this is purely additive to a form you already have.

---

## 2. What your meta function receives

The host POSTs a **flat** JSON object — the form as it stands, plus context:

```jsonc
{
  "projectKey": "OP",          // ← every field of the form, as currently filled in
  "issueType": "Task",
  "summary": "",

  "settings": {                 // ← the settings profile the node is bound to
    "baseUrl": "https://acme.atlassian.net",
    "email": "…",
    "apiToken": "…"
  },
  "value": "OP"                 // ← the value of the control the button sits on
}
```

Two things to internalise:

**This is not the action envelope.** An *action* arrives as
`{"_registry": …, "body": {…}}`. A meta function called from a form arrives
**flat** — the fields are at the top level. `sdkv1.CastRequestTo[T]` unmarshals
the `{_registry, body}` envelope, so using it here hands you a zero-valued struct
and an empty `Settings` map, with no error. Decode tolerantly instead:

```go
// Accept both shapes: the flat body a form button sends, and the {body:…}
// envelope other callers (and your own tests) may use.
func decodeMeta[T any](data []byte) T {
    var out T
    if len(bytes.TrimSpace(data)) == 0 {
        return out
    }
    var envelope struct {
        Body json.RawMessage `json:"body"`
    }
    if json.Unmarshal(data, &envelope) == nil && len(envelope.Body) > 0 {
        if json.Unmarshal(envelope.Body, &out) == nil {
            return out
        }
    }
    _ = json.Unmarshal(data, &out)
    return out
}
```

**The credentials are in `settings`, and only there.** A meta function is as
stateless as an action: it holds nothing between calls, reads no service-specific
environment variables, and pools its clients keyed on the resolved settings. The
same profile serves many accounts through one process.

---

## 3. What your meta function must return

The answer is applied to the form **by shape**:

| You return | The host does |
|---|---|
| A JSON **object** | Treats it as a patch: every key is a data path, every value is written there. `target` is ignored. |
| Anything else (array, string, number) | Writes the whole value to `target`, or to the button's own control if no `target` was given. |

```go
// A patch of several fields — project chosen, dependents filled in.
return map[string]any{
    "projectKey":   "OPS",
    "projectName":  "Operations",
    "issueType":    "Task",
}
```

### Three rules that bite

**Do not return `sdkv1.Response` from a form-button meta function.** It marshals
to `{"data": …, "error": …}` — an object — so the host patches two fields called
`data` and `error` into your form. `sdkv1.Response` is the right answer for a
`SubmitTo` validator and for the settings submit handler. It is the wrong answer
here. Return the patch itself.

**Do not return a bare option list to a control.** A meta function that answers
`[{"value":"OPS","label":"OPS — Operations"}, …]` is perfectly good for a REST
caller, but hanging a button on `projectKey` and returning that array sets
`projectKey` to the entire array. Bare arrays are for **array-typed** fields (see
Pattern C) — for a scalar field, return the resolved value.

**Patch leaf paths, not nested objects.**

```go
map[string]any{"connection.host": "api.example.com"}          // sets host
map[string]any{"connection": map[string]any{"host": "…"}}      // REPLACES connection,
                                                               // dropping port, secure, …
```

Keys are absolute dot-notation data paths, not JSON Pointers and not scoped to
the button's control.

---

## Four patterns that work today

### A. Resolve — free text becomes a canonical id

The one that fixes "assign to". The user types a name; the button turns it into
the id the API actually needs.

```jsonc
{ "type": "Control", "scope": "#/properties/assigneeQuery",
  "x-inflow-ui": {
    "action": { "name": "pluginFn", "fn": "jira.meta.users.resolve" },
    "button": { "position": "append", "label": "Find user" } } },
{ "type": "Control", "scope": "#/properties/assignee" },
{ "type": "Control", "scope": "#/properties/assigneeLabel", "options": { "readonly": true } }
```

```go
p.AddMeta(sdkv1.Meta{
    Method: "jira.meta.users.resolve",
    RequestHandler: func(r sdkv1.Request) any {
        in := decodeMeta[struct {
            Settings      map[string]any `json:"settings"`
            ProjectKey    string         `json:"projectKey"`
            AssigneeQuery string         `json:"assigneeQuery"`
        }](r.Data)

        users, err := lookupAssignableUsers(in.Settings, in.ProjectKey, in.AssigneeQuery)
        if err != nil {
            return map[string]any{"assigneeLabel": "lookup failed: " + err.Error()}
        }
        if len(users) == 0 {
            return map[string]any{"assigneeLabel": "no assignable user matches " + in.AssigneeQuery}
        }
        if len(users) > 1 {
            return map[string]any{
                "assignee":      users[0].AccountID,
                "assigneeLabel": fmt.Sprintf("%s (%s) — %d more matched, refine to narrow",
                    users[0].DisplayName, users[0].Email, len(users)-1),
            }
        }
        return map[string]any{
            "assignee":      users[0].AccountID,
            "assigneeLabel": users[0].DisplayName + " (" + users[0].Email + ")",
        }
    },
})
```

Note what the label field is doing: it is the **only** channel a meta function has
to say something to the user. See [Reporting failure](#reporting-failure) below.

### B. Cascade — one call fills the fields below it

The project is the dependency the rest of the form hangs off. Resolving it is a
good moment to fill in everything it determines.

```go
return map[string]any{
    "projectKey":       project.Key,
    "projectName":      project.Name,
    "issueType":        defaultIssueTypeFor(project),   // valid for THIS project
    "availableTypes":   names(issueTypesFor(project)),  // an array field, see C
}
```

### C. Fill a list — an array field from a lookup

When `target` (or the button's own control) is an array-typed property, a bare
array is exactly the right answer, and JSON Forms renders it as an editable list.

```jsonc
{ "type": "Control", "scope": "#/properties/labels",
  "x-inflow-ui": {
    "action": { "name": "pluginFn", "fn": "jira.meta.labels" },
    "button": { "position": "above", "label": "Load labels from project" } } }
```

```go
return []string{"backend", "bug", "regression"}   // → labels
```

### D. Test the connection

The same mechanism, with nothing to patch but a status line. Put it on the
settings form, hang it on a readonly `status` field, and the user finds out about
a bad token in the dialog instead of in a failed run at 3am.

```go
return map[string]any{"status": "connected to " + site + " as " + me.DisplayName}
```

---

## What does not work today

Be honest with yourself about the ceiling before you design a form around it.

**You cannot inject `enum` options into a `<select>` at runtime.** The answer is
patched into form **data**; the schema is not touched. `ctx.updateSchema` exists
in the renderer's context type but is a no-op that logs a warning. So "list this
account's projects in a dropdown and let the user pick one" is not expressible
yet — Pattern A (resolve free text) is the working substitute, and Pattern C
(fill an array field) is the working substitute for multi-select.

If your form genuinely needs a live-populated dropdown, say so on the catalog
issue tracker rather than working around it with a hidden JSON field; it needs a
host-side change (either implementing `updateSchema`, or an `x-inflow-ui.options`
source that the Inflow renderer reads from form data).

**Nothing fires automatically.** There is no on-change hook, no debounce, no
type-ahead. The user clicks the button. Label it with what it will do
(`Find user`, `Load labels from project`), not `↻` alone.

**There is no separate error channel.** See below.

**`FormBuilder.SubmitTo` is a different thing.** It names a meta method for
validating a form on submit, and that one *does* answer with `sdkv1.Response`.
It is not how buttons work and it does not fetch data into fields.

### Reporting failure

A form-button meta function that answers `{"error": "..."}` does not raise
anything the user sees as an error — the host patches a field called `error` into
the form and moves on. Only a transport failure (plugin down, timeout, non-2xx)
surfaces as a message under the form.

So: **give every dependent-field group a readonly status property** and write
your failures into it, as in Pattern A. It costs one string field and it is the
difference between "the button does nothing" and "no assignable user matches
'mehdi' — is the project key right?".

---

## Generating it with formkit

Everything above is the wire contract — the `x-inflow-ui` markup you hang on a
control and the patch shape your handler returns. The SDK's optional
[`formkit`](https://github.com/Inflowenger/go-plugin-sdk/tree/main/formkit)
package writes both, so the button's `fn`, `target`, and merged `body` cannot
drift from the field they point at.

**The button (Pattern A markup).** `.Lookup` names the meta function, `.Into`
sets the `target` it writes to, and `.Picks` names the action whose form is
rebuilt for the multi-match case:

```go
formkit.Text("assigneeQuery", "Assignee").
    Lookup("jira.meta.users.resolve", "Find user"). // the button
    Into("assignee")                                 // action.target
```

**The reply.** The same package carries the two answer shapes and the message
vocabulary, and both work against raw schema strings too — including forms you
hand-wrote:

```go
// One match — patch the field(s) and say what was found.
return formkit.Success("%s (%s)", u.DisplayName, u.Email).
    Patch(map[string]any{"assignee": u.AccountID})

// Several — re-render the dialog with that field as a drop-down.
return formkit.Choose(action.Form, "assignee", options, formkit.FormData(call),
    formkit.Info("%d users match — pick one.", len(options)))
```

`Patch` returns the plain patch object this doc requires — never `sdkv1.Response`.
`FormData` strips the host-added keys (`settings`, `value`, `targetField`,
`form`) before the form is echoed back, so credentials in `settings` are never
promoted into saved node data. `Choose` falls back to listing the candidates as
text when the form cannot be rebuilt. Full API in
[form-builder.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md).

---

## Design rules

**Never make the button the only way to fill the field.** Flows are templated and
re-used; a `projectKey` may legitimately come from a previous node's output or a
context expression, and the person editing the flow may not have credentials to
run your lookup at all. The button is an assist on a field that must stay
typable.

**Keep metas fast and bounded.** A user is staring at a spinner. Put a timeout
(~20s) on every meta handler and cap result sizes — a site with 4,000 projects
should not return 4,000 rows into a form.

**Fail with the fix, not the symptom.** `"no settings profile is bound — pick one
in the node drawer"` beats `"nil pointer"`. When a required upstream field is
empty, say which one: `"pick a project first — assignable users are per-project"`.

**Name them `<domain>.meta.<thing>`.** They share a namespace with your actions
on the wire; the prefix keeps the two apart in logs and subject lists.

**Never put connection fields in an action form.** Unchanged by any of this: no
`baseUrl`, no tokens. They come from the profile, and the host adds them to the
meta call for you.

---

## Checklist

- [ ] Every meta function called from a button decodes **flat** bodies (not just `{body:…}`).
- [ ] It reads credentials from `settings`, holds no state, and pools clients per connection.
- [ ] It returns a **patch object** (or a bare array into an array field) — never `sdkv1.Response`.
- [ ] Patch keys are absolute leaf paths.
- [ ] Every dependent-field group has a readonly status field, and every failure path writes to it.
- [ ] Every field the button fills is still typable by hand.
- [ ] Registered with `AddMeta` **before** `Start()`.
- [ ] The button's `icon` is a literal character; its `label` says what it does.

---

## See also

- [concepts.md](concepts.md) — actions vs. meta RPCs, settings profiles.
- [build-a-plugin.md § 8](build-a-plugin.md#8-add-meta-rpcs) — registering metas.
- [`@inflowenger/plugin-form-builder`](https://github.com/Inflowenger/inflow-js/tree/master/packages/plugin-form-builder)
  — the renderer that implements `x-inflow-ui`, and the host-side action contract.
- [form-builder.md](https://github.com/Inflowenger/go-plugin-sdk/blob/main/docs/form-builder.md)
  — the `FormBuilder` type and settings forms.
