#!/usr/bin/env bash
# Runs on Claude Code Stop event.
# Warns when meaningful changes exist but .claude/session-summary.md has no entry for today.
set -euo pipefail

SUMMARY_FILE=".claude/session-summary.md"
TODAY=$(date +%Y-%m-%d)

# Only warn when there are uncommitted or staged changes — silent on clean repos.
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null || \
   [ -n "$(git status --porcelain 2>/dev/null)" ]; then

    if [ ! -f "$SUMMARY_FILE" ]; then
        cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Changes detected but .claude/session-summary.md is missing.
 Please write a session summary now so context is preserved.

 Create .claude/session-summary.md with this entry:

 ## $TODAY | [brief task title]
 **Done**: what was implemented or changed
 **Decisions**: key choices made and why
 **Next**: what remains or is recommended next
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
        exit 0
    fi

    if ! grep -q "^## $TODAY" "$SUMMARY_FILE" 2>/dev/null; then
        cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Changes detected but today's entry ($TODAY) is missing
 from .claude/session-summary.md.

 Add a new entry at the top of the file:

 ## $TODAY | [brief task title]
 **Done**: what was implemented or changed
 **Decisions**: key choices made and why
 **Next**: what remains or is recommended next
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
    fi
fi
