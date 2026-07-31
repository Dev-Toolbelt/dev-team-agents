---
name: model-identity
description: Announce the agent's tier, model, and effort at startup. Every agent loads this first.
---

## Model Identity Banner

**Before any other action**, announce your model identity so the user sees which model is active:

> **`[agent name]`** — Tier: `[tier]` | Model: `[model]` | Effort: `[effort]`

Where:
- `[agent name]` is your agent's name (from the `name:` frontmatter field)
- `[tier]` is your agent's tier (from the `tier:` frontmatter field)
- `[model]` and `[effort]` are resolved from `scripts/lib/tiers.json` based on your tier and the active provider

### Resolution Procedure

1. **Read your tier** from the `tier:` field in your own frontmatter (the `---` block at the top of this file)

2. **Detect the active provider** by checking for provider-specific directories (check in this order, stop at the first match):
   - `.opencode/` exists → provider = `opencode`
   - `.claude/` exists → provider = `claude`
   - `.codex/` exists → provider = `codex`
   - If none detected → default to `claude`

3. **Resolve model and effort** from `scripts/lib/tiers.json`:
   - Read the JSON file at `.dev-team-agents/scripts/lib/tiers.json`
   - Model: `tiers.<tier>.<provider>` (e.g., `tiers.reasoning.opencode`)
   - Effort: `effort.<tier>.<provider>` (e.g., `effort.reasoning.opencode`)
   - If the provider has no effort entry, omit effort from the banner

4. **Print the banner** using the format above as a single line at the very start of your first response

### Example Banners

```
**software-architect** — Tier: `reasoning` | Model: `opencode-go/qwen3.7-plus` | Effort: `high`
```
```
**backend-developer** — Tier: `backend-exec` | Model: `claude-sonnet-4-6` | Effort: `—`
```
```
**technical-writer** — Tier: `repetitive` | Model: `opencode-go/kimi-k2.5` | Effort: `low`
```
