#!/bin/bash
# auth-gate.sh — the account gate for the delegated installers (ADR-0029 SR-30). Sourced, never run.
#
# opencode and Codex installs reach the project without going through `devteam bind`, so each
# installer calls `ag_gate` before it writes. The decision is `devteam auth check --json`
# itself (exit 0 entitled, 1 not entitled, 3 an online check is needed and could not be made,
# 4 lock conflict); a cached entitlement inside its offline window is already an exit 0.
#
# Mode comes from `gate_mode` in scripts/lib/auth-config.json: `warn` (also when the key is
# absent) prints one notice on stderr and lets the install proceed; `enforce` refuses with
# AG_BLOCKED_EXIT. Any other value reads as `enforce`, so a typo does not open the gate.
# When no CLI can be run (a slim tree without scripts/cli, an older `devteam` with no `auth`)
# the gate is skipped with a note: it cannot decide, and the install must not fail on that.

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/python.sh"
# shellcheck source=python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

AG_BLOCKED_EXIT=5

# ag_mode <scripts-dir> -> prints warn|enforce
ag_mode() {
  local cfg="$1/lib/auth-config.json"
  [ -f "$cfg" ] || { echo warn; return 0; }
  python3 - "$cfg" <<'PY' 2>/dev/null || echo warn
import json, sys
try:
    value = json.load(open(sys.argv[1])).get("gate_mode", "warn")
except Exception:
    value = "warn"
print(value if value in ("warn", "enforce") else "enforce")
PY
}

# ag_gate <label> <scripts-dir>
# Returns 0 when the install may proceed, AG_BLOCKED_EXIT when it must not.
ag_gate() {
  local label="$1" scripts="$2" out="" rc=0 mode msg
  local -a cli=()
  if [ -f "$scripts/cli/devteam" ] && command -v python3 >/dev/null 2>&1; then
    cli=(python3 "$scripts/cli/devteam")
  elif command -v devteam >/dev/null 2>&1; then
    cli=(devteam)
  else
    echo "$label: account check skipped (no devteam CLI available)" >&2
    return 0
  fi
  out="$("${cli[@]}" auth check --json 2>/dev/null)" || rc=$?
  case "$rc" in
    0) return 0 ;;
    1|3|4) ;;
    *) echo "$label: account check skipped (the CLI could not answer, exit $rc)" >&2; return 0 ;;
  esac
  msg="$(printf '%s' "$out" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
    print(d.get("error", ""))
except Exception:
    pass' 2>/dev/null || true)"
  [ -n "$msg" ] || msg="the account is not entitled"
  mode="$(ag_mode "$scripts")"
  if [ "$mode" = "warn" ]; then
    echo "$label: $msg. This will be required in an upcoming release - run \`devteam auth login\`." >&2
    return 0
  fi
  echo "$label: blocked: $msg." >&2
  echo "  Run \`devteam auth login\`, then re-run. \`devteam doctor\`, \`unbind\` and \`uninstall\` always work." >&2
  return "$AG_BLOCKED_EXIT"
}
