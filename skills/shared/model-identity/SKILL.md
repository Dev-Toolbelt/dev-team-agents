---
name: model-identity
description: Emit the agent's tier, model, and effort as a table before any other action.
---

# Model Identity

**Before any other action** — before reading a file, running a command, or answering — emit your run banner so the user sees which model is doing the work. Emit it **twice**: once opening your first response, and once closing the summary you return at the end.

## Procedure

1. Find the block marked `<!-- run-banner -->` in your own agent definition (inside the `## Model Identity` section).
2. Emit that markdown table verbatim, minus the `<!-- run-banner -->` comment line, as the first thing in your first response.
3. Emit nothing before it — no preamble, no "let me start by".
4. Emit the same table once more at the end of your final response — the summary you hand back — under the heading `**Ran on:**`.

Step 4 is not redundant. Only your **final** message reaches the main conversation; everything before it stays in your own context. A subagent running in the background surfaces as a task entry, and the opening banner is then visible only to someone who opens your transcript. Repeating it in the summary is what makes the model visible where the user is actually reading.

That block is generated at render time from `scripts/lib/tiers.json` for the provider you are running under, so its values are already correct. **Do not resolve the model yourself**: do not read `tiers.json`, do not detect the provider, do not infer a model from what you believe you are running on. Any of those produces a wrong or unverifiable banner, and all three cost a tool call the render already paid for.

If your definition has no `<!-- run-banner -->` block, emit the table with `` `unknown` `` in the Model and Effort cells and continue with the task — never block on a missing banner, and never substitute a guess.

## Format

| Agent | Tier | Model | Effort |
|---|---|---|---|
| `agent-name` | `tier` | `model-id` | `effort` |

- **Agent** — your `name:` frontmatter value
- **Tier** — one of `reasoning`, `backend-exec`, `frontend`, `repetitive`
- **Model** — the provider-native model id or alias
- **Effort** — the effort/variant level, or `inherit` when the agent runs at whatever level the session is using

Emit the banner exactly twice per invocation: opening the first response, and closing the final one. Do not repeat it after tool calls or between phases of a long task — those intermediate messages do not leave your context, so a banner there is noise.

## Examples

Claude Code — this tier sets no effort, so the agent runs at the session's level:

| Agent | Tier | Model | Effort |
|---|---|---|---|
| `backend-developer` | `backend-exec` | `sonnet` | `inherit` |

opencode:

| Agent | Tier | Model | Effort |
|---|---|---|---|
| `software-architect` | `reasoning` | `opencode-go/qwen3.7-plus` | `high` |

Codex CLI:

| Agent | Tier | Model | Effort |
|---|---|---|---|
| `technical-writer` | `repetitive` | `gpt-5.6-luna` | `low` |
