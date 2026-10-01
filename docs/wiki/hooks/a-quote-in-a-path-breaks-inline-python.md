# A quote in a path breaks inline python

**Origin:** review of the localized session-start notices found `open('$PREFS_FILE')` in the hook source | 2026-09-30
**Tags:** hook, shell, python, inline python, python3 -c, argv, heredoc, path with quote, syntax error, silent fallback, code injection, preferences

> A shell value pasted into `python3 -c` source becomes code. A `'` in the project path turns it into a SyntaxError that the hook's own fallback hides, so the hook runs on defaults and nothing looks broken.

---

## What it is

Hooks read JSON with short inline python snippets. Several built the snippet with the path inside it:

```bash
python3 -c "import json; d=json.load(open('$PREFS_FILE')); print(d.get('language','en'))" 2>/dev/null || echo en
```

The shell expands `$PREFS_FILE` before python sees the text. A project under `~/Code/it's-mine` produces `open('~/Code/it's-mine/…')`, an unterminated string. Every such call ends in `2>/dev/null || …`, so the error is swallowed and the default is used: language `en`, no suppression, no auto-update. The user sees a hook that ignores their preferences, with no error anywhere. A path chosen on purpose can close the string and run its own python.

## How it works

Hand values to python as arguments, and keep the source a literal the shell does not touch:

```bash
# one line: the source in single quotes, values after it
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("language","en"))' "$PREFS_FILE"

# several lines: the script on stdin, values as arguments
python3 - "$PREFS_FILE" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
PYEOF
```

`uc_read_pref` in `scripts/hooks/lib/update-check.sh` also takes the key and a default; the default is a python literal, so it arrives as `sys.argv[3]` and is parsed with `ast.literal_eval`, never pasted in.

## Gotchas

- **Escaping is not the fix.** Escaping `'` handles one character; the next path brings `\`, `$` or a newline. With argv the value is never parsed as code, whatever it contains.
- **The source must be single-quoted.** `python3 -c "…sys.argv[1]…"` still lets the shell expand any `$` in the source. Python strings inside it then use double quotes.
- **The heredoc delimiter must be quoted.** `<<'PYEOF'` keeps the shell out of the script; `<<PYEOF` expands `$` in it and brings the bug back.
- **`python3 -` reads the script from stdin**, so stdin is no longer free for data. Pass data as arguments or a file path.
- **A test needs the quote in the path.** Every fixture path was quote-free, so the suite was green for months. `tests/test_hook_quoted_paths.py` runs the hooks under a directory named `it's-mine`.

## References

- `docs/development/reuse-guidelines.md`: row `hook_python_argv` (lint pattern `open\(['"]\$`) and row `hook_message_language`, the other rule for text a hook builds.
- `scripts/hooks/session-start.sh`: the heredoc form. `scripts/hooks/lib/update-check.sh`: argv with a parsed default.
- `tests/test_hook_quoted_paths.py`: regression test.
