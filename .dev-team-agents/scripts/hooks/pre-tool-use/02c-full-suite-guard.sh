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
    *'"tool":"bash"'*|*'"tool": "bash"'*) ;;
    *) exit 0 ;;
esac

# Pull the command string out of tool_input.command without a JSON parser —
# consistent with 02-graphify-hint.sh's pure-bash approach on the hot path.
# The match stops at the closing quote of the JSON string value (an escaped
# \" or \\ inside the value is consumed as a pair), so sibling keys such as
# "description" are never absorbed into the command.
COMMAND=$(printf '%s' "$INPUT" | sed -n -E 's/.*"command"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\1/p' | head -1)
[ -n "$COMMAND" ] || exit 0
# Undo the JSON escapes that matter for matching.
COMMAND=${COMMAND//\\\"/\"}
COMMAND=${COMMAND//\\n/$'\n'}
COMMAND=${COMMAND//\\t/ }
COMMAND=${COMMAND//\\\\/\\}

# Explicit escape hatch for the block path only: the touched-files check below
# cannot see conversation history, so it cannot tell an explicitly-requested
# full run (e.g. "run the whole suite as a baseline" at session start, before
# anything is touched) from an unprompted one. Putting this marker anywhere in
# the command as a standalone word (`X=1 npm test`, `cd app && X=1 npm test`)
# is how the block message tells the agent/user to reissue it — an inline env
# var assignment, no state file.
CONFIRM_RE='(^|[[:space:];&|(])DEVTEAM_FULL_SUITE_CONFIRMED=1([[:space:]]|$)'
[[ "$COMMAND" =~ $CONFIRM_RE ]] && exit 0

# True when the args carry a scope qualifier: a flag/selector from the
# "Scoped command" column of scoped-test-execution/SKILL.md, or an explicit
# test file / nested test path. A bare `tests`, `.` or `./` is NOT a scope.
has_scope() {
    local a base
    for a in "$@"; do
        case "$a" in
            --filter*|--related*|--findRelatedTests*|--testNamePattern*|--tests*|--spec*|--) return 0 ;;
            -t|-k|-run|-only-testing:*|TESTPATH=*|FILTER=*|*::*) return 0 ;;
            -*) continue ;;
        esac
        a=${a%/}
        case "$a" in ''|.|..|./...|...) continue ;; esac
        base=${a##*/}
        [[ "$base" == *.* ]] && return 0
        a=${a#./}
        [[ "$a" == */* ]] && return 0
    done
    return 1
}

# classify <words…>: the command starts at $1 (leading wrappers are stripped
# here). Returns 0 when it is an unscoped full-suite run. A runner name only
# counts when it is the command being invoked, never an argument to `cat`,
# `grep`, `git log --grep=` and the like.
classify() {
    local w sub
    while [ $# -gt 0 ]; do
        case "$1" in
            [A-Za-z_]*=*|exec|sudo|time|nohup|env|command|npx|bunx|xargs|--) shift; continue ;;
            docker|docker-compose|podman|nerdctl|kubectl)
                # Wrap-through: find the first invoked runner after the exec/run subcommand.
                local seen=0
                while [ $# -gt 0 ]; do
                    case "$1" in
                        exec|run) seen=1 ;;
                    esac
                    shift
                    [ "$seen" = 1 ] && break
                done
                [ "$seen" = 1 ] || return 1
                while [ $# -gt 0 ]; do
                    case "${1##*/}" in
                        jest|vitest|pytest|py.test|phpunit|pest|rspec|go|gradle|gradlew|flutter|cargo|make|composer|npm|pnpm|yarn|bun|python|python3|php|bundle|poetry|uv|pipenv|artisan) break ;;
                    esac
                    shift
                done
                continue ;;
            *) break ;;
        esac
    done
    [ $# -gt 0 ] || return 1
    w=${1##*/}; shift
    case "$w" in
        jest|vitest)
            has_scope "$@" || return 0
            return 1 ;;
        pytest|py.test|phpunit|pest|rspec)
            has_scope "$@" || return 0
            return 1 ;;
        python|python3)
            [ "${1:-}" = "-m" ] && [ $# -ge 2 ] && { shift; classify "$@"; return; }
            return 1 ;;
        php)
            [ "${1:-}" = artisan ] && { shift; [ "${1:-}" = test ] || return 1; shift; has_scope "$@" || return 0; return 1; }
            [ $# -gt 0 ] && { classify "$@"; return; }
            return 1 ;;
        poetry|uv|pipenv)
            [ "${1:-}" = run ] && { shift; classify "$@"; return; }
            return 1 ;;
        bundle)
            [ "${1:-}" = exec ] && { shift; classify "$@"; return; }
            return 1 ;;
        go)
            [ "${1:-}" = test ] || return 1
            shift
            local a all=0 run=0
            for a in "$@"; do
                [ "$a" = "./..." ] && all=1
                [ "$a" = "-run" ] && run=1
            done
            [ "$all" = 1 ] && [ "$run" = 0 ] && return 0
            return 1 ;;
        gradle|gradlew)
            local a hasT=0 hasTests=0
            for a in "$@"; do
                case "$a" in test|*:test) hasT=1 ;; --tests*) hasTests=1 ;; esac
            done
            [ "$hasT" = 1 ] && [ "$hasTests" = 0 ] && return 0
            return 1 ;;
        flutter)
            [ "${1:-}" = test ] || return 1
            shift
            has_scope "$@" || return 0
            return 1 ;;
        cargo)
            [ "${1:-}" = test ] || return 1
            [ $# -eq 1 ] && return 0
            return 1 ;;
        make)
            # make is an opaque wrapper (Docker exec, phpunit, …): a test-ish
            # target is a full run unless a scope variable / `--` is passed
            # through. `cmake` is a different command and never lands here.
            local a target=0
            for a in "$@"; do
                case "$a" in
                    -*|*=*) ;;
                    *test*|*-e2e*) target=1 ;;
                esac
            done
            [ "$target" = 1 ] || return 1
            has_scope "$@" || return 0
            return 1 ;;
        composer)
            sub=${1:-}
            case "$sub" in test|test:*) ;; *) return 1 ;; esac
            shift
            has_scope "$@" || return 0
            return 1 ;;
        npm|pnpm|yarn|bun)
            sub=${1:-}
            case "$sub" in
                exec|dlx) shift; classify "$@"; return ;;
                jest|vitest|pytest) classify "$@"; return ;;
                run|run-script) shift; sub=${1:-} ;;
            esac
            case "$sub" in test|test:*) ;; *) return 1 ;; esac
            shift
            has_scope "$@" || return 0
            return 1 ;;
    esac
    return 1
}

# Each pipeline/list segment is judged on its own, so `cd app && npm test`,
# `docker exec x sh -c "pnpm test:run"` and `a | b` are all seen as commands.
is_full_suite() {
    local cmd="$1" line
    cmd=$(printf '%s' "$cmd" | tr -d "\"'\`" \
        | sed -E 's/(^|[[:space:]])(sh|bash|zsh|dash) -c /\n/g; s/&&|\|\||;|\||\$\(|\(|\)/\n/g')
    set -f
    while IFS= read -r line; do
        # shellcheck disable=SC2086
        set -- $line
        [ $# -gt 0 ] || continue
        if classify "$@"; then
            set +f
            return 0
        fi
    done <<< "$cmd"
    set +f
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
