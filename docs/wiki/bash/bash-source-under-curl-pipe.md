# BASH_SOURCE is empty under curl pipe

**Origin:** audit backlog — install.sh sourced from CWD when piped, not from install dir | 2026-10-02
**Tags:** bash, BASH_SOURCE, curl pipe, stdin, install script, cwd, dirname, relative path, set -u, unbound variable, safe fallback

> Under `curl … | bash`, `BASH_SOURCE[0]` is empty and `$0` is `bash`, so `${BASH_SOURCE[0]:-$0}` → `.` → a relative `source` reads from the user's CWD, not the script dir.

---

## What it is

A shell script that derives its own directory to source libraries does this:

```bash
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "$_SCRIPT_DIR/lib/state.sh"
```

Under `curl https://…/install.sh | bash`, the bash process receives no `BASH_SOURCE[0]` (empty string) and `$0` is the literal string `bash`. With `set -u` enabled, `${BASH_SOURCE[0]:-$0}` evaluates to `bash`, whose dirname is `.` — the current directory. Any relative path in the script then sources from the user's CWD, which may execute project code or incomplete setup code as if it were part of the installer.

## How it works

Check whether `BASH_SOURCE[0]` names a real file before using it:

```bash
_SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$_SCRIPT_DIR" ] && [ -f "$_SCRIPT_DIR/lib/state.sh" ]; then
    source "$_SCRIPT_DIR/lib/state.sh"
else
    # Fallback: inline the code or fail gracefully
    echo "Install requires the full source tree" >&2
    exit 1
fi
```

Only a `BASH_SOURCE[0]` that names an actual file counts as "this script's location."

## Gotchas

- **Escaping `$0` is not the fix.** Under `curl | bash`, `$0` is the string `bash`; escaping does not change that.
- **This is not specific to install scripts.** Any setup script downloaded and piped faces the same risk.
- **The fallback cannot be a bare `set -u` workaround** (e.g., `${BASH_SOURCE[0]:-"$0"}`). It must distinguish between "file exists" and "file does not exist."
- **Relative paths in sourced files are resolved in the sourcer's context, not the sourced file's.** Once `source` runs from the wrong directory, a relative path in that file will make things worse, not better.

## References

- `scripts/install.sh` — the fix for the installer
- `tests/test_audit_report_fixes.py` — test coverage for piped install scenarios
