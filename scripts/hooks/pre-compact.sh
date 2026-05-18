#!/usr/bin/env bash
# PreCompact hook — flushes session-summary before context is compacted.
# Mirrors the logic of stop/01-session-summary.sh so that in-progress work
# is captured even when the conversation is compacted mid-session.
set -euo pipefail

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# Skip if dev-team-agents user-data directory is not set up yet
[ -d ".claude/user-data" ] || exit 0

# Only act when there is something to summarise.
# shellcheck source=scripts/hooks/lib/session-summary-detect.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/session-summary-detect.sh"

[ "$HAS_CHANGES" = false ] && exit 0

SUMMARY_FILE=".claude/user-data/session-summary.md"

if [ ! -f "$SUMMARY_FILE" ] || ! grep -q "^## $TODAY" "$SUMMARY_FILE" 2>/dev/null; then
    cat >&2 <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SESSION SUMMARY REQUIRED (pre-compact)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 The conversation is about to be compacted but today's
 session-summary entry is missing.

 IMPORTANT: Write the entry in English.

 Before the compact proceeds, write to $SUMMARY_FILE:

 ## $NOW | [brief task title]
 **Done**: what was implemented or changed

 **Decisions**: key choices made and why

 **Next**: what remains or is recommended next

 ---
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
    exit 2
fi
