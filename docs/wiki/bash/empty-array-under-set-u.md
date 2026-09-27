# Expanding an empty array under `set -u` on bash 3.2

**Origin:** readme-sync gate dying on the first drift it found | 2026-09-27
**Tags:** bash, set -u, unbound variable, empty array, macOS, bash 3.2, KNOWN_DRIFT

> `"${arr[@]}"` on an empty array is an *unbound variable* error on bash before 4.4 — and macOS still ships 3.2.57. `${#arr[@]}` is safe, so guard the length before the expansion.

---

## What it is

A script with `set -euo pipefail` and a deliberately empty array — a drift baseline, an allowlist,
an opt-in list — dies the moment it expands that array, but only on older bash. CI on Ubuntu
(bash 5) never sees it; the contributor running the same gate locally on a Mac sees nothing but
`line NN: ARR[@]: unbound variable`.

## How it works

```bash
bash -c 'set -euo pipefail; E=(); echo "${#E[@]}"; echo safe'          # → 0, safe
bash -c 'set -euo pipefail; E=(); for x in "${E[@]}"; do :; done'      # → E[@]: unbound variable
```

The fix is a length guard, not `|| true` (which would also swallow real failures):

```bash
[ "${#ARR[@]}" -eq 0 ] && return 1
for entry in "${ARR[@]}"; do ...
```

## Gotchas

- The failure surfaces *only on the path that has something to report*, so the script looks healthy
  until the day it needs to tell you something — and then it reports a bash error instead of the
  finding, and stops before checking anything else.
- `${arr[@]:-}` silences it but injects an empty element into the loop, which is usually worse.
- An empty array that is *documented* as empty on a healthy tree is the highest-risk shape: nothing
  exercises the expansion until the first real finding.

## References

- `.github/scripts/ci/02-readme-sync.sh` — `is_known_drift`, and the `KNOWN_DRIFT` baseline above it
