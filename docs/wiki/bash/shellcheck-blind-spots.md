# Two shellcheck blind spots that cost a wild goose chase

**Origin:** SC2034 on the readme-sync parity gate | 2026-09-27
**Tags:** shellcheck, SC2034, SC1073, indirect expansion, directive, false positive, source-path

> shellcheck cannot trace `${!var}`, so every variable read only that way is reported unused — and a comment whose first word is the tool's own name is parsed as a directive and silently disables checking for the file.

---

## What it is

Two independent failure modes, both of which make shellcheck's output actively misleading rather
than merely incomplete.

## How it works

**1. Indirect expansion reads are invisible.** A gate that records per-check failures and then reads
them back by name:

```bash
for check in headings lines fences tables links; do
  local var="fail_$check"
  [ "${!var}" -eq 0 ] && continue
```

Static analysis cannot connect `fail_tables=1` to `${!var}`, so all five assignments raise SC2034
"appears unused". Deleting them — the obvious response — is what would actually break the gate.

**2. A comment can become a directive.** A line beginning with the tool's name followed by a space
is parsed as a directive, so ordinary prose that starts that way produces
`SC1073: Couldn't parse this shellcheck directive` and stops the file from being checked at all.

**3. `source=` resolves against the working directory**, not the script, so `-x` reports SC1091
for a sourced file that is right there on disk. `--source-path=SCRIPTDIR` fixes it for every
script at once.

## Gotchas

- SC2034 is a *warning* but shellcheck exits non-zero on any finding, so an info-level or
  warning-level false positive fails a blocking CI gate exactly like a real defect.
- Scope a `disable=` to the function, not the declaration line: the findings are raised at the
  **assignment** sites, so a directive above `local fail_x=0` suppresses nothing.
- Always record *why* a `disable=` is there. A bare disable is indistinguishable from hiding a real
  problem, and the next reader will try to "fix" it.

## References

- `.github/scripts/ci/02-readme-sync.sh` — the scoped `disable=SC2034` and its rationale
- `.github/scripts/ci/01-lint.sh` — `--source-path=SCRIPTDIR`
