# Security scanner pass — 2026-09-29

**This is a scanner pass, not a guardian audit pass.** It adds no row to `_index.md`'s Statistics
table, because it measures nothing that table tracks: there is no fingerprint coverage percentage,
no Fase 1/1b verification, no mortality rate. One original finding is registered in the bank
(`auto-github-actions-pinned-to-mutable-major-tags`); everything else here is either clean or a
false positive, and a false positive is not a finding.

**Why this pass exists.** Three scanners had been recorded as **NOT RUN because they were not
installed** — which means *unverified*, not clean. That distinction was carried in the session
record for several rounds. All three are now installed and have been run. The results below are
from runs executed on this machine on 2026-09-29, each with its command and tool version stated.

> A first attempt at this pass was delegated to a subagent, which completed the scans and then died
> twice before writing anything — once to a stream stall, once to the host sleeping. Its scan output
> is not quoted here, because a result whose provenance cannot be shown is not evidence. Every number
> below is from a run whose command line appears beside it.

---

## Summary

| Scanner | Version | Verdict | Findings |
|---------|---------|---------|----------|
| `gitleaks` | 8.30.1 | **clean** | 0 across 658 commits of full history |
| `osv-scanner` | 2.6.0 | **1 package, no remedy exists** | `extract-zip@2.0.1`, dev-only, 2 advisories — re-confirmed against the final 695-package lockfile |
| `semgrep` | 1.176.0 | **1 actionable, 17 false positives** | 33 raw → 16 actionable (one theme) |

Nothing found here is exploitable against a user of this repository today. The one actionable
finding is a supply-chain *hardening* gap in CI, not a defect.

---

## 1. `gitleaks` — secrets in history

```
gitleaks git --redact --report-format json --no-banner
```

**658 commits scanned, ~8.66 MB, 0 leaks.**

This is the result that most needed running, and it is the one that came back clean. This
repository's own rules state that credential *values* never live in a project file and never appear
in a commit — history is exactly where that rule gets violated without anyone noticing, and the
whole history is now checked rather than the working tree.

Two files that a naive reading would flag were examined and are **by design**, not leaks:
`credentials.local.json` at the repository root (read on purpose by
`docs/prompts/posthog-metrics-report.md`) and `.dev-team-agents/user-data/credentials.local.json`.
gitleaks did not flag either, so no suppression or allowlist entry was needed — worth recording so
the next pass does not add one speculatively.

---

## 2. `osv-scanner` — dependency advisories

```
osv-scanner scan source --lockfile app/package-lock.json --format json
```

**Scanned twice, because the lockfile changed during this round.** First pass: 592 packages. The
render-test work then added four devDependencies (`@testing-library/react`,
`@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`), so the scan was **re-run against
the final lockfile**: **695 packages, and still exactly one vulnerable package — the same one.** A
dependency-scan result that predates the last `npm install` of its own round is not a result, which is
why this says so rather than quoting the first number alone.

| Package | Version | Advisory | Max severity | Fixed in |
|---------|---------|----------|--------------|----------|
| `extract-zip` | 2.0.1 | `GHSA-7pqw-9j4j-h8q3` (`CVE-2026-19693`) — arbitrary file writes through symlink archive entries | 8.1 | **nothing published** |
| `extract-zip` | 2.0.1 | `GHSA-jmr9-qjv8-65gv` (`CVE-2026-56876`) — unvalidated symlink path traversal | 8.6 | **nothing published** |

### The `extract-zip` verdict

The standing claim was "two HIGH advisories with no non-breaking remedy". **That claim is too
generous to itself: there is no remedy at all, breaking or otherwise.** Both advisories' affected
ranges contain no `fixed` event — no patched version of `extract-zip` exists. An upgrade is not
being deferred for compatibility reasons; there is nothing to upgrade to. A lockfile `overrides`
entry has no target.

**Dependency path, traced rather than assumed.** Exactly one package declares it:

```
electron (devDependency of app/)  →  dependencies: { "extract-zip": "^2.0.1" }
```

`extract-zip` is installed at `node_modules/extract-zip` with `"dev": true`. Consequences, in order
of how much they reduce the risk:

1. **It ships in no artifact.** The `electron` npm package is a build-time tool; a packaged app
   bundles the Electron *runtime binary*, not this `node_modules` tree. No end user ever executes
   this code.
2. **Its only caller is Electron's own `install.js`**, which downloads the Electron binary archive
   and unpacks it. The attack requires a malicious zip *at that URL*, and Electron's downloader
   verifies the release SHASUMS — so exploitation needs a compromised official Electron release or
   a checksum bypass, not merely a hostile network.
3. **CI never runs it.** `.github/scripts/ci/05-app.sh` uses `npm ci --no-audit --no-fund
   --ignore-scripts`, so the postinstall that would extract anything does not execute on a runner.
   The measured 572-installed-against-641-locked figure in that gate's own log is the evidence.
   The exposed population is therefore *developer machines that ran a plain `npm install`*, extracting
   a checksum-verified archive from Electron's release host.

**Residual risk: accepted.** Not because the severity is low — 8.6 is not low — but because every
precondition for reaching the vulnerable code is outside the attacker's reach without first
compromising an Electron release. **Reopen when either is true:** a patched `extract-zip` is
published (add an `overrides` entry in the same change), or the app starts extracting an archive it
did not fetch from a checksum-verified source.

No dependency change was applied **to remediate anything**: `extract-zip` has no patched version to
move to. The four devDependencies that did land in `app/package-lock.json` this round are the render-test
environment, added by that work and not by this pass, and the re-scan above covers them — none is
flagged. They are dev-only and reach no packaged artifact, the same as the rest of the app's build
tooling.

---

## 3. `semgrep` — static analysis

```
semgrep scan --metrics=off \
  --config p/python --config p/typescript --config p/secrets --config p/github-actions \
  --config r/bash --config p/command-injection \
  --exclude node_modules --exclude dist --exclude release \
  scripts app/src app/test .github helpers agents skills commands templates tests
```

**416 files scanned** (272 `.md`, 66 `.sh`, 27 `.py`, 18 `.ts`, 17 `.tsx`), **33 raw findings**,
**13 scanner errors**.

`--metrics=off` and explicit rulesets rather than `--config auto`: `auto` reports repository context
to semgrep.dev. Rules are still fetched from the registry; no code from this repository is uploaded.
Note for the next pass: **`p/bash` does not exist** (HTTP 404) — the shell ruleset is `r/bash`. A run
that names `p/bash` fails the whole config load and can return zero findings while looking like it
worked.

### 3.1 Actionable — 16 findings, one theme

**`github-actions-mutable-action-tag` — HIGH impact — `.github/workflows/ci.yml` ×11,
`.github/workflows/release.yml` ×5.**

Every `uses:` in both workflows names a mutable major tag:

| Action | Count | Party |
|--------|-------|-------|
| `actions/checkout@v4` | 8 | GitHub first-party |
| `actions/setup-python@v5` | 4 | GitHub first-party |
| `actions/upload-artifact@v4` | 1 | GitHub first-party |
| `actions/download-artifact@v4` | 1 | GitHub first-party |
| `actions/setup-node@v4` | 1 | GitHub first-party |
| `ruby/setup-ruby@v1` | 1 | **third-party** |

The finding is real: a major tag is a moving pointer, and whoever controls the tag controls what
runs in CI. This is not hypothetical — tag-repointing supply-chain attacks against popular actions
have happened.

**Recommendation: pin `ruby/setup-ruby@v1` to a commit SHA; leave the five `actions/*` on their
major tags.** The reasoning, stated so it can be argued with rather than re-derived:

- The blast radius differs by workflow. `release.yml` is the privileged one — it is the workflow a
  tag push runs, and the only one positioned to publish anything. `ci.yml` runs on pull requests,
  including from forks.
- The trust differs by publisher. `actions/*` is GitHub's own org, hosted on the platform running
  the workflow; compromising it is compromising the runner's operator. `ruby/setup-ruby` is a
  third-party repository and is the one entry where pinning changes the threat model rather than
  the paperwork.
- Pinning all 16 without an automated bump mechanism trades a small, well-understood risk for a
  guaranteed maintenance failure: SHAs nobody updates, and security patches to `actions/checkout`
  silently not applied. If Dependabot is ever configured for `github-actions`, pin everything —
  that is the change that makes full pinning correct, and it is the reopening condition.

**Not applied in this pass.** This is a CI behaviour change and it is registered as a finding for a
decision, not executed under a scanner's authority.

### 3.2 False positives — 17 findings, every one checked

Each was opened and read. None is a defect, and one of the scanner's remedies would *introduce* a
vulnerability if followed.

**`insecure-file-permissions` — MEDIUM — `scripts/lib/devteam/paths.py:311`. The rule is wrong here,
not merely noisy.** The line is `os.chmod(str(created), 0o700)` applied to **directories** the store
creates. The rule's message reads: *"These permissions `0o700` are widely permissive… A good default
is `0o644`"*. On a directory, `0o700` is owner-only and `0o644` removes the owner's execute bit
(making the directory untraversable) while granting **world read**. That directory tree holds
`data/machines/<machine-id>/secrets/`. Following this rule's advice would open the secrets directory
to every local user. The rule is written for files and misfires on directories.
**Do not "fix" this, and do not let a future pass re-file it** — it is registered as a discard below.

**`ifs-tampering` — LOW — `helpers/agent-lint.sh:156`.**
`tier_allowed=$(IFS=", "; echo "${VALID_TIERS[*]}")` — `IFS` is set *inside a command substitution*,
so the change is scoped to that subshell and cannot affect the rest of the script. This is the
idiomatic array-join in bash.

**`unquoted-variable-expansion-in-command` / `unquoted-command-substitution-in-command` — 15
findings across 10 shell scripts.** Three distinct benign idioms, all confirmed by reading each line:

| Idiom | Lines | Why it is safe |
|-------|-------|----------------|
| Integer exit/return | `stop.sh:75`, `pre-tool-use.sh:38`, `02-readme-sync.sh:194,218` — `exit $EXIT_CODE`, `return $rc`, `exit $FAIL` | The value is an integer the script itself set; there is no word to split |
| Boolean-as-command | `install.sh:125`, `state.sh:143`, `orphan-template-scan.sh:111`, `check-codex-compat.sh:57,110`, `_disabled-04-notifier.sh:110` — `$first \|\| echo ","`, `if $FIX_MODE;`, `$QUIET \|\| echo …` | The variable holds the literal `true` or `false` and is being *executed*; quoting it is what would be wrong |
| Arithmetic expansion | `session-start.sh:249,256` — `echo $(( ( $(date +%s) - ts ) / 86400 ))` | `$(( ))` yields a number; no field splitting applies |
| Heredoc body | `slim-bootstrap.sh:199` — `$(cd "$SOURCE" && ls -1)` inside `<<EOF … EOF`, consumed by `while IFS= read -r` | Command substitution in a heredoc is text, not a word list, and `IFS= read -r` preserves whole lines including spaces |

**Corroboration, not just argument:** `.github/scripts/ci/01-lint.sh` runs `shellcheck` over 67
shell scripts and passes. `SC2086` is precisely the unquoted-expansion check, so a genuine instance
of this class would already be failing a blocking gate.

### 3.3 Coverage limit — 13 scanner errors, and what they mean

Eleven are semgrep's bash parser failing on the **first line** of a script
(`scripts/new-adr.sh:1`, `scripts/hooks/pre-tool-use/03-credential-guard.sh:1`,
`helpers/archive-index.sh:1`, and others): a shebang immediately followed by a comment block. Two
are `.github/scripts/ci/05-app.sh:201` (`>=` unexpected) and a duplicate of it.

**This is a coverage gap, and it is the honest limit of this pass:** those files were listed as
scanned but were not fully analyzed by the shell rules. `shellcheck` does cover them, on every pull
request, which is why this is recorded rather than escalated. A future pass should not report these
files as "clean by semgrep" — they are *unparsed* by semgrep.

---

## 4. Design review — the write-action surface added in this change set

Requested as review only; nothing here was edited. The app's write actions
(`bind`, `unbind`, `sync`, `pin`, `upgrade`) are reached through a `contextBridge` of named
operations, and the two provenance rules are the load-bearing part:

- **Every write names its target by `project_id`**, resolved in the main process against the
  registry's own `list --json` answer before an argv is built. An id the registry does not know is
  refused with no process spawned. This is what stops a compromised renderer from aiming `unbind`
  at a directory of its choosing — the renderer never supplies a path.
- **`bind` is the inverse**, because it has no existing project to name: the main process opens the
  native directory picker itself and records the chosen path in a per-session offered set;
  `bindProject` refuses any path not in that set.

**Bypasses considered.** A renderer that guesses a valid `project_id` still only reaches a project
the user already bound — it cannot reach a new path, which is the capability that matters. The
offered-set is per-session and in-memory, so it cannot be primed across restarts. The remaining
exposure is a renderer that is already executing attacker code, which can invoke any *legitimate*
action the user could invoke — that is not closed by this design and is not meant to be; it is held
by `sandbox: true`, `contextIsolation: true`, `nodeIntegration: false`, the absence of a generic
`invoke(channel, …)`, and `setWindowOpenHandler` denying outright.

**One residual worth stating plainly:** `devteam cred get` is unreachable because no allowed command
starts with `cred`, asserted by test. That is stronger than a special case, and it means no
credential value can enter the app's process by any route the app has. It also means the app has no
credential UI to audit — the moment one is added, that assertion becomes the thing to re-check.

**Not assessed:** anything about the renderer's UI code, which was being written concurrently with
this pass and was mid-edit. It is not reported as clean; it is not reported at all.

---

## 5. What remains unverified

| Item | Why |
|------|-----|
| semgrep's shell coverage of 11 scripts | Parser errors on shebang+comment first lines (§ 3.3). `shellcheck` covers them |
| The packaged app's own contents | No signed build exists to scan; every build is unsigned by configuration |
| `winget` manifest validity | Windows-only tooling; see `packaging/README.md` § Verification |
| Whether a future `extract-zip` fix exists | Checked on 2026-09-29 only. Re-check on any `electron` bump |

---

## Fingerprint registered

- `auto-github-actions-pinned-to-mutable-major-tags` — **MEDIUM** (HIGH impact, low likelihood) —
  target: `.github/workflows/ci.yml`, `.github/workflows/release.yml` — all 16 `uses:` name mutable
  major tags; recommendation is to pin `ruby/setup-ruby@v1` (third-party, and `release.yml` is the
  privileged workflow) and leave `actions/*` until a Dependabot `github-actions` config makes full
  pinning maintainable.

## Discarded, registered so they are not re-filed

- **`insecure-file-permissions` at `scripts/lib/devteam/paths.py:311`** — the rule's remedy (`0o644`
  on a directory) would make the secrets directory world-readable and untraversable. `0o700` is
  correct. A pass that re-files this has not read the line.
- **The 16 unquoted-expansion / IFS shell findings** — three benign idioms (integer exit,
  boolean-as-command, arithmetic expansion) plus one heredoc body, each verified line by line, and
  all inside a tree where `shellcheck`'s `SC2086` already gates on every pull request.
