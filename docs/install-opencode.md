# Installing dev-team-agents for opencode

The same agent team, skills, and slash commands run in opencode with the same model-tier rigour. The Claude slim installer intentionally **does not** bundle the opencode plumbing — you bootstrap it on demand.

## Install

From your **project root**, run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) opencode
```

This downloads the latest source, renders the 18 agents into `.opencode/agents/`, symlinks skills into `.opencode/skills/dev-team-agents/`, copies the hook adapter plugin to `.opencode/plugins/dev-team-agents.ts`, materialises the hook dispatchers at `.dev-team-agents/scripts/hooks/`, and deep-merges 22 `/devteam:<name>` command keys into `.opencode/opencode.json`.

## After install

Restart opencode. Type:

```
/devteam:plan do a plan
```

The UX is identical to Claude Code — same slash commands, same delegation flow.

## Working from a local clone

Skip the curl-pipe and point directly at the repo:

```bash
bash <path-to-dev-team-agents>/scripts/install-opencode.sh --source <path-to-dev-team-agents>
```

## Update

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) opencode
```

## Troubleshooting

- **`install-opencode.sh: ERROR: source missing cross-CLI plumbing`** — you tried to run `install-opencode.sh` from a slim Claude install that doesn't bundle it. Use the curl-pipe above instead.
- **`command not found: jq`** — install jq (`brew install jq`, `apt install jq`, or `choco install jq`). The installer needs it to merge `opencode.json`.
- **Commands aren't appearing in the TUI** — quit and restart opencode. Config is loaded at startup; the running session keeps the old config.
- **Hooks aren't firing** — verify `.dev-team-agents/scripts/hooks/` contains `stop.sh`, `pre-tool-use.sh`, `session-start.sh`, `pre-compact.sh`. Missing files mean the opencode plugin can't invoke the dispatchers. Re-run the install curl-pipe to restore them.

## Model tier → id map

| tier | opencode model id | effort |
|------|------------------|--------|
| reasoning | `opencode-go/glm-5.2` | (not configurable in opencode) |
| backend-exec | `opencode-go/deepseek-v4-flash` | — |
| frontend | `opencode-go/kimi-k2.6` | — |
| repetitive | `opencode-go/minimax-m3` | — |

> Effort is not currently settable per-agent in opencode. The tier map above is the design target; actual runtime behaviour depends on the provider's model default.
> Full reference: [docs/providers.md](../docs/providers.md)
