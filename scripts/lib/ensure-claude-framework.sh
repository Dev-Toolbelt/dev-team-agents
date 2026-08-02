#!/usr/bin/env bash
# ensure-claude-framework.sh — Materialize a stable `.dev-team-agents/`
# tree inside a target project so that bash hook dispatchers (referenced by
# the opencode plugin and by Codex hooks.json via project-relative paths) are
# resolvable at runtime.
#
  # Strategy: copy the framework's runtime subset (agents/, commands/, skills/,
# scripts/, templates/, VERSION if present) into <project>/.dev-team-agents/.
# This mirrors the slim Claude install, and is what the opencode plugin's
# `${directory}/.dev-team-agents/scripts/hooks/...` path expects.
#
# Usage (sourced by install-opencode.sh and install-codex.sh):
#   ensure_claude_framework <project-root> <source-dir>
# Idempotent: re-runs are safe and only refresh files that changed.

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
  if [[ "$source_abs" != "$framework_abs" ]]; then
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

  # Bootstrap runtime state dirs/files expected by shared hooks and the
  # health-check. Hooks will overwrite these on first real use; touching them
  # here avoids a fresh Codex/opencode bootstrap looking partially incomplete.
  mkdir -p "$framework_dir/user-data"
  touch "$framework_dir/user-data/.session-id"
  touch "$framework_dir/user-data/.notifier-state"
} 
