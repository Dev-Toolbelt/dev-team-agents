#!/usr/bin/env bash
# Shared detection logic for session-summary hooks.
# Source this file; it exports: TODAY, NOW, HAS_CHANGES, TODAY_COMMITS, REPO_ROOT.
# Assumes git repo check has already been done by the caller.

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%Y-%m-%d\ %H:%M:%S)

# user-data/ is shared state that lives only in the main worktree, never in a
# linked worktree's own tree. Resolve --git-common-dir (the shared .git dir)
# and take its parent so a hook running with cwd inside .worktrees/<name>/
# still reads/writes the same session-summary.md as the main checkout.
REPO_ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
[ -n "$REPO_ROOT" ] || REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

TODAY_COMMITS=$(git log --since="${TODAY} 00:00:00" --oneline 2>/dev/null || true)

HAS_CHANGES=false
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null || \
   [ -n "$(git status --porcelain 2>/dev/null)" ] || [ -n "$TODAY_COMMITS" ]; then
    HAS_CHANGES=true
fi

export TODAY NOW HAS_CHANGES TODAY_COMMITS REPO_ROOT
