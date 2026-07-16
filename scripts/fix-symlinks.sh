#!/usr/bin/env bash
# fix-symlinks.sh — Repairs dev-team-agents links that were materialized as
# regular text files instead of symlinks.
#
# This happens on Windows when git/MSYS checks out or creates the .claude/
# links without native symlink support (Developer Mode off AND the process
# is not elevated AND core.symlinks=false). git-bash then writes each link
# as a ~62-byte text file holding the target path. To git-bash's `ls -la`
# these still look like `lrwxrwxrwx` symlinks (MSYS emulation), but Windows,
# Node, and Claude Code see plain files — so the whole dev-team (commands,
# agents, skills) silently disappears.
#
# Strategy — try first, instruct second:
#   1. Enable core.symlinks and re-materialize each broken link
#      (git checkout if tracked, else re-link like install.sh).
#   2. Re-validate. If the OS now allows native symlinks → done.
#   3. If native symlinks are still blocked → exit 3 so the caller (agent)
#      presents the interactive 3-solution guidance printed below.
#
# Exit codes:
#   0  nothing was broken, OR everything was repaired successfully
#   3  broken links remain — the OS blocks native symlink creation
#   1  unexpected error

# Prevent WSL from loading /etc/bash.bashrc for every spawned sub-process.
unset BASH_ENV ENV

set -uo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT" || exit 1

CLAUDE_DIR="$PROJECT_ROOT/.claude"
AGENTS_LINK="$CLAUDE_DIR/agents/dev-team"
COMMANDS_LINK="$CLAUDE_DIR/commands/devteam"
SKILLS_DIR="$CLAUDE_DIR/skills"
INSTALL_DIR="$CLAUDE_DIR/dev-team-agents"

# ── A link is "materialized" when it exists, is NOT a symlink, and is NOT a
#    directory — i.e. git/MSYS wrote the target path into a plain file. ──────
_is_materialized() {
    [ -e "$1" ] && [ ! -L "$1" ] && [ ! -d "$1" ]
}

# Collect the set of link paths that are currently broken (materialized).
_collect_broken() {
    BROKEN=()
    _is_materialized "$AGENTS_LINK"   && BROKEN+=("$AGENTS_LINK")
    _is_materialized "$COMMANDS_LINK" && BROKEN+=("$COMMANDS_LINK")
    if [ -d "$SKILLS_DIR" ]; then
        for _p in "$SKILLS_DIR"/*; do
            [ -e "$_p" ] || continue
            _is_materialized "$_p" && BROKEN+=("$_p")
        done
    fi
}

# ── Detect ────────────────────────────────────────────────────────────────
_collect_broken
if [ "${#BROKEN[@]}" -eq 0 ]; then
    echo "→ No materialized (broken) dev-team-agents links found. Nothing to fix."
    exit 0
fi

echo "⚠️  Detected ${#BROKEN[@]} dev-team-agents link(s) materialized as files instead of symlinks."
echo "   This is the Windows 'no native symlink support' condition."
echo ""

# ── Attempt auto-fix ──────────────────────────────────────────────────────
IN_GIT=false
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && IN_GIT=true

if [ "$IN_GIT" = true ]; then
    # core.symlinks=true tells git to write real symlinks on the next checkout.
    git config core.symlinks true 2>/dev/null || true
fi

# Re-create each broken link. Scope git checkout to the specific paths only —
# never the whole .claude tree — so unrelated edits are never reverted.
_relink() {
    local link="$1"
    local rel="${link#"$PROJECT_ROOT"/}"

    # 1) If git tracks this exact path, let git re-materialize it.
    if [ "$IN_GIT" = true ] && git ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
        rm -f "$link" 2>/dev/null || true
        git checkout -- "$rel" 2>/dev/null || true
        [ -L "$link" ] && return 0
    fi

    # 2) Otherwise re-link manually, mirroring install.sh's targets.
    local target=""
    case "$link" in
        "$AGENTS_LINK")   target="../dev-team-agents/agents" ;;
        "$COMMANDS_LINK") target="../dev-team-agents/commands" ;;
        "$SKILLS_DIR"/*)
            local name; name="$(basename "$link")"
            # Find the skill directory under the installed package.
            local found; found="$(cd "$INSTALL_DIR" 2>/dev/null && \
                find skills -maxdepth 2 -type d -name "$name" 2>/dev/null | head -1)"
            [ -n "$found" ] && target="../dev-team-agents/${found}"
            ;;
    esac
    [ -z "$target" ] && return 1

    rm -f "$link" 2>/dev/null || true
    ln -s "$target" "$link" 2>/dev/null || true
    [ -L "$link" ] && return 0
    return 1
}

for _link in "${BROKEN[@]}"; do
    _relink "$_link" || true
done

# ── Re-validate ───────────────────────────────────────────────────────────
_collect_broken
if [ "${#BROKEN[@]}" -eq 0 ]; then
    echo "✅ All dev-team-agents links repaired as native symlinks."
    echo ""
    echo "→ Restart Claude Code so it re-indexes commands, agents, and skills."
    exit 0
fi

# ── Still broken → OS blocks native symlinks. Emit interactive guidance. ───
echo "🔧 ${#BROKEN[@]} link(s) still broken — this environment cannot create native symlinks yet."
echo ""
echo "[DEVTEAM:SYMLINK_MANUAL_FIX]"
echo "The OS is blocking native symlink creation. Present these 3 options to the"
echo "user (quiz-first), then auto-run the safe git steps once the blocker clears:"
echo ""
echo "  1. Developer Mode (recommended — no admin, fixes this and future clones)"
echo "     User: Settings → System → For developers → enable 'Developer Mode'."
echo "     Then the agent runs, in this repo:  git config core.symlinks true"
echo "                                         git checkout -- .claude"
echo "     and re-validates — no elevation needed."
echo ""
echo "  2. Elevated terminal once (fastest — no system setting)"
echo "     User opens PowerShell as Administrator and runs, in the project root:"
echo "       git config core.symlinks true"
echo "       git checkout -- .claude"
echo "     Then restart Claude Code (it indexes commands/agents/skills at startup)."
echo ""
echo "  3. Run Claude Code as administrator"
echo "     Fully close the app — including the tray icon and any lingering"
echo "     processes in Task Manager — then right-click the shortcut →"
echo "     'Run as administrator'. Reopen the project and re-run this fix."
echo ""
exit 3
