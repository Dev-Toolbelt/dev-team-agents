# Installing dev-team-agents for Codex CLI

The same agent team, skills, and lifecycle hooks run in OpenAI Codex CLI. The Claude slim installer intentionally **does not** bundle the Codex plumbing — you bootstrap it on demand.

> **Note:** Codex's slash-command namespace is hardcoded as `/prompts:`, so dev-team-agents commands are exposed as `/prompts:devteam-<name>` (e.g. `/prompts:devteam-plan`) rather than `/devteam:<name>`. The command body and delegation flow are identical.

## Install

From your **project root**, run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) codex
```

This downloads the latest source, renders 17 agents as `.codex/agents/<name>.toml`, renders 22 prompts as `.codex/prompts/devteam-<name>.md`, symlinks skills into `.codex/skills/dev-team-agents/`, writes 4 managed lifecycle hooks to `.codex/hooks.json`, and materialises the hook dispatchers at `.claude/dev-team-agents/scripts/hooks/`.

## After install

Restart Codex CLI. Trust the project's `.codex/` directory if prompted (Codex gates per-project config by trust). Then use the `/hooks` command to review and trust the 4 managed hooks. After that:

```
/prompts:devteam-plan do a plan
```

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
- **Hooks don't fire** — verify `.codex/hooks.json` has the 4 events (`SessionStart`, `PreToolUse`, `PreCompact`, `Stop`) and each `command` path points to an existing file under `.claude/dev-team-agents/scripts/hooks/`. If the files are missing, re-run the install curl-pipe.
- **Prompts don't appear** — ensure the project's `.codex/` directory is trusted (Codex warns on first open). Run Codex from the project root and accept the trust prompt.
- **`[features] hooks = false`** — Codex defaults hooks to enabled. If disabled via config, re-enable: `[features] hooks = true`.

## Model tier → id map

| tier | Codex model id | reasoning effort |
|------|----------------|------------------|
| reasoning | `gpt-5.6-sol` | `high` |
| backend-exec | `gpt-5.6-terra` | `medium` |
| frontend | `gpt-5.6-terra` | `medium` |
| repetitive | `gpt-5.6-luna` | `low` |

> Full reference: [docs/providers.md](../docs/providers.md)