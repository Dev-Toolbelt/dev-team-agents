---
status: approved
touches: [backend]
depends_on: [prompt-recall.md]
---

## Spec — Branch overlap

### User Story
As a developer editing a file, I want to know when a teammate's unmerged branch changes the same lines, so that I can coordinate before we both produce conflicting work.

### Context
Overlapping edits are found today only at merge time. This spec warns at edit time, from a local cache, through the context-hints channel of `prompt-recall.md`. Decision record: ADR-0051.

#### Refresh

A detached refresher, started at session start and at most every 10 minutes, fetches quietly, lists remote branches not merged into the base, not authored by the current git user and with a commit in the last 60 days, and records their changed files and hunk ranges in a dot-prefixed cache in the machine-local state directory.

#### Hint

After an edit, if the edited file's changed hunks overlap a cached branch's hunks, a `[DEVTEAM:HINT]` names the branch and its author, sanitized and quoted. The edit hook reads the cache only and never touches the network. Preference `branch_overlap_active` is a consent key: `true` in a fresh `preferences.json`, backfilled as `false` into an existing one.

### Links
- **PRD rules**: none — no PRD
- **Contract**: none — single layer, internal cache
- **Flow**: none — no UI

### Acceptance Criteria

**Scenario S1: overlapping hunks raise a hint**
- Given a cached remote branch by another author that changes lines 40–60 of a file
- When the agent edits lines 50–55 of that file
- Then a `[DEVTEAM:HINT]` names the branch and its author, sanitized of control and format characters and quoted

**Scenario S2: same file, different lines**
- Given a cached branch that changes lines 40–60 of a file
- When the agent edits lines 200–210 of that file
- Then no hint is raised

**Scenario S3: own branches are excluded**
- Given a remote branch authored by the current git user
- When the refresher runs
- Then it is not cached and never raises a hint

**Scenario S4: merged and stale branches are excluded**
- Given a remote branch already merged into the base, or whose last commit is older than 60 days
- When the refresher runs
- Then it is not cached

**Scenario S5: refresh frequency**
- Given a refresh finished less than 10 minutes ago
- When a new session starts
- Then no new refresh is started

**Scenario S6: refresh never blocks the session**
- Given a session start
- When the refresher runs
- Then it runs detached and the session start is not delayed

**Scenario S7: offline**
- Given no network
- When the refresher runs
- Then it exits 0, the previous cache is kept, and no error reaches the user

**Scenario S8: the edit hook never uses the network**
- Given an empty or missing cache
- When the agent edits a file
- Then no fetch is performed and no hint is raised

**Scenario S9: once per session**
- Given an overlap hint already delivered for a branch and file in the session
- When the agent edits the same overlapping lines again
- Then the hint is not repeated

**Scenario S10: caps shared with the channel**
- Given several overlap hints and other hints pending at once
- When they are delivered
- Then at most 5 lines are delivered in total

**Scenario S11: opt-out**
- Given `branch_overlap_active: false`
- When a session starts or a file is edited
- Then no refresh runs and no overlap hint is delivered

**Scenario S12: fail-open**
- Given a malformed cache, a repository without a remote, or any internal error
- When a file is edited
- Then the hook exits 0 and the edit is unaffected

**Scenario S13: delivery on Claude Code**
- Given the `claude` provider
- When an overlap is detected after an edit
- Then the hint is delivered immediately after that tool call, as PostToolUse context

**Scenario S14: delivery on opencode**
- Given the `opencode` provider
- When an overlap is detected after an edit
- Then the hint is queued and delivered with the next prompt through the plugin's system context

**Scenario S15: delivery on Codex**
- Given the `codex` provider
- When an overlap is detected after an edit
- Then the hint is delivered immediately after that tool call, as PostToolUse `additionalContext` (verified against the Codex source, openai/codex commit 970111f6cb62)

### Out of Scope
- Resolving or preventing the overlap
- Notifying the other branch's author
- Forges other than the git remote itself

### Dependencies
- **Depends on**: `prompt-recall.md` (context-hints channel)
- **Blocks**: none

### Amendment Log
- 2026-10-25 | backend-developer | S15 Then clause: conditional wording replaced by immediate delivery on Codex | Codex PostToolUse additionalContext verified in openai/codex@970111f6cb62 (post_tool_use.rs); Codex tools are Bash and apply_patch
- 2026-10-25 | software-architect | S1 Then clause: branch and author are sanitized and quoted | branch and author names are teammate-controlled text (ADR-0051 amendment)
- 2026-10-25 | software-architect | S4: branches whose last commit is older than 60 days are excluded too | abandoned branches should not raise hints (ADR-0051 amendment)
- 2026-10-25 | software-architect | Context: branch_overlap_active is a consent key, backfilled false into existing preferences | user decision in the fix round — the refresher runs a background git fetch the existing owner never agreed to
