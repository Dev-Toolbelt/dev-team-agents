---
status: approved
touches: [backend]
depends_on: []
---

## Spec — History mining

### User Story
As a developer onboarding a project, I want the corrections I keep repeating to agents and the review comments that made authors change code to be offered as reuse rules, wiki entries or preferences, so that knowledge already sitting in my history becomes project knowledge — and nothing is recorded unless I say yes.

### Context
Corrections and review feedback are lost after the session or PR closes. This spec reads them back and turns them into candidates; the user decides each one. Decision record: ADR-0049. Proposal flow lives in a new skill, `skills/shared/history-mining/SKILL.md`; `setup-assistant` references it from FIRST_RUN in one line.

#### Commands

| Command | Reads | Candidate |
|---|---|---|
| `devteam mine sessions --json` | The provider's local transcripts for this project: Claude `~/.claude/projects/<slug>/*.jsonl`, Codex `${CODEX_HOME:-~/.codex}/sessions/**/rollout-*.jsonl`, opencode's local storage. Only messages the user typed — never tool output, pasted content or headless runs | A correction or preference expressed on at least 2 distinct local days |
| `devteam mine reviews --json` | Inline review threads on the last 50 merged PRs (approximate: ordered by last update), through the GitHub integration adapter (ADR-0023); `gh` only when the adapter cannot | A thread that was resolved or outdated (the author changed the code), tied to its file |

Both are read-only, make no model call, and `sessions` makes no network call. Secrets are scrubbed from every candidate.

#### Proposal

Each candidate is proposed with one `AskUserQuestion`: as a reuse rule (through the `/devteam:rule` flow), a wiki entry, a preference (Correction Pattern Rule), or **Skip**.

### Links
- **PRD rules**: none — no PRD
- **Contract**: none — CLI `--json` output governed by the existing contract tests
- **Flow**: none — no UI

### Acceptance Criteria

**Scenario S1: a repeated correction becomes a candidate**
- Given the user typed the same correction ("don't spawn a worktree for this") in sessions on two different local days
- When `devteam mine sessions --json` runs
- Then one candidate is listed with its wording and the days it was seen

**Scenario S2: a correction from a single day is not a candidate**
- Given a correction seen several times but only on one local day
- When `devteam mine sessions --json` runs
- Then it is not listed

**Scenario S3: only what the user typed**
- Given transcripts containing tool output, pasted content and headless runs that match a correction pattern
- When `devteam mine sessions --json` runs
- Then none of them produce or count towards a candidate

**Scenario S4: Claude Code transcripts**
- Given a project used with the `claude` provider
- When `devteam mine sessions` runs
- Then it reads that project's transcripts under `~/.claude/projects/<slug>/`, keeping only those whose recorded `cwd` is this project

**Scenario S5: Codex transcripts**
- Given a project used with the `codex` provider
- When `devteam mine sessions` runs
- Then it reads rollouts under `${CODEX_HOME:-~/.codex}/sessions/` that belong to this project, honouring `CODEX_HOME`

**Scenario S6: opencode transcripts**
- Given a project used with the `opencode` provider
- When `devteam mine sessions` runs
- Then it reads opencode's local session storage for this project

**Scenario S7: no transcripts**
- Given no readable transcripts for any provider, or a malformed transcript file
- When `devteam mine sessions` runs
- Then it exits 0 with an empty list, skipping unreadable files and reporting the skipped-file count per provider

**Scenario S8: a review that changed code becomes a candidate**
- Given a merged PR among the last 50 (approximate: the GitHub query orders merged PRs by last update) with an inline thread that is resolved or outdated
- When `devteam mine reviews --json` runs
- Then a candidate is listed with the comment's gist, the file and the PR

**Scenario S9: unanswered review threads are ignored**
- Given an inline thread still open and not outdated on a merged PR
- When `devteam mine reviews --json` runs
- Then it is not listed

**Scenario S10: no GitHub access**
- Given neither the GitHub adapter nor `gh` can reach the repository
- When `devteam mine reviews` runs
- Then it reports that reviews could not be read and exits 0 with an empty list

**Scenario S11: secrets are scrubbed**
- Given a candidate's source text containing a token or password pattern
- When it is listed
- Then the secret is redacted in the output

**Scenario S12: nothing is written without the user's yes**
- Given a list of candidates
- When the history-mining flow proposes them
- Then each one is asked about with `AskUserQuestion`, and no reuse row, wiki entry or preference is written for a candidate the user skipped or did not answer

**Scenario S13: an accepted candidate goes through its own flow**
- Given the user accepts a candidate as a reuse rule, a wiki entry or a preference
- When it is recorded
- Then it goes through `/devteam:rule`, the wiki format (with its index row), or the Correction Pattern Rule respectively

**Scenario S14: offered at first setup**
- Given `setup-assistant` running FIRST_RUN in a project with history
- When it reaches the history-mining step
- Then it offers the flow, and declining it leaves the setup unchanged

**Scenario S15: read-only commands**
- Given any run of `devteam mine sessions` or `devteam mine reviews`
- When it completes
- Then no project, store or remote file has changed, and no model was called

### Out of Scope
- Mining non-GitHub review platforms
- Model-based classification of corrections
- Running automatically on a schedule

### Dependencies
- **Depends on**: none
- **Blocks**: none

### Amendment Log
- 2026-10-25 | software-architect | S4 Then clause: transcripts are kept only when their recorded cwd is this project | the slug encoding is lossy and two paths can share one (ADR-0049 amendment)
- 2026-10-25 | software-architect | S7 Then clause: skipped-file counts are reported per provider | an empty result must be distinguishable from a failed read (ADR-0049 amendment)
- 2026-10-25 | software-architect | S8 Given clause: last 50 merged PRs is approximate | the GitHub API orders by UPDATED_AT, not merge date (ADR-0049 amendment)
