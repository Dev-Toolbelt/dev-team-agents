# `set -e` inside a cleanup trap

**Origin:** packaging — `verify-formula-locally.sh` teardown aborting halfway | 2026-09-28
**Tags:** bash, set -e, errexit, pipefail, EXIT trap, cleanup, teardown, command substitution, brew uninstall, silent skip

> A bare `var=$(cmd | cmd)` inside an `EXIT` trap ends the whole trap the moment the
> pipeline exits non-zero. Everything after it — remaining teardown, and the assertions
> that would have reported the mess — silently does not run, and the script exits 1.

---

## What it is

A script with `set -euo pipefail` whose `EXIT` trap tears down machine state. Inside the
trap, `set -e` is still armed, so a single non-zero exit in a plain assignment terminates
the trap function. The teardown stops mid-way *and* the checks that would have said so are
part of what got skipped, so the run reports a failure with no explanation of which half of
the work happened.

Concretely, one spurious non-zero exit skipped the temp-directory removal and **both** of
the script's byte-identity assertions — that the machine's real `trust.json` and the tracked
formula were unmodified — which are the two guarantees its own header advertises
unconditionally, `--keep` or not.

## How it works

`pipefail`, not plain `set -e`, is what makes it fire here:

```bash
leftovers=$(printf '%s\n' "$post_list" | sort | comm -13 "$FORMULA_SNAPSHOT" - | tr '\n' ' ')
```

The pipeline's *last* command is `tr`, which always succeeds — so anyone auditing the final
command concludes the line is safe. `pipefail` promotes any earlier element's status to the
pipeline's, and the assignment inherits it.

The structural fix is to disarm, not to guard one line. `cleanup()` opens with:

```bash
set +e
set +o pipefail
trap - EXIT
```

then splits into a **mutating** teardown and a **read-only** verification half. Every step is
independent, returns 0, and records its own failure into a problem list; the exit code is
decided once at the end.

## Gotchas

- **The file looks internally consistent while exactly one occurrence is fatal.** Four other
  `var=$(brew …)` substitutions in the same trap path sit inside `if` conditions, where
  `set -e` does not apply. The `[ "$EXIT_RC" -eq 0 ] && EXIT_RC=1` shape in the same function
  is exempt too, being the left operand of `&&`. Only the bare assignment is exposed.
- **Guarding one line is not the fix.** Two more bare assignments of the same shape sit
  further down the same path — `trust_after=$(shasum …)` and `after=$(shasum …)` — so an
  unreadable file would have aborted before the verdict was printed.
- **"The command failed" and "the work did not happen" are different questions.**
  `brew uninstall` can remove the keg and still exit non-zero; an untrusted tap elsewhere on
  the machine is enough. A teardown should therefore assert on *state*, not on exit codes —
  this one re-lists and reports on presence.
- **A failed listing is not evidence of absence.** A `brew list` that could not be read is
  reported as its own problem, not as "the formula is gone".
- Did **not** reproduce, so nobody needs to re-investigate it: BSD `/usr/bin/comm` on macOS
  neither warns nor exits non-zero on unsorted input.

## References

- `packaging/verify-formula-locally.sh` — `cleanup`, `teardown`, `verify_invariants`, `problem`
- `docs/wiki/bash/empty-array-under-set-u.md` — the other `set -euo pipefail` failure that
  only surfaces on the path that has something to report
