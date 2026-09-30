# ADR-0018: Plugins as manifest-declared, per-project integrations

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

Graphify is the harness's first optional integration, and it is wired by hand into five places: a
skill (`graphify-setup`) that writes `.dev-team-agents/user-data/graphify.json`, a script
(`scripts/graphify-refresh.sh`), a PreToolUse hint (`pre-tool-use/02-graphify-hint.sh`), a Stop
refresh that was disabled for its per-session cost (`stop/_disabled-99-graphify-refresh.sh`), and a
gitignore negation in `bind.py`. None of it is visible to the desktop app, and adding a second
integration of the same kind would mean touching all five places again, plus the app.

Three existing decisions constrain the answer:

- [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md): the app is a
  pure CLI client. It runs fixed, typed commands — never a generic `run(command)` — and never touches
  the filesystem.
- [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md): what the machine observed
  (a binary was found, the last build commit) is machine-local; what the project decided is not.
- [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md):
  a new written shape gets a schema number the client must declare before it may write.

## Decision

### 1. A plugin is a directory in the core, described by one manifest

`plugins/<name>/plugin.json` in the canonical source, validated by `plugins/_schema/plugin.schema.json`.
Only plugins shipped in the versioned core exist; there is no remote or third-party install. The
manifest is the single contract: the CLI, the hook dispatchers and the app all read it, and **none of
them names a plugin**. Adding a plugin means adding `plugins/<name>/` and nothing else.

```json
{
  "schema": 1,
  "name": "graphify",
  "title": "Graphify",
  "description": "One sentence shown on the plugin card.",
  "homepage": "https://…",
  "requires": [
    { "binary": "graphify", "install_hint": "/devteam:install graphify" }
  ],
  "config": [
    { "key": "targetPaths", "type": "string_list", "label": "Source paths", "help": "…",
      "required": true, "default": [] },
    { "key": "auto_refresh", "type": "boolean", "label": "Refresh at session end", "help": "…",
      "default": false }
  ],
  "actions": [
    { "id": "detect", "label": "Detect paths", "help": "…", "runtime": "python3",
      "script": "scripts/detect.py", "output": "config", "requires_enabled": false,
      "timeout_seconds": 60 },
    { "id": "rebuild", "label": "Rebuild graph", "help": "…", "runtime": "bash",
      "script": "scripts/refresh.sh", "output": "log", "requires_enabled": true,
      "timeout_seconds": 1800 }
  ],
  "status": { "runtime": "bash", "script": "scripts/status.sh", "timeout_seconds": 10 },
  "hooks": { "pre_tool_use": "hooks/pre-tool-use.sh", "stop": "hooks/stop.sh" }
}
```

| Field | Rule |
|-------|------|
| `name` | `^[a-z][a-z0-9-]{1,31}$`, equal to the directory basename |
| `config[].type` | `boolean` · `string` · `integer` · `string_list` · `enum` (with `options: [{value,label}]`) |
| `actions[].output` | `config` — stdout is one JSON object of proposed config values, never written by the action · `json` — stdout is one JSON object returned verbatim · `log` — stdout+stderr are captured, the tail returned |
| `actions[].runtime` / `status.runtime` | `bash` or `python3` — the interpreter is fixed by the CLI, never taken from the file |
| `script`, `hooks.*` | Relative to the plugin directory; must not escape it (`..`, absolute paths refused) |
| `status` | Optional. Prints one JSON object `{ "summary": str, "facts": [{ "label": str, "value": str }] }`. Must be cheap: it runs on every `plugin list` for enabled plugins |
| `hooks` | Optional keys `pre_tool_use`, `stop`. Run only while the plugin is enabled |

### 2. Settings are per project, committed, in `.dev-team-agents/plugin-settings/<name>.json`

```json
{ "schema": 1, "enabled": true, "config": { "targetPaths": ["src"], "auto_refresh": false } }
```

Committed and shared by the team, the same standing `graphify.json` already had: whether a project
uses an integration, and over which paths, describes the project, not a person. It is a
**project-owned record** (`paths.PROJECT_OWNED_RECORDS`) and never moves into the store. It is not
`.dev-team-agents/plugins/`, because that path is the runtime link to the core's `plugins/` tree
(§ 4) — a settings write there would land inside the versioned core.

The CLI writes it locked and atomically, with `json.dumps(indent=2, sort_keys=True)` plus a trailing
newline and mode `0644`. That exact format is part of the contract: the PreToolUse dispatcher detects
an enabled plugin with a pure-bash match on `"enabled": true`, because it runs on every tool call and
cannot afford a JSON parser.

`config` stores only keys that differ from the manifest default; reads merge the defaults in. A key
the manifest no longer declares is kept and reported (`unknown_config`), never dropped.

Machine-local observations — a binary's resolved path, a last-run commit — are never written here.
Plugin scripts that need them use the resolved state dir (`DEVTEAM_STATE_DIR`).

**Graphify's legacy file.** `.dev-team-agents/user-data/graphify.json` is read as
`{enabled: true, config: <file>}` while no settings file exists (`source: "legacy"`), and `bind`,
`sync` and `setup-health-check` **move** it to `plugin-settings/graphify.json` — a rename wrapped in
the new shape, never a delete. Its gitignore negation stays for layout-1 projects until the next
major.

### 3. The CLI surface: `devteam plugin`

Every subcommand takes `--path` (project root, default: cwd) and `--json`. The app passes the path it
resolved from the `project_id` (ADR-0015 amendment: writes name their target by id).

| Command | Writes | JSON payload |
|---------|--------|--------------|
| `plugin list` | no | `{ "project_id", "plugins": [PluginView] }` |
| `plugin show <name>` | no | `PluginView` |
| `plugin enable <name> [--force]` | yes | `{ "plugin": PluginView, "changed": bool, "seeded": bool }` |
| `plugin disable <name>` | yes | `{ "plugin": PluginView, "changed": bool }` |
| `plugin config get <name> [<key>]` | no | `{ "plugin", "config": {…} }` or `{ "plugin", "key", "value" }` |
| `plugin config set <name> <key> <value>` | yes | `{ "plugin": PluginView, "key", "value" }` |
| `plugin config unset <name> <key>` | yes | `{ "plugin": PluginView, "key", "removed": bool }` |
| `plugin run <name> <action>` | per action | `RunResult` |

```
PluginView = {
  name, title, description, homepage,
  enabled: bool, source: "settings" | "legacy" | "none",
  settings_file: ".dev-team-agents/plugin-settings/<name>.json",
  requirements: [{ binary, found: bool, install_hint }],
  ready: bool,                       // every requirement found
  configured: bool,                  // every required config key has a non-empty value
  config_fields: [<manifest config entries>],
  config: { <key>: <effective value> },
  unknown_config: [<key>],
  actions: [{ id, label, help, output, requires_enabled, writes: bool }],
  hooks: ["pre_tool_use" | "stop"],
  status: { summary, facts: [{ label, value }] } | null   // null when disabled or no status script
}
RunResult = {
  plugin, action, ok: bool, exit_code: int, duration_ms: int,
  output: { … } | null,              // parsed stdout for output "config" / "json"
  log_tail: str                      // last 8 KiB of stdout+stderr, for output "log" and on failure
}
```

- `config set` parses `<value>` by the field's type: JSON for `string_list` (`'["src","lib"]'`),
  `true`/`false` for `boolean`, base-10 for `integer`, membership for `enum`. A wrong type is exit 2.
- `enable` refuses with exit 3 (environment) when a requirement is missing, with every
  `install_hint` in the error hint; `--force` enables anyway. When no settings exist and the manifest
  has an action with `output: "config"`, `enable` runs it and seeds the config from its answer
  (`seeded: true`). `disable` keeps the config and anything the plugin produced.
- `run` refuses exit 3 when a requirement is missing, exit 2 for an undeclared action, exit 4 when
  `requires_enabled` and the plugin is disabled. A script that exits non-zero is **not** a CLI error:
  the command succeeds with `ok: false` and the tail, so the app can show it.
- Scripts run with an argv array (`[bash|python3, <abs script>]`), cwd = project root, and the
  environment `DEVTEAM_PROJECT_ROOT`, `DEVTEAM_PLUGIN_DIR`, `DEVTEAM_PLUGIN_SETTINGS` (the settings
  file, possibly absent), `DEVTEAM_PLUGIN_CONFIG` (effective config as JSON), `DEVTEAM_STATE_DIR`.
- The written shape gets `plugin_settings: 1` in `compat.store_schemas()`; every writing subcommand
  goes through the ADR-0014 gate.

**The action allowlist is not a generic `run()`.** ADR-0015 forbids the app from running an arbitrary
command. `plugin run` takes two identifiers, both validated against the manifest of a plugin shipped
in the versioned core; the script, the interpreter and the working directory are all fixed by that
manifest and by the CLI. The app additionally validates both names against its own last
`plugin list` answer before invoking. The set of runnable things changes only with a core release.

### 4. Hooks: one dispatcher per event, no per-plugin wiring

`scripts/hooks/pre-tool-use/02d-plugins.sh` and `scripts/hooks/stop/99a-plugins.sh` iterate
`.dev-team-agents/plugin-settings/*.json`, keep the enabled ones (pure-bash match), and run the
matching hook from the plugin's manifest with the same environment as § 3. The PreToolUse dispatcher
exits before forking anything when the settings directory is absent or no file is enabled. Hook
scripts obey the sub-script rules in `CLAUDE-md/hooks.md` (exit 0 by default, `--quiet`,
`DEVTEAM_NO_CHANGES`).

`plugins` joins `bind.RUNTIME_TREES`, so `.dev-team-agents/plugins/` resolves to the core's tree in a
bound project exactly as `scripts/` does, and it joins the install `KEEP_ROOT` allowlist.

### 5. The app renders plugins generically

The project screen gets two tabs, **Preferences** and **Plugins**. Each plugin is a card built from
its `PluginView`: status badge, requirement warnings with the install hint, an enable switch, a
config form rendered from `config_fields`, one button per action, and the `status` facts. The app
has no plugin-specific code; a new plugin appears in it with zero app changes.

## Consequences

- Graphify becomes `plugins/graphify/`. `scripts/graphify-refresh.sh` and
  `pre-tool-use/02-graphify-hint.sh` remain for one minor version as wrappers (Immutability Contract).
- The graphify Stop refresh comes back as the plugin's `stop` hook, gated by `auto_refresh`, which
  defaults to `false` — the cost that disabled it stays opt-in, per project.
- Enabling a plugin from the app changes a committed file: the whole team gets it on the next pull.
  The app says so next to the switch.
- `helpers/plugin-lint.sh` validates every manifest against the schema and checks that every
  referenced script exists and stays inside its directory; CI runs it.

## Alternatives Considered

- **Toggles in `preferences.json`.** Rejected: preferences are personal layers (ADR-0008), and a
  plugin's target paths are the same for everyone on the repository.
- **Settings inside `.dev-team-agents/plugins/<name>.json`.** Rejected: that path is the runtime link
  to the core tree; writing there would modify the installed version.
- **Per-plugin hook files in `scripts/hooks/`.** Rejected: it is the hand-wiring this ADR removes, and
  the dispatchers would need editing for every new plugin.
- **Letting the app run plugin scripts directly.** Rejected by ADR-0015.

> **Amendment — what the first implementation settled.** Recorded here so the contract above is
> read together with these, not against them:
>
> - **`plugins/` is an optional core tree** (`versions.OPTIONAL_TREES`), not a required one. Making
>   it required would have marked every already-installed version incomplete and broken pinned
>   projects and rollback. `bind` skips the runtime link when the resolved version has no
>   `plugins/`.
> - **`PluginView.actions[]` also carries `timeout_seconds`** (manifest value, default 300) and
>   `writes` (`output != "config"`); `config_fields` passes the manifest entries through unchanged,
>   so `min`, `max`, `options` and `placeholder` reach the client when declared.
> - **`RunResult.ok` is the script's verdict.** `main()` sets a top-level `ok` on every payload; for
>   `plugin run` it keeps the command's own `ok: false` instead of overwriting it.
> - **`DEVTEAM_PLUGIN_CONFIG` is set for Stop hooks, actions and status, not for PreToolUse hooks.**
>   Computing it needs python3, which the PreToolUse path cannot afford on every tool call; a
>   PreToolUse hook reads `DEVTEAM_PLUGIN_SETTINGS` itself.
> - **The legacy move writes the new file first, then unlinks the old one**, so the content is never
>   held in one place only. It runs inside `bind` (and therefore `sync`); when the target already
>   exists neither file is touched and the skip is reported.
> - **Graphify's `rebuild` action forces a build**; the Stop hook and the deprecated
>   `scripts/graphify-refresh.sh` wrapper run it with `--if-changed`.
