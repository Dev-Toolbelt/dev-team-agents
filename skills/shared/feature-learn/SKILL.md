---
name: feature-learn
description: Automatic per-feature lessons-learned promotion at session close, scoped mirror of /learn.
---

# Feature Learn

Runs automatically at the end of a feature command's **Session close (mandatory)** phase — no user
confirmation, same footing as the mandatory review handoff, because it only writes local docs. It is
a scoped mirror of `/devteam:learn`'s mechanics (`commands/learn.md`), not a replacement: `/learn`
stays the manual, full-session pass; this fires every time a feature closes, so knowledge compounds
feature-to-feature instead of aging inside `session-summary.md` until someone remembers to run `/learn`.

## Scoped Evidence (this task only, not full session history)

- `git diff <base>...HEAD --stat` for this task's branch/worktree
- The linked spec's `### Amendment Log` (if any) — see `skills/shared/spec-gate/SKILL.md`
- Any `[SPEC-DRIFT]`, `[ARCH-DEVIATION]`, or `[BLOCKER]` finding raised during this task's review
  handoff
- Any decision made during this task's execution that isn't yet reflected in `docs/development/*.md`,
  `docs/wiki/`, or an ADR

## Classify and Promote

Apply the same bucket table `/devteam:learn` Step 2 uses (Doc patch / Wiki entry / ADR candidate /
Session summary / Nothing to update) — do not restate it here, reference `commands/learn.md`. Spawn:

- `technical-writer` — only if at least one bucket has content; writes doc patches and wiki entries
  per `skills/shared/docs-sync/SKILL.md`
- `software-architect` — only if an ADR candidate was identified; follows `skills/shared/adr/SKILL.md`

## Anti-Dead-Log Rule (hard gate)

<HARD-GATE>
An Amendment Log entry, a `[SPEC-DRIFT]` finding, or any other non-obvious discovery from this task
resolves to exactly one of: a wiki entry, a doc patch, an ADR, or an explicit "not worth keeping"
call made out loud to the user. It never sits only in the spec file or the session summary once the
task closes — that is what turns the memory system into a dead log instead of compounding knowledge.
</HARD-GATE>

## Commit

Fold the promoted files into this task's own Session-close commit(s) (layered per
`conventional-commits`), or as one trailing `docs:` commit — never leave promoted docs uncommitted
and unmentioned in the hand-off message.

## Nothing to Promote

If the scoped evidence yields no bucket hits, skip silently — no agent spawn, no commentary. Mirrors
`/devteam:learn`'s "Nothing to update" behavior so the gate never manufactures busywork on trivial
tasks.
