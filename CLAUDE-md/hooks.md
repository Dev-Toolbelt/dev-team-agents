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
| `04-` | User-facing notifications | `04-notifier.sh` |
| `05-` | External reporting (telemetry) | `05-telemetry.sh` |
| `99-` | Final/cleanup tasks | `99-graphify-refresh.sh`, `99b-archive-index.sh` |

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
| `01-` | Installation freshness | `01-check-updates.sh` — thin orchestrator over `scripts/hooks/lib/update-check.sh`; TTL-based update check, auto-updates when the `.auto-update` flag exists |
| `02-` | Context injection and reporting | `02-graphify-hint.sh` — injects a graph hint on Glob/Grep when `graphify-out/graph.json` exists; `02b-telemetry.sh` — queues agent-spawn and `/devteam:*` command events |

> One script per bare number. `02-graphify-hint.sh` keeps `02-` because it is referenced externally; the telemetry script is `02b-telemetry.sh`. Two files sharing a bare prefix leaves execution order to an alphabetical tiebreak on the rest of the filename — never rely on that. Add a **lowercase letter suffix** (`02b-`, `02c-`, …) instead.

Each sub-script must:
- **Match the filename pattern `NN-name.sh` or `NNx-name.sh`** — the same regex the Stop dispatcher uses. Non-matching files are skipped, not run; `DEVTEAM_HOOK_DEBUG=1` traces both
- Exit `0` in all normal paths — a PreToolUse sub-script runs on **every tool call** and must never block one
- Stay off the hot path: return from the TTL/cache check before forking anything (no `python3`, no network) — see `update-check.sh`, whose interval sidecar cache is invalidated with the `[ prefs -nt cache ]` bash builtin

### Hook Files Map

| Event | File | Dispatcher | Purpose |
|-------|------|-----------|---------|
| `SessionStart` | `scripts/hooks/session-start.sh` | — | Stale config detection, missing prefs |
| `PreToolUse` | `scripts/hooks/pre-tool-use.sh` | Dispatcher | Runs `pre-tool-use/`: update checks, graphify hint, telemetry queue |
| `PreCompact` | `scripts/hooks/pre-compact.sh` | — | Session summary before context compaction |
| `Stop` | `scripts/hooks/stop.sh` | Dispatcher | Runs `stop/`: session summary, orphan scans, lint, fingerprint uniqueness, notifications, telemetry, graph refresh, archive rotation. Computes `DEVTEAM_NO_CHANGES` and `DEVTEAM_TOUCHED_PATHS` once and exports them |
| — | `scripts/hooks/lib/session-summary-detect.sh` | Shared library | Not a hook. Sourced by **both** `pre-compact.sh` and `stop/01-session-summary.sh`; exports `TODAY`, `NOW`, `HAS_CHANGES`, `TODAY_COMMITS`. Changing it affects both hooks — test both. |
| — | `scripts/hooks/lib/touched-paths.sh` | Shared library | Not a hook. Sourced by `stop.sh` to compute the touched-path set once; sub-scripts `02`, `02b`, `03`, `03b` consume `DEVTEAM_TOUCHED_PATHS` instead of re-forking `git status` + `git log`, and fall back to computing it themselves when run standalone. |
| — | `scripts/hooks/lib/update-check.sh` | Shared library | Not a hook. The update-check engine behind `pre-tool-use/01-check-updates.sh`; also owns the auto-update path, which delegates the download to `scripts/lib/installer-fetch.sh` and **skips the upgrade entirely** when that library is absent rather than falling back to an unverified fetch. |

### PreCompact Block — Ask, Don't Just Comply

`pre-compact.sh` can only emit plain text on stdout — it has no way to render an interactive prompt. When its "SESSION SUMMARY REQUIRED" block appears, Claude must not silently write the entry (nor sit idle waiting on the user to notice). Instead, use `AskUserQuestion` with:

- **"Generate and write it automatically" (recommended)** — Claude drafts the entry from the session's own changes and writes it immediately
- **"I'll write it myself"** — wait for the user's own text, then write it verbatim
- **"Show me a draft first"** — Claude drafts the entry and shows it before writing, so the user can edit before compaction proceeds

This is a Claude-side response behavior, not a change to the hook script — the script's role stays limited to detection and blocking.
