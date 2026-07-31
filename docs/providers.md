# Providers — Multi-CLI Port

`dev-team-agents` is portable across AI coding CLIs. The canonical source — `agents/`, `commands/`, `skills/`, `scripts/hooks/` — is provider-agnostic and lives in this repo. A pair of lightweight adapters per provider (a renderer + an install script) emit the provider-specific file tree into each target project.

Supported providers:

| Provider | CLI | Install script | Agent file form | Command invocation | Hook binding |
| --- | --- | --- | --- | --- | --- |
| **claude** | Claude Code | `scripts/install.sh` (existing) | `agents/*.md` symlinked to `.claude/agents/dev-team/` | `/devteam:<name>` (subdir-derived) | `.claude/settings.json` (existing) |
| **opencode** | opencode TUI/CLI | `scripts/install-opencode.sh` | `.opencode/agents/<name>.md` (mode: subagent) | `/devteam:<name>` (inline in `.opencode/opencode.json` `command` object — NOT file-based, see note below) | `.opencode/plugins/dev-team-agents.ts` → `scripts/hooks/*.sh` |
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
| `reasoning` | architecture, planning, big refactors | `claude-opus-4-7` | `opencode-go/qwen3.7-plus` (effort: high) | `openai/gpt-5.6-sol` (effort: high) |
| `backend-exec` | backend implementation, review, database, devops, qa, mobile | `claude-sonnet-4-6` | `opencode-go/kimi-k2.7-code` (effort: default) | `openai/gpt-5.6-terra` (effort: medium) |
| `frontend` | frontend implementation, review, design, frontend tests | `claude-sonnet-4-6` | `opencode-go/kimi-k2.6` (effort: default) | `openai/gpt-5.6-terra` (effort: medium) |
| `repetitive` | test scaffolding, docs, runbook generation, high-volume low-judgment | `claude-sonnet-4-6` | `opencode-go/kimi-k2.5` (effort: low) | `openai/gpt-5.6-luna` (effort: low) |

`model:` was removed from `agents/*.md` frontmatter. **`tier:` is the single source of truth** — the renderer reads it and resolves it through `scripts/lib/tiers.json` into a provider-specific model id. No agent ever names a model; to change one, edit `tiers.json`.

How that resolved id reaches the CLI differs by provider:

- **opencode / codex** — the id (and the `effort` value, where the provider has one) is written into the rendered agent file: `model:` / `variant:` in the opencode frontmatter, `model = ` / `model_reasoning_effort = ` in the Codex TOML.
- **claude** — the render is the identity case: `agents/*.md` is emitted byte-identical to source, so the rendered file carries no `model:` key and Claude Code applies its own default subagent model. The `claude` column in `tiers.json` documents the intended mapping (and satisfies the provider-column completeness check in `.github/scripts/ci/provider/_contract.py`), but it is not injected into the output.

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
   (symlink — install.sh)    (deep-merge into .opencode/opencode.json)
                                                  .codex/hooks.json (4 managed entries)
                              .opencode/plugins/dev-team-agents.ts (event ↔ bash hooks)
```

**Bodies are emitted verbatim.** A short "Tool conventions" preamble added per provider explains how each Claude Code tool name the body references maps to the target provider's native tool (e.g., `Task` → `task` in opencode, `Task` → `spawn_agent` in codex, `AskUserQuestion` → plain-text in codex since it has no structured quiz tool). No token munging elsewhere — the model figures out the native call.

**Skills stay shared.** Every provider's installer symlinks this repo's `skills/` directory into the provider's skill-search path. Skill frontmatter is already compliant with the agentskills.io specification (`name` + `description` only), so no provider-specific rewrite is needed.

> **Skill `name` must equal the skill's directory basename, and must be unique across all categories.** This is a cross-provider invariant, not a style rule: the render engine resolves opencode skills by frontmatter `name`, while the installers symlink by directory. A skill whose `name` disagrees with its directory loads under Claude and Codex but not under opencode. `helpers/agent-lint.sh` enforces both the match and the uniqueness.

**Hooks stay shared.** `scripts/hooks/{session-start,pre-tool-use,pre-compact,stop}.sh` are the same bash scripts across all three providers. Only the *binding* differs: Claude uses `.claude/settings.json`, opencode uses a TS plugin, Codex uses `.codex/hooks.json` with `PreToolUse` / `Stop` / `PreCompact` / `SessionStart` event names (which coincide with Claude's).

---

## Adding a new provider

Expected cost: ~1 hour, no edits to `agents/`, `commands/`, `skills/`, or `scripts/hooks/`.

1. **Add a column to `scripts/lib/tiers.json`** — under each `tiers.<tier>` entry (and `effort.<tier>` if the provider has an effort concept), add your `<provider>` key with the model id.
2. **Add a row to `scripts/lib/tool-map.json`** — `providers.<provider>.tool_rewrites` listing the Claude tool-name → your provider's tool-name mapping (empty `{}` if identity).
3. **Add a row to `scripts/lib/command-map.json`** — `providers.<provider>` declaring where slash commands are emitted and how the colon-separated name surfaces to the user.
4. **(optional) Add a hook-binding adapter** — if the new provider exposes lifecycle events that should fire `scripts/hooks/*.sh`, add a plugin file (TS, bash, etc.) in a `<provider>/plugin/` directory inside this repo. Leave it out if the provider has no equivalent.
5. **Add `scripts/install-<provider>.sh`** — a thin bash script (see `install-opencode.sh` for a template) that: locates the framework source, calls `scripts/render-provider.sh --provider <name>`, and wires the rendered tree into the target project.
6. **Add a value to the CI matrix** in `.github/workflows/ci.yml` (`provider-contracts` job, `matrix.provider`).

> Note on packaging: the render engine, `scripts/lib/*.json`, `install-opencode.sh` and `install-codex.sh` **are** bundled into a Claude install — `scripts/lib/strip-tarball.sh` removes only `opencode/` (the plugin source), `helpers/`, `.claude/`, `.github/`, `.gitignore` and `scripts/install.sh`. Keeping the plumbing means a Claude user can add Codex or opencode support offline by running `.dev-team-agents/scripts/install-codex.sh` / `install-opencode.sh` directly. `scripts/install-provider.sh` remains the curl-pipe entry point for users starting from scratch; it also fetches `opencode/plugin/` on demand.

If your provider can't expose `/devteam:<name>` (e.g., it hardcodes a slash namespace), document the divergence in this file's table above — never alter the canonical `commands/` source to fit the provider.

---

## Known limitations

- **opencode `variant` maps to model effort.** The renderer injects `variant: <effort>` into each agent's frontmatter and each command snippet's inline config. opencode passes `variant` to the model provider, which maps it to reasoning effort (e.g., `high`, `default`, `low`). The tier map's effort column is now enforced via the `variant` field.
- **Skill-loading idiom differs per provider.** Agent bodies were authored for Claude Code (e.g., `Load skills/shared/plan-mode/SKILL.md`). In opencode, the model should invoke the `skill` tool with the skill's folder name (e.g., `skill({ name: 'plan-mode' })`). In Codex, the model reads the file at `.dev-team-agents/skills/<category>/<name>/SKILL.md`. The renderer prepends a per-provider preamble that explains this to each provider's agent — no body rewrite occurs.
- **Codex UX divergence.** Codex's custom-prompt namespace is hardcoded as `/prompts:`. Commands are exposed as `/prompts:devteam-<name>` (e.g., `/prompts:devteam-plan`) rather than `/devteam:<name>`. Claude Code and opencode preserve the canonical `/devteam:<name>` UX.
- **opencode command registration.** Commands must be declared as **inline entries** in `opencode.json` under the `command` key (e.g., `"devteam:plan": {…}`). File-based `.opencode/commands/` files produce commands without the `devteam:` prefix (e.g., `/backend` instead of `/devteam:backend`). The renderer (`render_provider.py`) emits inline entries automatically; if `.opencode/commands/` files exist from an older install, remove them and re-render, or manually add the `command` block to `opencode.json`.

## Troubleshooting

**`render-provider: ERROR: tier 'X' has no model id for provider 'Y'`** — add a column `Y` under the missing tier in `scripts/lib/tiers.json`.

**`render-provider: ERROR: agent 'X' has no 'tier:' key in frontmatter`** — add `tier: <one-of-the-4-tiers>` to that agent's frontmatter. `helpers/agent-lint.sh` catches this locally before it reaches CI.

**opencode won't load the new commands** — quit and restart opencode. Config is loaded once at startup; the running session keeps using already-loaded config.

**Codex prompts aren't appearing** — Codex must trust the project's `.codex/` directory (it gates per-project config trust). Run `codex` once in the project root and approve the trust prompt, then restart.

**Hooks aren't firing in Codex** — Codex requires non-managed command hooks to be reviewed and trusted per-hash before they run, and `features.hooks` must be `true` (the default). The installer writes hooks with relative paths (`.dev-team-agents/scripts/hooks/…`) so they're stable across machines, but each new contributor still needs to accept the trust prompt on first session.

---

## Model Provider Reference

Below are the top providers and their model IDs (from [models.dev](https://models.dev)) for use in framework decisions. Each model lists attachment (vision), reasoning, and tool-call support.

### Top 7 Model Providers

| # | Provider | models.dev ID | Flagship Model | attach | reason | tools | Use Case |
|---|----------|---------------|----------------|--------|--------|-------|----------|
| 1 | **OpenAI** | `openai` | `gpt-5.2`, `gpt-5.1-codex` | ✅ | ✅ | ✅ | General-purpose, coding, reasoning |
| 2 | **Anthropic** | `anthropic` | `claude-opus-4-7`, `claude-sonnet-4-6` | ✅ | ✅ | ✅ | Architecture, complex reasoning, safe coding |
| 3 | **Google** | `google` | `gemini-3.1-flash`, `gemini-3.1-pro` | ✅ | ✅ | ✅ | Multimodal, flash tasks, vision |
| 4 | **DeepSeek** | `deepseek` | `deepseek-v4-flash`, `deepseek-v4-pro` | ✅ | ✅ | ✅ | Open-source coding, cost-effective |
| 5 | **Alibaba (Qwen)** | `alibaba` | `qwen3.7-plus`, `qwen3.7-max` | ✅ | ✅ | ✅ | Multimodal reasoning, open-source |
| 6 | **Moonshot AI (Kimi)** | `moonshotai` | `kimi-k2.7-code`, `kimi-k3` | ✅ | ✅ | ✅ | Long-context coding, best-in-class code |
| 7 | **Meta** | `meta` | `llama-4-maverick-17b`, `llama-4-scout-17b` | ✅ | ✅ | ✅ | Open-source foundation, fine-tuning |

### OpenCode Access Tiers

These are the two tiers available through the OpenCode CLI, both accessed via your `opencode-go` or `opencode` connection:

| Tier | Provider ID | API | Best For |
|------|-------------|-----|----------|
| **OpenCode Go** | `opencode-go` | `https://opencode.ai/zen/go/v1` | Cost-effective coding, everyday use |
| **OpenCode Zen** | `opencode` | `https://opencode.ai/zen/v1` | Premium models, full catalog |

### Model ID Format

When configuring opencode (in `opencode.jsonc` or agent frontmatter), use:

```
<provider-id>/<model-id>
```

Examples from the currently configured models:

```
# OpenCode Go (default for this project)
opencode-go/qwen3.7-plus         → Qwen3.7 Plus (vision, reasoning)
opencode-go/kimi-k2.7-code       → Kimi K2.7 Code (vision, reasoning, code)
opencode-go/deepseek-v4-flash    → DeepSeek V4 Flash (reasoning, no vision)
opencode-go/glm-5.2              → GLM-5.2 (reasoning, no vision)

# OpenCode Zen (premium tier)
opencode/gpt-5.1-codex           → GPT-5.1 Codex
opencode/claude-sonnet-4-6       → Claude Sonnet 4.6
opencode/kimi-k2.7-code          → Kimi K2.7 Code
```

### Tier → Model Mapping in This Framework

`scripts/lib/tiers.json` is the canonical source. Current mapping (using `opencode-go` models):

| Tier | opencode-go (default, from `tiers.json`) | opencode-zen (premium alternative) |
|------|----------------------|----------------------|
| `reasoning` | `opencode-go/qwen3.7-plus` | `opencode/claude-opus-4-7` |
| `backend-exec` | `opencode-go/kimi-k2.7-code` | `opencode/gpt-5.6-terra` |
| `frontend` | `opencode-go/kimi-k2.6` | `opencode/gpt-5.6-terra` |
| `repetitive` | `opencode-go/kimi-k2.5` | `opencode/gpt-5.6-luna` |

Only the first column is read by the renderer. The premium column is a suggested
substitution — changing it here changes nothing; edit `tiers.json` to change what ships.

### All opencode-go Models (alphabetical)

| Model ID | Name | attach | reason | tools |
|----------|------|--------|--------|-------|
| `deepseek-v4-flash` | DeepSeek V4 Flash | ❌ | ✅ | ✅ |
| `deepseek-v4-pro` | DeepSeek V4 Pro | ❌ | ✅ | ✅ |
| `glm-5` | GLM-5 | ❌ | ✅ | ✅ |
| `glm-5.1` | GLM-5.1 | ❌ | ✅ | ✅ |
| `glm-5.2` | GLM-5.2 | ❌ | ✅ | ✅ |
| `grok-4.5` | Grok 4.5 | ✅ | ✅ | ✅ |
| `hy3` | Hy3 | ❌ | ✅ | ✅ |
| `kimi-k2.5` | Kimi K2.5 | ✅ | ✅ | ✅ |
| `kimi-k2.6` | Kimi K2.6 | ✅ | ✅ | ✅ |
| `kimi-k2.7-code` | Kimi K2.7 Code | ✅ | ✅ | ✅ |
| `kimi-k3` | Kimi K3 (2x usage) | ✅ | ✅ | ✅ |
| `minimax-m2.5` | MiniMax-M2.5 | ❌ | ✅ | ✅ |
| `minimax-m2.7` | MiniMax-M2.7 | ❌ | ✅ | ✅ |
| `minimax-m3` | MiniMax-M3 | ❌ | ✅ | ✅ |
| `mimo-v2-omni` | MiMo V2 Omni | ✅ | ✅ | ✅ |
| `mimo-v2-pro` | MiMo V2 Pro | ✅ | ✅ | ✅ |
| `mimo-v2.5` | MiMo V2.5 | ✅ | ✅ | ✅ |
| `mimo-v2.5-pro` | MiMo V2.5 Pro | ✅ | ✅ | ✅ |
| `qwen3.5-plus` | Qwen3.5 Plus | ✅ | ✅ | ✅ |
| `qwen3.6-plus` | Qwen3.6 Plus | ✅ | ✅ | ✅ |
| `qwen3.7-max` | Qwen3.7 Max | ❌ | ✅ | ✅ |
| `qwen3.7-plus` | Qwen3.7 Plus | ✅ | ✅ | ✅ |