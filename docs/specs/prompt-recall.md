---
status: approved
touches: [backend]
depends_on: []
---

## Spec — Prompt recall and the context-hints channel

### User Story
As a developer working in a bound project, I want the ADRs, wiki entries and reuse rules that bear on what I just asked to be pointed out to the agent automatically, so that existing project knowledge is used without depending on the agent remembering to look it up.

### Context
Today project knowledge reaches the agent only if it follows the Context Loading Order in `skills/shared/project-context/SKILL.md`. This spec delivers it by deterministic code at prompt time, and defines the shared context-hints channel that `repair-ledger.md` and `branch-overlap.md` also use. Decision record: ADR-0047 (context-hints channel and prompt recall). Provider set: `scripts/lib/devteam/providers.py:ALL_PROVIDERS`.

#### Context-hints channel

- A per-session queue of pending hint lines, kept in the machine-local state directory under a dot-prefixed name (so `paths.is_machine_local_record` already classifies it).
- A hook raising a hint either emits it immediately, where the provider accepts context at that point, or enqueues it; the next prompt drains the queue.
- Lines carry a prefix: `[DEVTEAM:RECALL]` for recall pointers, `[DEVTEAM:HINT]` for hints raised by other hooks.
- Caps per delivery: at most 5 lines and about 1200 characters. Each pointer or hint is delivered at most once per session.

#### Recall sources and relevance

| Source | Entries read |
|---|---|
| ADR index (`<adr-dir>/README.md`, directory resolved as `new-adr.sh --dir` does) | Rows with Status `Accepted` only — keywords and "read it when" |
| Wiki retrieval index (`docs/wiki/README.md`) | `path \| keywords \| read-it-when` rows |
| Reuse guidelines (`docs/development/reuse-guidelines.md`) | Rows — name, rule, scope |

An entry is shown only when the prompt shares at least two of its keywords, or one keyword that appears in its title or name. Results are ordered best first, at most 5, each a pointer (path plus its one-line "read it when"), never the entry's body.

#### Gates (checked before any interpreter is started)

Prompt of at least 12 characters; preference `recall_active` not `false` (default `true`); at least one of the three sources exists.

### Links
- **PRD rules**: none — no PRD
- **Contract**: none — single layer; the delivery surface is the existing provider hook outputs
- **Flow**: none — no UI

### Acceptance Criteria

**Scenario S1: a relevant ADR is pointed out**
- Given an Accepted ADR whose index row lists the keywords `webhook` and `retry`
- When the user submits a prompt mentioning webhook retries
- Then the agent's context receives one `[DEVTEAM:RECALL]` line with that ADR's path and its "read it when" text, and not the ADR body

**Scenario S2: an unrelated entry never rides along**
- Given an index entry that shares only one keyword with the prompt, and that keyword is not in its title or name
- When the prompt is submitted
- Then that entry is not delivered

**Scenario S3: only Accepted ADRs are recalled**
- Given a matching ADR whose Status is `Proposed`, `Superseded` or `Deprecated`
- When a matching prompt is submitted
- Then that ADR is not delivered

**Scenario S4: wiki and reuse rules are recalled too**
- Given a wiki index row and a reuse-guidelines row that both match the prompt
- When the prompt is submitted
- Then both are delivered as pointers, ordered with the stronger match first

**Scenario S5: at most five lines per delivery**
- Given more than five entries that match the prompt
- When the prompt is submitted
- Then exactly five lines are delivered, the best matches, and the total stays within about 1200 characters

**Scenario S6: each pointer once per session**
- Given a pointer already delivered earlier in the session
- When a later prompt in the same session matches it again
- Then it is not delivered a second time; a new session may deliver it again

**Scenario S7: short prompts are skipped**
- Given a prompt shorter than 12 characters (for example "yes" or "go on")
- When it is submitted
- Then nothing is delivered and no interpreter is started

**Scenario S8: opt-out**
- Given `recall_active: false` in the resolved preferences
- When any prompt is submitted
- Then no recall line is delivered; hints queued by other hooks are still drained unless their own key is off

**Scenario S9: no index in the project**
- Given a project with none of the three sources
- When a prompt is submitted
- Then nothing is delivered and no interpreter is started

**Scenario S10: fail-open**
- Given a malformed index, an unreadable state directory, or any internal error in recall
- When a prompt is submitted
- Then the prompt goes through unchanged, the hook exits 0, and no error text reaches the agent's context

**Scenario S11: delivery on Claude Code**
- Given a bound project on the `claude` provider
- When a prompt produces recall lines
- Then they reach the model through the `UserPromptSubmit` hook's output in the same turn

**Scenario S12: delivery on Codex**
- Given a bound project on the `codex` provider
- When a prompt produces recall lines
- Then they reach the model through the `UserPromptSubmit` hook's output in the same turn

**Scenario S13: delivery on opencode**
- Given a bound project on the `opencode` provider, whose `chat.message` output is not shown to the model
- When a prompt produces recall lines
- Then the opencode plugin captures the lines prefixed `[DEVTEAM:RECALL]` and `[DEVTEAM:HINT]` and adds them to the system context of that turn, the same way `[DEVTEAM:LANGUAGE]` is delivered

**Scenario S14: queued hints drain at the next prompt**
- Given hints enqueued by another hook since the last prompt
- When the next prompt is submitted
- Then they are delivered with that prompt within the same 5-line cap, and the queue is emptied

**Scenario S15: prompt-time budget**
- Given a project with populated indexes
- When a prompt is submitted
- Then recall adds under 150 ms in the typical case

### Out of Scope
- Delivering the body of an ADR, wiki entry or rule — pointers only
- Semantic or model-based matching; any network call
- Changing the Context Loading Order rule itself
- Recall of specs or session summaries

### Dependencies
- **Depends on**: none
- **Blocks**: `repair-ledger.md`, `branch-overlap.md`

### Amendment Log
