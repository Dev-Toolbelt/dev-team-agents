## Session Start Banner — Echo Rule

`scripts/hooks/session-start.sh` prints a `[DEVTEAM:SESSION_BANNER]`-tagged block (name, installed version, repo link, language, auto-update status, worktree status) once per session. **A `SessionStart` hook's stdout is delivered to Claude as context, not printed to the user's terminal** — unlike a plain shell script, nothing renders it on screen unless Claude's own reply does.

**Trigger: `[DEVTEAM:SESSION_BANNER]` present in session-start context.** Reproduce the three lines that follow the tag **verbatim, unmodified**, as the first thing in your **first reply of the session** — before any other text, tool call, or acknowledgment. Do not summarize, translate, or reformat the block. This applies to every session, including ones not routed through a `/devteam:*` command, since `session-start.sh` fires for all of them.

If the tag is absent from context (a session resumed mid-conversation, a hook error, or a provider that does not deliver SessionStart context this way), do not fabricate the banner — say nothing about it.

---

## Stop Hook (Automated Enforcement)

`install.sh` registers `scripts/hooks/stop.sh` as the `Stop` dispatcher in `.claude/settings.json`. This dispatcher runs every sub-script in `scripts/hooks/stop/` whose filename matches the naming convention, in order, including `01-session-summary.sh`, which:

- Runs automatically each time Claude finishes responding
- Detects uncommitted changes **or commits made today** without a session-summary entry for today
- Outputs a structured reminder visible to Claude on the next turn, which then writes the summary

No manual setup is required — the installer handles registration.

### Stop Hook Sub-script Convention

Sub-scripts in `scripts/hooks/stop/` are executed in alphabetical order by filename. The numeric prefix controls execution order:

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | State detection and collection (session context) | `01-session-summary.sh` |
| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh`, `02b-orphan-template-scan.sh` |
| `03-` | Static validation | `03-agent-lint.sh`, `03b-fingerprint-uniqueness.sh`, `03c-reuse-lint.sh`, `03d-design-token-lint.sh` |
| `04-` | User-facing notifications | _(disabled — see § Disabled Hooks)_ |
| `05-` | External reporting (telemetry) | _(disabled — see § Disabled Hooks)_ |
| `99-` | Final/cleanup tasks | `99b-archive-index.sh` (graphify refresh disabled — see § Disabled Hooks) |

Each sub-script must:
- **Match the filename pattern `NN-name.sh` or `NNx-name.sh`** — regex `^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$`. The dispatcher **skips any file that does not match**, so a draft, a `.sh.bak`, or a `notes.sh` left in the directory is ignored instead of being auto-run on every Stop. Set `DEVTEAM_HOOK_DEBUG=1` to see what was run and what was skipped
- Accept `--quiet` flag and suppress output when OK
- Honour the dispatcher's `DEVTEAM_NO_CHANGES=1` fast path — a Stop with no staged/unstaged changes and no commits today must not trigger a full scan
- Reuse `DEVTEAM_TOUCHED_PATHS` / `DEVTEAM_TOUCHED_COMPUTED` (exported by `stop.sh` via `scripts/hooks/lib/touched-paths.sh`) instead of re-running `git status`/`git log`, while still working standalone when they are unset
- Exit with code `0` when nothing is wrong
- Exit non-zero only when action is required from the user

Prefix `00-` is reserved for future preconditions. When adding a new sub-script, choose the correct tier and pick a number within that tier (e.g. `02-new-check.sh`). When the tier's number is already taken and the new script must run adjacent to the existing one, append a **lowercase letter suffix** instead of claiming a new number — `02b-`, `02c-`, … — which sorts immediately after `02-` and keeps the tier boundaries intact.

Sub-scripts that call a `helpers/` tool (`03b-fingerprint-uniqueness.sh`, `99b-archive-index.sh`) must degrade silently when `helpers/` is absent — it is stripped from every installed project.

Data files may live under `scripts/hooks/stop/`: `tips/` holds the notifier's rotating tips as one file per locale (`tips.en.txt`, `tips.pt-BR.txt`, `tips.es.txt`, 15 lines each). Only the selected locale's file is read, and only after the once-per-day gate opens. They are not `.sh` and are never dispatched.

### PreToolUse Hook Sub-script Convention

Sub-scripts in `scripts/hooks/pre-tool-use/` are run by `scripts/hooks/pre-tool-use.sh`, which reads the hook JSON from stdin once and pipes the same payload to every sub-script in alphabetical order. The dispatcher propagates the first non-zero exit code.

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | Installation freshness | _(free — the update check moved to `SessionStart`, see below and § Disabled Hooks)_ |
| `02-` | Context injection and reporting | `02-graphify-hint.sh` — injects a graph hint on Glob/Grep when `graphify-out/graph.json` exists; telemetry queueing disabled, see § Disabled Hooks; `02c-full-suite-guard.sh` — nudges on unscoped full-suite test commands (Bash), see below |

> One script per bare number. `02-graphify-hint.sh` keeps `02-` because it is referenced externally; the telemetry script is `02b-telemetry.sh`. Two files sharing a bare prefix leaves execution order to an alphabetical tiebreak on the rest of the filename — never rely on that. Add a **lowercase letter suffix** (`02b-`, `02c-`, …) instead.

Each sub-script must:
- **Match the filename pattern `NN-name.sh` or `NNx-name.sh`** — the same regex the Stop dispatcher uses. Non-matching files are skipped, not run; `DEVTEAM_HOOK_DEBUG=1` traces both
- Exit `0` in all normal paths — a PreToolUse sub-script runs on **every tool call** and must never block one
- Stay off the hot path: return from the TTL/cache check before forking anything (no `python3`, no network) — see `update-check.sh`, whose interval sidecar cache is invalidated with the `[ prefs -nt cache ]` bash builtin

`02c-full-suite-guard.sh` is the per-command safety net for `skills/shared/scoped-test-execution/SKILL.md`: when a `Bash` command matches an unscoped full-suite shape (e.g. `pytest` with no path/`-k`, `vendor/bin/phpunit` with no `--filter`), it injects an `additionalContext` reminder of the rule — it never blocks, consistent with the rule above. It complements, and does not replace, the `SessionStart` reminder below, which covers sessions that never issue a matching Bash command but still need the rule in context from the start (e.g. work happening outside `/devteam:*` routing, where `project-context`'s mandatory skill load is never triggered).

### Hook Files Map

| Event | File | Dispatcher | Purpose |
|-------|------|-----------|---------|
| `SessionStart` | `scripts/hooks/session-start.sh` | — | Stale config detection, missing prefs, TTL-gated update check (moved from `PreToolUse` — runs once per session instead of once per tool call), unconditional scoped-test-execution reminder, `[DEVTEAM:SESSION_BANNER]` identity banner (see § Session Start Banner — Echo Rule above) |
| `PreToolUse` | `scripts/hooks/pre-tool-use.sh` | Dispatcher | Runs `pre-tool-use/`: graphify hint, full-suite test guard (update checks and telemetry queue disabled, see § Disabled Hooks) |
| `PreCompact` | `scripts/hooks/pre-compact.sh` | — | Session summary before context compaction |
| `Stop` | `scripts/hooks/stop.sh` | Dispatcher | Runs `stop/`: session summary, orphan scans, lint, fingerprint uniqueness, archive rotation (notifications, telemetry, and graph refresh disabled, see § Disabled Hooks). Computes `DEVTEAM_NO_CHANGES` and `DEVTEAM_TOUCHED_PATHS` once and exports them |
| — | `scripts/hooks/lib/session-summary-detect.sh` | Shared library | Not a hook. Sourced by **both** `pre-compact.sh` and `stop/01-session-summary.sh`; exports `TODAY`, `NOW`, `HAS_CHANGES`, `TODAY_COMMITS`. Changing it affects both hooks — test both. |
| — | `scripts/hooks/lib/touched-paths.sh` | Shared library | Not a hook. Sourced by `stop.sh` to compute the touched-path set once; sub-scripts `02`, `02b`, `03`, `03b` consume `DEVTEAM_TOUCHED_PATHS` instead of re-forking `git status` + `git log`, and fall back to computing it themselves when run standalone. |
| — | `scripts/hooks/lib/update-check.sh` | Shared library | Not a hook. The update-check engine, now sourced directly by `session-start.sh`; also owns the auto-update path, which delegates the download to `scripts/lib/installer-fetch.sh` and **skips the upgrade entirely** when that library is absent rather than falling back to an unverified fetch. |

### Disabled Hooks

The following sub-scripts are disabled by renaming them out of the dispatcher's filename convention (`^[0-9]{2}[a-z]?-...\.sh$`, see above) — the file and its logic are untouched, they simply aren't invoked. Rename back to the original `NN-name.sh` to re-enable.

| Disabled file | Was | Status |
|---|---|---|
| `stop/_disabled-04-notifier.sh` | `04-notifier.sh` | Pending review — disabled 2026-08-06, no observed user-visible benefit relative to its per-Stop cost |
| `pre-tool-use/_disabled-02b-telemetry.sh` | `02b-telemetry.sh` | Pending review — disabled 2026-08-06, part of the telemetry module being reviewed for optimization |
| `stop/_disabled-05-telemetry.sh` | `05-telemetry.sh` | Pending review — disabled 2026-08-06, part of the telemetry module being reviewed for optimization |
| `pre-tool-use/_disabled-01-check-updates.sh` | `01-check-updates.sh` | Superseded — logic moved into `session-start.sh` so the check runs once per session instead of on every tool call |
| `stop/_disabled-99-graphify-refresh.sh` | `99-graphify-refresh.sh` | Deliberate change — Graphify refresh is on-demand only now; run manually: `bash .dev-team-agents/scripts/graphify-refresh.sh` |

### PreCompact Block — Ask, Don't Just Comply

`pre-compact.sh` can only emit plain text on stdout — it has no way to render an interactive prompt. When its "SESSION SUMMARY REQUIRED" block appears, Claude must not silently write the entry (nor sit idle waiting on the user to notice). Instead, use `AskUserQuestion` with:

- **"Generate and write it automatically" (recommended)** — Claude drafts the entry from the session's own changes and writes it immediately
- **"I'll write it myself"** — wait for the user's own text, then write it verbatim
- **"Show me a draft first"** — Claude drafts the entry and shows it before writing, so the user can edit before compaction proceeds

This is a Claude-side response behavior, not a change to the hook script — the script's role stays limited to detection and blocking.
