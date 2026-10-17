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
    COMMON="$(git rev-parse --git-common-dir 2>/dev/null)" || exit 0
    [ -n "$COMMON" ] || exit 0
    ROOT="$(cd "${COMMON}/.." 2>/dev/null && pwd)" || exit 0
fi
PREFS="${ROOT}/.dev-team-agents/resolved/preferences.json"
[ -f "$PREFS" ] || PREFS="${ROOT}/.dev-team-agents/user-data/preferences.json"
[ -f "$PREFS" ] || exit 0

# The value becomes model context on every prompt, so it must be shaped like a language tag and
# nothing more: at most two subtags, 20 characters, and only the first match in the file.
LANG_TAG="$(grep -m1 -oE '"language"[[:space:]]*:[[:space:]]*"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8}){0,2}"' "$PREFS" 2>/dev/null \
    | head -n1 | sed -E 's/.*"([^"]+)"$/\1/')"
[ "${#LANG_TAG}" -le 20 ] || exit 0
case "$(printf '%s' "$LANG_TAG" | tr '[:upper:]' '[:lower:]')" in
    ""|en|en-*) exit 0 ;;
esac

echo "[DEVTEAM:LANGUAGE] Reply to the user in ${LANG_TAG} — every message, including the last one of a task and any fixed message a command says to output exactly (code, paths, versions, commands, placeholders and emoji stay as written). Only what a command says to output verbatim stays as written. Documents, code comments, commit messages and the session summary stay in English."
exit 0
