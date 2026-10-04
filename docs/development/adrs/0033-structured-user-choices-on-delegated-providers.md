# ADR-0033: Structured user choices on delegated providers

**Date:** 2026-10-04  
**Status:** Accepted
**Deciders:** dev-team-agents maintainers
**Relates to:** [ADR-0022](0022-delegated-provider-installers-own-files-not-directories.md) (ownership rules), [ADR-0032](0032-bind-writes-provider-native-ask-rules-for-integration-writes.md) (permission rules)

## Context

The quiz-first rule requires every agent to use `AskUserQuestion` when asking finite-set questions. Codex and opencode have distinct rendering paths that broke this rule in production:

**Codex rendering.** Codex renders every `AskUserQuestion` as `request_user_input` (which works in Plan mode). For `interaction_mode: optional` commands, a fallback appears: a numbered plain-text list inside the preamble. In Codex Default mode, the model takes the fallback instead of using `request_user_input`, violating the quiz-first rule on plan-approval gates like `$devteam-learn`. Codex registers `request_user_input` but rejects it in Default mode unless the experimental flag `[features] default_mode_request_user_input = true` is set (off by default). The app exposes `request_user_input_async` as an alternative. A regex bug in the renderer produced nested backticks in the fallback text.

**opencode rendering.** opencode agents were rendered with `mode: subagent`, so commands ran as subtasks where a `question` tool may not reach the root session. The renderer called `_opencode_permission()`, which derived permissions from the now-removed `tools:` frontmatter key, leaving every agent with `bash: deny` and no `question: allow`. The result: no chooser appeared even when the user's project had `question: allow` globally.

Both breakdowns are isolated to the rendering and installer layers — neither is a fundamental incompatibility.

## Decision

### 1. Canonical Codex structured-choice phrase

Add one canonical reference in `scripts/lib/tool-map.json` under `providers.codex.structured_choice`, naming both `request_user_input` and `request_user_input_async` without a Plan-mode pin. The renderer references this phrase when emitting structured choices.

Fallback only when neither tool is listed in the turn:
- **Optional commands**: ask in conversation as a numbered list and mention the flag once per session.
- **Required commands** (`plan`, `setup`): route to `/plan` or include a note that the flag enables interactive mode.
- Preamble states: plan approvals are user decisions, not permission escalations.

### 2. Codex flag ownership — warnings only

Decision 2.1 (D1): `devteam` never writes `~/.codex/config.toml` or the project's `.codex/config.toml` (per ADR-0022 ownership rules; the flag is under development and unstable). Instead:
- `devteam doctor` warns when the flag is absent and explains what it does.
- The health check includes the same warning with the configuration snippet to add.

### 3. opencode permissions and agent mode

Decision 2.2 (D2): Permissions are a canonical set, not derived from frontmatter:
- `task: allow` (for spawning subagents and commands)
- `question: allow` (for `AskUserQuestion`)
- `bash: ask` (for shell commands; all agents ask before running)

Agents now render with `mode: all` so commands run in the primary session, not as subtasks. The providers module recognises both `subagent` (older renders) and `all` as valid, allowing gradual provider updates.

## Consequences

### Positive
- Plan approvals on Codex now respect quiz-first rule in Default mode (with the experimental flag).
- opencode agents appear in the primary-agent switcher and can ask questions in the root session.
- One canonical phrase prevents drift in structured-choice rendering across updates.
- Warnings in `doctor` and the health check prevent silent degradation.

### Negative (Trade-offs)
- Codex Default mode requires a user-set experimental flag to show interactive choices; without it, falls back to numbered lists.
- opencode agents now share the primary session instead of running as isolated subtasks (less isolation, more conversational flow).
- Projects relying on `mode: subagent` isolation must migrate to `mode: all` (which is treated as forward-compatible).

### Neutral
- Nested backticks in fallback text are fixed by the regex correction.
- Render regressions are caught by `scripts/check-codex-compat.sh` and `tests/test_structured_choice_render.py`.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Writing `~/.codex/config.toml` with the flag automatically | Violates ADR-0022 ownership rules; the flag is experimental and may be renamed or moved; users should make this choice deliberately |
| Keeping `mode: subagent` for opencode agents | Breaks the quiz-first rule when `question: allow` is global; subagent mode cannot reach the root session's question tool |
| Per-command patches in `commands/*.md` to handle Codex fallback | Does not scale; every command would need its own fallback and flag mention; centralizing in the renderer is more maintainable |
