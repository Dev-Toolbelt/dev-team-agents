#!/usr/bin/env bash
# Runs on Claude Code Stop event.
# Warns when meaningful changes exist but .claude/user-data/session-summary.md has no entry for today.
# Returns exit 2 to surface the warning in the Claude Code UI.
set -euo pipefail

SUMMARY_FILE=".claude/user-data/session-summary.md"
TODAY=$(date +%Y-%m-%d)

TODAY_COMMITS=$(git log --since="${TODAY} 00:00:00" --oneline 2>/dev/null || true)

# Warn when there are uncommitted/staged changes OR commits were made today.
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null || \
   [ -n "$(git status --porcelain 2>/dev/null)" ] || [ -n "$TODAY_COMMITS" ]; then

    if [ ! -f "$SUMMARY_FILE" ]; then
        # Create the file with a placeholder entry so it exists for future appends.
        mkdir -p "$(dirname "$SUMMARY_FILE")"
        cat > "$SUMMARY_FILE" <<EOF
## $TODAY | [session title — fill in]
**Done**: (fill in what was implemented or changed)
**Decisions**: (fill in key choices made and why)
**Next**: (fill in what remains or is recommended next)
EOF
        cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Changes detected. Created $SUMMARY_FILE with a
 placeholder entry for today ($TODAY).

 Please fill in the entry now:

 ## $TODAY | [brief task title]
 **Done**: what was implemented or changed
 **Decisions**: key choices made and why
 **Next**: what remains or is recommended next
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
        exit 2
    fi

    if ! grep -q "^## $TODAY" "$SUMMARY_FILE" 2>/dev/null; then
        cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Changes detected but today's entry ($TODAY) is missing
 from $SUMMARY_FILE.

 Add a new entry at the top of the file:

 ## $TODAY | [brief task title]
 **Done**: what was implemented or changed
 **Decisions**: key choices made and why
 **Next**: what remains or is recommended next
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
        exit 2
    fi
fi
