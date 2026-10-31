#!/bin/bash
# provision-tools.sh — the helper tools for an install that does not go through `devteam bind`
# (ADR-0060). Sourced, never run.
#
# `devteam bind` installs the pinned tools itself. install.sh, install-opencode.sh and
# install-codex.sh can also reach a project standalone, and each calls `pt_provision` once at
# the end so that path leaves the same tools behind. The work is `devteam tools install`; this
# file only finds a CLI to run it with, the same way `auth-gate.sh` does.
#
# Never fails the install: no CLI, a refused account check, or a tool that cannot be installed
# all print a line and return 0. DEVTEAM_SKIP_TOOLS=1 is honoured by the CLI.

_pt_py="$(dirname "${BASH_SOURCE[0]}")/python.sh"
# shellcheck source=python.sh
[ -f "$_pt_py" ] && . "$_pt_py"

# pt_provision <label> <scripts-dir>
pt_provision() {
  local label="$1" scripts="$2"
  local -a cli=()
  if [ -f "$scripts/cli/devteam" ] && command -v python3 >/dev/null 2>&1; then
    cli=(python3 "$scripts/cli/devteam")
  elif command -v devteam >/dev/null 2>&1; then
    cli=(devteam)
  else
    echo "$label: helper tools not installed (no devteam CLI) — run \`devteam tools install\` later"
    return 0
  fi
  echo ""
  "${cli[@]}" tools install </dev/null || echo "$label: some tools were not installed; \`devteam tools install\` retries"
  return 0
}
