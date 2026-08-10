# Installing dev-team-agents for Codex CLI

The same agent team, skills, and lifecycle hooks run in OpenAI Codex CLI. The Claude slim installer intentionally **does not** bundle the Codex plumbing — you bootstrap it on demand.

> **Note:** Codex custom prompts are deprecated upstream in favor of skills. dev-team-agents therefore uses **project-local skills** (`$devteam-<name>`) as the official command path.

## Install

From your **project root**, run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) codex
```

This downloads the latest source, renders 18 agents as `.codex/agents/<name>.toml`, renders matching command skills as `.codex/skills/devteam-<name>/SKILL.md`, symlinks the shared skill library into `.codex/skills/dev-team-agents/`, writes 4 managed lifecycle hooks to `.codex/hooks.json`, materialises the hook dispatchers at `.dev-team-agents/scripts/hooks/`, and injects a small managed rule into `AGENTS.md` so the SessionStart banner is actually echoed in Codex's first visible reply.

## After install

Restart Codex CLI. Trust the project's `.codex/` directory if prompted (Codex gates per-project config by trust). Then use the `/hooks` command to review and trust the 4 managed hooks. After that, the default project-local entrypoint is:

```
$devteam-plan do a plan
```

You can also open `/skills` and select `devteam-plan`.

## First-time trust flow

Codex requires non-managed hooks to be reviewed before they run. On first use:

1. Codex prints a warning about new hooks
2. Run `/hooks` to inspect them
3. Trust each hook entry
4. The hooks now fire on `SessionStart`, `PreToolUse`, `PreCompact`, and `Stop`

## Session banner

Codex does not automatically print a `SessionStart` hook's stdout to the chat transcript. The installer therefore appends a managed rule block to `AGENTS.md` that tells Codex to echo the `[DEVTEAM:SESSION_BANNER]` block verbatim as the first visible reply when that marker is present in hook context.

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
- **Hooks fire but the session banner still does not appear** — verify `AGENTS.md` contains the managed marker `<!-- dev-team-agents: codex-session-banner -->`. If it does not, re-run the install command.
- **`$devteam-*` doesn't appear or run** — ensure the project's `.codex/` directory is trusted, restart Codex, and verify `.codex/skills/devteam-<name>/SKILL.md` exists in the project.
- **`[features] hooks = false`** — Codex defaults hooks to enabled. If disabled via config, re-enable: `[features] hooks = true`.

## Model tier → id map

| tier | Codex model id | reasoning effort |
|------|----------------|------------------|
| reasoning | `gpt-5.6-sol` | `high` |
| backend-exec | `gpt-5.6-terra` | `medium` |
| frontend | `gpt-5.6-terra` | `medium` |
| repetitive | `gpt-5.6-luna` | `low` |

> Full reference: [docs/providers.md](../docs/providers.md)
