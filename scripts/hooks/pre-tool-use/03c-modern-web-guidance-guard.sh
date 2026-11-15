#!/usr/bin/env bash
# PreToolUse sub-script: refuses a shell command that downloads or runs the
# `modern-web-guidance` command-line tool (ADR-0047).
#
# WHY
# ===
# skills/third-party/modern-web-guidance/ is vendored as Markdown only. Its upstream SKILL.md,
# which cannot be edited, tells the agent to run `npx -y modern-web-guidance@latest …` on every
# web task: an unpinned package fetched at run time, which reports the agent name, guide ids
# and search queries to its publisher by default. The framework reads the vendored guides
# instead (skills/architecture/third-party-web-skills/SKILL.md). That skill is text; an agent
# that only saw the upstream description never loads it, so the refusal lives here.
#
# WHAT THIS IS NOT
# ================
# A hygiene gate, NOT a sandbox. It matches command text at command position, so a variable, a
# script file or an unusual wrapper walks past it, as 03-credential-guard.sh documents for
# itself. It FAILS OPEN: an unparseable payload or an internal error allows the call.
# There is no bypass variable: a user who wants the tool runs it in their own terminal.
#
# Command position is the start of a line or what follows `;`, `&`, `|`, `(`, a backtick, `{`,
# `!`, `then`, `do` or `else`. The text is not parsed as shell, so:
#   - a mention on one line inside a quoted argument passes
#     (`grep "npx modern-web-guidance" docs/`);
#   - a mention that follows a newline or one of those separators INSIDE quoted text or a
#     heredoc body is refused (a multi-line `git commit -m`, `cat > notes.md <<EOF`). Write
#     that text with the file-edit tool, or pass it from a file (`git commit -F`);
#   - a literal backslash-n typed inside a quoted string reads as a newline too
#     (`printf 'x\nnpx modern-web-guidance'`), with the same result.
#
# WHAT IT REFUSES
# ===============
#   - a package runner executing it, whatever flags come first: npx, npx.cmd, pnpx, bunx,
#     `pnpm|yarn|bun dlx|x`, `npm exec|x`, also as `npm:modern-web-guidance`,
#     `github:GoogleChrome/modern-web-guidance` or `--package=modern-web-guidance`
#   - a package manager installing it: `npm|pnpm|yarn|bun … install|i|add … modern-web-guidance`
#   - the installed binary with one of its subcommands
#   Claude Code  Bash            tool_input.command
#   Codex        Bash, shell, exec_command   tool_input.command / tool_input.cmd (argv array)
#   opencode     bash            args.command
#
# EXIT CONTRACT
# =============
# Documented, narrow exception to "Exit 0 in all normal paths" in CLAUDE-md/hooks.md
# § PreToolUse Hook Sub-script Convention: a refusal exits 2 with the reason on stderr. Every
# other path exits 0, enforced by the EXIT trap. `set -e` is deliberately not used.
set -uo pipefail

VERDICT=""
# shellcheck disable=SC2329,SC2317  # invoked indirectly, by the EXIT trap below.
_mwg_guard_exit() {
    if [ "${VERDICT:-}" = "refuse" ]; then
        exit 2
    fi
    exit 0
}
trap _mwg_guard_exit EXIT

# Every pattern below is ASCII. Under a UTF-8 locale BSD sed stops on one invalid byte and
# prints nothing, which would let the command through.
export LC_ALL=C

INPUT=$(cat 2>/dev/null || true)

# Hot path: one bash string test, no fork, for every call that does not name the package.
case "$INPUT" in
    *modern-web-guidance*) ;;
    *) exit 0 ;;
esac
SHELL_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"(Bash|shell|exec_command|bash)"'
[[ "$INPUT" =~ $SHELL_RE ]] || exit 0

# The JSON escapes are undone in the stream, never with bash `${VAR//…}`: on bash 3.2 that
# replacement is worse than quadratic, and a 40 KB heredoc naming the package took 27 s.
_unescape() {
    sed -e 's/\\"/"/g' -e 's/\\t/ /g' | awk '{ gsub(/\\n/, "\n") } 1'
}

COMMAND=$(printf '%s' "$INPUT" | sed -nE 's/.*"(command|cmd)"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\2/p' | head -1 | _unescape)
if [ -z "$COMMAND" ]; then
    # Codex argv array: join the elements with spaces.
    COMMAND=$(printf '%s' "$INPUT" | sed -nE 's/.*"(command|cmd)"[[:space:]]*:[[:space:]]*\[(([^]"]|"([^"\\]|\\.)*")*)\].*/\2/p' | head -1 \
        | sed -E 's/"[[:space:]]*,[[:space:]]*"/ /g; s/^[[:space:]]*"//; s/"[[:space:]]*$//' | _unescape)
fi
[ -n "$COMMAND" ] || exit 0

# Command position (see the header), then optional env assignments and wrappers with their
# flags, and a `sh -c` / `bash -lc` prefix (how a Codex argv array reads once joined).
ARG='[^[:space:];|&]+'
WRAP="(([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*|(sudo|env|time|command|exec|nohup|xargs|timeout)([[:space:]]+-[^[:space:]]+)*([[:space:]]+[0-9][^[:space:]]*)?)[[:space:]]+)*"
START='(^|[;&|(`{!]|[[:space:]](then|do|else))[[:space:]]*'
POS="${START}${WRAP}((ba|z|da)?sh[[:space:]]+-[a-z]*c[[:space:]]+[\"']?${WRAP})*([^[:space:];|&]*/)?"
PKG="[\"']?(--package=|npm:|github:GoogleChrome/)?modern-web-guidance(@[^[:space:]\"';|&)]*)?"
END="([[:space:]\"';|&)\`]|\$)"
RUNNER='(npx(\.cmd)?|pnpx|bunx|(pnpm|yarn|bun)[[:space:]]+(dlx|x)|npm[[:space:]]+(exec|x))'
MANAGER='(npm|pnpm|yarn|bun)'
SUBCOMMANDS='(search|retrieve|list|install|legacy-scan|set-allow-origin-trials|set-allow-volatile-features)'

# Between a runner and the package only flags count, each with an optional value: a
# positional argument means the runner executes another tool (`npx prettier --check <dir>`).
FLAG='-[^[:space:];|&]*([[:space:]]+[^-[:space:];|&][^[:space:];|&]*)?'
RUN_RE="${POS}${RUNNER}([[:space:]]+${FLAG})*[[:space:]]+${PKG}${END}"
INSTALL_RE="${POS}${MANAGER}([[:space:]]+${ARG})*[[:space:]]+(install|i|add)([[:space:]]+${ARG})*[[:space:]]+${PKG}${END}"
BIN_RE="${POS}modern-web-guidance[[:space:]]+${SUBCOMMANDS}${END}"

if printf '%s\n' "$COMMAND" | grep -qE -e "$RUN_RE" -e "$INSTALL_RE" -e "$BIN_RE"; then
    VERDICT="refuse"
    cat >&2 <<'MSG'
Refused: the modern-web-guidance command-line tool is not run in this project.
It is an unpinned package fetched at run time that reports usage to its publisher.
The same guides are vendored as Markdown: load
skills/architecture/third-party-web-skills/SKILL.md and read the matching file under
the modern-web-guidance skill folder's guides/<category>/<id>.md instead.
A user who wants the tool itself runs it in their own terminal.
If this command only mentions the tool inside a heredoc or a multi-line message,
write that text with the file-edit tool or pass it from a file (git commit -F).
MSG
fi
exit 0
