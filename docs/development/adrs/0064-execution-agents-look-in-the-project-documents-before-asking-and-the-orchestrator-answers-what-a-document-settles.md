# ADR-0064: Execution agents look in the project documents before asking and the orchestrator answers what a document settles

**Date:** 2026-11-09  
**Status:** Accepted  
**Deciders:** Maintainers  
**Applies to:** `skills/shared/interaction-patterns/SKILL.md`, `skills/shared/spec-gate/SKILL.md`, `skills/shared/plan-mode/SKILL.md`, `skills/shared/backlog-template/SKILL.md`, `skills/architecture/orchestration/SKILL.md`, `commands/sprint.md`

## Context

Sprints on well-documented projects stopped for questions the documents already answered. The rules caused it. Scope Lock told an agent to stop and ask whenever a spec did not state something, and specs are business-level by design, so technical details are decided elsewhere. The Question Relay forbade the orchestrator from answering any item, so a documented answer still reached the user. Coding agents had no exception to plan-mode inside a sprint whose plan the user had just approved. The spawn prompt carried no decisions, and the context loading order left out the PRD, glossary, NFR, source answers and scope overview.

## Decision

- `interaction-patterns` § Documented Answer First is the one home of a fixed lookup order and a table of what the search result leads to. Only explicit, current sources count: Accepted ADRs and documents with no historical banner, never existing code. Questions remain for conflicting sources, business behavior nobody decided, security, compliance, money, deleted data and hard-to-reverse choices. A silent, easily changed technical detail takes the base standard and is listed under `Assumptions` in the agent's report, which the orchestrator shows the user with the `Answered from` list.
- During approved work, every `## Open Decisions` item that is not an approval gate carries `Searched:`. The orchestrator may answer such an item only by citing the file and section that settles it, and tells the user in one line. It never answers an approval gate, and a recommended default is not a source.
- A `PLAN_APPROVED: <where the user approved it>` line in a spawn prompt exempts that agent from presenting a plan. Work beyond the prompt's scope is reported back.
- `/devteam:sprint` passes that line, condensed context and the task's optional `Refs`, and its pre-flight requires the documents tasks decide from to be committed, because a worktree holds only committed history.

## Consequences

### Positive
- Questions that reach the user during a sprint are the ones only the user can answer.
- An agent's technical defaults become visible in its report instead of being silent or blocking.

### Negative
- An agent can take a technical default the user would have decided differently; the `Assumptions` list is how the user catches it.
- An orchestrator can cite a source that does not really settle the item; the one-line notice lets the user correct it.

### Neutral
- Only `/devteam:sprint` and the orchestration spawn contract emit `PLAN_APPROVED:` today. Other commands keep their behavior until they adopt it.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Require specs to state every technical detail | Specs are business-level by design, and the detail would duplicate the documents that own it |
| Keep every question and let the orchestrator batch them | Fewer interruptions, but the user still answers what is already written |
