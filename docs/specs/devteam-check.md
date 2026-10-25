---
status: approved
touches: [backend]
depends_on: []
---

## Spec — `devteam check`

### User Story
As a developer about to push or open a PR, I want my branch's changes checked against the ADRs and reuse rules that govern the files I touched, so that I find a contradiction with an accepted decision before a reviewer does, without being blocked by rules that are still under review.

### Context
The `03h` Stop hook only reminds the user to re-read an ADR whose `**Applies to:**` globs match a touched path. This spec adds an explicit check that can fail. Decision record: ADR-0049. Glob semantics follow `skills/shared/adr/SKILL.md` § Applies To and the reuse-row detection follows the existing reuse-lint logic — neither is restated here.

#### Command — `devteam check [--base <ref>] [--json] [--path <dir>]`

Compares the branch diff (from the merge-base with the base, default the origin default branch, plus the working tree) against:

| Source | Matches when |
|---|---|
| Accepted ADR with `**Applies to:**` | A changed path matches one of its globs |
| `reuse-guidelines.md` row with a `detection` pattern | An added line matches it, within the row's `scope` |
| Number-changed rule | A changed line alters a numeric literal bound to a name that an applicable ADR cites with the old value |

#### Finding kinds

| Kind | When | Effect |
|---|---|---|
| `conflict` | The source is committed on the base branch **and** applies to that very path **and**, for a reuse row, its severity is not `advisory` | Exit 1 |
| `lead` | Everything else, including an ADR added or edited on the branch, and an edit to a base ADR (its own lead) | Shown, never fails |

Preference `check_active` (default `true`). `--json` follows the CLI contract (ADR-0011, ADR-0014).

#### Pre-flight in `/devteam:pr` and `/devteam:push`

Runs before the push. On a conflict, the findings are shown and one `AskUserQuestion` offers: **Fix it first**, **Justify** (in the PR body for `/devteam:pr`, in the commit message for `/devteam:push`), **Abort**. The procedure lives in `skills/shared/git-workflow/SKILL.md` § Decision Check Pre-flight.

### Links
- **PRD rules**: none — no PRD
- **Contract**: none — the `--json` shape is governed by the existing CLI contract tests
- **Flow**: none — no UI

### Acceptance Criteria

**Scenario S1: an accepted base ADR governing a changed path is a conflict**
- Given an ADR committed on the base branch, Accepted, whose `**Applies to:**` glob matches a file the branch changed, and a changed line that contradicts it under the number-changed rule
- When `devteam check` runs
- Then a `conflict` naming the ADR and the path is reported and the exit code is 1

**Scenario S2: an ADR introduced on the branch is only a lead**
- Given an ADR added on the current branch whose globs match a changed path
- When `devteam check` runs
- Then it is reported as a `lead` and does not change the exit code

**Scenario S3: editing a base ADR is a lead of its own**
- Given the branch edits an ADR that exists on the base branch
- When `devteam check` runs
- Then a `lead` reports the edit, measured against the ADR's merge-base version, and the edited text does not produce a `conflict` against its own paths

**Scenario S4: a reuse rule violation on an added line**
- Given a non-advisory reuse row with a `detection` pattern and a `scope` covering a changed file, committed on the base branch
- When an added line in that file matches the pattern and `devteam check` runs
- Then a `conflict` naming the row's `name`, path and line is reported and the exit code is 1; a pattern whose match times out yields a `lead` instead

**Scenario S5: advisory or out-of-scope reuse rows only lead**
- Given a matching reuse row whose severity is `advisory`, or whose `scope` does not cover the file
- When `devteam check` runs
- Then the advisory match is a `lead` and the out-of-scope match is not reported; the exit code is 0

**Scenario S6: removed lines are not checked against reuse rows**
- Given a line matching a reuse pattern that the branch removes
- When `devteam check` runs
- Then no finding is reported for it

**Scenario S7: number changed against an ADR's cited value**
- Given an applicable base ADR that says `MAX_RETRIES` is 3, and the branch changes `MAX_RETRIES = 3` to `MAX_RETRIES = 5` in a governed path
- When `devteam check` runs
- Then a `conflict` names the constant, the old and new value, and the ADR

**Scenario S8: clean branch**
- Given a branch with no matching source
- When `devteam check` runs
- Then it reports no findings and exits 0

**Scenario S9: base ref**
- Given `--base <ref>`
- When `devteam check` runs
- Then the diff is taken from the merge-base with `<ref>` plus the working tree; without `--base` the origin default branch is used

**Scenario S10: JSON output**
- Given `--json`
- When `devteam check` runs
- Then the output follows the CLI `--json` contract and lists each finding with its kind, source, path and reason

**Scenario S11: pre-flight asks on a conflict**
- Given a branch with a `conflict`
- When the user runs `/devteam:pr` or `/devteam:push`
- Then the findings are shown and an `AskUserQuestion` offers fix first, justify (in the PR body for `/devteam:pr`, in the commit message for `/devteam:push`), or abort; nothing is pushed before the answer

**Scenario S12: pre-flight passes leads through**
- Given a branch with only `lead` findings
- When the user runs `/devteam:pr` or `/devteam:push`
- Then the leads are listed and the flow continues without a question

**Scenario S13: opt-out**
- Given `check_active: false`
- When `/devteam:pr` or `/devteam:push` runs
- Then the pre-flight is skipped; running `devteam check` directly still works

**Scenario S14: no ADR directory and no reuse guidelines**
- Given a project with neither source
- When `devteam check` runs
- Then it exits 0 with no findings

**Scenario S15: the pre-flight fails open**
- Given `devteam check` cannot run (no merge-base, missing base ref, internal error)
- When `/devteam:pr` or `/devteam:push` runs
- Then the user is told the check was skipped and why, and the flow continues

**Scenario S16: the Stop reminder stays**
- Given a session that touched an ADR-governed path
- When the session stops
- Then the existing `03h` reminder is still raised, independently of `devteam check`

**Scenario S17: same verdict on every provider**
- Given the same branch in a project bound for `claude`, `opencode` and `codex`
- When the push or PR pre-flight runs on each
- Then each runs the same check and asks the same question on a conflict

### Out of Scope
- Judging whether code honours an ADR's prose beyond the three sources above
- Blocking a commit (only push and PR flows)
- Auto-fixing a conflict

### Dependencies
- **Depends on**: none
- **Blocks**: none

### Amendment Log
- 2026-10-25 | main | S11: justification goes in the commit message for `/devteam:push` | a push has no PR body yet; matches `commands/push.md`
- 2026-10-25 | software-architect | S3 Then clause: the edit lead is measured against the merge-base version of the ADR | a later base-branch change must not be reported as the branch's edit (ADR-0049 amendment)
- 2026-10-25 | software-architect | S4 Then clause: a detection pattern that times out yields a lead | detection runs through grep -E with a timeout, the reuse-lint engine; a timeout must never fail the check (ADR-0049 amendment)
