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
# When no CLI can be run (a slim tree without scripts/cli, an older `devteam` with no `auth`),
# or `auth check` answers with an unexpected exit code, the gate cannot decide: `warn` skips
# with a note, `enforce` blocks (SR-42), so a missing or broken CLI never opens the gate.

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
    1|3|4) ;;
    *) ag_undecided "$label" "$scripts" "the CLI could not answer, exit $rc"; return $? ;;
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
  ag_block "$label" "$msg"
}
