# Matching an untrusted glob with bash's own matcher

**Origin:** ADR-0039 scope check (Stop hook 03h) | 2026-10-19
**Tags:** bash, glob, pattern matching, [[ ==, case, backtracking, bash 3.2, extglob, grep -E, glob_to_ere

> Never match a glob that comes from repository content with `[[ "$s" == $p ]]` or `case "$s" in $p)`. Both backtrack without bound, and a hostile pattern can hang a hook. Convert it to an anchored ERE and match with `grep -E`.

---

## What it is

A glob written in repository content (an ADR `Applies to:` line, a config list) is data, not code. Feeding it to bash's pattern matcher lets the author of that content control how long the matcher runs.

## How it works

Cost grows roughly with `length^stars`, so a star cap does not bound it.

| Matcher | Behaviour |
|---------|-----------|
| `[[ "$s" == $p ]]` on bash 3.2 (macOS `/bin/bash`) | `*a*a*a*a*a*b` against a 200-char path ran past 45 s |
| `[[ "$s" == $p ]]` on bash 4.1+ | Applies extended globbing regardless of `shopt -u extglob`; nested `+(+(a\|aa))…` hangs with zero `*` (measured on bash 5.2) |
| `case "$s" in $p)` | Honours `extglob`, so it is also exposed on 4.1+ |
| `grep -E` on an anchored ERE | Instant on both: 0.2 s for 1000-char paths on bash 3.2 |

The fix used in `scripts/hooks/stop/03h-adr-scope-check.sh` (`glob_to_ere`):

```bash
glob_to_ere() {
  printf '^%s$' "$(printf '%s' "$1" | sed -e 's/[].[^$\\+(){}|]/\\&/g' -e 's/\*/.*/g' -e 's/?/./g')"
}

# Build one -e per pattern, then match all patterns in a single grep call
exprs=()
for p in "${patterns[@]}"; do exprs+=(-e "$(glob_to_ere "$p")"); done
printf '%s\n' "$candidates" | grep -E "${exprs[@]}"
```

## Gotchas

- Only `*` and `?` are supported. `[ab]` classes become literal characters. Document this where the glob syntax is user-facing.
- Escape the ERE metacharacters before converting `*` and `?`, or a `.` or `(` in a path becomes live syntax.
- Reject patterns with `(` outright, and cap the length and star count, as defence in depth. The cap is not the fix.

## References

- `scripts/hooks/stop/03h-adr-scope-check.sh` (`glob_to_ere`)
- ADR-0039 (`docs/development/adrs/0039-*.md`)
