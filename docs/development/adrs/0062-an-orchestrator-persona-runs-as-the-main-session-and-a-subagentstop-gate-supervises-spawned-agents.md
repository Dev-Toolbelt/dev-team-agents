# ADR-0062: An orchestrator persona runs as the main session and a SubagentStop gate supervises spawned agents

**Date:** 2026-11-02  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Relates to:** [ADR-0033](0033-structured-user-choices-on-delegated-providers.md) (question fallback), [ADR-0035](0035-planning-sequence-owned-by-the-main-conversation-per-scope-backlog-and-routing-in-every-provider-s-instruction-file.md) (the main conversation orchestrates), [ADR-0018](0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md) (SubagentStop capture)  
**Applies to:** `agents/orchestrator.md`, `commands/orchestrate.md`, `scripts/hooks/subagent-supervise.sh`, `scripts/hooks/subagent-stop/00-supervision.sh`, `scripts/hooks/lib/subagent-supervision.sh`

## Context

Orchestration lives in `skills/architecture/orchestration/SKILL.md` and is applied by the commands
that load it (`/devteam:sprint`, `/devteam:release-qa`, `/devteam:spec`). Outside those commands, a
request in plain language gets whatever discipline the routing section in `CLAUDE.md`/`AGENTS.md`
carries. Users asked for one high-level agent that coordinates the specialists, relays between them
and the user, and supervises what they hand back.

ADR-0035 keeps orchestration in the main conversation because a spawned agent cannot ask the user
and only its final message returns. Nesting is no longer the obstacle: Claude Code lets a subagent
spawn subagents up to three levels deep. The other two limits still hold, so an orchestrator spawned
as a subagent would relay every question through `## Open Decisions` and hide every wave from the user.

What each provider offers the main session was probed on 2026-11-01/02, comparing a persona session
with a plain one in non-interactive mode:

| Provider | Persona mechanism | Persona tool set vs. plain session |
|---|---|---|
| Claude Code 2.1.226 | `claude --agent <name>`; `"agent": "<name>"` in `.claude/settings.json` | Identical native tools: `Agent`, `SendMessage`, `TaskStop`, `ScheduleWakeup`, `Monitor` |
| opencode 1.18.10 | Agent switcher; `default_agent` in `opencode.json` (primary agents only) | Identical: `task`, `todowrite`, … |
| Codex 0.164.0 | None: no `--agent`, no default-agent key; `developer_instructions` exists but devteam does not write Codex `config.toml` | Main session has `spawn_agent`, `send_message`, `interrupt_agent`, `wait_agent`, `request_user_input` |

The question tool is absent from every non-interactive run, persona or not, so the probe proves
parity with the plain session rather than the question tool itself; ADR-0033 already covers it.

## Decision

1. **`agents/orchestrator.md`** (tier `reasoning`) is a main-session persona. Its body delegates to
   the orchestration skill and never restates it. It is not in the orchestration Agent Roster, and
   `helpers/agent-lint.sh` fails a roster row or a `subagent_type` that names it. opencode renders it
   with `mode: primary`, so its `task` tool cannot spawn it; Claude Code and Codex can still spawn it
   by name, and its Session Guard is the runtime defense: with no spawn tool it stops and says so. A
   missing question tool alone does not stop it — it uses the ADR-0033 fallback.
2. **`/devteam:orchestrate`** activates the persona for the current session on every provider
   (`$devteam-orchestrate` on Codex). It is the only activation path on Codex.
3. **`orchestrator_default`** (preference, default `false`) is personal, so it never lands in a
   committed file. On Claude Code, `devteam bind`/`sync` write `"agent": "orchestrator"` into the
   git-ignored `.claude/settings.local.json`, only when `agent` is absent there; turning the
   preference off, or unbinding, removes it only while it still holds `"orchestrator"` — that value is
   treated as ours. opencode and Codex are excluded: opencode's only default-agent key lives in a
   committed project config (or in the user's global one, outside the project bind owns), and devteam
   does not write Codex `config.toml` (the `doctor` policy). On both, the agent switcher (opencode) and
   the command cover the session.
4. **A SubagentStop supervision gate** sends a finished agent back once when its final message lacks
   the closing run banner, or, for a reviewer or QA agent, the `review-result` marker. It applies only
   to agent types in `agents/`; built-in agents are never held. It blocks at most once per stop
   (`stop_hook_active`), so it cannot loop. Claude Code gets a dedicated `SubagentStop` entry
   (`subagent-supervise.sh`), leaving the Codex-only task-board capture untouched; Codex runs the
   same check as `subagent-stop/00-supervision.sh`, and its dispatcher now relays a sub-script's
   block decision. opencode has no SubagentStop event: there the persona applies orchestration
   § Spawn Integrity check 3 itself.

## Consequences

### Positive
- One orchestrator behavior, reachable on every provider, with model selection where the provider honors it.
- Missing run banners and review markers are caught by a hook instead of by a prompt that already failed to produce them.

### Negative
- Claude Code gains a hook event; every spawned devteam agent pays one more fork at stop.
- opencode supervision stays prompt-only until it exposes a stop event.
- opencode and Codex users have no persistent default; the command (or opencode's agent switcher) is needed per session.

### Neutral
- Commands that orchestrate today keep doing so; under the persona they behave the same, because the persona is the main conversation.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Orchestrator as a spawned subagent | No question tool and only its final message returns: every decision becomes a relay and the user loses wave-level visibility |
| Agent teams (Claude Code) | Experimental, off by default, Claude-only, one team per session and no nested teams |
| Codex persona through `developer_instructions` in `.codex/config.toml` | devteam never writes Codex `config.toml`, and project config loads only in trusted projects |
| Codex persona through the `AGENTS.md` routing section | That file is committed and shared, while the default is a personal preference |
| `agent` in `.claude/settings.json`, `default_agent` in `.opencode/opencode.json` | Both files are committed so teammates get the hooks; a personal default there would flip for the whole team on every teammate's sync |
| Supervision gate on the existing `subagent-stop.sh` for Claude too | Its task-board sub-script is Codex-only; Claude's spawns already reach PostToolUse, so the board would record them twice |
