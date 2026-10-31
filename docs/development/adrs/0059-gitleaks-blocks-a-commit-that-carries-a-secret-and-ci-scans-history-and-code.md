# ADR-0059: gitleaks blocks a commit that carries a secret and CI scans history and code

**Date:** 2026-10-31  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/hooks/pre-tool-use/03b-staged-secret-guard.sh`, `.github/scripts/ci/08-security-scan.sh`, `.github/security-tools.pin`, `.gitleaksignore`, `.gitleaks.toml`

## Context

gitleaks and semgrep were recommended in the security skills (`dependency-audit`,
`sast-pipeline`, `secret-management`) but nothing ran them. A secret reached history only if
someone remembered to audit, and the last audit (`docs/reports/2026-09-29/00-security-scanners.md`)
was a manual run. The skills also still used commands upstream had deprecated
(`gitleaks detect`/`protect`, `returntocorp/semgrep-action`).

An agent commits often and fast. The cheapest moment to stop a secret is before the commit
exists: after it, the value is in history and has to be rotated, not just deleted.

## Decision

Two gates, one per moment:

- **Before a commit, in every bound project.** A PreToolUse sub-script,
  `03b-staged-secret-guard.sh`, runs on a shell call whose command is `git commit` and runs
  `gitleaks git --pre-commit --staged --redact` in the target repository (the unstaged diff too
  for `-a`/`--all`; for `git add … && git commit` the add is applied to a copy of the index first,
  since the hook runs before the add). A finding refuses the call with exit 2, naming file, line
  and rule only. A commit that changes `.gitleaksignore` or `.gitleaks.toml` is scanned without
  them, so it cannot bring the suppression for its own secret.
  It runs for Claude Code, Codex and opencode through the shared dispatcher.
- **On every pull request and push to `main`, in this repository.** The `security-scan` CI job
  runs a sha256-pinned gitleaks over the full history and a pinned semgrep at ERROR severity
  with explicit rulesets and `--metrics=off`.

False positives are recorded where a reviewer sees them: a fingerprint in `.gitleaksignore`, an
allowlist entry in `.gitleaks.toml`, a `gitleaks:allow` or `# nosemgrep: <rule> -- <reason>`
comment. The guard has no environment-variable bypass, because an agent could set one itself.

Without gitleaks installed the commit is allowed, and one hint per project is queued through the
context-hints channel (ADR-0048) so the agent can tell the user. ADR-0060 is what puts gitleaks
on the machine in the first place.

## Consequences

### Positive
- A secret in an agent's commit is stopped before it reaches history, on all three providers.
- History and code of this repository are scanned on every PR, with the same gitleaks version
  the local guard uses.

### Negative
- The guard reads command text: a commit from a script, an alias, or `cd other && git commit`
  into another repository is not seen. CI is the backstop here; a project's own pre-commit hook
  is the backstop elsewhere.
- semgrep rulesets come from the registry at run time, so a ruleset update can turn CI red with
  no code change. The fix is a reviewed suppression or a code change, never dropping the ruleset.
- A false positive blocks the commit until someone marks it.

### Neutral
- The first baseline holds 31 reviewed findings: test fixtures, cPanel documentation examples
  and the Supabase publishable key (public by design, ADR-0029).
- A new Codex hook entry is not involved: the sub-script runs under the existing PreToolUse
  dispatcher, so no re-trust is needed.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| A git `pre-commit` hook installed into each project | Writes into `.git/hooks`, which the project or another tool may own; the PreToolUse dispatcher already runs on every provider |
| semgrep in the commit guard too | Seconds to minutes per run and network access for rulesets; too slow for every commit |
| A `DEVTEAM_SECRET_SCAN_CONFIRMED=1` bypass like the credential guard's | An agent could prefix it on its own; the ignore file and the inline comment leave a trace in the diff |
| Warn-only (Stop hook) | Fires after the commit, when the value is already in history |
