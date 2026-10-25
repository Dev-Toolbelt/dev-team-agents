# ADR-0050: A machine-local repair ledger turns repeated command failures into hints

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/hooks/post-tool-use/03-repair-detect.sh`, `scripts/lib/devteam/repairs.py`, `scripts/lib/devteam/paths.py`  
**Relates to:** [ADR-0047](0047-a-context-hints-channel-and-deterministic-per-prompt-recall-from-the-retrieval-indexes.md) (context-hints channel), [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (machine-local records), [ADR-0018](0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md) (PostToolUse hooks)

## Context

Agents rediscover the same local fix every session: a command fails, and a few calls later the same command succeeds because an env var was set, a flag added, a wrapper prepended, or another step ran first. That knowledge is specific to one machine and toolchain, so it does not belong in the committed wiki, yet it is lost when the session ends.

## Decision

1. `scripts/hooks/post-tool-use/03-repair-detect.sh` calls `scripts/lib/devteam/repairs.py` on shell tool results (`PostToolUse` and `PostToolUseFailure`, both already matched on `Bash`).
2. **A repair is recorded** when a shell command failed (non-zero) and a retry of the same command signature within 10 calls succeeded with a delta: an env var set, a flag added, a wrapper from a fixed list prepended, or another program's step run in between.
3. **Ignored failures:** hook or host denies, reads of test or CI logs, SQL and GraphQL errors, flakes (same command succeeding with no delta), and look-only commands.
4. Deltas are redacted with the credential-guard patterns before they are stored.
5. **Store:** `repair-ledger.json`, machine-local. It is added to `paths.py:MACHINE_LOCAL_RECORDS` and its mirrors (`CLAUDE-md/cli.md`, `CLAUDE-md/user-data.md`, the machine-local list in `CLAUDE.md`, the tuple's docstring).
6. **Hint:** a later failure with the same signature enqueues "this failed before; what fixed it: <delta>" on the context-hints channel (ADR-0047).
7. Preference `repair_hints_active`, default `true`.
8. **Provider parity.** Detection runs from the shared `post-tool-use.sh` dispatcher, which all three providers wire (`hooks.py` for claude, `install-codex.sh` for codex, the plugin's `tool.execute.after` for opencode). Delivery is ADR-0047's: immediate on claude, next prompt on codex and opencode. The shell tool's name differs per provider, so the sub-script recognises each provider's shell tool from the hook payload rather than one hardcoded name; a per-provider fixture covers each.

## Consequences

### Positive
- The second time a known failure happens, the fix is in front of the agent before it re-explores.
- Nothing machine-specific leaks into the repository.

### Negative
- Signature matching can pair a failure with an unrelated success; the hint is phrased as "what fixed it before", not as an instruction.
- The ledger grows with use; it is capped and oldest entries are dropped.
- A stored delta can still reveal a path or hostname the redaction patterns do not cover.

### Neutral
- The ledger is per machine; teammates do not share it, by design.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Write repairs to the wiki | Committed and shared, while the fix is usually specific to one machine's toolchain; wiki entries need the user's authorship |
| Ask the model to record what it fixed | Depends on the model remembering to, which is the failure mode this harness replaces with code |
| Record every failure | Most failures are expected (a failing test the agent is fixing); without a success-with-delta there is nothing to teach |
| Portable store under `data/` | ADR-0013: what the machine observed is machine-local |

## Amendment 2026-10-25

- **Codex delivery is immediate.** Codex `PostToolUse` `additionalContext` was verified at openai/codex `970111f6cb62`, as ADR-0047 records, so Decision 8's "next prompt on codex" no longer holds: repair hints are delivered right after the tool call on claude and codex, and on the next prompt on opencode.
- **Latency sentinel.** `$TMPDIR/devteam-repair-open-<session>` marks that the session has an open failure, so a successful command with nothing to pair skips the Python call. It lives outside the store, holds no data, and is harmless when stale or missing (the full path runs). It is opened with `O_NOFOLLOW` and mode `0600`.
- **Flag values are not stored.** A flag delta records the option name only, never its value; every stored delta, env var or wrapper included, passes through `redact()` first. This narrows the Negative consequence about paths or hostnames leaking through a delta.
- **Transient files are swept.** Transient per-session files, the sentinel included, are removed by age, so an abandoned session leaves nothing that grows.
