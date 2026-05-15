#!/usr/bin/env bash
# Stop sub-script: warns when meaningful changes exist but session-summary has no entry for today.
# Returns exit 2 to surface the warning in the Claude Code UI.
set -euo pipefail

# Fast-path: dispatcher sets DEVTEAM_NO_CHANGES=1 when there are no staged/unstaged
# changes and no commits today — nothing to summarise.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

. "$(dirname "${BASH_SOURCE[0]}")/../lib/session-summary-detect.sh"

SUMMARY_FILE=".claude/user-data/session-summary.md"

# Warn when there are uncommitted/staged changes OR commits were made today.
if [ "$HAS_CHANGES" = true ]; then

    if [ ! -f "$SUMMARY_FILE" ]; then
        cat >&2 <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Changes detected but $SUMMARY_FILE does not exist.

 IMPORTANT: Write the entry in English.

 Create the file and write today's entry:

 ## $NOW | [brief task title]
 **Done**: what was implemented or changed

 **Decisions**: key choices made and why

 **Next**: what remains or is recommended next

 ---
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
        exit 2
    fi

    if ! grep -q "^## $TODAY" "$SUMMARY_FILE" 2>/dev/null; then
        cat >&2 <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Changes detected but today's entry ($TODAY) is missing
 from $SUMMARY_FILE.

 IMPORTANT: Write the entry in English.

 Add a new entry at the top of the file:

 ## $NOW | [brief task title]
 **Done**: what was implemented or changed

 **Decisions**: key choices made and why

 **Next**: what remains or is recommended next

 ---
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
        exit 2
    fi
fi
