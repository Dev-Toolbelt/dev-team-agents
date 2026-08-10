#!/usr/bin/env bash
# PreToolUse sub-script: nudges Claude when a Bash command looks like an
# unscoped full-suite test run. Does not block — see "Exit 0 in all normal
# paths" in CLAUDE-md/hooks.md — it only injects a reminder of
# skills/shared/scoped-test-execution/SKILL.md at the moment the command is
# about to run, as a safety net for sessions where that skill was never
# loaded (e.g. main-loop work outside /devteam:* routing).
set -euo pipefail

INPUT=$(cat)

case "$INPUT" in
    *'"tool_name":"Bash"'*|*'"tool_name": "Bash"'*) ;;
    *) exit 0 ;;
esac

# Pull the command string out of tool_input.command without a JSON parser —
# consistent with 02-graphify-hint.sh's pure-bash approach on the hot path.
COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)".*/\1/p' | head -1)
[ -n "$COMMAND" ] || exit 0

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
    return 1
}

if is_full_suite "$COMMAND"; then
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"scoped-test-execution: this command looks like an UNSCOPED full test suite run. Per skills/shared/scoped-test-execution/SKILL.md, the full suite runs only when the user explicitly asked for it in THIS session. If that is not the case, stop and scope this run to the files touched (git diff --name-only) plus their tests instead."}}\n'
fi

exit 0
