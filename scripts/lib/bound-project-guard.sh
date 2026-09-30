#!/usr/bin/env bash
# bound-project-guard.sh — stop a v2-only tool from running inside a v3-bound project.
#
# A v3 bind links `<project>/.dev-team-agents/scripts` into the store, so every v2
# tool is reachable at the path its own documentation names. Before that link
# existed the path did not resolve and the tools failed harmlessly; now `update.sh`
# would re-vendor a v2 tree over the bind, `rollback.sh` would restore one, and
# `fix-symlinks.sh` would repoint `.claude/` at directories a bind does not create.
# `project.json` is what makes a project v3 — a v2 install never has one.
#
# Usage (sourced):
#   refuse_if_bound <path-to-.dev-team-agents> "<the devteam command to run instead>"

refuse_if_bound() {
  local devteam_dir="$1"
  local instead="$2"
  if [[ -f "$devteam_dir/project.json" ]]; then
    echo "✗ This project is bound by the devteam CLI (v3); $(basename "$0") is a v2 install tool." >&2
    echo "  Run instead: $instead" >&2
    exit 2
  fi
}
