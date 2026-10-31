# ADR-0058: Agents run the commands they can and pause only for interactive steps

**Date:** 2026-10-31  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `skills/shared/interaction-patterns/SKILL.md`

## Context

Agents often ended a step by telling the user to run a command the agent could have run itself:
an install, an environment start, a config change. The user then copied commands one at a time,
and the flow lost its place whenever one of them needed a password or a second terminal. Each skill
that hit the case (`tool-installers` for `sudo`, `local-environment` for start commands,
`/devteam:symlinks` for an elevated terminal) wrote its own version of the hand-off, and the
versions did not match.

## Decision

`skills/shared/interaction-patterns/SKILL.md` § Command Run Plan is the one rule for this case:

- The agent lists the commands it would otherwise hand over, or that change the machine beyond
  the task's own work, as a summary plus a numbered table with a **Who runs it** column.
- One `AskUserQuestion` approves the whole list, with **Run all** as the recommended option. The
  agent then runs every row itself.
- A row that waits on a person (a password or `sudo` prompt, MFA, a browser sign-in, an elevated
  terminal) is an interactive step. The agent stops there, shows the command for the user's own
  terminal, waits for `Done` / `It failed` / `Skip`, verifies the result where it can, and
  continues to the end of the list.
- Routine work stays outside the rule: read-only inspection, the task's own builds, tests and
  lints, and anything an approved plan or the user's request already covers.

## Consequences

- One approval replaces a stream of copy-paste instructions, and interactive steps keep their
  place in the order instead of ending the flow.
- Interactive steps run in the user's own terminal, never through a session shell such as
  Claude Code's `!` prefix. A secret typed there would land in the transcript, and
  `credentials` § 3b already requires a secret prompt to happen in the user's terminal. This also
  keeps the rule the same on every provider.
- A sub-agent cannot pause for the user. It relays the list through § Sub-agent Question Relay and
  returns at each interactive row, which costs one round trip per such row.
- Skills with a stricter confirmation (`local-environment` § Start) keep it; the rule sets a floor,
  not a ceiling.

## Alternatives Considered

| Alternative | Why not |
|---|---|
| Ask before each command | Many prompts for one approved intent; the reason users stopped reading them |
| Run everything without asking | Installs and config changes reach outside the checkout; the user must see them first |
| Cover every shell command | Would put a quiz in front of `git status`, tests and lints, and conflict with scoped test execution and autonomous sprints |
