# Installing dev-team-agents for Codex CLI

The same agent team, skills, and lifecycle hooks run in OpenAI Codex CLI. The Claude slim installer intentionally **does not** bundle the Codex plumbing — you bootstrap it on demand.

> **Note:** Codex's custom-prompt namespace is hardcoded as `/prompts:` and that surface is now deprecated upstream in favor of skills. dev-team-agents therefore treats **project-local skills** (`$devteam-<name>`) as the default path. Compatibility prompts (`/prompts:devteam-<name>`) are optional user-local aliases you can install into `~/.codex/prompts`.

## Install

From your **project root**, run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) codex
```

This downloads the latest source, renders 17 agents as `.codex/agents/<name>.toml`, renders matching command skills as `.codex/skills/devteam-<name>/SKILL.md`, symlinks the shared skill library into `.codex/skills/dev-team-agents/`, writes 4 managed lifecycle hooks to `.codex/hooks.json`, and materialises the hook dispatchers at `.dev-team-agents/scripts/hooks/`.

## After install

Restart Codex CLI. Trust the project's `.codex/` directory if prompted (Codex gates per-project config by trust). Then use the `/hooks` command to review and trust the 4 managed hooks. After that, the default project-local entrypoint is:

```
$devteam-plan do a plan
```

You can also open `/skills` and select `devteam-plan`.

## Optional slash-command aliases

If you specifically want `/prompts:devteam-*` autocomplete, install the optional
user-level prompt aliases:

```bash
bash <path-to-dev-team-agents>/scripts/install-codex.sh --user-prompts --source <path-to-dev-team-agents>
```

Or, from a project using the bootstrap installer:

```bash
bash .dev-team-agents/scripts/install-codex.sh --user-prompts
```

This copies `devteam-*.md` prompts into `~/.codex/prompts/`, which is the
location Codex documents for custom prompts. Restart Codex afterward so they are
re-indexed.

## First-time trust flow

Codex requires non-managed hooks to be reviewed before they run. On first use:

1. Codex prints a warning about new hooks
2. Run `/hooks` to inspect them
3. Trust each hook entry
4. The hooks now fire on `SessionStart`, `PreToolUse`, `PreCompact`, and `Stop`

## Working from a local clone

```bash
bash <path-to-dev-team-agents>/scripts/install-codex.sh --source <path-to-dev-team-agents>
```

## Update

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) codex
```

## Troubleshooting

- **`install-codex.sh: ERROR: source missing cross-CLI plumbing`** — you tried to run `install-codex.sh` from a slim Claude install. Use the curl-pipe above instead.
- **Hooks don't fire** — verify `.codex/hooks.json` has the 4 events (`SessionStart`, `PreToolUse`, `PreCompact`, `Stop`) and each `command` path points to an existing file under `.dev-team-agents/scripts/hooks/`. If the files are missing, re-run the install curl-pipe.
- **`$devteam-*` doesn't appear or run** — ensure the project's `.codex/` directory is trusted, restart Codex, and verify `.codex/skills/devteam-<name>/SKILL.md` exists in the project.
- **`/prompts:devteam-*` doesn't appear** — those are optional user-level aliases, not project files. Install them with `bash .dev-team-agents/scripts/install-codex.sh --user-prompts`, then restart Codex.
- **`[features] hooks = false`** — Codex defaults hooks to enabled. If disabled via config, re-enable: `[features] hooks = true`.

## Model tier → id map

| tier | Codex model id | reasoning effort |
|------|----------------|------------------|
| reasoning | `gpt-5.6-sol` | `high` |
| backend-exec | `gpt-5.6-terra` | `medium` |
| frontend | `gpt-5.6-terra` | `medium` |
| repetitive | `gpt-5.6-luna` | `low` |

> Full reference: [docs/providers.md](../docs/providers.md)
