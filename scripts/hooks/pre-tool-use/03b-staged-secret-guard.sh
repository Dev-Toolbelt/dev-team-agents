#!/usr/bin/env bash
# PreToolUse sub-script: refuse a `git commit` whose changes carry a secret (ADR-0059).
#
# WHAT IT DOES
# ============
# On a shell tool call whose command runs `git commit`, it runs
#   gitleaks git --pre-commit --staged --redact
# in the repository the commit targets. A finding refuses the call (exit 2) with the file,
# line and rule of each finding on stderr — never the value: `--redact` masks it, and this
# script prints only the location fields. With `-a`/`--all` the unstaged diff of tracked
# files is scanned too, because that is what such a commit records.
#
# WHAT IT IS NOT
# ==============
# Like 03-credential-guard.sh, a guard on the ordinary spelling, not a boundary. It reads
# command text: a commit run from a script, an alias, `cd x && git commit` into another
# repository, or any tool other than the shell walks past it. The CI job
# (`.github/workflows/ci.yml`, security-scan) is the backstop for this repository; a
# project's own pre-commit hook is the backstop anywhere else.
#
# FALSE POSITIVES
# ===============
# The refusal names the two reviewable ways out, both of which land in the diff: a
# fingerprint line in `.gitleaksignore`, or a `gitleaks:allow` comment on the line. There is
# deliberately no environment-variable escape hatch — an agent could set that on its own.
#
# NO GITLEAKS
# ===========
# `devteam bind` installs it (ADR-0060). When it is missing anyway (DEVTEAM_SKIP_TOOLS, no
# network at install time), the commit is allowed and one hint is queued for the model, once
# per project, through the context-hints channel (ADR-0048) — a hook's stdout never reaches
# the user, so the agent is the one who can tell them.
#
# EXIT CONTRACT
# =============
# A documented exception to "exit 0 in all normal paths" (CLAUDE-md/hooks.md), alongside
# 02c, 03 and 05: a refusal exits 2. Every other path — including every internal error and a
# gitleaks crash — exits 0, enforced by the EXIT trap, because a hook that breaks the user's
# commit for its own failure is worse than one that misses.
set -uo pipefail

VERDICT=""
# shellcheck disable=SC2329,SC2317  # invoked indirectly, by the EXIT trap below.
_secret_guard_exit() {
    if [ "${VERDICT:-}" = "refuse" ]; then
        exit 2
    fi
    exit 0
}
trap _secret_guard_exit EXIT

INPUT=$(cat 2>/dev/null || true)

# Hot path, zero forks: a shell tool, and the word `commit` somewhere in the payload.
case "$INPUT" in
    *commit*) ;;
    *) exit 0 ;;
esac
# Every provider's shell tool: Claude Code `Bash`, Codex `Bash`/`shell`/`exec_command`, opencode
# `bash` — the same alternation 04-task-board.sh uses.
SHELL_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"(Bash|shell|exec_command|bash)"'
[[ "$INPUT" =~ $SHELL_RE ]] || exit 0

# Exact extraction of the command string (see 03-credential-guard.sh for why not greedy). Codex
# may send `command`/`cmd` as an argv array instead: its elements are joined with spaces.
COMMAND=$(printf '%s' "$INPUT" | sed -nE 's/.*"(command|cmd)"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\2/p' | head -1)
if [ -z "$COMMAND" ]; then
    COMMAND=$(printf '%s' "$INPUT" | sed -nE 's/.*"(command|cmd)"[[:space:]]*:[[:space:]]*\[(([^]"]|"([^"\\]|\\.)*")*)\].*/\2/p' | head -1 \
        | sed -E 's/"[[:space:]]*,[[:space:]]*"/ /g; s/^[[:space:]]*"//; s/"[[:space:]]*$//')
fi
[ -n "$COMMAND" ] || exit 0
NL='
'
COMMAND="${COMMAND//\\\"/\"}"
COMMAND="${COMMAND//\\n/$NL}"
COMMAND="${COMMAND//\\t/ }"

# `git commit`, `git -C <dir> commit`, `git -c k=v commit` — a git invocation whose
# subcommand is commit, anywhere in a command chain.
# Global options before the subcommand: `-C <dir>`, `-c k=v`, `--no-pager`, `--git-dir=…`, `-p`.
GIT_OPTS='([[:space:]]+(-[cC][[:space:]]+[^[:space:]]+|--(git-dir|work-tree|namespace|exec-path)[[:space:]]+[^-[:space:]][^[:space:]]*|--[a-z][a-z-]*(=[^[:space:]]+)?|-[pP]))*'
COMMIT_RE="(^|[^[:alnum:]_./-])git${GIT_OPTS}[[:space:]]+commit([[:space:]]|\$)"
printf '%s' "$COMMAND" | grep -qE "$COMMIT_RE" || exit 0

# The repository the commit targets: `git -C <dir>` when given, else the hook's own cwd.
REPO_DIR="."
C_DIR=$(printf '%s' "$COMMAND" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+("([^"]+)"|'"'"'([^'"'"']+)'"'"'|([^[:space:]]+)).*/\2\3\4/p' | head -1)
[ -n "$C_DIR" ] && REPO_DIR="$C_DIR"
# The work tree's root, absolute: git reports changed paths relative to it.
REPO_DIR="$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$REPO_DIR" ] || exit 0

_find_gitleaks() {
    local candidate
    candidate="$(command -v gitleaks 2>/dev/null || true)"
    [ -n "$candidate" ] && { printf '%s' "$candidate"; return 0; }
    # The bin directory `devteam tools install` writes to, which may not be on a hook's PATH.
    for candidate in "${DEVTEAM_BIN_DIR:-}/gitleaks" "$HOME/.local/bin/gitleaks" \
        "${LOCALAPPDATA:-}/Programs/devteam/bin/gitleaks.exe"; do
        [ -x "$candidate" ] && { printf '%s' "$candidate"; return 0; }
    done
    return 1
}

GITLEAKS="$(_find_gitleaks)" || {
    HOOK_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)"
    if [ -n "$HOOK_LIB" ] && [ -f "$HOOK_LIB/warn-once.sh" ] && [ -f "$HOOK_LIB/context-hints.sh" ]; then
        # shellcheck source=scripts/hooks/lib/warn-once.sh
        . "$HOOK_LIB/warn-once.sh"
        # shellcheck source=scripts/hooks/lib/context-hints.sh
        . "$HOOK_LIB/context-hints.sh"
        SESSION="$(devteam_hints_session_id "$INPUT")"
        if [ -n "$SESSION" ] && devteam_warn_once .secret-scan-missing-warned gitleaks-missing; then
            devteam_hints_enqueue "$SESSION" "Commits in this project are not scanned for secrets: gitleaks is not installed. Tell the user that \`devteam tools install gitleaks\` turns the check on."
        fi
    fi
    exit 0
}

ALL_FLAG=0
# `-a`, `-am`, `--all`: tracked changes that are not staged yet are part of this commit.
printf '%s' "$COMMAND" | grep -qE '[[:space:]](-[[:alpha:]]*a[[:alpha:]]*|--all)([[:space:]"'"'"']|$)' && ALL_FLAG=1
# `git add … && git commit` in one command: this hook runs before the add, so nothing is staged
# yet. What the add is about to stage — tracked changes and untracked files — is scanned too.
ADD_FIRST=0
printf '%s' "$COMMAND" | grep -qE "(^|[^[:alnum:]_./-])git${GIT_OPTS}[[:space:]]+add([[:space:]]|\$)" && ADD_FIRST=1

REPORT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/devteam-secret-scan.XXXXXX" 2>/dev/null)" || exit 0
# shellcheck disable=SC2329,SC2317  # invoked indirectly, by the EXIT trap below.
_cleanup_and_exit() {
    rm -rf "$REPORT_DIR"
    _secret_guard_exit
}
trap _cleanup_and_exit EXIT

_scan() {  # <report-file> <gitleaks subcommand and its arguments…>
    local report="$1"
    shift
    "$GITLEAKS" "$@" --redact --no-banner --log-level error \
        --exit-code 3 --report-format json --report-path "$report" >/dev/null 2>&1
}

# What the commit will record. For `-a`/`--all` or a leading `git add`, the add runs first
# against a copy of the index (GIT_INDEX_FILE), so one staged scan sees exactly the commit —
# no file cap, and untracked files nothing adds never count. The copy and any blobs the add
# writes are the hook's own; the real index is never touched.
if [ "$ALL_FLAG" = 1 ] || [ "$ADD_FIRST" = 1 ]; then
    GIT_DIR_ABS="$(git -C "$REPO_DIR" rev-parse --absolute-git-dir 2>/dev/null)" || exit 0
    TMP_INDEX="$REPORT_DIR/index"
    if [ -f "$GIT_DIR_ABS/index" ]; then
        cp "$GIT_DIR_ABS/index" "$TMP_INDEX" 2>/dev/null || exit 0
    fi
    ADD_MODE="-u"
    [ "$ADD_FIRST" = 1 ] && ADD_MODE="-A"
    GIT_INDEX_FILE="$TMP_INDEX" git -C "$REPO_DIR" add "$ADD_MODE" >/dev/null 2>&1 || exit 0
    export GIT_INDEX_FILE="$TMP_INDEX"
fi

# A commit that changes the suppression files themselves is scanned without them: otherwise one
# commit could add a secret and the fingerprint that silences it. gitleaks reads
# `<repo>/.gitleaksignore` and `<repo>/.gitleaks.toml` whatever flags it gets, so the staged
# version of each changed file goes through `gitleaks stdin` from the report directory instead.
OVERRIDE=0
if git -C "$REPO_DIR" diff --cached --name-only -- .gitleaksignore .gitleaks.toml 2>/dev/null | grep -q .; then
    OVERRIDE=1
    printf '[extend]\nuseDefault = true\n' > "$REPORT_DIR/default.toml"
fi

# Any exit other than "clean" (0) or "leaks" (3) is gitleaks failing: that scan allows the commit.
FOUND=0
if [ "$OVERRIDE" = 1 ]; then
    n=0
    while IFS= read -r -d '' path; do
        n=$((n + 1))
        printf '%s\t%s\n' "$n" "$path" >> "$REPORT_DIR/paths.tsv"
        git -C "$REPO_DIR" show ":$path" 2>/dev/null \
            | (cd "$REPORT_DIR" && _scan "$REPORT_DIR/file-$n.json" stdin --config "$REPORT_DIR/default.toml")
        [ $? -eq 3 ] && FOUND=1
    done < <(git -C "$REPO_DIR" diff --cached --name-only --diff-filter=ACMR -z 2>/dev/null)
else
    _scan "$REPORT_DIR/staged.json" git --pre-commit --staged "$REPO_DIR"
    [ $? -eq 3 ] && FOUND=1
fi
[ "$FOUND" = 1 ] || exit 0

# Location fields only. `Secret`/`Match` are redacted already, and are still never printed.
# python.sh gives Windows Git Bash a working `python3`; without one the refusal still stands.
PY_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" 2>/dev/null && pwd)"
# shellcheck source=scripts/lib/python.sh
if [ -n "$PY_LIB" ] && [ -f "$PY_LIB/python.sh" ]; then . "$PY_LIB/python.sh" 2>/dev/null || true; fi
LOCATIONS=$(python3 - "$REPORT_DIR" <<'PY' 2>/dev/null || true
import glob, json, os, sys
names = {}
try:
    for line in open(os.path.join(sys.argv[1], "paths.tsv"), encoding="utf-8"):
        index, _, path = line.rstrip("\n").partition("\t")
        names["file-{}.json".format(index)] = path
except OSError:
    pass
seen = []
for path in sorted(glob.glob(sys.argv[1] + "/*.json")):
    try:
        findings = json.load(open(path, encoding="utf-8")) or []
    except Exception:
        continue
    for f in findings:
        name = names.get(os.path.basename(path)) or f.get("File") or "?"
        row = "  {}:{}  ({})".format(name, f.get("StartLine", "?"), f.get("RuleID", "?"))
        if row not in seen:
            seen.append(row)
print("\n".join(seen[:20]))
if len(seen) > 20:
    print("  … and {} more".format(len(seen) - 20))
PY
)

VERDICT="refuse"
{
    echo "devteam: commit blocked — gitleaks found what looks like a secret in the changes being committed (ADR-0059):"
    [ -n "$LOCATIONS" ] && printf '%s\n' "$LOCATIONS"
    echo "  Remove the value and keep it out of the repository (an env var, the credentials store)."
    echo "  If it is not a secret, mark it where a reviewer will see it: a \`gitleaks:allow\` comment on"
    echo "  that line, or its fingerprint in .gitleaksignore (\`gitleaks git --pre-commit --staged --redact -v\` prints it)."
    [ "$OVERRIDE" = 1 ] && echo "  This commit changes .gitleaksignore or .gitleaks.toml, so they were not applied to it — commit that file on its own first."
} >&2
exit 2
