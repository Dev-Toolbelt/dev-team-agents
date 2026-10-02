## Audit Report: cross-os-providers

### Scope

Every place where behavior differs between operating systems (macOS with BSD userland and
`/bin/bash` 3.2, Linux/WSL with GNU userland, Windows with Git Bash/MSYS2 or `cmd.exe`) and
between the supported providers (`scripts/lib/devteam/providers.py:ALL_PROVIDERS` — Claude Code,
opencode, Codex).

- **Provider layer:** `scripts/lib/devteam/{providers,bind,hooks,doctor,global_skills,tasks}.py`,
  `scripts/lib/render_provider.py`, `scripts/install*.sh`, `scripts/update.sh`,
  `scripts/rollback.sh`, `scripts/lib/provider-ownership.sh`,
  `scripts/lib/ensure-claude-framework.sh`, `opencode/plugin/dev-team-agents.ts`.
- **Hooks:** the seven dispatchers in `scripts/hooks/` and their sub-scripts, as each provider
  consumes them (exit codes, stdout/stderr, payload shape).
- **OS layer:** shell portability of every shipped script, `paths.py` platform detection,
  symlink/copy handling, text encoding.
- **Desktop app:** `app/src/cli/{resolve,invoke,stream}.ts`, provider lists, path comparison.
- **CI:** `.github/workflows/ci.yml` matrix and `.github/scripts/ci/**`.

Analysis ran in parallel: backend (provider parity), devops (cross-OS shell + CI), security,
frontend (desktop app), backend tests. The GNU `stat` defect was reproduced in an
`ubuntu:22.04` container; the bash 3.2 defect against the stock macOS `/bin/bash` 3.2.57.

### Critical Issues

| # | Severity | Layer | Description | Suggested Fix |
|---|----------|-------|-------------|---------------|
| 1 | high | Provider | opencode: the plugin's `runScript` resolves on `close` and discards the exit code and stderr, and both guards (`03-credential-guard.sh`, `02c-full-suite-guard.sh`) only act on `"tool_name":"Bash"` while opencode sends `"tool":"bash"` — no PreToolUse refusal ever blocks on opencode | Return `{code, stdout, stderr}` from `runScript`; throw on exit 2 in `tool.execute.before`; send `tool_name`/`tool_input` aliases; widen the guard gates |
| 2 | high | OS | `stat -f %m f \|\| stat -c %Y f` (`session-start.sh`, `hooks/lib/agent-usage.sh`): GNU `stat -f` prints a filesystem block before failing, so the captured value is garbage on every Linux/WSL session start | Probe `stat -c` first and validate the result is numeric |
| 3 | high | OS | `declare -A` (bash 4) in the no-python fallbacks of `install.sh` and `lib/state.sh`; macOS `/bin/bash` 3.2 aborts, and `state.sh` is sourced by `update.sh`/`check-updates.sh` | Parse the flat key/value list without associative arrays |
| 4 | med | Provider | opencode: Stop and PreCompact messages (stderr + exit 2) are discarded, so session-summary, ADR-gap and agent-lint prompts never reach the model | Capture stderr; push it into the compaction context; log it on idle |
| 5 | med | Hooks | Dispatchers keep the first non-zero exit, so an exit 1 from an earlier sub-script masks a later exit 2 refusal on every provider | Exit 2 wins over any other non-zero code |
| 6 | med | Hooks | Stop sub-scripts exit 2 with no `stop_hook_active` guard: a condition the turn cannot clear re-blocks every continuation | When the payload says `stop_hook_active: true`, report but do not block again |
| 7 | med | Provider | `install-codex.sh` replaces a malformed `.codex/hooks.json` with `{"hooks":{}}` and writes non-atomically — user hooks are lost (No-Destruction Rule) | Refuse with the conflict exit code and write nothing; write via temp file + `os.replace` |
| 8 | med | Both | Codex on Windows gets a bare `bash <relative path>` hook: no root walk (fails from a subdirectory) and `cmd.exe` resolves `bash` to WSL's `System32\bash.exe` or nothing | Emit the absolute Git Bash path and the same root walk, double-quoted for `cmd.exe` |
| 9 | med | Provider | `install-opencode.sh` reports success when `opencode.json` is JSONC (comments/trailing commas) and the merge fails — no `/devteam:*` commands registered | Check the merge status; fail with a message naming the file |
| 10 | med | Provider | `rollback.sh` never re-renders opencode/Codex; `update.sh` under `set -e` stops at the first failing provider and skips the rest | Re-run provider installers on rollback; make each provider step non-fatal with a warning |
| 11 | med | Provider | `doctor` checks hook wiring only in `.claude/settings.json`, warning forever on Codex/opencode-only binds and never checking their wiring | Check per provider recorded in the bind manifest |
| 12 | med | OS | `render_provider.py` reads/writes text without `encoding="utf-8"`; 22 sources fail to decode under cp1252, so the opencode/Codex render crashes on Windows. `_ENV_PASSTHROUGH` also drops `SYSTEMROOT`, `TEMP`, `USERPROFILE`, `PYTHONUTF8` | Explicit UTF-8 everywhere; pass the Windows-required variables through |
| 13 | med | OS | Under Git Bash, `ln -s` without `MSYS=winsymlinks:nativestrict` silently copies; the delegated installers record a copy as a link that then goes stale | Export the MSYS setting on `MINGW*/MSYS*`; verify `[ -L ]` after `ln` and fail clearly |
| 14 | med | OS | `sed -i ''` in `migrate-to-root.sh` is BSD-only — the v1→root migration leaves stale hook paths on Linux/WSL | `sed -i.bak … && rm -f *.bak` |
| 15 | med | FE | Windows: the app can never spawn the CLI — the only CLI is an extensionless python script, `.cmd` shims are refused by design, and the remedy text points at that same script | On win32, run a non-`.exe` CLI through the resolved python interpreter; fix the remedy text |
| 16 | med | FE | The CLI child environment drops `TEMP`/`TMP`, `PATHEXT`, `COMSPEC`, proxy and git/gh/ssh variables | Extend the allowlist with the variables the CLI and its git/gh children read |
| 17 | med | FE | Project path comparison is case-sensitive on case-insensitive macOS/Windows, offering a duplicate bind | Compare case-insensitively on darwin/win32 |
| 18 | med | BE | `resume_command` (`cd '<path>' && claude --resume …`) cannot run in `cmd.exe`/PowerShell 5 on Windows | Emit a PowerShell-safe form on Windows |
| 19 | low | OS | `date -d \|\| date -j` chain gives `ts=0` on BusyBox; hardcoded `/tmp` in `mktemp` ignores `$TMPDIR` | python fallback for the epoch; `${TMPDIR:-/tmp}` |
| 20 | low | Provider | `unbind` leaves `devteam:*` command keys in `opencode.json` | Remove only our keys on unbind |
| 21 | low | Provider | Global skill roots ignore `CODEX_HOME` and `XDG_CONFIG_HOME` (task board honors `CODEX_HOME`) | Resolve both before falling back to `~` |
| 22 | low | FE | Six hardcoded provider lists in the app with no check against `ALL_PROVIDERS` | Parity test reading `providers.py` |

### Security Findings

| # | Severity | Description | Fix |
|---|----------|-------------|-----|
| S1 | med | Same root cause as #1: the `git add -f credentials.local.json` refusal is a silent no-op on opencode | Covered by #1 |
| S2 | med | Delegated installers write through a symlinked `.codex`/`.opencode`: `_preflight` runs `require_inside` only for Claude artifacts, so a committed `.codex -> ~/.codex` lands dev-team hooks in the user's global Codex config (ADR-0022 parity gap) | `require_inside` for every delegated target; installers refuse a target whose real parent leaves the project |
| S3 | med | Standalone opencode/Codex installs never ignore `.dev-team-agents/credentials.local.json`; only the Claude installer and `bind` do | Add the same `info/exclude` entries from the shared framework step |
| S4 | med | Same as #8: the credential guard silently does not run for Codex on Windows | Covered by #8 |
| S5 | low | The app's PATH walk keeps relative entries (`.`), resolved against the app's working directory | Skip non-absolute PATH entries |

No scanners (secrets/SAST/dependency) were run: this was a targeted code audit.

### Infrastructure Findings

- The provider-contract, slim-bootstrap and hook-script coverage run on ubuntu only; `requires_bash()`
  skips every shell-driven test on Windows. #2 passes on macOS, #3 passes on ubuntu — neither is
  caught today.
- Recommended (minimal): run the provider-contract job on `macos-latest` too; add a bash 3.2 lint
  gate (no `declare -A`, `mapfile`, `readarray`, `${x,,}`, `local -n` in shipped scripts); a
  regression test that the session-start mtime helper returns a number.
- Docs drift: Codex hooks documented as "4 managed entries" (code writes 7; CI validates 4);
  `CLAUDE-md/hooks.md` says `02c` never blocks; DPAPI documented as unverified while the code
  says CI verifies it.

### Test Coverage Gaps

| Priority | Routine/Component | Why It Needs Tests | Suggested Scenarios |
|----------|-------------------|--------------------|--------------------|
| P0 | opencode plugin exit handling | Only enforcement path for guards on opencode; no tests exist | exit 2 blocks with stderr message; exit 0 passes; payload carries `tool_name` |
| P0 | Guards with every provider's payload | Guard gates are provider-shape sensitive | Claude, Codex, opencode payload per `ALL_PROVIDERS` |
| P1 | Dispatcher exit precedence | Refusal masking | sub-script 1 exits 1, sub-script 2 exits 2 → dispatcher exits 2 |
| P1 | `install-codex.sh` hooks merge | Data loss on malformed input; Windows form | malformed file refused and untouched; Windows command has root walk |
| P1 | mtime helper | GNU regression | numeric result on the host's `stat` |
| P2 | `install-opencode.sh` JSONC, rollback re-render, doctor per provider, render UTF-8, symlinked target containment, credentials ignore on standalone installs | Each is a silent failure today | one scenario each |

### Improvement Plan (ordered by value)

1. opencode guard enforcement + payload aliases + stderr surfacing (#1, #4, S1) — the only path where a secret can reach a remote silently — M
2. Dispatcher exit precedence + `stop_hook_active` guard (#5, #6) — refusals lost on every provider — S
3. GNU `stat`, bash 3.2, `sed -i`, `date`, `mktemp` portability (#2, #3, #14, #19) — broken on stock Linux/macOS — S
4. Codex installer: no-destruction merge, atomic write, Windows hook form (#7, #8, S4) — M
5. Containment and credentials ignore for delegated installers (S2, S3) — S
6. opencode JSONC merge, rollback/update provider re-render, unbind cleanup (#9, #10, #20) — M
7. Windows: UTF-8 render, env passthrough, Git Bash symlinks (#12, #13) — S
8. Doctor per provider, `CODEX_HOME`/XDG roots (#11, #21) — S
9. Desktop app on Windows: interpreter spawn, env, case-insensitive paths, relative PATH, provider parity test; Windows `resume_command` (#15–#18, #22, S5) — M
10. CI: macOS provider-contract leg, bash 3.2 lint gate; docs drift — S

### Out of Scope / Deferred

- A single python-launcher shim (`python3` → `python` → `py -3`) across ~30 shell call sites on
  Windows: a cross-cutting change that needs its own design decision; recorded as a follow-up.
- Shipping a native `devteam.exe` for Windows (packaging decision, ADR-0011 placeholder).

### Recommended Next Steps

- Run a manual smoke of the opencode and Codex installs on a real Windows host once #8, #12, #13
  and #15 are in: CI cannot exercise those paths today.

### Execution Status

Every item in the Improvement Plan was implemented on branch `audit/cross-os-providers`, plus two
regressions found by the code review of the change (a CI heredoc missing `import re`, and a
`client.app.log` rejection that could escape the plugin's hook runner and block a tool) and one
pre-existing defect surfaced by the test run: the Homebrew formula's `scripts/lib/devteam/*.py` glob
missed the `integrations/` subpackage, so the staged CLI failed to import (5 `test_packaging`
failures already on `main`).

Not verified on a real host: the Windows Codex hook command under `cmd.exe /C`, the Git Bash symlink
path, and the desktop app's interpreter launch on Windows — CI has no Windows leg for shell paths.
