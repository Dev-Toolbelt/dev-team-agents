#!/usr/bin/env bash
# SubagentStop dispatcher for Claude Code (ADR-0062 decision 4): sends a finished agent from `agents/`
# back once when its final message lacks the closing run banner or, for a reviewer / QA agent, the
# review-result marker. Separate from `subagent-stop.sh`, whose task-board capture is Codex-only.
# Prints a block decision or nothing; always exits 0 (fail open).

unset BASH_ENV ENV
set -uo pipefail

_dta_lib="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/lib" 2>/dev/null && pwd)" || exit 0
# shellcheck source=scripts/hooks/lib/subagent-supervision.sh
. "$_dta_lib/subagent-supervision.sh" || exit 0

devteam_subagent_supervise
exit 0
