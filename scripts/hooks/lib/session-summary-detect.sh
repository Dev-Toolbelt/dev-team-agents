#!/usr/bin/env bash
# Shared detection logic for session-summary hooks.
# Source this file; it exports: TODAY, NOW, HAS_CHANGES, TODAY_COMMITS.
# Assumes git repo check has already been done by the caller.

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%Y-%m-%d\ %H:%M:%S)

TODAY_COMMITS=$(git log --since="${TODAY} 00:00:00" --oneline 2>/dev/null || true)

HAS_CHANGES=false
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null || \
   [ -n "$(git status --porcelain 2>/dev/null)" ] || [ -n "$TODAY_COMMITS" ]; then
    HAS_CHANGES=true
fi

export TODAY NOW HAS_CHANGES TODAY_COMMITS
