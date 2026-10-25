# zsh does not split an unquoted variable into words

**Origin:** ad-hoc commit loop run through the Bash tool, which runs under zsh | 2026-10-25
**Tags:** zsh, word splitting, unquoted variable, pathspec, git add, ${=var}, set -e, bash tool

> In zsh an unquoted `$FILES` is one word, so `git add -- $FILES` with `FILES="a b c"` looks for a single file named `a b c`. Split the list on purpose.

---

## What it is

The Bash tool in this environment runs `zsh`, not `bash`. Bash splits an unquoted parameter expansion on `IFS`; zsh does not. Any ad-hoc command that expects a space-separated list from a variable silently changes meaning.

## How it works

```zsh
FILES="a.md b.md c.md"
git add -- $FILES            # zsh: one pathspec "a.md b.md c.md" -> "did not match any files"
git add -- ${=FILES}         # zsh word split on purpose -> three pathspecs
```

An array avoids the flag entirely:

```zsh
files=(a.md b.md c.md)
git add -- "${files[@]}"
```

Under `set -e` the failed `git add` stops a loop before its first commit, so the failure looks like a partial commit run rather than a quoting bug.

## Gotchas

- Repository scripts with `#!/usr/bin/env bash` are not affected. This applies to commands typed into the tool.
- Running the snippet as `bash -c '…'` also works and matches what the scripts expect.
- Path lists with spaces break both shells. Use arrays or `-z` NUL streams, not `${=var}`.

## References

- `skills/shared/token-efficiency/SKILL.md` (prefer small, explicit commands over long shell pipelines)
