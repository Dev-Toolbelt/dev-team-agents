# ADR-0037: Spec status, scenario IDs and a mechanical spec lint close the spec-driven loop

**Date:** 2026-10-17  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/spec-lint.sh`, `scripts/hooks/stop/03f-spec-lint.sh`, `skills/shared/spec-gate/SKILL.md`, `templates/spec-template.md`  
**Relates to:** [ADR-0035](0035-planning-sequence-owned-by-the-main-conversation-per-scope-backlog-and-routing-in-every-provider-s-instruction-file.md) (planning sequence, per-scope backlog)

## Context

The spec layer (`skills/shared/spec-gate/SKILL.md`) defined "done" as a spec's `Given/When/Then` blocks, but the loop around it had gaps:

1. **Criteria lived in three places.** An epic's checklist, a sprint task's `Acceptance Criteria` and the spec all held acceptance criteria, and nothing said the first two derive from the third.
2. **Nothing tied a test to a scenario.** The Spec Sync Gate asked `qa-specialist` to judge whether each scenario was built and tested, with no evidence it could check.
3. **Specs had no lifecycle.** The overview had an approval gate; specs did not, so implementation could start from criteria the user never approved.
4. **Test-first covered only backend.** `/devteam:frontend`, `/devteam:mobile` and the frontend track of `/devteam:fullstack` stayed test-after even with a spec.
5. **No command accepted a sprint task.** `TASK-NNN` meant nothing to `/devteam:backend` and the others, so the task's spec link and status were the user's to carry by hand.
6. **Every rule was prose.** A spec with a duplicated scenario, a `depends_on` naming a missing spec, or a task citing a spec that did not exist failed nowhere.
7. **Built features had no way in.** Only `/devteam:plan` wrote specs, and only for new scope, so a feature that already existed skipped every gate above.

## Decision

1. **Spec status** — `draft → approved → implemented` in the spec frontmatter. `product-analyst` writes `draft` and sets `approved` after the user's approval gate (relayed by `/devteam:plan`), and a command that stops on a `draft` spec sets it when the user approves there; whichever command marks a task Done sets `implemented` once every scenario is covered by Done tasks with no `[SPEC-DRIFT]` open; for a retroactive spec, `product-analyst` sets it once every scenario's latest verdict is `matches` (Decision 7). Execution refuses a `draft` spec. A spec without the key is legacy and treated as `approved`.
2. **Stable scenario IDs** — `**Scenario S<n>: <name>**`, never renumbered or reused. A sprint task cites the scenarios it delivers in `**Covers**:` and restates nothing; an epic points at its specs. A task with no spec keeps its own criteria.
3. **Traceability token** — every test derived from a scenario carries `[spec:<feature>#S<n>]`, in its description string or, when the framework has none, a one-line comment (an exception recorded in `comments-policy`).
4. **§ Task Resolution** in `spec-gate` — every implementation command resolves `TASK-NNN` to its sprint task, spec, contract and `Covers` IDs, scopes the work to those scenarios, and flips the task status. `/devteam:sprint` applies the same rules per wave.
5. **Test-first per track** — backend, frontend and mobile derive failing tests from the resolved scenarios before implementation. Visual and styling work outside the scenarios stays test-after.
6. **`scripts/spec-lint.sh` + `stop/03f-spec-lint.sh`** — structural defects (status, touches, scenario IDs, `depends_on` existence and cycles, Amendment Log reasons, a task's `Spec`/`Covers`, a contract without its spec) exit 1 and block at Stop; legacy specs and an `implemented` scenario no test references only warn, once per set of findings. A contract template (`templates/contract-template.md`) gives contracts their own Amendment Log.

7. **Retroactive specs** — `/devteam:spec <feature>` writes the spec of a feature that already exists (`spec-gate` § Retroactive Spec): `product-analyst` drafts it from the code, tests and docs as observable behavior; after approval, `qa-specialist` executes the feature and returns `matches`/`diverges` per scenario while the test authors tag existing tests and list gaps; each divergence is the user's call — describe it as built, or keep the intended behavior and offer `/devteam:fix`. The spec reaches `implemented` only when every scenario's latest QA verdict is `matches`; a rewrite as built is re-verified, and tagging runs on the final wording. `/devteam:fix` and `/devteam:qa` offer the command when a feature has no spec. A separate command rather than a `/devteam:plan` mode, because planning scopes new work and this verifies built work.

## Consequences

### Positive
- Criteria have one home, and the Spec Sync Gate has evidence to check.
- A sprint task is enough input for any implementation command, on every provider.
- Malformed specs and broken task links surface the session they are introduced.

### Negative
- Tests carry a token that is not a natural part of their name.
- Existing specs without status or IDs warn until they are migrated by hand.

### Neutral
- The coverage warning is a heuristic: it finds the token, not whether the test asserts the scenario.
- A project with `TESTS_REQUIRED=no` skips the coverage check.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep task criteria and require them to match the spec | The duplication that drifts stays; a rule to keep two copies equal is the copy problem |
| Block the hook on an uncovered scenario | Tests can legitimately land after the spec flips, and the token check cannot prove coverage |
| Block legacy specs | Every existing spec, including this repository's own, would start failing the Stop hook on upgrade |
| Map tests to scenarios in a separate index file | A second artifact to keep in sync; the token lives with the test it describes |
