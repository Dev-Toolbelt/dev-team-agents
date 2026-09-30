# Plugin Authoring Guide

A plugin is an optional, per-project integration declared by a manifest. This guide explains how to create one.

## Directory Layout

```
plugins/<name>/
├── plugin.json               ← manifest (required)
├── scripts/
│   ├── <action-id>.py       ← action implementations (python3 or bash)
│   └── <action-id>.sh
├── lib/
│   └── <name>.sh            ← optional shared library
├── hooks/
│   ├── pre-tool-use.sh      ← optional: runs on every tool call
│   └── stop.sh              ← optional: runs at session end
└── README.md                ← optional: authoring notes
```

## The Manifest (`plugin.json`)

The manifest declares what your plugin does and what it needs. See `plugins/_schema/plugin.schema.json` for the authoritative schema.

Key fields:

| Field | Type | Purpose |
|-------|------|---------|
| `schema` | number | Always `1` |
| `name` | string | Lowercase identifier, 2–32 chars, matches directory name. Pattern: `^[a-z][a-z0-9-]{1,31}$` |
| `title` | string | Display name, max 40 chars |
| `description` | string | One-line summary, max 200 chars |
| `requires` | array | Binaries needed (e.g., `graphify`, `jq`). Each has `binary` name and `install_hint` (command to install) |
| `config` | array | Configurable fields users can set via `devteam plugin config set` |
| `actions` | array | Named operations (e.g., `detect`, `rebuild`) that users can trigger |
| `status` | object | Optional script that prints status facts |
| `hooks` | object | Optional `pre_tool_use` and `stop` hook scripts |

## Config Field Types

| Type | Example | Notes |
|------|---------|-------|
| `boolean` | `{ type: "boolean", default: false }` | Rendered as a toggle |
| `string` | `{ type: "string", default: "" }` | Text input |
| `integer` | `{ type: "integer", min: 1, max: 100, default: 10 }` | Number input |
| `string_list` | `{ type: "string_list", default: [] }` | JSON array: `'["src","lib"]'` from CLI |
| `enum` | `{ type: "enum", options: [{value:"a",label:"A"}], default: "a" }` | Dropdown |

Every field also needs `key`, `label` and `help`; `required: true` makes an empty value mark the plugin
as not configured. The default must match the type — `helpers/plugin-lint.sh` checks it.

## Action Outputs

| Output | Behavior | Use when |
|--------|----------|----------|
| `config` | Stdout is one JSON object of proposed config changes. Never written automatically. | Proposing smart defaults (e.g., auto-detection) |
| `json` | Stdout is one JSON object, returned verbatim. | Returning structured data |
| `log` | Stdout + stderr captured, tail returned. Exit code stored. | Running a build or refresh |

## Script Environment

Every action, hook, and status script receives:

```bash
DEVTEAM_PROJECT_ROOT       # Project root (cwd of the script)
DEVTEAM_PLUGIN_DIR         # Absolute path to the plugin directory
DEVTEAM_PLUGIN_SETTINGS    # Path to plugin-settings/<name>.json (may not exist)
DEVTEAM_PLUGIN_CONFIG      # Effective config as JSON (Stop hooks, actions, status only; not PreToolUse)
DEVTEAM_STATE_DIR          # Machine-local state directory
```

The script runs with cwd = project root.

## Hooks

Declare hooks in the manifest (`"hooks": {"pre_tool_use": "hooks/pre-tool-use.sh", "stop": "hooks/stop.sh"}`).
They run only while the plugin is enabled, dispatched by `scripts/hooks/pre-tool-use/02d-plugins.sh` and
`scripts/hooks/stop/99a-plugins.sh` — never add a per-plugin file to `scripts/hooks/`. Follow the
sub-script conventions in `CLAUDE-md/hooks.md`:

- **PreToolUse** runs on every tool call and receives the tool call JSON on stdin. Keep it cheap, never
  block: always exit 0. `DEVTEAM_PLUGIN_CONFIG` is not set on this path — read `DEVTEAM_PLUGIN_SETTINGS`
  yourself if you need config.
- **Stop** runs at session end and receives `--quiet`. Honour `DEVTEAM_NO_CHANGES=1` (set by the Stop
  dispatcher when the session changed nothing) by exiting early. A non-zero exit is reported; it never
  fails the Stop.
- Machine-local markers go through `scripts/lib/state.sh` (`state_get` / `state_set`) against
  `$DEVTEAM_STATE_DIR/state.json`.

## Settings File

A bound project stores plugin configuration in `.dev-team-agents/plugin-settings/<name>.json`:

```json
{ "schema": 1, "enabled": true, "config": { "key": "value" } }
```

This file is committed and shared. The CLI writes it locked and atomically. Machine-local data (binary paths, last-run markers) go in `DEVTEAM_STATE_DIR`, not here.

## Testing

Lint every manifest (the optional argument is a plugins directory, default `plugins/`):

```bash
bash helpers/plugin-lint.sh --verbose
```

Test an action:

```bash
devteam plugin run <name> <action> --json
```

Test config:

```bash
devteam plugin config get <name>
devteam plugin config set <name> <key> <value>
```

## Example: Detection Action

A `detect` action with output `config` proposes paths without saving:

```python
#!/usr/bin/env python3
import json
import os

config = {
    "targetPaths": ["src", "lib"],
    "manifestPaths": ["package.json"],
}
print(json.dumps(config))
```

Enable the plugin and seed its config from detection:

```bash
devteam plugin enable <name>        # with no settings yet, runs the `config` action and saves its answer
devteam plugin config get <name>    # see the saved values
```

## Adding a Plugin

1. Create `plugins/<name>/plugin.json` with your manifest.
2. Write action scripts in `plugins/<name>/scripts/`.
3. (Optional) Add hooks in `plugins/<name>/hooks/`.
4. Lint: `bash helpers/plugin-lint.sh`.
5. No app or CLI changes needed — the system picks it up from the manifest.

Graphify (`plugins/graphify/`) is the reference implementation.
