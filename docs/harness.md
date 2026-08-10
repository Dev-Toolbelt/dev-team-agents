# Harness Architecture

How Dev Team Agents works internally: one canonical source, multiple CLI targets, shared hooks, and provider-specific adapters.

---

## Index

- [Summary](#summary)
- [Canonical Source](#canonical-source)
- [Render and Install Flow](#render-and-install-flow)
- [Provider Outputs](#provider-outputs)
- [Commands, Agents, and Skills](#commands-agents-and-skills)
- [Model Tiers and Resolution](#model-tiers-and-resolution)
- [Hooks and Shared Runtime](#hooks-and-shared-runtime)
- [Why This Structure Exists](#why-this-structure-exists)
- [Related Documents](#related-documents)

---

## Summary

Dev Team Agents is a multi-provider harness. The repository does not store three independent implementations for Claude Code, opencode, and Codex. Instead, it stores one canonical source and renders provider-specific outputs at install time.

That separation is deliberate:

- Content and behavior live once in `agents/`, `commands/`, `skills/`, `templates/`, and `scripts/hooks/`.
- Provider adapters live in `scripts/lib/*.json`.
- Installers materialize only the file tree each CLI expects.
- Hooks call the same shell dispatchers regardless of provider.

---

## Canonical Source

These directories are the source of truth:

| Path | Responsibility |
|------|----------------|
| `agents/` | Role prompts and behavioral rules for agents |
| `commands/` | Command entrypoints and orchestration prompts |
| `skills/` | Shared reusable instructions |
| `templates/` | Reusable output templates |
| `scripts/hooks/` | Lifecycle hook dispatchers and helpers |
| `scripts/lib/tiers.json` | Tier-to-model mapping per provider |
| `scripts/lib/tool-map.json` | Tool-convention mapping per provider |
| `scripts/lib/command-map.json` | Command/entrypoint mapping per provider |
| `scripts/lib/commands.json` | Command metadata, including tiers |

Nothing in those source directories is meant to be duplicated per provider.

---

## Render and Install Flow

The internal flow has two phases:

1. `scripts/render-provider.sh` reads the canonical source and renders provider-specific artifacts.
2. The installer for each provider places or links those artifacts where the CLI expects them.

High-level flow:

```text
canonical source
  -> render-provider.sh
  -> provider-specific files
  -> provider installer
  -> project-local integration
```

The render step is intentionally lightweight: plain Python with the standard library only.

---

## Provider Outputs

Each provider gets a different shape, but the same intent:

| Provider | Output form |
|----------|-------------|
| Claude Code | `.claude/agents/`, `.claude/commands/devteam/`, `.claude/skills/`, `.claude/settings.json` |
| opencode | `.opencode/agents/`, `.opencode/skills/`, plugin/runtime glue |
| Codex | `.codex/agents/*.toml`, `.codex/skills/devteam-*/SKILL.md`, `.codex/hooks.json` |

Key point: the source is not rewritten manually for each CLI. The render/install layer adapts it.

---

## Commands, Agents, and Skills

The harness is split into three orchestration layers:

| Layer | Purpose |
|------|---------|
| Commands | User-facing entrypoints like `/devteam:plan` or `$devteam-plan` |
| Agents | Specialized executors such as `backend-developer` or `technical-writer` |
| Skills | Shared rules used by commands and agents |

This is why role naming works across supported CLIs: the provider-specific files are rendered from the same canonical source, so the behavior stays aligned even though the file format changes.

For Codex specifically, the project-local entrypoint is the generated skill path `$devteam-<name>` via `.codex/skills/devteam-*/SKILL.md`. That skill is orchestration only; the rendered agents in `.codex/agents/*.toml` are what enforce the provider-side model and effort policy.

---

## Model Tiers and Resolution

Commands and agents do not hardcode provider models directly as the main source of truth. They declare tiers such as `reasoning`, `backend-exec`, `frontend`, and `repetitive`.

The resolution works like this:

| Step | Result |
|------|--------|
| Command or agent declares a tier | Intent is expressed in provider-neutral form |
| `tiers.json` maps tier per provider | The provider gets a concrete model |
| Render/install applies provider conventions | The final artifact carries the right model information |

This is why one behavior can map to different concrete models on Claude Code, opencode, and Codex without editing every prompt body.

### Command model selection

Every command declares a tier in `scripts/lib/commands.json`.

- On opencode and Codex, that tier resolves to a concrete model at install time.
- On Claude Code, command bodies are symlinked as-is, so tier selection only reaches the command through a `model:` key in frontmatter.
- That `model:` key is intentionally used only on `repetitive` commands such as `docs`, `pr`, `push`, `commit`, `learn`, `update`, `symlinks`, and `health-check`.

The reason is cost control. A `model:` override on a planning command would silently replace the model chosen in the current session. A low-cost override on repetitive commands can only reduce cost, not increase it unexpectedly.

---

## Hooks and Shared Runtime

Provider integration differs, but the runtime behavior converges on the same shell layer:

| Concern | Shared implementation |
|---------|-----------------------|
| Session start | `scripts/hooks/session-start.sh` |
| Pre-tool logic | `scripts/hooks/pre-tool-use/` |
| Stop/session end logic | `scripts/hooks/stop/` |
| Helper utilities | `scripts/helpers/` and `scripts/lib/` |

The important design choice is that providers call the same hook logic instead of maintaining duplicate hook implementations per CLI.

That is also why user state such as preferences, session summaries, and credentials are documented as project-local runtime data rather than provider-specific features.

---

## Why This Structure Exists

This structure solves four problems:

- Consistency: behavior changes once, not three times.
- Portability: a new provider mostly needs adapter metadata and an installer.
- Auditability: model policy, hook policy, and command routing are centralized.
- Maintenance cost: fixes land in the canonical source instead of drifting across multiple copies.

In practice, Dev Team Agents is less a prompt pack and more a translation layer between one authored system and several execution surfaces.

---

## Related Documents

- [README](../README.md)
- [Provider Notes](providers.md)
- [Agent Reference](agents.md)
- [User Preferences](user-preferences.md)
- [Credentials Reference](credentials.local.md)
