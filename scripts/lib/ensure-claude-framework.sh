#!/usr/bin/env bash
# ensure-claude-framework.sh — Materialize a stable `.dev-team-agents/`
# tree inside a target project so that bash hook dispatchers (referenced by
# the opencode plugin and by Codex hooks.json via project-relative paths) are
# resolvable at runtime.
#
# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/python.sh"
# shellcheck source=python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

  # Strategy: copy the framework's runtime subset (agents/, commands/, skills/,
# scripts/, templates/, VERSION if present) into <project>/.dev-team-agents/.
# This mirrors the slim Claude install, and is what the opencode plugin's
# `${directory}/.dev-team-agents/scripts/hooks/...` path expects.
#
# Usage (sourced by install-opencode.sh and install-codex.sh):
#   ensure_claude_framework <project-root> <source-dir>
# Idempotent: re-runs are safe and only refresh files that changed.

# _ecf_ignore_credentials <project-root> <source-dir>
# Keeps git from tracking .dev-team-agents/credentials.local.json (and its backups) on a
# standalone opencode/Codex install, as the Claude installer and `devteam bind` already do.
# Reuses credentials_local.ensure_ignored (the machine-local info/exclude block) instead of
# re-implementing that format. Never fatal: a missing devteam package only costs a warning.
_ecf_ignore_credentials() {
  local project_root="$1" source_dir="$2" lib_dir native_root
  for lib_dir in "$source_dir/scripts/lib" "$project_root/.dev-team-agents/scripts/lib"; do
    [[ -d "$lib_dir/devteam" ]] || continue
    native_root="$project_root"
    command -v cygpath >/dev/null 2>&1 && { native_root="$(cygpath -m "$project_root")"; lib_dir="$(cygpath -m "$lib_dir")"; }
    if python3 - "$native_root" "$lib_dir" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from devteam import credentials_local
sys.exit(0 if credentials_local.ensure_ignored(Path(sys.argv[1])) else 1)
PY
    then
      return 0
    fi
    break
  done
  echo "  ! could not add .dev-team-agents/credentials.local.json to the git exclude list;" >&2
  echo "    add it to your .gitignore so credentials are never committed." >&2
  return 0
}

ensure_claude_framework() {
  local project_root="$1"
  local source_dir="$2"
  local framework_dir="$project_root/.dev-team-agents"
  local source_abs
  local framework_abs

  source_abs="$(cd "$source_dir" && pwd)"
  framework_abs="$(mkdir -p "$framework_dir" && cd "$framework_dir" && pwd)"

  # When the provider installer is re-run from the already-installed project
  # copy (for example `bash .dev-team-agents/scripts/install-codex.sh --source
  # .dev-team-agents`), source and destination are the same directory. In that
  # case copying back into itself only raises "identical" cp errors and does no
  # useful work; skip the mirror pass and keep only the state-file bootstrap
  # below.
  # A v3 bind links <project>/.dev-team-agents/{scripts,templates} into the store,
  # which already resolves every project-relative framework path the hooks and the
  # provider plugins use. Mirroring the tree on top of that copied 2.3 MB of
  # framework back into the project — the exact thing the v3 store exists to
  # eliminate — and, now that `scripts` IS a link, the `cp` below would write
  # through it into the installed store version itself. So a bound project
  # (`project.json`) or a linked `scripts` skips the mirror; only the state
  # bootstrap below runs. `core` is still honoured for a project bound before the
  # links replaced it and not yet synced.
  if [[ -f "$framework_dir/project.json" || -L "$framework_dir/scripts" || -e "$framework_dir/core" ]]; then
    :
  elif [[ "$source_abs" != "$framework_abs" ]]; then
    # Copy the runtime subset only (no .git, no .github, no .opencode, no .codex,
    # no helpers/ which is dev-only, no opencode/ plumbing dir from the repo,
    # no scripts/install-*.sh cross-CLI scripts — those are bootstrap-time only).
    local keep_dirs=(agents commands skills templates)
    for d in "${keep_dirs[@]}"; do
      if [[ -d "$source_dir/$d" ]]; then
        mkdir -p "$framework_dir/$d"
        cp -rf "$source_dir/$d/." "$framework_dir/$d/"
      fi
    done

    # scripts/: copy the Claude-runtime subset plus the minimal cross-CLI
    # render plumbing required for project-local re-runs of install-opencode.sh
    # / install-codex.sh via `--source .dev-team-agents`.
    if [[ -d "$source_dir/scripts" ]]; then
      mkdir -p "$framework_dir/scripts/lib" "$framework_dir/scripts/hooks" "$framework_dir/scripts/helpers"
      cp -f "$source_dir/scripts/"*.sh "$framework_dir/scripts/" 2>/dev/null || true
      cp -f "$source_dir/scripts/lib/"*.json "$framework_dir/scripts/lib/" 2>/dev/null || true
      cp -f "$source_dir/scripts/lib/"*.sh "$framework_dir/scripts/lib/" 2>/dev/null || true
      cp -f "$source_dir/scripts/lib/"*.py "$framework_dir/scripts/lib/" 2>/dev/null || true
      if [[ -d "$source_dir/scripts/hooks" ]]; then
        cp -rf "$source_dir/scripts/hooks/." "$framework_dir/scripts/hooks/"
      fi
      if [[ -d "$source_dir/scripts/helpers" ]]; then
        cp -f "$source_dir/scripts/helpers/"*.sh "$framework_dir/scripts/helpers/" 2>/dev/null || true
      fi
    fi

    # VERSION tag if available.
    if [[ -f "$source_dir/VERSION" ]]; then
      cp -f "$source_dir/VERSION" "$framework_dir/VERSION" 2>/dev/null || true
    fi
  fi

  _ecf_ignore_credentials "$project_root" "$source_dir"

  # Bootstrap runtime state dirs/files expected by shared hooks and the
  # health-check. Hooks will overwrite these on first real use; touching them
  # here avoids a fresh Codex/opencode bootstrap looking partially incomplete.
  # Not in a bound project: its state lives behind the `state-dir` pointer, and
  # recreating user-data/ here undoes what `devteam upgrade` retired.
  if [[ -f "$framework_dir/project.json" ]]; then
    return 0
  fi
  mkdir -p "$framework_dir/user-data"
  # session_id used to live as a standalone .session-id dotfile placeholder;
  # it is now a key in the consolidated state.json. Just ensure the file
  # exists as valid JSON — do not set session_id itself here, so a value
  # written by another hook is never clobbered.
  [ -f "$framework_dir/user-data/state.json" ] || echo '{}' > "$framework_dir/user-data/state.json"
  touch "$framework_dir/user-data/.notifier-state"
} 
