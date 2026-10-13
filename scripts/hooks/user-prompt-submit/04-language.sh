#!/usr/bin/env bash
# UserPromptSubmit sub-script: restates the conversation language on EVERY prompt. The session
# banner names the language once, at session start, and only the agents load the language policy
# (skills/shared/project-context/SKILL.md § Language Policy); the main conversation drifted to
# English in long sessions, mostly right after writing an English commit or session summary.
# Claude Code and Codex add this stdout to the model context; the opencode plugin captures it from
# `chat.message` and adds it to the system prompt.
# Prints nothing when the language is English or unreadable. No python fork: a single grep.
# Exits 0 always.
set -uo pipefail

ROOT="$PWD"
if [ ! -d "${ROOT}/.dev-team-agents" ]; then
    # The preferences live in the MAIN checkout only, never in a linked worktree.
    ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)" || exit 0
fi
PREFS="${ROOT}/.dev-team-agents/resolved/preferences.json"
[ -f "$PREFS" ] || PREFS="${ROOT}/.dev-team-agents/user-data/preferences.json"
[ -f "$PREFS" ] || exit 0

LANG_TAG="$(grep -m1 -oE '"language"[[:space:]]*:[[:space:]]*"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*"' "$PREFS" 2>/dev/null \
    | sed -E 's/.*"([^"]+)"$/\1/')"
case "$LANG_TAG" in
    ""|en|en-*|EN|EN-*) exit 0 ;;
esac

echo "[DEVTEAM:LANGUAGE] Reply to the user in ${LANG_TAG} — every message, including the last one of a task. Documents, code comments, commit messages and the session summary stay in English."
exit 0
