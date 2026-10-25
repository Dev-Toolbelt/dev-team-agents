---
status: approved
touches: [backend]
depends_on: [prompt-recall.md]
---

## Spec — Repair ledger

### User Story
As a developer whose agent hits the same failing shell command again, I want it told what fixed that command last time, so that it does not rediscover the fix by trial and error.

### Context
Agents repeatedly fail on the same environment quirks (a missing env var, a wrapper, a flag). This spec records the fix when a failed command is retried successfully and replays it as a hint through the context-hints channel of `prompt-recall.md`. Decision record: ADR-0050.

#### Detection

A repair is recorded when a shell command fails (non-zero) and a retry of the same command signature within the next 10 calls succeeds with a delta: an env var set, a flag added, a wrapper from a fixed list prepended, or another program's step run in between.

Ignored failures: hook or host denials, reads of test or CI logs, SQL and GraphQL errors, flakes (same command succeeding with no delta), and look-only commands.

#### Store

`repair-ledger.json`, machine-local — added to `paths.py:MACHINE_LOCAL_RECORDS` and its mirrors. Deltas are redacted with the credential-guard patterns before being stored; an added flag is stored by its option name only, never its value. Preference `repair_hints_active` (default `true`).

### Links
- **PRD rules**: none — no PRD
- **Contract**: none — single layer, internal record
- **Flow**: none — no UI

### Acceptance Criteria

**Scenario S1: a repair is recorded**
- Given a command that failed, and a retry of the same signature within 10 calls that succeeded with an env var set
- When the retry completes
- Then the ledger holds one entry with the signature and the delta

**Scenario S2: the fix is replayed on a later failure**
- Given a ledger entry for a signature
- When the same signature fails again, in this or a later session
- Then a `[DEVTEAM:HINT]` line says it failed before and what fixed it, naming the delta

**Scenario S3: a retry with no delta is a flake**
- Given a failing command that succeeds on an identical retry
- When the retry completes
- Then nothing is recorded

**Scenario S4: a retry beyond the window**
- Given a failing command whose successful retry comes more than 10 calls later
- When the retry completes
- Then nothing is recorded

**Scenario S5: ignored failure kinds**
- Given a failure caused by a hook or host denial, a read of a test or CI log, an SQL or GraphQL error, or a look-only command
- When it later succeeds with a delta
- Then nothing is recorded

**Scenario S6: secrets never reach the ledger**
- Given a delta that sets a token or password
- When it is recorded
- Then its value is redacted in the ledger and in any hint, and an added flag is stored by its option name only, without its value

**Scenario S7: machine-local**
- Given the ledger file
- When `paths.is_machine_local_record` classifies it
- Then it is machine-local, and it is listed in `MACHINE_LOCAL_RECORDS` and its documentation mirrors

**Scenario S8: once per session**
- Given a hint for a signature already delivered in the session
- When the signature fails again in the same session
- Then the hint is not repeated

**Scenario S9: caps shared with the channel**
- Given several repair hints and other hints pending at once
- When they are delivered
- Then at most 5 lines are delivered in total

**Scenario S10: opt-out**
- Given `repair_hints_active: false`
- When commands fail and are retried
- Then nothing is recorded and no repair hint is delivered

**Scenario S11: fail-open**
- Given an unreadable or malformed ledger, or any internal error
- When a tool call completes
- Then the hook exits 0 and the agent's work is unaffected

**Scenario S12: delivery on Claude Code**
- Given the `claude` provider
- When a known signature fails
- Then the hint is delivered immediately after that tool call, as PostToolUse context

**Scenario S13: delivery on opencode**
- Given the `opencode` provider
- When a known signature fails
- Then the hint is queued and delivered with the next prompt through the plugin's system context

**Scenario S14: delivery on Codex**
- Given the `codex` provider
- When a known signature fails
- Then the hint is delivered immediately after that tool call, as PostToolUse `additionalContext` (verified against the Codex source, openai/codex commit 970111f6cb62)

### Out of Scope
- Applying a fix automatically
- Sharing the ledger between machines
- Non-shell tool failures

### Dependencies
- **Depends on**: `prompt-recall.md` (context-hints channel)
- **Blocks**: none

### Amendment Log
- 2026-10-25 | backend-developer | S14 Then clause: conditional wording replaced by immediate delivery on Codex | Codex PostToolUse additionalContext verified in openai/codex@970111f6cb62 (post_tool_use.rs); Codex tools are Bash and apply_patch
- 2026-10-25 | software-architect | S6 Then clause: an added flag is stored by option name only, without its value | fix round decision recorded in ADR-0050 amendment — flag values may carry secrets redact() does not recognise
