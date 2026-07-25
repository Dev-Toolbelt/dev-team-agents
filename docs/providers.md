# Providers — Multi-CLI Port

`dev-team-agents` is portable across AI coding CLIs. The canonical source — `agents/`, `commands/`, `skills/`, `scripts/hooks/` — is provider-agnostic and lives in this repo. A pair of lightweight adapters per provider (a renderer + an install script) emit the provider-specific file tree into each target project.

Supported providers:

| Provider | CLI | Install script | Agent file form | Command invocation | Hook binding |
| --- | --- | --- | --- | --- | --- |
| **claude** | Claude Code | `scripts/install.sh` (existing) | `agents/*.md` symlinked to `.claude/agents/dev-team/` | `/devteam:<name>` (subdir-derived) | `.claude/settings.json` (existing) |
| **opencode** | opencode TUI/CLI | `scripts/install-opencode.sh` | `.opencode/agents/<name>.md` (mode: subagent) | `/devteam:<name>` (key in `opencode.json` `command` object) | `.opencode/plugins/dev-team-agents.ts` → `scripts/hooks/*.sh` |
| **codex** | OpenAI Codex CLI | `scripts/install-codex.sh` | `.codex/agents/<name>.toml` | `/prompts:devteam-<name>` (Codex hardcodes the `/prompts:` namespace — divergent, see note below) | `.codex/hooks.json` → `scripts/hooks/*.sh` |

The slash-command UX is preserved across providers where possible:

```
Claude    :  /devteam:plan do a plan
opencode  :  /devteam:plan do a plan
Codex     :  /prompts:devteam-plan do a plan   (forced divergence)
```

The `/prompts:devteam-…` divergence in Codex is structural: Codex CLI exposes custom prompts under a hardcoded `/prompts:` namespace with no free colon support. To preserve discoverability and grouping, the `devteam-` prefix is baked into the prompt file name. The command body — including `$ARGUMENTS`, plan gate, and delegation to the same subagents — is identical across all three providers.

---

## Tier → model id

Every agent and command declares one of four tiers. Each tier is resolved to a concrete model id per provider via `scripts/lib/tiers.json`.

| tier | role | claude | opencode | codex |
| --- | --- | --- | --- | --- |
| `reasoning` | architecture, planning, big refactors | `claude-opus-4-7` | `opencode-go/glm-5.2` (effort: high) | `openai/gpt-5.6-sol` (effort: high) |
| `backend-exec` | backend implementation, review, database, devops, qa, mobile | `claude-sonnet-4-6` | `opencode-go/deepseek-v4-flash` (effort: default) | `openai/gpt-5.6-terra` (effort: medium) |
| `frontend` | frontend implementation, review, design, frontend tests | `claude-sonnet-4-6` | `opencode-go/kimi-k2.6` (effort: default) | `openai/gpt-5.6-terra` (effort: medium) |
| `repetitive` | test scaffolding, docs, runbook generation, high-volume low-judgment | `claude-sonnet-4-6` | `opencode-go/minimax-m3` (effort: low) | `openai/gpt-5.6-luna` (effort: low) |

`model:` in each `agents/*.md` frontmatter is the Claude fallback and stays valid — non-Claude providers ignore it and resolve through `tiers.json`.

---

## How the port works — single source, plural adapters

```
                  ┌──────────────────────────────────────────────────┐
                  │  Source of truth (this repo, versioned)         │
                  │                                                  │
                  │  agents/*.md           — agent body + tier:      │
                  │  commands/*.md         — command body            │
                  │  skills/**/SKILL.md    — body, agentskills.io    │
                  │  scripts/hooks/*.sh    — hook dispatchers (bash)│
                  │  scripts/lib/*.json    — tier/model/tool/command│
                  │                          maps                   │
                  └─────────────────┬────────────────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────┐
            │ scripts/render-provider.sh            │
            │   (python3, no deps beyond stdlib)    │
            └─────┬───────────────┬─────────────┬───┘
                  │               │             │
            --provider claude  --provider opencode  --provider codex
                  ▼               ▼             ▼
   .claude/agents/dev-team/  .opencode/agents/   .codex/agents/<name>.toml
   .claude/commands/devteam/ .opencode/opencode.json    .codex/prompts/devteam-*
   (symlink — install.sh)    (deep-merge into opencode.json)
                                                  .codex/hooks.json (4 managed entries)
                              .opencode/plugins/dev-team-agents.ts (event ↔ bash hooks)
```

**Bodies are emitted verbatim.** A short "Tool conventions" preamble added per provider explains how each Claude Code tool name the body references maps to the target provider's native tool (e.g., `Task` → `task` in opencode, `Task` → `spawn_agent` in codex, `AskUserQuestion` → plain-text in codex since it has no structured quiz tool). No token munging elsewhere — the model figures out the native call.

**Skills stay shared.** Every provider's installer symlinks this repo's `skills/` directory into the provider's skill-search path. Skill frontmatter is already compliant with the agentskills.io specification (`name` + `description` only), so no provider-specific rewrite is needed.

**Hooks stay shared.** `scripts/hooks/{session-start,pre-tool-use,pre-compact,stop}.sh` are the same bash scripts across all three providers. Only the *binding* differs: Claude uses `.claude/settings.json`, opencode uses a TS plugin, Codex uses `.codex/hooks.json` with `PreToolUse` / `Stop` / `PreCompact` / `SessionStart` event names (which coincide with Claude's).

---

## Adding a new provider

Expected cost: ~1 hour, no edits to `agents/`, `commands/`, `skills/`, or `scripts/hooks/`.

1. **Add a column to `scripts/lib/tiers.json`** — under each `tiers.<tier>` entry (and `effort.<tier>` if the provider has an effort concept), add your `<provider>` key with the model id.
2. **Add a row to `scripts/lib/tool-map.json`** — `providers.<provider>.tool_rewrites` listing the Claude tool-name → your provider's tool-name mapping (empty `{}` if identity).
3. **Add a row to `scripts/lib/command-map.json`** — `providers.<provider>` declaring where slash commands are emitted and how the colon-separated name surfaces to the user.
4. **(optional) Add a hook-binding adapter** — if the new provider exposes lifecycle events that should fire `scripts/hooks/*.sh`, add a plugin file (TS, bash, etc.) in a `<provider>/plugin/` directory inside this repo. Leave it out if the provider has no equivalent.
5. **Add `scripts/install-<provider>.sh`** — a thin bash script (see `install-opencode.sh` for a template) that: locates the framework source, calls `scripts/render-provider.sh --provider <name>`, and wires the rendered tree into the target project.
6. **Add a row in the CI matrix** in `.github/workflows/ci.yml` (`provider-matrix` job).

> Note: `install-opencode.sh` and `install-codex.sh` (plus the render engine and `scripts/lib/{tiers,tool-map,command-map,commands}.json` + `opencode/plugin/`) are NOT bundled into a slim Claude install. Users bootstrap provider support by curl-piping `scripts/install-provider.sh <provider>`, which downloads the tarball and runs the matching installer from a temp source dir. This keeps the default client footprint minimal without sacrificing cross-CLI capability.

If your provider can't expose `/devteam:<name>` (e.g., it hardcodes a slash namespace), document the divergence in this file's table above — never alter the canonical `commands/` source to fit the provider.

---

## Troubleshooting

**`render-provider: ERROR: tier 'X' has no model id for provider 'Y'`** — add a column `Y` under the missing tier in `scripts/lib/tiers.json`.

**`render-provider: ERROR: agent 'X' has no 'tier:' key in frontmatter`** — add `tier: <one-of-the-4-tiers>` to that agent's frontmatter. `helpers/agent-lint.sh` catches this locally before it reaches CI.

**opencode won't load the new commands** — quit and restart opencode. Config is loaded once at startup; the running session keeps using already-loaded config.

**Codex prompts aren't appearing** — Codex must trust the project's `.codex/` directory (it gates per-project config trust). Run `codex` once in the project root and approve the trust prompt, then restart.

**Hooks aren't firing in Codex** — Codex requires non-managed command hooks to be reviewed and trusted per-hash before they run, and `features.hooks` must be `true` (the default). The installer writes hooks with relative paths (`.claude/dev-team-agents/scripts/hooks/…`) so they're stable across machines, but each new contributor still needs to accept the trust prompt on first session.