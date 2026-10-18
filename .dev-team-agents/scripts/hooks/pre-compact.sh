#!/usr/bin/env bash
# PreCompact hook — flushes session-summary before context is compacted.
# Mirrors the logic of stop/01-session-summary.sh so that in-progress work
# is captured even when the conversation is compacted mid-session.

# Prevent WSL from loading /etc/bash.bashrc (and its start-systemd-namespace
# call) for every bash sub-process spawned by this script.
unset BASH_ENV ENV

set -euo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/../lib/python.sh"
# shellcheck source=../lib/python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# Skip if this project's memory directory is not set up yet.
# Only act when there is something to summarise.
# shellcheck source=scripts/hooks/lib/session-summary-detect.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/session-summary-detect.sh"

# MEMORY_DIR is exported by session-summary-detect.sh, resolved through the
# `memory-dir` pointer (ADR-0013): layout 1's user-data/ or layout 2's
# portable project directory in the store. Gating on it (instead of the old
# hardcoded user-data/ check) is what keeps this hook working after
# `devteam upgrade` — the previous guard disabled it silently on layout 2.
[ -d "$MEMORY_DIR" ] || exit 0

[ "$HAS_CHANGES" = false ] && exit 0

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
