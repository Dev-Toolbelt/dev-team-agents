#!/usr/bin/env bash
# PreToolUse sub-script: credential-store hygiene guard (ADR-0010).
#
# WHAT THIS IS NOT
# ================
# A hygiene and auditability layer, NOT a sandbox. ADR-0010 says it plainly:
# "an agent with Bash can read anything the user can read", and `scope` is
# "hygiene and auditability, not a sandbox". This hook matches command *text*,
# so it is trivially bypassed — `c""at`, the path held in a variable, base64, a
# python one-liner, a here-doc, or any of a hundred other spellings walk
# straight past it. Presenting it as a boundary would be "a lie that a future
# reader would build on", which is the ADR's own phrasing and the reason this
# paragraph is here. What it actually buys:
#   * a loud, attributable stop on the OBVIOUS spelling of "dump the credential
#     store" — which is the spelling an agent reaches for by default;
#   * a pointer at `devteam cred get`, the one read path that audits itself.
# The real mitigations stay the ones ADR-0010 lists: secrets out of git, out of
# the transcript, scoped narrowly, short-lived, separated per project.
#
# PRECISION OVER RECALL — DELIBERATE
# ==================================
# This runs before every Bash call in every bound project. One false positive on
# a developer's own `grep -r` and the hook gets disabled, after which it buys
# nothing at all. So a command is only acted on when it BOTH references a real
# credential-store path (or the devteam keychain namespace) AND uses a verb that
# discloses or copies content. The word "credentials" in a path is never enough.
# Consequence, stated rather than hidden: recall is low by construction.
#
# OUTPUT DISCIPLINE
# =================
# Never print the matched path's contents, a resolved value, the resolved
# absolute path, or the command line — a guard that echoes what it just refused
# to let you read is the defect it exists to prevent, and the command line is
# itself a place a secret may already be. Messages name the store KIND only.
#
# EXIT CONTRACT
# =============
# Documented, narrow exception to "Exit 0 in all normal paths" in
# CLAUDE-md/hooks.md § PreToolUse Hook Sub-script Convention — the second one,
# alongside 02c-full-suite-guard.sh: a refusal exits 2 so the dispatcher
# propagates it and the tool call is blocked, with the reason on stderr. Every
# other path — including every internal error — exits 0. That is enforced by an
# EXIT trap rather than by discipline, because `set -u` and `pipefail` can abort
# mid-script with a non-zero status, and a non-zero status from this file blocks
# the user's tool call. A hook that breaks the tool is worse than one that
# misses. `set -e` is deliberately NOT used for the same reason.
set -uo pipefail

VERDICT=""
# shellcheck disable=SC2329  # invoked indirectly, by the EXIT trap below
_cred_guard_exit() {
    if [ "${VERDICT:-}" = "refuse" ]; then
        exit 2
    fi
    exit 0
}
trap _cred_guard_exit EXIT

INPUT=$(cat 2>/dev/null || true)

case "$INPUT" in
    *'"tool_name":"Bash"'*|*'"tool_name": "Bash"'*) ;;
    *) exit 0 ;;
esac

# Hot-path gate: pure-bash substring test on the still-unparsed payload, zero
# forks. Unless one of these appears verbatim, nothing below can possibly match,
# so the overwhelming majority of Bash calls leave here having forked nothing.
# Case variants instead of a lowercase fold for the same reason (no `tr` yet,
# and bash 3.2 has no `${var,,}`); `credentials.local.json` on a case-folding
# filesystem is the one realistic mixed-case spelling.
GATE=0
case "$INPUT" in
    *credential*|*Credential*|*CREDENTIAL*|\
    *secret*|*Secret*|*SECRET*|\
    *keychain*|*Keychain*|*KEYCHAIN*|\
    *find-generic-password*|*find-internet-password*|\
    *cmdkey*|*'cred get'*) GATE=1 ;;
esac
# Second stage. `git add -f .` contains no credential word at all, so stage one
# cannot see the one command that stages a secret for a remote. Gated on a force
# flag as well so an ordinary `git add` — by far the common case — still leaves
# here having forked nothing.
# `' -f'` covers -f, -fA, -fv and -fu; `-Af` with the f second is NOT covered,
# and that is a named miss rather than an oversight.
if [ "$GATE" = 0 ]; then
    case "$INPUT" in
        *'git add'*|*'git -C'*|*'git -c'*)
            case "$INPUT" in
                *' -f'*|*'--force'*) GATE=1 ;;
            esac ;;
    esac
fi
[ "$GATE" = 1 ] || exit 0

# Pathname expansion OFF for the rest of the script. Every loop below splits an
# unquoted list on IFS, and SECRET_PATHS legitimately carries a glob
# (`machines/*/secrets`) that must stay a glob for `case` to match with — if the
# shell expanded it against the filesystem first, the generic pattern would be
# silently replaced by whatever concrete directories happen to exist, and would
# stop matching any other machine id. Nothing here needs filename expansion.
set -f

# Extraction is EXACT, not greedy-to-the-last-quote as 02c-full-suite-guard.sh
# does. The ERE group `([^"\\]|\\.)*` consumes escaped quotes but stops at the
# first UNescaped one, so a nested-quote command (`sh -c "cat x"`) is captured
# whole AND the capture ends where the JSON string ends.
#
# 02c can be greedy because it only substring-matches runner shapes, where
# over-capturing is harmless. Here it is not: argument POSITION is load-bearing
# for `_search_is_needle`, and the greedy form swallowed the sibling
# `"description"` field, which then became the last "argument" of the command.
# That made `grep -i <pat> <credfile>` — a real dump — look like a search and
# pass silently, on every realistic payload, since Claude Code always sends a
# description. Do not restore the greedy pattern here.
COMMAND=$(printf '%s' "$INPUT" | sed -nE 's/.*"command"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\1/p' | head -1)
[ -n "$COMMAND" ] || exit 0

# Explicit escape hatch, mirroring 02c's DEVTEAM_FULL_SUITE_CONFIRMED=1 prefix.
# Present on purpose: this guard cannot tell a deliberate, user-requested
# inspection of a credential store from an unprompted one, and an in-band opt-out
# for the one command is strictly better than the alternative the user reaches
# for otherwise, which is deleting the hook. It is not a weakening — see
# WHAT THIS IS NOT above; nothing here was ever a boundary.
case "$COMMAND" in
    DEVTEAM_CRED_READ_CONFIRMED=1\ *) exit 0 ;;
esac

# Two normalisations, both fork-free bash 3.2 substitutions:
#   LC        — JSON-unescaped, for PATH matching. Backslashes survive, because a
#               Windows store path ($APPDATA) is spelled with them.
#   TOK       — metacharacters and backslashes blanked, space-padded, for VERB
#               matching as whitespace-delimited tokens. `$(cat x)`, `;cat x`,
#               `|cat x` and `sh -c \"cat x\"` all reduce to ` cat `.
LC="${COMMAND//\\\"/\"}"
LC="${LC//\\\\/\\}"
LC="${LC//\\n/ }"
LC="${LC//\\t/ }"
# A shell-escaped space: `Application\ Support` must match the same path as
# `"Application Support"`. Only backslash-SPACE is collapsed, so a Windows
# store path ($APPDATA, spelled with backslashes) still matches intact.
LC="${LC//\\ / }"
LC="${LC//[[:space:]]/ }"
LC="$(printf '%s' "$LC" | tr '[:upper:]' '[:lower:]')"

TOK="${LC//[\"\'\\|\&\;\(\)\<\>\{\}\`\$]/ }"
TOK=" $TOK "

# ── protected locations ──────────────────────────────────────────────────────
# Mirrors scripts/lib/devteam/paths.py (data_dir / credentials_dir / secrets_dir)
# in bash, on purpose: a python3 subprocess on every Bash call is not acceptable
# on this path, and the repository already made that call once for state.sh
# ("asking the CLI would mean a python subprocess on every `state_get`").
# All three platform defaults are added regardless of host — the
# `dev-team-agents/data/` segment is distinctive enough that a match on a
# foreign-platform path means a real store, not a collision.
DATA_ROOTS=""
_add_root() { [ -n "${1:-}" ] && DATA_ROOTS="${DATA_ROOTS}$1
"; return 0; }

HOME_DIR="${HOME:-}"
[ -n "${DEVTEAM_HOME:-}" ] && _add_root "${DEVTEAM_HOME%/}/data"
_add_root "$HOME_DIR/Library/Application Support/dev-team-agents/data"
_add_root "${APPDATA:-$HOME_DIR/AppData/Roaming}/dev-team-agents/data"
_add_root "${XDG_DATA_HOME:-$HOME_DIR/.local/share}/dev-team-agents/data"

# A store that was relocated (or created under a $DEVTEAM_HOME this shell does
# not export) is not at any default above. The `state-dir` pointer a v3 bind
# writes resolves to <data>/machines/<id>/projects/<pid>, so four parents give
# <data> — one file read, no parser, and ignored unless it has that exact shape,
# which is what keeps a layout-1 pointer into the project tree out of the list.
# The upward walk is pure bash (no forks) and finds the pointer whenever cwd is
# inside the main checkout, which is the normal case. `git rev-parse` is paid
# only when the walk finds nothing — a linked worktree, whose `.dev-team-agents/`
# lives in the main checkout instead. Same resolution as
# scripts/hooks/lib/data-dirs.sh, reached in the cheap order.
POINTER=""
_walk="$PWD"
while [ -n "$_walk" ] && [ "$_walk" != "/" ]; do
    if [ -f "$_walk/.dev-team-agents/state-dir" ]; then
        POINTER="$_walk/.dev-team-agents/state-dir"
        break
    fi
    _walk="${_walk%/*}"
done
if [ -z "$POINTER" ]; then
    GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null || true)"
    if [ -n "$GIT_COMMON" ]; then
        MAIN_ROOT="$(cd "$GIT_COMMON/.." 2>/dev/null && pwd || true)"
        [ -n "$MAIN_ROOT" ] && [ -f "$MAIN_ROOT/.dev-team-agents/state-dir" ] && \
            POINTER="$MAIN_ROOT/.dev-team-agents/state-dir"
    fi
fi
if [ -n "$POINTER" ]; then
    PTR="$(tr -d '\r\n' < "$POINTER" 2>/dev/null || true)"
    case "$PTR" in
        */machines/*/projects/*)
            PTR="${PTR%/*}"; PTR="${PTR%/*}"; PTR="${PTR%/*}"; PTR="${PTR%/*}"
            _add_root "$PTR" ;;
    esac
fi

# Path classes. REF = the reference layer: non-secret by design (purpose, ref,
# scope — no value), so reading it is a warning at most. The point of noticing
# it is that the same pattern is about to be repeated on a value.
# SECRET = a value at rest, including the last-resort insecure.json. Reading it
# IS dumping a credential store.
REF_PATHS=""
SECRET_PATHS=""
ROOT_PATHS=""
# The absolute store paths only, without the bare-basename entry. Used by
# `_search_is_needle`: an absolute store path is never a plausible grep pattern,
# and on macOS it contains a space ("Application Support") so the token walk
# cannot see it as one token anyway. Keeping it out of the needle logic is what
# stops `grep -i token '<store>/secrets/insecure.json'` being read as a search.
ABS_PATHS=""
# DATA_ROOTS is lowercased ONCE here — the single `tr` fork on this path. Doing
# it inside _add_path cost one fork per path variant (~48 per call, measured at
# 97ms) for a result that is identical.
DATA_ROOTS="$(printf '%s' "$DATA_ROOTS" | tr '[:upper:]' '[:lower:]')"
HOME_LC="$(printf '%s' "$HOME_DIR" | tr '[:upper:]' '[:lower:]')"

_add_path() {
    local lc="$2"
    case "$1" in
        ref) REF_PATHS="${REF_PATHS}${lc}
" ;;
        secret) SECRET_PATHS="${SECRET_PATHS}${lc}
" ;;
        root) ROOT_PATHS="${ROOT_PATHS}${lc}
" ;;
        abs) ABS_PATHS="${ABS_PATHS}${lc}
" ;;
    esac
}

OLDIFS="$IFS"
IFS='
'
for root in $DATA_ROOTS; do
    [ -n "$root" ] || continue
    for variant in "$root" "${root/#$HOME_LC/\~}" "${root/#$HOME_LC/\$home}"; do
        _add_path ref "$variant/credentials"
        _add_path secret "$variant/machines/*/secrets"
        _add_path secret "$variant/secrets"
        _add_path root "$variant"
        _add_path abs "$variant/credentials"
        _add_path abs "$variant/machines/*/secrets"
        _add_path abs "$variant/secrets"
    done
done
IFS="$OLDIFS"
# The v2 plaintext file, wherever it sits: unmigrated projects still have one,
# and this repository carries one at its own root. Matched by basename because
# it holds VALUES and there is no benign reason to dump it — the sanctioned read
# is `devteam cred get`, and `devteam cred import` migrates it.
_add_path secret "credentials.local.json"

# ── verb classes ─────────────────────────────────────────────────────────────
# DUMP discloses or copies content out. ENUM only reveals existence, names or
# size — worth a note, never a block. Anything not listed is silent: `chmod`,
# `touch`, `test -f`, `realpath` and friends are deliberately absent, because a
# health check legitimately runs them and a nag there is pure noise.
DUMP_VERBS="cat bat less more head tail nl tac strings xxd od hexdump base64 grep egrep fgrep rg ag ack jq yq awk sed perl ruby php node python python3 tee cp mv rsync scp sftp tar zip gzip curl wget openssl pbcopy xclip xsel read mapfile readarray source eval export diff cmp dd open code subl cursor"
ENUM_VERBS="ls dir find tree stat du wc file rm shasum md5 md5sum sha1sum sha256sum"

_has_verb() {
    # IFS is set explicitly, not inherited: the segment loop below runs with
    # IFS=newline, and the verb lists are SPACE-delimited. Inheriting made the
    # whole list expand as one word, so no verb ever matched inside the loop and
    # every segment came back clean. Same reason `_matches` sets its own.
    local v old="$IFS"
    IFS=' '
    for v in $2; do
        case "$1" in *" $v "*) IFS="$old"; return 0 ;; esac
    done
    IFS="$old"
    return 1
}

_matches() {  # _matches <newline list of lc glob patterns> <haystack>
    local p old="$IFS"
    IFS='
'
    for p in $1; do
        [ -n "$p" ] || continue
        # shellcheck disable=SC2254  # $p intentionally carries a glob (machines/*/secrets)
        case "$2" in *$p*) IFS="$old"; return 0 ;; esac
    done
    IFS="$old"
    return 1
}

_tok_protected() {  # one token: is it a protected target?
    _matches "$SECRET_PATHS" "$1" && return 0
    _matches "$REF_PATHS" "$1" && return 0
    return 1
}

# _search_is_needle <seg_tok> <seg> — true when the protected name is what a search
# verb is LOOKING FOR rather than what it is opening.
#
# `grep -n "credentials.local.json" docs/prompts/x.md` reads a markdown file; the
# protected basename is the needle. `grep -i token credentials.local.json` reads
# the credential file. Both are `grep` + a DUMP verb + a protected basename in
# one string, so only argument POSITION separates them, and position is what this
# walks: skip flags, then the first non-flag token is the pattern and the last is
# the target.
#
# Two rules, both requiring a search verb in the segment:
#   A. the protected token IS the pattern and no later token is protected
#      — exact, and also covers `rg <name>` with no path argument at all.
#   B. the protected token is not the LAST non-flag token and that last token is
#      not protected — catches a multi-word quoted pattern
#      (`grep "uses credentials.local.json" docs.md`), which rule A cannot see
#      because quote removal splits it into several tokens.
#
# Rule B's cost, stated rather than buried: `grep pat <credfile> <otherfile>` —
# two targets, the protected one not last — is let through, and that is a real
# read. This is the direction chosen on purpose. `grep <name> <docs>` is a
# frequent, harmless command that anyone maintaining these docs runs, while the
# realistic spellings of dumping the file keep the path in the last position
# (`grep pat <credfile>`, `cat <credfile>`, `< <credfile>`), which rules A and B
# both leave refused. Preferring recall here, precision everywhere else.
_search_is_needle() {
    local t old="$IFS"
    local seen_verb=0 nonflag=0 prot_pattern=0 prot_later=0 last_prot=0
    IFS=' '
    for t in $1; do
        [ -n "$t" ] || continue
        if [ "$seen_verb" = 0 ]; then
            case "$t" in
                grep|egrep|fgrep|rg|ag|ack|ripgrep) seen_verb=1 ;;
            esac
            continue
        fi
        case "$t" in -*) continue ;; esac
        nonflag=$((nonflag + 1))
        if _tok_protected "$t"; then
            last_prot=1
            if [ "$nonflag" = 1 ]; then prot_pattern=1; else prot_later=1; fi
        else
            last_prot=0
        fi
    done
    IFS="$old"
    [ "$seen_verb" = 1 ] || return 1
    # An ABSOLUTE store path is never a needle. It also defeats the token walk
    # above, because the macOS store path contains a space and splits into two
    # tokens that neither match on their own — which silently turned
    # `grep -i token '<store>/secrets/insecure.json'` into a "search". Bail
    # before either rule can fire.
    _matches "$ABS_PATHS" "$2" && return 1
    # A
    [ "$prot_pattern" = 1 ] && [ "$prot_later" = 0 ] && return 0
    # B
    [ "$nonflag" -ge 2 ] && [ "$last_prot" = 0 ] && return 0
    return 1
}

#  ── git subcommand lists: one EXEMPTS, one REFUSES ──────────────────────────
#  These two lists are deliberately adjacent, because a maintainer who sees only
#  one of them will get the other wrong. They are not two halves of one set and
#  no command name is missing from both by accident:
#
#    EXEMPT  log show diff blame grep whatchanged rev-list shortlog stash status
#            — these READ committed objects. Every protected path is gitignored,
#              so history cannot contain one and `git show HEAD:<path>` returns
#              nothing. They must stay SILENT.
#    REFUSE  add, and only with -f/--force
#            — this WRITES to the index. `-f` on a gitignored credential file has
#              no innocent reading: the file is gitignored precisely so a plain
#              `git add` skips it, and forcing it is the first step of the
#              disaster ADR-0010 names in its Context, "one `git add -f` away
#              from a public repository".
#
#  Everything else git does is in NEITHER list on purpose — silent, because it
#  neither discloses a value nor stages one.

# _protected_under <dir> — is there a credential file beneath this add target?
# Only `credentials.local.json` is looked for, and that is not an oversight:
# `git add` stages from the WORK TREE, and the v3 store lives outside every
# repository, so the v2 plaintext file is the only protected thing a force-add
# can reach.
# `-maxdepth 4` and the prune list bound the cost, since this forks a `find`.
# Consequence, stated: a credential file nested deeper than 4 levels, or inside a
# pruned directory, is missed. Depth 4 covers the two locations that exist in
# practice — the repository root and `.dev-team-agents/user-data/`.
_protected_under() {
    local hit
    hit="$(find "$1" -maxdepth 4 \
        \( -name node_modules -o -name .git -o -name vendor -o -name dist \
           -o -name build -o -name .venv -o -name target \) -prune \
        -o -name 'credentials.local.json' -print 2>/dev/null | head -1 || true)"
    [ -n "$hit" ]
}

# _sweep_root <pathspec> — the directory a non-file add target would sweep.
# Prints nothing and returns 1 when the token is not a directory sweep.
# The token is case-folded, like everything else in a segment. On a
# case-insensitive filesystem (macOS, Windows) that is invisible; on Linux, an
# add target with an uppercase component (`git add -f Docs/`) fails the `-d`
# test and tier 2 misses it. Named rather than papered over: the alternative is
# carrying a second, case-preserving copy of every segment through the whole
# decision path, and tier 1 — the named-path case, which is the one with no
# innocent reading — is unaffected because both sides of that match are folded.
_sweep_root() {
    local t="$1"
    case "$t" in
        .|./|:/) printf '%s' "."; return 0 ;;
    esac
    t="${t#:\(*\)}"
    case "$t" in
        *\**) t="${t%/*}"; [ -n "$t" ] || t="." ;;
    esac
    [ -d "$t" ] || return 1
    printf '%s' "$t"
}

# _git_add_force <seg_tok> — true when this segment force-adds a protected path.
# `add` must be the FIRST non-flag token after `git` (allowing the `-C <dir>` and
# `-c <cfg>` pairs), so a commit message that merely quotes the words
# `add -f credentials.local.json` is not mistaken for the command itself.
_git_add_force() {
    local t old="$IFS" stage=git skip=0
    local force=0 sweep_all=0 prot_named=0 targets="" root
    IFS=' '
    for t in $1; do
        [ -n "$t" ] || continue
        if [ "$skip" = 1 ]; then skip=0; continue; fi
        case "$stage" in
            git)
                case "$t" in
                    git|*/git) stage=sub ;;
                esac
                continue ;;
            sub)
                case "$t" in
                    -C|-c) skip=1; continue ;;
                    -*) continue ;;
                    add) stage=args; continue ;;
                    *) IFS="$old"; return 1 ;;
                esac ;;
            args)
                case "$t" in
                    --force) force=1; continue ;;
                    --all|--update) sweep_all=1; continue ;;
                    --*) continue ;;
                    -*)
                        # Patterns are LOWERCASE because seg_tok has been
                        # case-folded: `-A` arrives as `-a`, and matching `*A*`
                        # here silently never fired, so `git add -f -A` — a
                        # whole-tree force-add — passed clean. Any flag test
                        # added below must be lowercase for the same reason.
                        case "$t" in *f*) force=1 ;; esac
                        case "$t" in *a*|*u*) sweep_all=1 ;; esac
                        continue ;;
                esac
                if _tok_protected "$t"; then
                    prot_named=1
                else
                    targets="$targets $t"
                fi ;;
        esac
    done
    IFS="$old"

    [ "$stage" = args ] || return 1
    [ "$force" = 1 ] || return 1          # a plain `git add` skips ignored files
    [ "$prot_named" = 1 ] && return 0     # tier 1: the path is named outright

    # tier 2: a directory / glob / -A sweep, but ONLY when something protected is
    # actually beneath it. Force-adding an ignored build artifact is common and
    # none of this guard's business.
    if [ -z "$targets" ] && [ "$sweep_all" = 1 ]; then targets=" ."; fi
    [ -n "$targets" ] || return 1
    IFS=' '
    for t in $targets; do
        [ -n "$t" ] || continue
        if root="$(_sweep_root "$t")"; then
            if _protected_under "$root"; then IFS="$old"; return 0; fi
        fi
    done
    IFS="$old"
    return 1
}

# ── decision, per pipeline segment ───────────────────────────────────────────
# The command is judged one PIPELINE SEGMENT at a time, not as one string. `|`,
# `;` and `&` separate; `<` and `>` deliberately do NOT, because a redirection
# belongs to the command it feeds (`python3 - < <secrets>` stays one segment).
#
# Segmenting exists because of a real false positive: piping any command through
# a formatter puts a DUMP verb in the same string as whatever path the first
# stage named, so `devteam cred import <file> | sed 's/^/  /'` — the migration
# ADR-0010 specifies, in the shape anyone would actually run it — was refused.
# Per segment, the formatter stage carries a verb and no target, and the stage
# that carries the target is the audited CLI itself.
NL='
'
SEGMENTS="${LC//\|/$NL}"
SEGMENTS="${SEGMENTS//;/$NL}"
SEGMENTS="${SEGMENTS//&/$NL}"

ACTION=""
KIND=""
_escalate() {  # _escalate <action> <kind> — a refusal always wins over a warning
    if [ "$1" = "refuse" ]; then
        ACTION="refuse"
        KIND="$2"
    elif [ -z "$ACTION" ]; then
        ACTION="warn"
        KIND="$2"
    fi
    return 0
}

OLDIFS="$IFS"
IFS="$NL"
for seg in $SEGMENTS; do
    [ -n "$seg" ] || continue
    # A heredoc or herestring body is inline DATA, not a path being read:
    # `cat >> docs/notes.md <<EOF … credentials.local.json … EOF` documents the
    # name, and `cat <<< '<name>' > file` writes it. Only the part of the segment
    # BEFORE `<<` can name a target, so truncate there.
    # Consequence, stated rather than buried: a heredoc that FEEDS a reader
    # (`python3 - <<'PY' … open('<secrets>') … PY`) is invisible to this guard.
    # That is the python-one-liner bypass already named in WHAT THIS IS NOT at
    # the top of the file, not a new hole opened here.
    seg="${seg%%<<*}"
    [ -n "$seg" ] || continue
    seg_tok="${seg//[\"\'\\\(\)\<\>\{\}\`\$]/ }"
    seg_tok=" $seg_tok "

    # `devteam cred …` EXEMPTION. Every subcommand of the audited CLI legitimately
    # names a credential path or key on its own command line — `cred import <file>`
    # cannot be spelled any other way, and `cred set <key> < file` reads one — so a
    # protected path in this segment is an ARGUMENT to the resolver, not a dump of
    # it. Also covers `cred get/set/list/check`.
    #
    # This widens the bypass surface, knowingly and on the record: segments are
    # judged separately, so `devteam cred list ; cat <secrets>` is still caught,
    # but `devteam cred list "$(cat <secrets>)"` is not caught at all. The widening
    # is the right trade, for the reason in WHAT THIS IS NOT at the top of this
    # file — the guard was never a boundary, so a bypass costs a bypass that was
    # already available in a dozen spellings, whereas a false positive on the one
    # command that migrates a plaintext credential file onto the audited path is
    # the failure that gets the entire hook deleted. Do not "tighten" this back
    # without reading that paragraph first.
    case "$seg_tok" in *devteam\ cred\ *|*devteam\ cred) continue ;; esac

    # GIT ADD --FORCE. Checked BEFORE the history exemption below, which would
    # otherwise `continue` straight past it. See the two-list comment above.
    if _git_add_force "$seg_tok"; then
        _escalate refuse gitadd
        continue
    fi

    # GIT HISTORY EXEMPTION. `git log/show/diff/blame/grep -- <path>` reads
    # committed objects, not the live store, and every protected path is
    # gitignored — so history cannot contain one and `git show HEAD:<path>`
    # returns nothing. Written as an explicit rule rather than left to the
    # accident that git subcommands are absent from the verb lists, because
    # `diff` and `grep` are BOTH already DUMP verbs: `git diff -- <credfile>`
    # was refused before this rule existed, and a future edit to those lists
    # would silently reintroduce the same class of false positive.
    case "$seg_tok" in
        *" git "*)
            case "$seg_tok" in
                *" log "*|*" show "*|*" diff "*|*" blame "*|*" grep "*|\
                *" whatchanged "*|*" rev-list "*|*" shortlog "*|*" stash "*|\
                *" log"|*" show"|*" diff"|*" status "*) continue ;;
            esac ;;
    esac

    seg_kind=""
    if _matches "$SECRET_PATHS" "$seg"; then
        seg_kind="secret"
    elif _matches "$REF_PATHS" "$seg"; then
        seg_kind="ref"
    fi

    # `< file` and `$(<file)` disclose content with no verb of their own. Any
    # `<<` was already cut above, so a remaining `<` is a real file redirect.
    seg_redir=0
    case "$seg" in *'<'*) seg_redir=1 ;; esac

    # The protected name is the needle, not the file being opened.
    if [ -n "$seg_kind" ] && _search_is_needle "$seg_tok" "$seg"; then
        continue
    fi

    if [ -n "$seg_kind" ]; then
        if _has_verb "$seg_tok" "$DUMP_VERBS" || [ "$seg_redir" = 1 ]; then
            if [ "$seg_kind" = "secret" ]; then
                _escalate refuse secret
            else
                _escalate warn ref
            fi
        elif _has_verb "$seg_tok" "$ENUM_VERBS"; then
            _escalate warn "$seg_kind"
        fi
        continue
    fi

    # A sweep whose obvious purpose is to LOCATE the store's credential subtree:
    # `find <data> -name credentials`, `ls -R <data> | grep secrets`. The store root
    # on its own is deliberately NOT protected — reading `preferences.json` out of it
    # is legitimate and frequent, and warning on that is the noise that gets a hook
    # switched off — so the search term has to be there too for this to fire.
    if _matches "$ROOT_PATHS" "$seg"; then
        if _has_verb "$seg_tok" "$ENUM_VERBS" || _has_verb "$seg_tok" "$DUMP_VERBS"; then
            case "$seg" in
                *credential*|*secret*) _escalate warn sweep ;;
            esac
        fi
    fi
done
IFS="$OLDIFS"

# ── keychain / OS secret store ───────────────────────────────────────────────
# Only the devteam namespace is refused: service `dev-team-agents`, account
# `devteam/<project_id>/<key>` (scripts/lib/devteam/secrets.py). A developer
# reading their OWN app's keychain item is none of this hook's business, and
# refusing it is exactly the false positive that gets the hook deleted.
# Any `security`/`secret-tool` call arriving here is by definition outside the
# resolver: `devteam cred get` reaches the keychain from python, which never
# passes through a PreToolUse Bash hook.
case "$TOK" in
    *" security "*|*" secret-tool "*|*" cmdkey "*)
        case "$LC" in
            *find-generic-password*|*find-internet-password*|*" lookup "*|*" search "*)
                case "$LC" in
                    *devteam/*|*dev-team-agents*) ACTION="refuse"; KIND="keychain" ;;
                esac ;;
        esac
        case "$LC" in
            *dump-keychain*)
                # -d is what prints the values; bare `dump-keychain` lists items.
                case "$LC" in
                    *" -d"*|*--dump*) ACTION="refuse"; KIND="keychain" ;;
                    *) [ -z "$ACTION" ] && ACTION="warn" && KIND="keychain" ;;
                esac ;;
            *" /list"*|*" -list"*)
                case "$TOK" in
                    *" cmdkey "*) [ -z "$ACTION" ] && ACTION="warn" && KIND="keychain" ;;
                esac ;;
        esac ;;
esac

# ADR-0010: "warns on echoing a resolved value". A bare `devteam cred get` is
# the sanctioned path and stays silent; piping it into something that reproduces
# the value in the transcript, a log or a request is the pattern worth a note.
# Anchored on the full `devteam cred get` and not a bare `cred get`: the looser
# form fired on an unrelated command that merely quoted this hook's own help
# text, which is the false-positive class this file exists to avoid.
if [ -z "$ACTION" ]; then
    case "$LC" in
        *"devteam cred get"*)
            case "$TOK" in
                *" echo "*|*" printf "*|*" tee "*|*" curl "*|*" wget "*|*" logger "*)
                    ACTION="warn"; KIND="echo" ;;
            esac ;;
    esac
fi

[ -n "$ACTION" ] || exit 0

case "$KIND" in
    secret)   WHAT="a credential VALUE store (data/machines/<machine-id>/secrets/, or a v2 credentials.local.json)" ;;
    keychain) WHAT="the dev-team-agents OS keychain namespace" ;;
    ref)      WHAT="the credential REFERENCE layer (data/credentials/ — no values, but the same pattern on a value would be a leak)" ;;
    echo)     WHAT="a resolved credential value being reproduced in output" ;;
    gitadd)   WHAT="a credential file being force-added to the git index" ;;
    sweep)    WHAT="the credential store's location (a sweep looking for the credential or secret subtree)" ;;
    *)        WHAT="a credential store" ;;
esac

if [ "$ACTION" = "refuse" ] && [ "$KIND" = "gitadd" ]; then
    {
        echo "credential-guard: BLOCKED — this command force-adds a credential file to the git index."
        echo "This is not about the read being unaudited. That file is gitignored ON PURPOSE, which is the only thing keeping the value out of the repository; -f overrides exactly that, and one push then puts a live secret on a remote where it cannot be recalled."
        echo "The fix is to remove the value, not to stage it: run \`devteam cred import <file>\`, which pushes each value into the OS keychain, rewrites the file as non-secret references and quarantines the original. A migrated file has nothing left in it to leak, and committing it is then harmless."
        echo "If you are force-adding something else and a credential file merely sits under the same path, name that path explicitly instead of sweeping it."
    } >&2
    VERDICT="refuse"
    exit 2
fi

if [ "$ACTION" = "refuse" ]; then
    {
        echo "credential-guard: BLOCKED — this command reads $WHAT."
        echo "Per ADR-0010 the only sanctioned read is \`devteam cred get <key>\`, which checks scope and appends an audit line (who, when, which key — never the value)."
        echo "This guard is hygiene, not a sandbox: it matches command text and is trivially bypassed. It is telling you the read is unaudited, not that it is impossible."
        echo "If the user explicitly asked for this exact command, reissue it prefixed with DEVTEAM_CRED_READ_CONFIRMED=1. Never paste a credential value into your reply, a file, or a commit."
    } >&2
    VERDICT="refuse"
    exit 2
fi

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"credential-guard: this command touches %s. Reading it is allowed, but per ADR-0010 credential VALUES are read only via devteam cred get <key>, which scopes and audits the read. Do not reproduce any value in your reply, a log, a file or a commit."}}\n' "$WHAT"
exit 0
