# ADR-0058: Agents run the commands they can and pause only for interactive steps

**Date:** 2026-10-31  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `skills/shared/interaction-patterns/SKILL.md`, `skills/devops/tool-installers/SKILL.md`, `skills/devops/local-environment/SKILL.md`, `commands/symlinks.md`

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
  the task's own work, as a summary plus a numbered table with **Source** and **Who runs it**
  columns.
- One `AskUserQuestion` approves the whole list. **Run all** is recommended only when no row is
  risky or comes from untrusted content; otherwise **One by one** is, and a flagged row keeps its
  own question. The agent then runs every row itself, `sudo` as `sudo -n`.
- A row that waits on a person (a password or `sudo` prompt, MFA, a browser sign-in, an elevated
  terminal) is an interactive step. The agent stops there, shows the command for the user's own
  terminal, waits for `Done` / `It failed` / `Skip`, verifies the result where it can, and
  continues to the end of the list.
- Routine work skips the list and the question: read-only inspection, the task's own builds,
  tests and lints, and anything an approved plan or the user's request already covers, unless it
  has a risky shape. The pause, elevation and secret rules still apply to it.
- A sub-agent runs only the approved rows, verbatim, and returns at each interactive row, failure
  or new command with the results so far. An autonomous run never approves a run plan.

## Consequences

- One approval replaces a stream of copy-paste instructions, and interactive steps keep their
  place in the order instead of ending the flow.
- Interactive steps run in the user's own terminal, never through a session shell such as
  Claude Code's `!` prefix, because a secret typed there would land in the transcript. The skill
  says so itself, since this ADR does not ship. A secret that a `credentials` § 3b path can use
  never becomes an interactive step. Naming the user's terminal also keeps the rule the same on
  every provider.
- A sub-agent cannot pause for the user. It relays the list through § Sub-agent Question Relay and
  returns at each interactive row, which costs one round trip per such row; the per-row results it
  returns keep a re-spawned agent from running a row twice.
- Skills with a stricter confirmation or failure handling (`local-environment` § Start) keep it;
  the rule sets a floor, not a ceiling. A step that needs the CLI to restart (`/devteam:symlinks`,
  elevated terminal) is a hand-off that ends the flow, not a run-plan step.

## Alternatives Considered

| Alternative | Why not |
|---|---|
| Ask before each command | Many prompts for one approved intent; the reason users stopped reading them |
| Run everything without asking | Installs and config changes reach outside the checkout; the user must see them first |
| Cover every shell command | Would put a quiz in front of `git status`, tests and lints, and conflict with scoped test execution and autonomous sprints |
