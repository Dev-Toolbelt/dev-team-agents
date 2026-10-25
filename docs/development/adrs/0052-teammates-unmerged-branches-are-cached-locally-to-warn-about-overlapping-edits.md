# ADR-0052: Teammates' unmerged branches are cached locally to warn about overlapping edits

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/branch_overlap.py`, `scripts/hooks/post-tool-use/04-branch-overlap.sh`, `scripts/hooks/session-start.sh`, `scripts/lib/devteam/hooks.py`  
**Relates to:** [ADR-0048](0048-a-context-hints-channel-and-deterministic-per-prompt-recall-from-the-retrieval-indexes.md) (context-hints channel), [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (machine-local records), [ADR-0018](0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md) (hook-fed records)

## Context

An agent editing a file has no view of the teammate who is changing the same lines on an unmerged branch. The conflict surfaces at merge, after both sides invested in incompatible changes. The information is already in the remote: every pushed branch and its diff. What is missing is putting it in front of the agent at edit time without a network call on the edit path.

## Decision

1. `scripts/lib/devteam/branch_overlap.py` runs as a **detached refresher**, started at session start and at most every 10 minutes. It runs `git fetch --quiet`, lists remote branches not merged into the base and not authored by the current git user, and records each branch's changed files and hunk ranges into a dot-prefixed cache in the machine-local state dir. Offline or any error: exit 0, cache left as it was.
2. `scripts/hooks/post-tool-use/04-branch-overlap.sh` runs after an edit. If the edited file's changed hunks overlap a cached branch's hunks, it enqueues a hint naming the branch and its author on the context-hints channel (ADR-0048). It **reads the cache only** — never git network.
3. The `PostToolUse` matcher in `hooks.py` is widened to the edit tools, with the previous matcher added to `PREVIOUS_MATCHERS` so existing installs are rewritten in place.
4. Preference `branch_overlap_active`, default `true`.
5. **Provider parity.** The refresher starts from `session-start.sh` and the hook from `post-tool-use.sh`, which all three providers dispatch. The edit tool names differ per provider (claude `Edit`/`Write`, opencode lowercase `edit`/`write`, codex its patch tool), so the sub-script recognises each provider's edit tool from the hook payload, and the codex installer and the opencode plugin get the matching filter. Which tool name and payload shape Codex reports for a patch is confirmed against its source before wiring, as with ADR-0048's `PostToolUse` check. Delivery follows ADR-0048.

## Consequences

### Positive
- An overlapping edit is flagged while it is still cheap to coordinate.
- The edit path costs a local file read; network happens only in the detached refresher.

### Negative
- `git fetch` runs in the background in the user's repository, which some users will not expect; it is quiet, rate-limited and can be turned off.
- The cache is up to 10 minutes stale, and only pushed branches are visible.
- Hunk overlap is computed against the base, so a teammate's rebase can shift ranges until the next refresh.

### Neutral
- The cache is a dot-prefixed machine-local file, so it needs no `MACHINE_LOCAL_RECORDS` entry.
- Only the current git user's own branches are excluded; identity is the git author email.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Fetch on each edit | Network on the edit path; slow, and fails offline |
| Query the forge's PR API | Needs an integration and credentials, and misses pushed branches with no PR; plain git covers every provider and forge |
| File-level overlap only | Too noisy on shared files such as manifests and indexes; hunk ranges keep the hint meaningful |
| Check at PR time only | `devteam check` (ADR-0049) is about decisions; overlap is cheapest to act on at edit time, before the work exists |

## Amendment 2026-10-25

- **Codex edit tool confirmed and wired.** Codex reports patches as `apply_patch` (`codex-rs/core/src/tools/hook_names.rs` at `970111f`); the codex installer's filter and the sub-script recognise it, closing the open check in Decision 5.
- **Shared sentinel directory.** `$TMPDIR/devteam-branch-overlap/` is shared across repositories: a cache present for any repository sends every repository's edit hook down the full path. That costs latency only, never correctness, since the full path reads the repository's own cache. The directory is used and swept only when it is a real directory owned by the current user and not writable by group or others (opened without following a symlink, entries removed relative to the open descriptor), so one planted by another account in a shared `/tmp` is ignored; stale sentinels are swept after 24 h and a refresh refreshes a live one's age.
- **User git state is not changed.** The refresher does not run `git fetch --prune` or `git remote set-head`; it only fetches. Remote-tracking refs and `origin/HEAD` stay as the user left them.
- **Author and branch text is untrusted.** Branch and author names come from teammates' pushes, so they are sanitized (control and format characters stripped, length bounded) and quoted in the hint.
- **Stale branches are ignored.** A remote branch whose last commit is older than 60 days is not cached, so abandoned branches do not raise hints.
- **`branch_overlap_active` is a consent key** (user decision). Because the refresher runs `git fetch` in the user's repository in the background, the key joins `CONSENT_KEYS`: `true` in a fresh `preferences.json`, backfilled as `false` into an existing one, whose owner never agreed to a background fetch. This holds for the per-project `preferences.json` that `install.sh` and the session-start backfill write (a project not yet bound to the v3 store); the v3 cascade in `scripts/lib/devteam/prefs.py` does **not** list it in its `CONSENT_KEYS`, so a v3 project resolves it to the schema's `true` unless a layer sets it (user decision: on by default in v3, opt-out with `devteam prefs set branch_overlap_active false`). This replaces Decision 4's unconditional default.
