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

  mkdir -p "$framework_dir"

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

  # scripts/: copy the Claude-runtime subset only (mirror what install.sh
  # would put at .dev-team-agents/scripts/). Cross-CLI plumbing is
  # intentionally NOT copied — bootstrap-on-demand took care of it.
  if [[ -d "$source_dir/scripts" ]]; then
    mkdir -p "$framework_dir/scripts/lib" "$framework_dir/scripts/hooks" "$framework_dir/scripts/helpers"
    cp -f "$source_dir/scripts/"*.sh "$framework_dir/scripts/" 2>/dev/null || true
    cp -f "$source_dir/scripts/lib/"*.json "$framework_dir/scripts/lib/" 2>/dev/null || true
    cp -f "$source_dir/scripts/lib/"*.sh "$framework_dir/scripts/lib/" 2>/dev/null || true
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
}