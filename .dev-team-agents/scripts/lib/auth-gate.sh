#!/bin/bash
# auth-gate.sh — the account gate for the delegated installers (ADR-0029 SR-30). Sourced, never run.
#
# opencode and Codex installs reach the project without going through `devteam bind`, so each
# installer calls `ag_gate` before it writes. The decision is `devteam auth check --json`
# itself (exit 0 entitled, 1 not entitled, 3 an online check is needed and could not be made,
# 4 lock conflict); a cached entitlement inside its offline window is already an exit 0.
#
# Mode is the `gate_mode` the CLI itself reports in the `auth check --json` body, so there is
# one reader of auth-config.json. Without a body (no CLI, or one that crashed) it falls back
# to the file, then to AG_DEFAULT_MODE, which is this release's mode and is held equal to
# entitlement.DEFAULT_GATE_MODE by tests/test_auth_gate.py. `warn` prints one notice on
# stderr and lets the install proceed; `enforce` refuses with AG_BLOCKED_EXIT. Any other value
# reads as `enforce`, so a typo does not open the gate. When no CLI can be run, or `auth check`
# answers with an exit code that is not a decision (a lock conflict, a crash), the gate cannot
# decide: `warn` skips with a note, `enforce` blocks (SR-42).

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/python.sh"
# shellcheck source=python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

AG_BLOCKED_EXIT=5
AG_DEFAULT_MODE=warn

# ag_mode <scripts-dir> [check-json] -> prints warn|enforce
ag_mode() {
  local cfg="$1/lib/auth-config.json" body="${2:-}" mode=""
  if [ -n "$body" ]; then
    mode="$(printf '%s' "$body" | python3 -c 'import json,sys
try:
    v = json.load(sys.stdin).get("gate_mode")
    print(v if v in ("warn", "enforce") else ("enforce" if v is not None else ""))
except Exception:
    pass' 2>/dev/null || true)"
  fi
  if [ -z "$mode" ] && [ -f "$cfg" ]; then
    mode="$(python3 - "$cfg" "$AG_DEFAULT_MODE" <<'PY' 2>/dev/null || true
import json, sys
try:
    value = json.load(open(sys.argv[1])).get("gate_mode", sys.argv[2])
except Exception:
    value = sys.argv[2]
print(value if value in ("warn", "enforce") else "enforce")
PY
)"
  fi
  echo "${mode:-$AG_DEFAULT_MODE}"
}

# ag_block <label> <message> -> prints the refusal and returns AG_BLOCKED_EXIT
ag_block() {
  echo "$1: blocked: $2." >&2
  echo "  Run \`devteam auth login\`, then re-run. \`devteam doctor\`, \`unbind\` and \`uninstall\` always work." >&2
  return "$AG_BLOCKED_EXIT"
}

# ag_undecided <label> <scripts-dir> <reason>
# The gate could not get an answer: warn mode skips with a note, enforce mode blocks (SR-42).
ag_undecided() {
  if [ "$(ag_mode "$2")" = "warn" ]; then
    echo "$1: account check skipped ($3)" >&2
    return 0
  fi
  ag_block "$1" "the account check could not be made ($3)"
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
    ag_undecided "$label" "$scripts" "no devteam CLI available"
    return $?
  fi
  out="$("${cli[@]}" auth check --json 2>/dev/null)" || rc=$?
  case "$rc" in
    0) return 0 ;;
    1|3) ;;
    4) ag_undecided "$label" "$scripts" "the account lock is busy"; return $? ;;
    *) ag_undecided "$label" "$scripts" "the CLI could not answer, exit $rc"; return $? ;;
  esac
  msg="$(printf '%s' "$out" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
    print(d.get("error", ""))
except Exception:
    pass' 2>/dev/null || true)"
  [ -n "$msg" ] || msg="the account is not entitled"
  mode="$(ag_mode "$scripts" "$out")"
  if [ "$mode" = "warn" ]; then
    echo "$label: $msg. This will be required in an upcoming release - run \`devteam auth login\`." >&2
    return 0
  fi
  ag_block "$label" "$msg"
}
