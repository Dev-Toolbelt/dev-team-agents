#!/usr/bin/env bash
# backlog-prime.sh — print the active sprint work for a compacted or resumed context (ADR-0044).
#
# Called by session-start.sh on source=compact|resume (Claude Code, Codex) and by the opencode
# plugin from `experimental.session.compacting`. Prints `devteam backlog prime` and nothing else;
# silent when no sprint is in progress, outside a bound project, or when python3 or the CLI is
# missing. Exits 0 always: a hook never disturbs the provider.
unset BASH_ENV ENV
set -uo pipefail

_bp_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || exit 0
# shellcheck source=../lib/python.sh
[ -f "${_bp_dir}/../lib/python.sh" ] && . "${_bp_dir}/../lib/python.sh"
command -v python3 >/dev/null 2>&1 || exit 0

# Inherited git overrides would read another repository's state (ADR-0043).
unset GIT_DIR GIT_COMMON_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY
_bp_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
_bp_main="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
[ -n "$_bp_main" ] || _bp_main="$_bp_root"
[ -f "${_bp_main}/.dev-team-agents/project.json" ] || exit 0

_bp_cli="${_bp_dir}/../cli/devteam"
[ -f "$_bp_cli" ] || exit 0
# A hung read must not hold SessionStart: the call is bounded where a timeout command exists
# (the opencode plugin bounds every hook itself).
_bp_timeout=""
for _bp_t in timeout gtimeout; do
    command -v "$_bp_t" >/dev/null 2>&1 && { _bp_timeout="$_bp_t 5"; break; }
done
# shellcheck disable=SC2086 # `_bp_timeout` is a command and its argument, or empty
$_bp_timeout python3 "$_bp_cli" backlog prime --path "$_bp_root" 2>/dev/null || true
exit 0
