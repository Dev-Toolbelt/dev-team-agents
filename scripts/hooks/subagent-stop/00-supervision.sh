#!/usr/bin/env bash
# SubagentStop sub-script (Codex): the supervision gate of ADR-0062. Prints a block decision on stdout,
# which the dispatcher relays; prints nothing when the agent finished properly. Exits 0 always.
unset BASH_ENV ENV
set -uo pipefail

_dta_lib="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0
# shellcheck source=scripts/hooks/lib/subagent-supervision.sh
. "$_dta_lib/subagent-supervision.sh" || exit 0

devteam_subagent_supervise
exit 0
