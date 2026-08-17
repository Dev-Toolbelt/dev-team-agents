#!/usr/bin/env bash
# PreToolUse sub-script: guards against an unscoped full-suite test run.
# Documented, narrow exception to "Exit 0 in all normal paths" in
# CLAUDE-md/hooks.md § PreToolUse Hook Sub-script Convention: when the
# command looks like a full suite AND nothing has been touched yet this
# session (clean working tree, no commits today), there is no scope to
# derive from and no plausible "user asked for this" context either — the
# session hasn't done anything yet. That combination is blocked (exit 2)
# instead of just nudged, because it is the one case cheap enough to detect
# reliably (git status is fast, no network) without false-positiving on
# legitimate mid-task or explicitly-requested full runs, which still only
# get the additionalContext nudge as before.
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"
# shellcheck source=../lib/touched-paths.sh
source "$HOOK_DIR/touched-paths.sh"

INPUT=$(cat)

case "$INPUT" in
    *'"tool_name":"Bash"'*|*'"tool_name": "Bash"'*) ;;
    *) exit 0 ;;
esac

# Pull the command string out of tool_input.command without a JSON parser —
# consistent with 02-graphify-hint.sh's pure-bash approach on the hot path.
# Greedy match to "...\?"$ so a command wrapped in nested quotes
# (docker exec ... sh -c "pnpm test:run") is captured whole instead of being
# cut at the first embedded double quote.
COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)"[[:space:]]*[,}].*/\1/p' | head -1)
[ -n "$COMMAND" ] || exit 0

# Explicit escape hatch for the block path only: the touched-files check below
# cannot see conversation history, so it cannot tell an explicitly-requested
# full run (e.g. "run the whole suite as a baseline" at session start, before
# anything is touched) from an unprompted one. Prefixing the command with this
# marker is how the block message tells the agent/user to reissue it — an
# inline env var assignment, no state file, no bypass for the untouched-files
# case being wrong by default.
case "$COMMAND" in
    DEVTEAM_FULL_SUITE_CONFIRMED=1\ *) exit 0 ;;
esac

# Each pattern below is a command shape with NO scope qualifier (no path,
# no --filter/-k/--tests/-only-testing/-run), matching the "Scoped command"
# column in scoped-test-execution/SKILL.md's runner table.
is_full_suite() {
    local cmd="$1"
    case "$cmd" in
        *jest*)
            [[ "$cmd" != *--findRelatedTests* && "$cmd" != *.test.* && "$cmd" != *.spec.* ]] && return 0 ;;
    esac
    case "$cmd" in
        *vitest*)
            [[ "$cmd" != *--related* && "$cmd" != *.test.* && "$cmd" != *.spec.* && "$cmd" != *-t\ * && "$cmd" != *--testNamePattern* ]] && return 0 ;;
    esac
    case "$cmd" in
        *pnpm\ test*|*npm\ test*|*npm\ run\ test*|*yarn\ test*|*bun\ test*)
            [[ "$cmd" != *.test.* && "$cmd" != *.spec.* && "$cmd" != *--\ * && "$cmd" != *-t\ * && "$cmd" != *--filter* && "$cmd" != *--related* && "$cmd" != *--findRelatedTests* ]] && return 0 ;;
    esac
    case "$cmd" in
        *pytest*)
            [[ "$cmd" != *::* && "$cmd" != *'-k '* && "$cmd" != *.py* ]] && return 0 ;;
    esac
    case "$cmd" in
        *phpunit*|*pest*)
            [[ "$cmd" != *--filter* && "$cmd" != *.php* ]] && return 0 ;;
    esac
    case "$cmd" in
        *'go test'*./...*)
            [[ "$cmd" != *'-run '* ]] && return 0 ;;
    esac
    case "$cmd" in
        *gradlew\ test*|*'gradle test'*)
            [[ "$cmd" != *--tests* ]] && return 0 ;;
    esac
    case "$cmd" in
        *'flutter test'*)
            [[ "$cmd" != *'flutter test '*/* ]] && return 0 ;;
    esac
    case "$cmd" in
        *'cargo test'*)
            case "$cmd" in
                *'cargo test'|*'cargo test &&'*|*'cargo test;'*) return 0 ;;
            esac ;;
    esac
    case "$cmd" in
        *rspec*)
            [[ "$cmd" != *:[0-9]* ]] && return 0 ;;
    esac
    # `make <target>` and `composer test:*` are opaque wrappers around a real
    # runner (Docker exec, phpunit, etc.) — the literal command string never
    # contains a runner name for the patterns above to match, so a project
    # routing everything through Make/Composer sails past this guard entirely
    # unless checked here. A scoped invocation passes TESTPATH=/FILTER=/-- args
    # through to the wrapped composer script; a bare target name does not.
    case "$cmd" in
        *make\ *test*|*make\ *-e2e*)
            [[ "$cmd" != *TESTPATH=* && "$cmd" != *FILTER=* && "$cmd" != *--\ * ]] && return 0 ;;
    esac
    case "$cmd" in
        *composer\ test:*)
            [[ "$cmd" != *--filter* && "$cmd" != *--\ * ]] && return 0 ;;
    esac
    case "$cmd" in
        *composer\ test*)
            [[ "$cmd" != *test:* ]] && return 0 ;;
    esac
    return 1
}

if is_full_suite "$COMMAND"; then
    TOUCHED="$(devteam_compute_touched_paths || true)"
    if [ -z "$TOUCHED" ]; then
        # Nothing changed yet this session — there is no blast radius to scope
        # to, and no in-flight work that a "the user asked for this" full run
        # could plausibly belong to. Block instead of nudge.
        {
            echo "scoped-test-execution: BLOCKED — unscoped full test suite run with no touched files this session."
            echo "Per skills/shared/scoped-test-execution/SKILL.md, the full suite runs only when the user explicitly asked for it in THIS session."
            echo "Nothing has been changed yet, so there is nothing to scope this run to. If the user explicitly asked for a full run this session, reissue the command prefixed with DEVTEAM_FULL_SUITE_CONFIRMED=1 (e.g. 'DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test'). Otherwise wait until there is a diff to scope tests to."
        } >&2
        exit 2
    fi
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"scoped-test-execution: this command looks like an UNSCOPED full test suite run. Per skills/shared/scoped-test-execution/SKILL.md, the full suite runs only when the user explicitly asked for it in THIS session. If that is not the case, stop and scope this run to the files touched (git diff --name-only) plus their tests instead."}}\n'
fi

exit 0
