# Plugin settings: where they live and why their format is load-bearing

**Origin:** plugin system and Graphify as the first plugin (ADR-0019) | 2026-09-30
**Tags:** plugins, plugin-settings, plugin.json, runtime link, .dev-team-agents/plugins, "enabled": true, 02d-plugins.sh, OPTIONAL_TREES, graphify.json, legacy migration, sort_keys

> Never write plugin settings under `.dev-team-agents/plugins/` — in a bound project that path is a symlink into the installed core version, so a write there modifies the framework for every project on the machine.

---

## What it is

A plugin's manifest ships in the core (`plugins/<name>/plugin.json`); a project's decision to use it —
`enabled` plus its config — is committed at `.dev-team-agents/plugin-settings/<name>.json`. The two
directories look interchangeable and are not: `plugins` joins `bind.RUNTIME_TREES`, exactly like
`scripts/` and `templates/`.

## How it works

```
.dev-team-agents/plugins/            -> <store>/core/versions/<v>/plugins/   (link, excluded)
.dev-team-agents/plugin-settings/    real directory, committed, written only by `devteam plugin`
```

The CLI writes every settings file as `json.dumps(obj, indent=2, sort_keys=True) + "\n"`.

## Gotchas

- **The serialization is a fast-path contract, not style.** `pre-tool-use/02d-plugins.sh` runs on every
  tool call and decides whether a plugin is enabled with pure-bash matching — no JSON parser, nothing
  forked. The canonical line (`"enabled": true|false` at two-space indent, as `json.dumps(indent=2,
  sort_keys=True)` writes it) decides when present, so a nested config key called `enabled` cannot flip
  the result. A minified or re-indented file has no such line and falls back to a whitespace-tolerant
  `"enabled" : true` match anywhere in the file — which a nested `enabled: true` could satisfy, so
  hand-edit only through `devteam plugin enable/config set`.
- **`plugins` is an optional core tree** (`versions.OPTIONAL_TREES`). Required would have marked every
  already-installed version incomplete and broken pinned projects; `bind` skips the link when the
  resolved version has none, so hooks in a project pinned to an older core simply find no plugins.
- **The legacy Graphify file moves, it is never re-created.** `bind`/`sync` write
  `plugin-settings/graphify.json` first and then unlink `user-data/graphify.json`. When both exist,
  neither is touched and a warning is emitted — resolve it by hand, keeping the newer one. A legacy file
  whose content equals the settings file is a finished move and is unlinked silently. `config set/unset`,
  `enable` and `disable` on a still-legacy plugin complete the move in the same locked write.
- **`DEVTEAM_PLUGIN_CONFIG` is absent in PreToolUse hooks** (computing it needs python3); those hooks
  read `DEVTEAM_PLUGIN_SETTINGS` themselves.

## References

ADR-0019 · `scripts/lib/devteam/plugins.py` · `scripts/hooks/lib/plugins.sh` · `plugins/README.md`
