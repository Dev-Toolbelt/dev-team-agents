# Stripping control characters from repository text

**Origin:** ADR-0039 scope check (Stop hook 03h) | 2026-10-19
**Tags:** tr, control characters, newline, IFS read loop, sanitize, bidi override, C1 controls, sed, command substitution, printable ASCII

> `tr -d '\000-\037'` also deletes the newline, and `$(...)` silently drops trailing newlines. Both break the checks that are meant to catch unsafe names before they reach an agent.

---

## What it is

Text from a repository (ADR titles, filenames) is printed back to an agent. Before printing, control characters must go. Three traps appear when doing this in bash.

## How it works

**(a) Newline is in the range.** `\012` is inside `\000-\037`, so the following loop sees one unterminated line and its body never runs:

```bash
printf '%s\n' "$hits" | tr -d '\000-\037' | while IFS= read -r line; do ...; done   # body never runs
printf '%s\n' "$hits" | tr -d '\000-\011\013-\037\177' | while IFS= read -r line; do ...; done
```

**(b) Command substitution hides a trailing newline.** A check for "nothing non-printable left" passes on a name that ends in `\n`:

```bash
[ -z "$(printf '%s' "$name" | tr -d ' -~')" ]          # passes for "name\n"
[ "$(printf '%s' "$name" | tr -d ' -~'; printf x)" = x ]   # sentinel keeps the output
```

**(c) Multi-byte characters escape byte-oriented tools.** `[[:cntrl:]]` and `tr` work on bytes, so they miss C1 controls (U+0080–U+009F) and bidi overrides such as U+202E (`\xe2\x80\xae`). Strip them with `sed` in the C locale; this form works on BSD and GNU sed:

```bash
LC_ALL=C sed $'s/\xc2[\x80-\x9f]//g; s/\xe2\x80[\xaa-\xae]//g; s/\xe2\x81[\xa6-\xa9]//g'
```

Where a name must be a plain identifier, rejecting any non-printable-ASCII name outright is simpler and safer than stripping.

## Gotchas

- Use the sentinel form in (b) for every "is it clean" test. Plain `$(...)` tests lie about trailing newlines.
- Stripping is not validation. A sanitized title still has to be checked against the format it is printed into.

## References

- `scripts/hooks/stop/03h-adr-scope-check.sh` (`sanitize`)
- ADR-0039 (`docs/development/adrs/0039-*.md`)
