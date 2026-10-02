# An early exit sub-script masks a block

**Origin:** audit backlog — hook dispatcher piped payloads to sub-scripts, risking SIGPIPE | 2026-10-02
**Tags:** hook, dispatcher, pre-tool-use, post-tool-use, user-prompt-submit, stdin, pipe, SIGPIPE, exit 2, block code, full-suite guard, credential guard, payload

> A sub-script that exits without reading stdin dies with SIGPIPE (141) once the payload exceeds the pipe buffer, and that signal masks a later sub-script's exit 2 block, fail-opening the guard.

---

## What it is

The PreToolUse, PostToolUse, and UserPromptSubmit dispatchers piped the hook JSON payload directly to each sub-script:

```bash
printf '%s\n' "$INPUT" | env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?
```

A sub-script that read nothing from stdin and exited would receive SIGPIPE (141) from the write side once the payload exceeded the pipe buffer (typically ~65KB). The dispatcher's `[ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]` logic — first non-zero exit wins — let that 141 overwrite the intended exit 2 from the credential guard or full-suite guard that ran later. The block check was silently skipped.

## How it works

Feed the payload via a file instead of a pipe:

```bash
INPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/devteam-hook-input.XXXXXX")
trap 'rm -f "$INPUT_FILE"' EXIT
printf '%s\n' "$INPUT" > "$INPUT_FILE"

for script in …; do
    env -u BASH_ENV -u ENV bash "$script" < "$INPUT_FILE" || SCRIPT_EXIT=$?
    # Exit 2 is the blocking code and always wins; otherwise the first non-zero exit is kept.
    if [ "$SCRIPT_EXIT" -eq 2 ]; then
        EXIT_CODE=2
    elif [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done
```

Now `exit 2` always reaches the parent when a guard blocks, regardless of payload size.

## Gotchas

- **The trap must be set before the temp file exists,** or cleanup skips it on early exit.
- **SIGPIPE is platform behavior, not a bug in any one sub-script.** A sub-script that doesn't need stdin is fine; the bug is in the dispatcher's assumption that it can pipe without losing control.
- **This risk exists wherever a dispatcher pipes without caring whether the reader consumes it.** grep that pattern: `| env.*bash` in any hook.

## References

- `scripts/hooks/pre-tool-use.sh`, `scripts/hooks/post-tool-use.sh`, `scripts/hooks/user-prompt-submit.sh` — dispatcher fix
- `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — exit 2 guard
- `skills/shared/credentials/SKILL.md` — credential guard behavior
- `tests/test_pretooluse_hooks.py` — regression test, including SIGPIPE under 100KB payloads
