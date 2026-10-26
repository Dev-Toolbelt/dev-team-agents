#!/usr/bin/env bash
# PreToolUse sub-script: refuses edits to the read-only raw inputs of the gated docs layout
# (skills/shared/doc-flow/SKILL.md § Read-only Inputs, ADR-0045).
#
# WHAT THIS IS NOT
# ================
# A hygiene gate, NOT a sandbox. It sees the file-edit tools only — a Bash `sed -i`, `mv`,
# `rm` or redirect into the same folder walks straight past it, by design: reading shell text
# for every possible write is the recall game 03-credential-guard.sh documents losing. What it
# buys is a loud stop on the obvious path, the edit tool an agent reaches for by default.
# For the same reason it FAILS OPEN: an internal error, an unparseable payload or a path it
# cannot resolve allows the call. A guard that breaks the edit tool is worse than one that misses.
#
# WHAT IT REFUSES
# ===============
# The folders flagged `readonly: true` in scripts/lib/doc-layouts.json for the `docs_layout`
# of the project that OWNS THE TARGET FILE — the nearest `.dev-team-agents/project.json` found
# walking up from the file (bounded), not the session's project dir. A git worktree carries
# its own committed project.json, so `.worktrees/<ctx>/<title>/docs/source/` and a worktree
# outside the project dir are each judged against their own docs write root
# (scripts/lib/docs_root.py). Inside those folders, changing or deleting an EXISTING file is
# refused; creating a NEW one (intake, a design import) is allowed.
#   - A path that runs through a symlink inside such a folder is refused, as scripts/new-adr.sh
#     refuses symlinked ADR folders: what it points at cannot be vouched for.
#   - A path elsewhere whose realpath lands on an existing file inside such a folder (a symlink
#     pointing in) is refused.
#   - On darwin and win32 the comparison is case-insensitive (`docs/Source/` is `docs/source/`
#     on their default filesystems).
#   Claude Code  Edit|MultiEdit|Write|NotebookEdit   tool_input.file_path / notebook_path
#   opencode     edit|write|multiedit (args.filePath), patch (args.patchText); the plugin
#                also sends Edit/Write with tool_input = args
#   Codex        apply_patch — the patch text in tool_input (`*** Update File:`, `*** Delete
#                File:`, `*** Move to:` refused; `*** Add File:` only when the file exists)
#
# PRECISION OVER RECALL
# =====================
# It runs on every tool call in every bound project. A non-edit tool leaves on one bash string
# test. For an edit tool, bash pulls the target paths out of the payload and walks up from each
# (string ops and `-f` tests, no forks); python runs only when one of them, or the session's
# project dir, belongs to a project whose project.json says `"docs_layout": "gated"`.
#
# EXIT CONTRACT
# =============
# Documented, narrow exception to "Exit 0 in all normal paths" in CLAUDE-md/hooks.md
# § PreToolUse Hook Sub-script Convention, alongside 02c and 03: a refusal exits 2 with the
# reason on stderr. Every other path — every internal error included — exits 0, enforced by
# the EXIT trap. `set -e` is deliberately not used.
set -uo pipefail

VERDICT=""
# shellcheck disable=SC2329,SC2317  # invoked indirectly, by the EXIT trap below.
_ro_guard_exit() {
    if [ "${VERDICT:-}" = "refuse" ]; then
        exit 2
    fi
    exit 0
}
trap _ro_guard_exit EXIT

INPUT=$(cat 2>/dev/null || true)

EDIT_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?(Edit|MultiEdit|Write|NotebookEdit|apply_patch|edit|write|multiedit|patch)"'
[[ "$INPUT" =~ $EDIT_RE ]] || exit 0

MAX_LEVELS=64
GATED_RE='"docs_layout"[[:space:]]*:[[:space:]]*"gated"'

# 0 when the nearest .dev-team-agents/project.json at or above $1 says gated — no forks.
_gated_from() {
    local dir="$1" levels=0 json=""
    while [ -n "$dir" ] && [ "$levels" -lt "$MAX_LEVELS" ]; do
        if [ -f "$dir/.dev-team-agents/project.json" ]; then
            IFS= read -r -d '' json < "$dir/.dev-team-agents/project.json" || true
            [[ "$json" =~ $GATED_RE ]]
            return
        fi
        [ "$dir" = "/" ] && return 1
        dir="${dir%/*}"
        [ -n "$dir" ] || dir="/"
        levels=$((levels + 1))
    done
    return 1
}

# 0 when $1 or one of its ancestors is a symlink — it may land in another project's
# read-only folder, which the lexical walk above cannot see. -L tests only, no forks.
_has_link() {
    local dir="$1" levels=0
    while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$levels" -lt "$MAX_LEVELS" ]; do
        [ -L "$dir" ] && return 0
        dir="${dir%/*}"
        levels=$((levels + 1))
    done
    return 1
}

BASE="${PWD}"
CWD_RE='"cwd"[[:space:]]*:[[:space:]]*"([^"\\]+)"'
[[ "$INPUT" =~ $CWD_RE ]] && BASE="${BASH_REMATCH[1]}"

CANDIDATES=("${CLAUDE_PROJECT_DIR:-$PWD}" "$BASE")
# A `\` (a JSON escape, or the `\n` closing a patch header) ends the match: the prefix still
# names an ancestor directory, which is all the walk needs.
for RE in '"(file_path|filePath|notebook_path|path)"[[:space:]]*:[[:space:]]*"([^"\\]+)' \
          '\*\*\* (Add File|Update File|Delete File|Move to): ([^"\\]+)'; do
    REST="$INPUT"
    COUNT=0
    while [ "$COUNT" -lt 64 ] && [[ "$REST" =~ $RE ]]; do
        P="${BASH_REMATCH[2]}"
        case "$P" in /*) ;; *) P="$BASE/$P" ;; esac
        CANDIDATES+=("$P")
        REST="${REST#*"${BASH_REMATCH[0]}"}"
        COUNT=$((COUNT + 1))
    done
done

GATED=""
# The first two candidates are the session dirs: a symlinked ancestor there (macOS /var, /tmp)
# says nothing about the edited file, so only payload paths are checked for links.
I=0
for C in "${CANDIDATES[@]}"; do
    if _gated_from "$C" || { [ "$I" -ge 2 ] && _has_link "$C"; }; then GATED=1; break; fi
    I=$((I + 1))
done
[ -n "$GATED" ] || exit 0

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" 2>/dev/null && pwd)" || exit 0
[ -f "$LIB/doc-layouts.json" ] && [ -f "$LIB/docs_root.py" ] || exit 0
# shellcheck source=scripts/lib/python.sh
if [ -f "$LIB/python.sh" ]; then . "$LIB/python.sh" 2>/dev/null || true; fi
command -v python3 >/dev/null 2>&1 || exit 0

read -r -d '' GUARD_PY <<'PY'
import json, os, re, sys

# Anything unexpected allows the call, silently: a guard that breaks the tool is worse than one that misses.
sys.excepthook = lambda *_: os._exit(0)

lib = sys.argv[1]
sys.path.append(lib)
from docs_root import write_root

MAX_LEVELS = 64
INSENSITIVE = sys.platform in ("darwin", "win32")
EDIT_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit", "edit", "write", "multiedit"}
PATCH_TOOLS = {"apply_patch", "patch"}
PATH_KEYS = ("file_path", "filePath", "notebook_path", "path")
HEADER = re.compile(r"^\*\*\* (Add|Update|Delete) File: (\S(?:[^\n]*\S)?)[ \t]*$|^\*\*\* Move to: (\S(?:[^\n]*\S)?)[ \t]*$", re.M)

payload = json.loads(sys.stdin.read())
tool = payload.get("tool_name") or payload.get("tool") or ""
tool = tool.rsplit(".", 1)[-1]
args = payload.get("tool_input")
if not isinstance(args, dict):
    args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
base = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()

with open(os.path.join(lib, "doc-layouts.json"), encoding="utf-8") as fh:
    layouts = json.load(fh)


def key(path):
    path = os.path.normcase(path)
    return path.casefold() if INSENSITIVE else path


def inside(path, folder):
    path, folder = key(path), key(folder)
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def owner_root(full):
    """Nearest ancestor of ``full`` holding .dev-team-agents/project.json, bounded."""
    here = full
    for _ in range(MAX_LEVELS):
        if os.path.isfile(os.path.join(here, ".dev-team-agents", "project.json")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent
    return None


_readonly = {}


def readonly_of(root):
    """Read-only folders of ``root``, relative to it, for its docs_layout ([] when not gated)."""
    if root not in _readonly:
        folders = []
        with open(os.path.join(root, ".dev-team-agents", "project.json"), encoding="utf-8") as fh:
            layout = json.load(fh).get("docs_layout")
        if layout in layouts.get("layouts", []):
            docs = write_root(root)
            for entry in layouts.get("docs", {}).values():
                rel = entry.get(layout)
                if entry.get("readonly") is True and isinstance(rel, str) and rel:
                    folders.append(os.path.normpath(os.path.join(docs, rel)))
        _readonly[root] = folders
    return _readonly[root]


def folder_of(path):
    """(read-only folder, reason) when ``path`` must not be written, else None."""
    full = os.path.normpath(path if os.path.isabs(path) else os.path.join(base, path))
    root = owner_root(full)
    readonly = readonly_of(root) if root is not None else []
    rel = os.path.relpath(full, root) if root is not None else ""
    for ro in readonly:
        if not inside(rel, ro):
            continue
        walk = root
        for part in rel.split(os.sep):
            walk = os.path.join(walk, part)
            if os.path.islink(walk):
                return ro, "symlink"
        if os.path.lexists(walk):
            return ro, "existing"
        return None
    # Lexically elsewhere: a symlink pointing into a read-only folder still lands on its file,
    # judged by the project that owns the real path — which may not be the one holding the link.
    if os.path.exists(full):
        real = os.path.realpath(full)
        real_root = owner_root(real)
        if real_root is not None:
            for ro in readonly_of(real_root):
                if inside(real, os.path.realpath(os.path.join(real_root, ro))):
                    return ro, "existing"
    return None


hits = []
if tool in EDIT_TOOLS:
    for name in PATH_KEYS:
        value = args.get(name)
        if isinstance(value, str) and value:
            hit = folder_of(value)
            if hit:
                hits.append((value,) + hit)
            break
elif tool in PATCH_TOOLS:
    texts = [v for v in args.values() if isinstance(v, str) and "*** " in v]
    for text in texts:
        for m in HEADER.finditer(text):
            target = m.group(2) or m.group(3)
            hit = folder_of(target)
            if hit:
                hits.append((target,) + hit)

if not hits:
    sys.exit(0)
target, ro, why = hits[0]
shown = ro.rstrip(os.sep) + "/"
reason = "runs through a symlink" if why == "symlink" else "already exists"
sys.stderr.write(
    "readonly-docs-guard: BLOCKED — {0} is in the read-only folder {1} and {2}.\n"
    "Raw inputs are immutable: derive a working doc that cites it instead "
    "(skills/shared/doc-flow/SKILL.md § Read-only Inputs). Adding a new file there is allowed.\n".format(
        target, shown, reason
    )
)
sys.exit(2)
PY

STATUS=0
printf '%s' "$INPUT" | python3 -I -c "$GUARD_PY" "$LIB" || STATUS=$?
[ "$STATUS" -eq 2 ] && VERDICT="refuse"
exit 0
