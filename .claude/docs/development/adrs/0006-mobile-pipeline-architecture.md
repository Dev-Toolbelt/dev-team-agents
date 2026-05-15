# ADR 0006 — Mobile Pipeline Architecture

**Date:** 2026-05-15
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

The `mobile-developer` agent currently handles both mobile implementation AND mobile testing (Detox, Maestro, Appium routing added in 2026-05-12). This has been flagged in 4 consecutive audit passes (2026-05-11 through 2026-05-14) as a gap:

- `backend` and `frontend` each have a dedicated `*-test-specialist`
- `mobile-developer` is the only coding agent with dual responsibility (implement + test)
- `/devteam:tester`, `/devteam:fix`, and `/devteam:review` declare `mobile-developer¹` conditional spawn but none of the command files actually spawn it

## Options Considered

### Option A — Create `mobile-test-specialist` agent
Separate the test routing from mobile-developer. Create `agents/mobile-test-specialist.md` with scope: Detox, Maestro, Appium, XCTest, Espresso.

**Pros:** Full symmetry with backend/frontend pipeline. `/devteam:tester` can spawn 3 specialists.
**Cons:** Increased agent count. Most mobile projects test less aggressively than backend; a dedicated specialist may be underutilized.

### Option B — Document mobile-developer as intentionally dual-purpose
Keep `mobile-developer` covering both implementation and testing. Update all commands that declare `mobile-developer¹` to actually spawn it. Add clear documentation that this is a design choice.

**Pros:** Simpler; avoids agent sprawl; mobile testing expertise is naturally tied to platform knowledge.
**Cons:** Breaks symmetry with backend/frontend pipeline.

## Decision

**Option B** — `mobile-developer` is intentionally dual-purpose (implement + test). This is documented as a design exception, not a gap.

Rationale: Mobile testing (Detox, Maestro, XCTest, Espresso) is deeply platform-specific and inseparable from implementation knowledge. The benefit of a separate specialist is low compared to the added complexity for teams with one or few mobile developers.

## Consequences

1. `agents/mobile-developer.md` must explicitly document its test routing responsibility
2. `/devteam:tester` must spawn `mobile-developer` conditionally (mobile file detection)
3. `/devteam:fix` must spawn `mobile-developer` conditionally
4. `/devteam:review` must spawn `mobile-developer` conditionally
5. CLAUDE.md `mobile-developer¹` declarations in command table are correct; the commands must be updated to match
6. This decision is final unless mobile test complexity warrants a specialist (re-evaluate at v2.0)
