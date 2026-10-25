# ADR-0048: devteam check compares a branch diff with base-branch decisions before a PR

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/check.py`, `scripts/lib/devteam/cli.py`, `commands/pr.md`, `commands/push.md`, `skills/shared/git-workflow/SKILL.md`  
**Relates to:** [ADR-0039](0039-adrs-declare-the-paths-they-govern-and-a-stop-hook-names-them-when-those-paths-change.md) (Applies to), [ADR-0036](0036-path-scoped-and-severity-graded-rules-in-the-reuse-registry-enforced-at-stop-by-exit-2.md) (reuse registry), [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) and [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (`--json` contract), [ADR-0047](0047-a-context-hints-channel-and-deterministic-per-prompt-recall-from-the-retrieval-indexes.md) (recall)

## Context

ADR-0039's Stop hook reminds an agent of an ADR when a session touches a governed path, and ADR-0036's reuse lint checks added lines at Stop. Both see one session. A branch is several sessions, and the last moment to catch a departure from a recorded decision cheaply is before the PR is opened, against what the base branch has actually accepted. Neither check distinguishes a decision already reviewed on the base branch from one written on the branch itself, so neither can safely fail.

## Decision

1. `devteam check [--base <ref>] [--json] [--path]` in `scripts/lib/devteam/check.py`, registered in `cli.py`. It diffs the merge-base with the base (default: the origin default branch) plus the working tree.
2. The diff is compared against three sources:
   - **(a)** Accepted ADRs whose `**Applies to:**` globs match a changed path — the glob semantics of `03h-adr-scope-check.sh` and `skills/shared/adr/SKILL.md` § Applies To are reused, never restated.
   - **(b)** `reuse-guidelines.md` rows with a `detection` regex, scoped by `scope`, on added lines — the reuse-lint logic is reused, not duplicated.
   - **(c)** **Number-changed rule:** a changed line alters a numeric literal bound to a name that an applicable ADR's text cites with the old value.
3. **Two finding kinds.** A `conflict` fails (exit 1) only when the source is committed on the base branch, applies to that very path, and (for reuse rows) is not `advisory`. Everything else is a `lead`, which never fails. An ADR added or edited on the branch cannot fail the check, since it is not yet reviewed; editing a base ADR on the branch is a lead of its own.
4. `--json` follows the CLI contract (ADR-0011, ADR-0014) and is covered by `tests/test_json_contract.py`.
5. Wired as a pre-flight in `commands/pr.md` and `commands/push.md`: on a conflict the findings are shown and the user chooses via `AskUserQuestion` — fix, justify in the PR body, or abort. The `03h` Stop reminder stays.
6. Preference `check_active`, default `true`.
7. **Provider parity.** The check is a CLI subcommand and a step in two shipped commands, so it is provider-agnostic: claude runs it from `/devteam:pr` and `/devteam:push`, codex from the rendered `$devteam-pr` / `$devteam-push` skills, opencode from its rendered commands. No hook wiring differs per provider.

## Consequences

### Positive
- A PR that contradicts a reviewed decision is caught before review, with the ADR and path named.
- Only base-branch decisions can block, so a branch that changes its own ADR is never stuck on it.
- The desktop app and CI can consume the same `--json` output.

### Negative
- Rule (c) is a heuristic; it reports leads that are false positives when a number is coincidentally equal to a cited value. It is a lead unless the other conflict conditions hold.
- A base ref that is not fetched gives a stale comparison; the check reports which ref it used.

### Neutral
- Coverage still depends on ADRs carrying `Applies to` and reuse rows carrying `detection`.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Extend the Stop hooks to fail on conflicts | Stop sees one session, cannot tell base decisions from branch-local ones, and a Stop failure interrupts unrelated work |
| A CI-only check | Feedback arrives after the PR is open and needs CI per project; a local CLI serves both and CI can still call it |
| Every finding fails | Branch-local and heuristic findings would block legitimate work and train users to bypass the check |
| Model-based semantic review of ADR compliance | Non-deterministic and costly; review agents already do judgment work, this check is the mechanical floor |

## Amendment 2026-10-25

- **Shared logic is ported, with parity tests.** `check.py` ports the `**Applies to:**` glob matching and the reuse-lint row parsing to Python rather than shelling out to the bash implementations. Each port is guarded by a parity test against its source — `glob_to_ere` in `03h-adr-scope-check.sh` and the row parsing in `reuse-lint.sh` — so the semantics stay single-sourced in behaviour even though the code exists twice. Decision 2's "reused, never restated" is enforced by those tests.
- **Detection regexes use the reuse-lint engine.** A row's `detection` pattern runs through `grep -E` with a timeout, the same engine `reuse-lint.sh` uses, so a pattern matches identically in both. A pattern that times out yields a `lead`, never a `conflict` and never a crash.
- **Edits to a base ADR are measured against the merge-base.** The `edited` lead of Decision 3 compares the branch's ADR text with its merge-base version, not with the current base tip, so a later change on the base branch is not reported as the branch's edit.
- **Pre-flight procedure location.** The pr/push pre-flight of Decision 5 lives in `skills/shared/git-workflow/SKILL.md` § Decision Check Pre-flight; `commands/pr.md` and `commands/push.md` point at it. The justify option writes the justification in the PR body for `/devteam:pr` and in the commit message for `/devteam:push`, which has no PR body yet.
