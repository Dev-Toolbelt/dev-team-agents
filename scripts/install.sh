#!/bin/bash
# install.sh — Installs or updates dev-team-agents at the PROJECT level.
#
# Run this script from your project root. It installs agents and skills
# into .claude/ inside your project (not globally into ~/.claude/).
#
# Usage (from project root):
#   curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
#   bash <(curl -sSL ...) v1.2.0                       # specific version
#   .dev-team-agents/scripts/install.sh latest  # update after first install
#
# What it does:
#   1. Resolves the requested version via the GitHub API
#   2. Downloads and extracts the release tarball (no .git folder)
#   3. Symlinks agents/ to .claude/agents/dev-team/
#   4. Symlinks each skill to .claude/skills/<skill-name>/
#   5. Configures the update-check hook in .claude/settings.json
#   6. Ensures .gitattributes enforces LF line endings for shell scripts
#   7. Records the installed version

set -euo pipefail

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"

PROJECT_ROOT="$(pwd)"
INSTALL_DIR="$PROJECT_ROOT/.dev-team-agents"
AGENTS_TARGET="$PROJECT_ROOT/.claude/agents"
SKILLS_TARGET="$PROJECT_ROOT/.claude/skills"
SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.json"
USER_DATA_DIR="$PROJECT_ROOT/.dev-team-agents/user-data"
VERSION="${1:-latest}"

echo "dev-team-agents installer (project-level)"
echo "========================================="
echo "Project root: $PROJECT_ROOT"
echo ""

# ── Prerequisites check ──────────────────────────────────────────
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "  WARNING: not inside a git repository."
    echo "  Run this installer from your project root (where .git lives)."
    echo ""
fi
if ! command -v claude >/dev/null 2>&1; then
    echo "  NOTE: 'claude' command not found."
    echo "  Install Claude Code before using agents: https://claude.ai/code"
    echo ""
fi

# ── HTTP tool detection ───────────────────────────────────────────
if command -v curl >/dev/null 2>&1; then
    HTTP_GET()      { curl -fsSL "$1"; }
    HTTP_GET_FILE() { curl -fsSL -o "$2" "$1"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_GET()      { wget -qO- "$1"; }
    HTTP_GET_FILE() { wget -qO "$2" "$1"; }
else
    echo "ERROR: curl or wget is required but neither was found." >&2
    exit 1
fi

# ── Temp workspace and failure-safe cleanup ───────────────────────
# Everything downloaded or extracted lives under TMP_DIR.
#
# The installation swap (Step 2c) never deletes the current installation
# before the replacement is in place: the old tree is *renamed aside* and is
# only removed once the new tree has been renamed into position. _cleanup()
# is the safety net — if the process dies between those two renames it puts
# the old tree back, so the project is never left without an installation.
TMP_DIR=$(mktemp -d)
NEW_DIR=""            # staged new installation (sibling of INSTALL_DIR)
OLD_DIR=""            # previous installation, moved aside during the swap
SWAP_DONE=false

# Retries a directory rename a few times before giving up. On Windows a
# `mv` of a directory can fail transiently with a permission/lock error when
# antivirus real-time scanning or an editor/terminal still holds a handle on
# a file inside it — most of these clear within a second or two on their own.
_mv_retry() {
    local src="$1" dst="$2" attempt=0 max_attempts=5
    while [ "$attempt" -lt "$max_attempts" ]; do
        if mv "$src" "$dst" 2>/dev/null; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    return 1
}

_cleanup() {
    local _rc=$?
    if [ "$SWAP_DONE" != true ] && [ -n "$OLD_DIR" ] && [ -d "$OLD_DIR" ]; then
        if [ ! -e "$INSTALL_DIR" ]; then
            if _mv_retry "$OLD_DIR" "$INSTALL_DIR"; then
                echo "" >&2
                echo "→ Install failed (exit $_rc). Previous installation restored." >&2
            else
                echo "" >&2
                echo "ERROR: install failed AND the previous installation could not be" >&2
                echo "       restored automatically. It is intact at:" >&2
                echo "         $OLD_DIR" >&2
                echo "       Restore it with:" >&2
                echo "         mv \"$OLD_DIR\" \"$INSTALL_DIR\"" >&2
            fi
        else
            echo "" >&2
            echo "NOTE: a copy of the previous installation was left at:" >&2
            echo "        $OLD_DIR" >&2
        fi
    fi
    if [ -n "$NEW_DIR" ] && [ -d "$NEW_DIR" ]; then rm -rf "$NEW_DIR" 2>/dev/null || true; fi
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then rm -rf "$TMP_DIR" 2>/dev/null || true; fi
    return $_rc
}
trap _cleanup EXIT

# Surface the real reason an HTTP request failed instead of swallowing it.
# Reads a captured stderr log and prints up to 5 unique lines, indented.
_print_http_error() {
    local _file="$1"
    local _indent="${2:-  }"
    [ -f "$_file" ] && [ -s "$_file" ] || return 0
    echo "${_indent}Reported by the HTTP client:" >&2
    awk 'NF && !seen[$0]++' "$_file" | head -5 | sed "s|^|${_indent}  |" >&2
    return 0
}

# ── Step 1: Resolve version via GitHub API ────────────────────────
_API_ERR="$TMP_DIR/github-api.err"

if [ "$VERSION" = "latest" ]; then
    _releases_json=$(HTTP_GET "${GITHUB_API}/releases/latest" 2>>"$_API_ERR" || true)
    RESOLVED=$(echo "$_releases_json" \
        | grep '"tag_name"' | head -1 \
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/' || true)

    # Fallback: tags list (repo has tags but no formal release)
    if [ -z "$RESOLVED" ]; then
        _tags_json=$(HTTP_GET "${GITHUB_API}/tags" 2>>"$_API_ERR" || true)
        RESOLVED=$(echo "$_tags_json" \
            | grep '"name"' | head -1 \
            | sed 's/.*"name": *"\([^"]*\)".*/\1/' || true)
    fi

    # Fallback: main branch (no tags yet, or the API is unreachable/rate-limited)
    if [ -z "$RESOLVED" ]; then
        echo "→ Could not resolve a release tag from the GitHub API. Using main branch."
        _print_http_error "$_API_ERR" "  "
        RESOLVED="main"
    else
        echo "→ Installing latest: $RESOLVED"
    fi
else
    echo "→ Installing version: $VERSION"
    RESOLVED="$VERSION"
fi

# ── Step 2: Download and extract tarball ──────────────────────────
if [ "$RESOLVED" = "main" ]; then
    TARBALL_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/heads/main.tar.gz"
else
    TARBALL_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/tags/${RESOLVED}.tar.gz"
fi

TMP_TAR="$TMP_DIR/archive.tar.gz"
_DL_ERR="$TMP_DIR/download.err"

set +e
HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>"$_DL_ERR"
_DL_RC=$?
set -e

if [ "$_DL_RC" -ne 0 ]; then
    echo "ERROR: failed to download the release tarball (HTTP client exit $_DL_RC)." >&2
    echo "  URL: $TARBALL_URL" >&2
    _print_http_error "$_DL_ERR" "  "
    if [ -f "$USER_DATA_DIR/.installed-version" ]; then
        echo "→ Keeping the existing installation ($(cat "$USER_DATA_DIR/.installed-version" 2>/dev/null || echo unknown))." >&2
        exit 0
    fi
    exit 1
fi

mkdir -p "$TMP_DIR/extracted"
_TAR_ERR="$TMP_DIR/extract.err"
if ! tar -xzf "$TMP_TAR" -C "$TMP_DIR/extracted" 2>"$_TAR_ERR"; then
    echo "ERROR: could not extract the downloaded archive." >&2
    echo "  URL: $TARBALL_URL" >&2
    echo "  The download may be truncated, or the server returned an error page." >&2
    _print_http_error "$_TAR_ERR" "  "
    exit 1
fi

EXTRACTED_ROOT=$(find "$TMP_DIR/extracted" -maxdepth 1 -mindepth 1 -type d | head -1)
if [ -z "$EXTRACTED_ROOT" ]; then
    echo "ERROR: Tarball extraction produced no directory." >&2
    exit 1
fi

# Preserve last-check timestamp across installs
PREV_CHECK=""
[ -f "$USER_DATA_DIR/.last-update-check" ] && PREV_CHECK=$(cat "$USER_DATA_DIR/.last-update-check")

# Replace existing installation (handles tarball and legacy git-clone installs).
mkdir -p "$(dirname "$INSTALL_DIR")"

# Allowlist: only these top-level entries are distributed to users
KEEP_ROOT=(agents scripts skills templates commands)

for item in "$EXTRACTED_ROOT"/*; do
    name=$(basename "$item")
    keep=false
    for k in "${KEEP_ROOT[@]}"; do
        [ "$name" = "$k" ] && keep=true && break
    done
    [ "$keep" = false ] && rm -rf "$item"
done

# Strip dotfiles/dotdirs (not matched by KEEP_ROOT glob above), repo-only
# scripts, and cross-CLI plumbing. The exact list lives in
# scripts/lib/strip-tarball.sh so the slim-shape CI contract test
# (.github/scripts/ci/slim-bootstrap.sh) sources the SAME rules without duplication.
#
# Source from the extracted tarball, NOT from BASH_SOURCE[0] — when run via
# update.sh (or curl | bash) the script lives in a temp file, but the tarball
# always has strip-tarball.sh at a known path inside EXTRACTED_ROOT.
# shellcheck source=scripts/lib/strip-tarball.sh
source "$EXTRACTED_ROOT/scripts/lib/strip-tarball.sh"
apply_strip "$EXTRACTED_ROOT"

# ── Step 2c: Swap the new installation into place (failure-safe) ──
# Nothing is destroyed before its replacement exists. Order of operations:
#
#   1. stage the new tree as a sibling of the target   (.dev-team-agents.new.$$)
#   2. copy the existing user-data/ into the staged tree
#   3. rename the current installation aside           (.dev-team-agents.old.$$)
#   4. rename the staged tree into place               (same-filesystem rename)
#   5. delete the aside copy — only after step 4 succeeded
#
# Steps 3 and 4 are same-filesystem renames, so each is atomic. A failure at
# any point leaves either the old tree or the new tree in place, never
# nothing, and _cleanup() restores the old tree if we die between 3 and 4.
# Staging as a sibling also means the running script's own directory is
# renamed rather than unlinked, which is what keeps `update.sh` (executing
# from inside the tree being replaced) readable for the rest of its run.
NEW_DIR="$INSTALL_DIR.new.$$"
rm -rf "$NEW_DIR"
if ! _mv_retry "$EXTRACTED_ROOT" "$NEW_DIR"; then
    # mv across filesystems (or a still-locked file) can fail part-way;
    # fall back to an explicit copy.
    rm -rf "$NEW_DIR"
    mkdir -p "$NEW_DIR"
    cp -R "$EXTRACTED_ROOT/." "$NEW_DIR/"
fi

# Carry user data (preferences.json, session-summary.md, telemetry queue, …)
# into the staged tree BEFORE the swap, so it is never the only copy on disk.
if [ -d "$USER_DATA_DIR" ]; then
    rm -rf "$NEW_DIR/user-data"
    cp -R "$USER_DATA_DIR" "$NEW_DIR/user-data"
fi

if [ -d "$INSTALL_DIR" ]; then
    [ -d "$INSTALL_DIR/.git" ] && echo "→ Legacy git-based installation detected. Converting to tarball install..."
    OLD_DIR="$INSTALL_DIR.old.$$"
    rm -rf "$OLD_DIR"
    if ! _mv_retry "$INSTALL_DIR" "$OLD_DIR"; then
        echo "" >&2
        echo "ERROR: could not move $INSTALL_DIR aside to install the update." >&2
        echo "       This is almost always a file inside it locked by another" >&2
        echo "       process — an editor, a terminal cd'd into the folder, or" >&2
        echo "       antivirus real-time scanning (common on Windows right after" >&2
        echo "       a download). Close anything with files open under:" >&2
        echo "         $INSTALL_DIR" >&2
        echo "       then re-run the update. Nothing was changed." >&2
        exit 1
    fi
fi

if ! _mv_retry "$NEW_DIR" "$INSTALL_DIR"; then
    echo "" >&2
    echo "ERROR: staged update could not be moved into place (same permission" >&2
    echo "       lock issue as above). Close anything with files open under:" >&2
    echo "         $INSTALL_DIR" >&2
    echo "       then re-run the update." >&2
    exit 1
fi
SWAP_DONE=true
NEW_DIR=""

if [ -n "$OLD_DIR" ]; then
    rm -rf "$OLD_DIR" 2>/dev/null || true
    OLD_DIR=""
fi

# ── Step 2b: Create credentials.local.json if missing ─────────────
# The distributed tarball carries no user-data/ (it is runtime state, and the
# KEEP_ROOT allowlist strips it), so on a first install this directory does not
# exist yet and the heredoc below would fail with "No such file or directory".
mkdir -p "$USER_DATA_DIR"

CREDENTIALS_FILE="$USER_DATA_DIR/credentials.local.json"
if [ ! -f "$CREDENTIALS_FILE" ]; then
    cat > "$CREDENTIALS_FILE" <<'JSONEOF'
{
  "devops": {
    "agents": ["software-architect", "devops-specialist", "security-specialist"],
    "staging": {
      "ssh": {
        "user": "",
        "host": "",
        "privateKeyPath": "",
        "path": ""
      },
      "database": [
        {
          "type": "",
          "host": "",
          "port": "",
          "database": "",
          "username": "",
          "password": ""
        }
      ]
    },
    "production": {
      "ssh": {
        "user": "",
        "host": "",
        "privateKeyPath": "",
        "path": ""
      },
      "docker": {},
      "database": [
        {
          "type": "",
          "host": "",
          "port": "",
          "database": "",
          "username": "",
          "password": ""
        }
      ]
    }
  },
  "app": {
    "agents": ["software-architect", "backend-developer", "frontend-developer", "code-reviewer", "backend-reviewer", "frontend-reviewer", "qa-specialist", "security-specialist", "backend-test-specialist", "frontend-test-specialist"],
    "staging": {
      "appUrl": "",
      "username": "",
      "password": ""
    },
    "production": {
      "appUrl": "",
      "username": "",
      "password": ""
    }
  }
}
JSONEOF
    chmod 600 "$CREDENTIALS_FILE"
    echo "→ Credentials template: $CREDENTIALS_FILE"
else
    echo "→ Credentials file exists: $CREDENTIALS_FILE (kept)"
fi

# ── Step 2c: Migrate root-level credentials.local.json if present ──
if [ -f "$PROJECT_ROOT/credentials.local.json" ]; then
    if [ ! -f "$CREDENTIALS_FILE" ]; then
        mv "$PROJECT_ROOT/credentials.local.json" "$CREDENTIALS_FILE"
        chmod 600 "$CREDENTIALS_FILE"
        echo "→ Migrated credentials.local.json from project root to $CREDENTIALS_FILE"
    else
        echo "→ WARNING: credentials.local.json found at project root AND at $CREDENTIALS_FILE"
        echo "  The root file will be ignored. Delete it: rm $PROJECT_ROOT/credentials.local.json"
    fi
fi

# ── Step 3: Create target directories ────────────────────────────
COMMANDS_TARGET="$PROJECT_ROOT/.claude/commands"
mkdir -p "$AGENTS_TARGET"
mkdir -p "$SKILLS_TARGET"
mkdir -p "$COMMANDS_TARGET"

# ── Step 4: Link agents ───────────────────────────────────────────
AGENTS_LINK="$AGENTS_TARGET/dev-team"
if [ ! -L "$AGENTS_LINK" ] && [ ! -e "$AGENTS_LINK" ]; then
    ln -s "../../.dev-team-agents/agents" "$AGENTS_LINK"
    echo "→ Agents linked: .claude/agents/dev-team/"
else
    echo "→ Agents already linked: .claude/agents/dev-team/ (skipped)"
fi

# ── Step 5: Link skills ───────────────────────────────────────────
for SKILL_CATEGORY in "$INSTALL_DIR/skills"/*/; do
    for SKILL_DIR in "$SKILL_CATEGORY"*/; do
        [ -d "$SKILL_DIR" ] || continue
        SKILL_NAME=$(basename "$SKILL_DIR")
        SKILL_TARGET_PATH="$SKILLS_TARGET/$SKILL_NAME"
        if [ ! -L "$SKILL_TARGET_PATH" ] && [ ! -e "$SKILL_TARGET_PATH" ]; then
            REL_SKILL="${SKILL_DIR#"$INSTALL_DIR"/}"
            REL_SKILL="${REL_SKILL%/}"
            ln -s "../../.dev-team-agents/${REL_SKILL}" "$SKILL_TARGET_PATH"
        fi
    done
done
echo "→ Skills linked: .claude/skills/"

# Prune stale skill symlinks left over from renamed or removed skills.
# Only removes symlinks that point into dev-team-agents — user-owned skills are untouched.
_stale_count=0
for _SKILL_LINK in "$SKILLS_TARGET"/*; do
    [ -L "$_SKILL_LINK" ] || continue
    case "$(readlink "$_SKILL_LINK")" in
        *dev-team-agents/*) ;;
        *) continue ;;
    esac
    if [ ! -e "$_SKILL_LINK" ]; then
        rm -f "$_SKILL_LINK"
        _stale_count=$((_stale_count + 1))
    fi
done
[ "$_stale_count" -gt 0 ] && echo "→ Removed $_stale_count stale skill symlink(s)"

# ── Step 6: Link commands ─────────────────────────────────────────
# Commands are grouped under .claude/commands/devteam/ so they are invoked
# as /devteam:plan, /devteam:backend, etc. — namespaced and separate from
# any project-specific commands at the .claude/commands/ root.
COMMANDS_LINK="$COMMANDS_TARGET/devteam"
if [ ! -L "$COMMANDS_LINK" ] && [ ! -e "$COMMANDS_LINK" ]; then
    ln -s "../../.dev-team-agents/commands" "$COMMANDS_LINK"
    echo "→ Commands linked: .claude/commands/devteam/ (invoke as /devteam:plan, /devteam:backend, etc.)"
else
    echo "→ Commands already linked: .claude/commands/devteam/ (skipped)"
fi

# ── Step 6b: Verify symlinks materialized as real links ──────────
# On Windows without Developer Mode / core.symlinks=true, `ln -s` and git
# checkout write the link target into a plain text file instead of a real
# symlink. git-bash's `ls -la` still shows it as lrwxrwxrwx (MSYS emulation),
# but Claude Code sees a file — so the dev-team silently disappears. Detect
# it here so the install does not report false success.
_is_materialized() { [ -e "$1" ] && [ ! -L "$1" ] && [ ! -d "$1" ]; }
_broken_links=0
_is_materialized "$AGENTS_LINK"   && _broken_links=$((_broken_links + 1))
_is_materialized "$COMMANDS_LINK" && _broken_links=$((_broken_links + 1))
for _sl in "$SKILLS_TARGET"/*; do
    [ -e "$_sl" ] || continue
    _is_materialized "$_sl" && _broken_links=$((_broken_links + 1))
done

if [ "$_broken_links" -gt 0 ]; then
    echo ""
    echo "⚠️  ${_broken_links} link(s) were written as plain files, not symlinks."
    echo "    This machine cannot create native symlinks (typical on Windows"
    echo "    without Developer Mode). The dev-team will NOT load until this is"
    echo "    fixed. Repair options, in order of preference:"
    echo ""
    echo "    1. Enable Developer Mode (recommended, no admin):"
    echo "       Settings → System → For developers → 'Developer Mode' ON,"
    echo "       then re-run this installer."
    echo "    2. Run once in an elevated (Administrator) terminal:"
    echo "       git config core.symlinks true && git checkout -- .claude"
    echo "    3. After first install, run the repair helper anytime:"
    echo "       bash .dev-team-agents/scripts/fix-symlinks.sh"
    echo ""
    echo "    Restart Claude Code after repairing so it re-indexes the dev-team."
    echo ""
fi

# ── Step 7: Configure hooks in .claude/settings.json ────────────
# Hooks are wrapped with `env -u BASH_ENV -u ENV` so that WSL environments
# where BASH_ENV=/etc/bash.bashrc do not trigger bashrc errors on every hook
# invocation (start-systemd-namespace is absent in many WSL setups).
PRE_TOOL_USE_HOOK="env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-tool-use.sh"
STOP_HOOK="env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/stop.sh"
SESSION_START_HOOK="env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/session-start.sh"
PRE_COMPACT_HOOK="env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-compact.sh"

if [ ! -f "$SETTINGS_FILE" ]; then
    cat > "$SETTINGS_FILE" <<EOF
{
  "includeCoAuthoredBy": false,
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "$PRE_TOOL_USE_HOOK"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$STOP_HOOK"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$SESSION_START_HOOK"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$PRE_COMPACT_HOOK"
          }
        ]
      }
    ]
  }
}
EOF
    echo "→ Created .claude/settings.json with hook dispatchers"
else
    # Inject missing hooks into existing settings.json via python3 (safe JSON merge)
    _inject_hook() {
        local hook_type="$1"
        local hook_cmd="$2"
        local check_str="$3"

        if grep -q "$check_str" "$SETTINGS_FILE" 2>/dev/null; then
            echo "→ $hook_type hook already present in .claude/settings.json"
            return
        fi

        if command -v python3 >/dev/null 2>&1; then
            python3 - "$SETTINGS_FILE" "$hook_type" "$hook_cmd" <<'PYEOF'
import sys, json

settings_file, hook_type, hook_cmd = sys.argv[1], sys.argv[2], sys.argv[3]

with open(settings_file, 'r') as f:
    data = json.load(f)

hooks = data.setdefault('hooks', {})
entries = hooks.setdefault(hook_type, [])

new_entry = {"hooks": [{"type": "command", "command": hook_cmd}]}
if hook_type == "PreToolUse":
    new_entry["matcher"] = ".*"

entries.append(new_entry)

with open(settings_file, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
            echo "→ Added $hook_type hook to .claude/settings.json"
        else
            echo "→ NOTE: python3 not found. Add this $hook_type hook manually to $SETTINGS_FILE:"
            echo "  { \"type\": \"command\", \"command\": \"$hook_cmd\" }"
        fi
    }

    # Migrate existing hook commands to use `env -u BASH_ENV -u ENV` wrapper
    # (fixes WSL /etc/bash.bashrc noise from start-systemd-namespace).
    if grep -q "hooks/pre-tool-use.sh\|hooks/stop.sh\|hooks/session-start.sh\|hooks/pre-compact.sh" "$SETTINGS_FILE" 2>/dev/null; then
        if ! grep -q "env -u BASH_ENV" "$SETTINGS_FILE" 2>/dev/null; then
            if command -v python3 >/dev/null 2>&1; then
                python3 - "$SETTINGS_FILE" <<'PYEOF'
import sys, json, re

settings_file = sys.argv[1]
with open(settings_file, 'r') as f:
    content = f.read()

# Replace bare hook paths with env-wrapped versions
hooks = ["pre-tool-use.sh", "stop.sh", "session-start.sh", "pre-compact.sh"]
for hook in hooks:
    pattern = r'(\.dev-team-agents/scripts/hooks/' + re.escape(hook) + r')'
    replacement = r'env -u BASH_ENV -u ENV \1'
    content = re.sub(pattern, replacement, content)

with open(settings_file, 'w') as f:
    f.write(content)
PYEOF
                echo "→ Migrated hook commands to use env -u BASH_ENV (WSL fix)"
            fi
        else
            echo "→ Hook commands already use env -u BASH_ENV (skipped)"
        fi
    fi

    _inject_hook "PreToolUse"   "$PRE_TOOL_USE_HOOK"   "hooks/pre-tool-use.sh"
    _inject_hook "Stop"         "$STOP_HOOK"           "hooks/stop.sh"
    _inject_hook "SessionStart" "$SESSION_START_HOOK"  "hooks/session-start.sh"
    _inject_hook "PreCompact"   "$PRE_COMPACT_HOOK"    "hooks/pre-compact.sh"

    # Ensure includeCoAuthoredBy is set to false (idempotent)
    if ! grep -q '"includeCoAuthoredBy"' "$SETTINGS_FILE" 2>/dev/null; then
        if command -v python3 >/dev/null 2>&1; then
            python3 - "$SETTINGS_FILE" <<'PYEOF'
import sys, json

settings_file = sys.argv[1]
with open(settings_file, 'r') as f:
    data = json.load(f)

data['includeCoAuthoredBy'] = False

with open(settings_file, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
            echo "→ Set includeCoAuthoredBy: false in .claude/settings.json"
        else
            echo "→ NOTE: python3 not found. Add manually to $SETTINGS_FILE: \"includeCoAuthoredBy\": false"
        fi
    fi
fi

# ── Step 8: Inject pre-compact auto-summary rule into project CLAUDE.md ──────
_TARGET_CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"
_DTA_MARKER="<!-- dev-team-agents: pre-compact-auto-summary -->"

if ! grep -qF "$_DTA_MARKER" "$_TARGET_CLAUDE_MD" 2>/dev/null; then
    cat >> "$_TARGET_CLAUDE_MD" <<'CLAUDEEOF'

<!-- dev-team-agents: pre-compact-auto-summary -->
# Pre-compact Hook — Auto Session Summary
When `/compact` is blocked by the `pre-compact.sh` hook with the message "SESSION SUMMARY REQUIRED (pre-compact)", do the following **automatically, without asking the user**:

1. Write the session summary entry at the top of `.dev-team-agents/user-data/session-summary.md` using the format:
   ```
   ## YYYY-MM-DD HH:MM:SS | [brief task title]
   **Done**: what was implemented or changed

   **Decisions**: key choices made and why

   **Next**: what remains or is recommended next

   ---
   ```
   - Use today's date and current time
   - Base the content on the current conversation context
   - Always write in English
2. After writing, tell the user: "Session summary written. Run `/compact` again to proceed."

Do not ask for confirmation. Do not wait for user input. Write and notify immediately.
CLAUDEEOF
    echo "→ Injected pre-compact auto-summary rule into CLAUDE.md"
else
    echo "→ Pre-compact auto-summary rule already present in CLAUDE.md (skipped)"
fi

# ── Step 9: Record installed version ─────────────────────────────
mkdir -p "$USER_DATA_DIR"
echo "$RESOLVED" > "$USER_DATA_DIR/.installed-version"
if [ -n "$PREV_CHECK" ]; then
    echo "$PREV_CHECK" > "$USER_DATA_DIR/.last-update-check"
else
    date +%s > "$USER_DATA_DIR/.last-update-check"
fi

# ── Step 10: Ensure user-data dir and worktree session are gitignored ────────
_GITIGNORE="$PROJECT_ROOT/.gitignore"

# Remove legacy individual entries if present (migration to directory pattern)
_LEGACY_ENTRIES=(
    ".dev-team-agents/user-data/session-summary.md"
    ".dev-team-agents/user-data/.last-update-check"
    ".dev-team-agents/user-data/.installed-version"
    ".dev-team-agents/user-data/.auto-update"
)
if [ -f "$_GITIGNORE" ]; then
    for _LEGACY in "${_LEGACY_ENTRIES[@]}"; do
        # Use a temp file to remove the line in-place (portable, no sed -i -e portability issues)
        if grep -vF "$_LEGACY" "$_GITIGNORE" > "$_GITIGNORE.tmp"; then
            mv "$_GITIGNORE.tmp" "$_GITIGNORE"
        fi
    done
fi

# Add directory-level ignore (covers all user-data files at once)
_add_gitignore() {
    local _entry="$1"
    if [ -f "$_GITIGNORE" ]; then
        grep -qF "$_entry" "$_GITIGNORE" || echo "$_entry" >> "$_GITIGNORE"
    else
        echo "$_entry" >> "$_GITIGNORE"
    fi
}

_add_gitignore ".dev-team-agents/user-data/"
_add_gitignore "!.dev-team-agents/user-data/graphify.json"
_add_gitignore ".dev-team-agents/user-data/credentials.local.json"
_add_gitignore ".dev-team-agents/.worktree-session"
_add_gitignore ".dev-team-agents/worktrees/"

echo "→ .gitignore updated (user-data dir pattern + credentials + worktree-session + worktrees dir)"

# ── Step 10b: Ensure project .gitattributes enforces LF for shell scripts ─────
# Prevents Windows Git (core.autocrlf=true) from converting hook scripts to
# CRLF on clone/checkout, which causes `bash\r: No such file or directory`
# errors on WSL/Linux.
_GITATTRIBUTES="$PROJECT_ROOT/.gitattributes"

_add_gitattributes() {
    local _entry="$1"
    if [ -f "$_GITATTRIBUTES" ]; then
        grep -qF "$_entry" "$_GITATTRIBUTES" || echo "$_entry" >> "$_GITATTRIBUTES"
    else
        echo "$_entry" >> "$_GITATTRIBUTES"
    fi
}

_added_gitattributes=false

# Add catch-all rule only if no wildcard text=auto line exists yet
if ! grep -qF "* text=auto" "$_GITATTRIBUTES" 2>/dev/null; then
    _add_gitattributes "* text=auto eol=lf"
    _added_gitattributes=true
fi

# Always ensure *.sh has an explicit LF rule
if ! grep -qE '^\*\.sh[[:space:]]' "$_GITATTRIBUTES" 2>/dev/null; then
    _add_gitattributes "*.sh text eol=lf"
    _added_gitattributes=true
fi

if [ "$_added_gitattributes" = true ]; then
    echo "→ .gitattributes updated (LF enforcement for shell scripts)"
else
    echo "→ .gitattributes already has LF enforcement (skipped)"
fi

# ── Step 11: Make scripts executable ─────────────────────────────
# Walk the whole scripts/ tree instead of enumerating directories one by one.
# The manual list silently went stale when scripts/hooks/lib/, scripts/helpers/
# and scripts/lib/ were added — a recursive find cannot drift that way.
if [ -d "$INSTALL_DIR/scripts" ]; then
    find "$INSTALL_DIR/scripts" -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true
fi

# ── Step 12: Set up user preferences ─────────────────────────────
PREFS_FILE="$USER_DATA_DIR/preferences.json"
# Keep this in sync with "language" in scripts/lib/preferences-defaults.json.
PREFS_LANGUAGE="pt-BR"
# Canonical default schema — single source of truth, also read by the
# session-start health-check backfill (scripts/hooks/session-start.sh).
PREFS_DEFAULTS_FILE="$INSTALL_DIR/scripts/lib/preferences-defaults.json"

# ── Interactivity detection ───────────────────────────────────────
# The documented install path is `curl … | bash`, where stdin is a PIPE. A
# `[ -t 0 ]` test is therefore false even when a human is sitting at the
# terminal watching the install scroll by, so it is the wrong question to ask.
# The right question is "can we reach the controlling terminal?" — which is
# exactly what reading from /dev/tty needs. Set DEVTEAM_NONINTERACTIVE=1 to
# force the silent path (CI, image builds, automated provisioning).
_can_prompt() {
    [ "${DEVTEAM_NONINTERACTIVE:-0}" = "1" ] && return 1
    [ -e /dev/tty ] || return 1
    { : </dev/tty; } 2>/dev/null || return 1
    return 0
}

# Read one line from the controlling terminal into the named variable.
# Returns non-zero on EOF or timeout, so callers can distinguish "the user
# pressed Enter" (consent to the default) from "nobody answered".
_prompt_read() {
    local __var="$1"
    local __timeout="${2:-60}"
    local __reply=""
    local __rc=0
    read -r -t "$__timeout" __reply </dev/tty || __rc=$?
    printf -v "$__var" '%s' "$__reply"
    return $__rc
}

# Ask for language preference when a terminal is reachable and
# preferences.json does not yet exist
if [ ! -f "$PREFS_FILE" ] && _can_prompt; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " LANGUAGE PREFERENCE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " In which language should agents converse with you?"
    echo " (Documents and technical output always remain in English)"
    echo ""
    echo "  Examples: en  pt-BR  es  fr  de  ja  zh-CN"
    printf " Language [pt-BR]: "
    _prompt_read PREFS_LANGUAGE 60 || echo ""
    # Sanitize: this value is interpolated into JSON on the no-python3 path.
    PREFS_LANGUAGE=$(printf '%s' "$PREFS_LANGUAGE" | tr -cd 'A-Za-z0-9_-' | cut -c1-16)
    [ -n "$PREFS_LANGUAGE" ] || PREFS_LANGUAGE="pt-BR"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
elif [ ! -f "$PREFS_FILE" ]; then
    echo "→ NOTE: No terminal available. Setting language to 'pt-BR'. Edit .dev-team-agents/user-data/preferences.json to change."
fi

# Value written to a FRESH preferences.json — it comes from the canonical
# schema (auto_update: true). It is never applied to an install that already
# has a preferences.json: existing values win, and a pre-existing file that
# predates the field is treated as "never opted in" (see CONSENT_KEYS below).
AUTO_UPDATE_VALUE="true"

# The legacy .auto-update flag file predates the auto_update field. An install
# carrying it opted in explicitly, so the consent guard must not read its
# missing auto_update key as a "no" and silently revoke that choice.
LEGACY_AUTO_UPDATE="false"
if [ -f "$USER_DATA_DIR/.auto-update" ]; then
    LEGACY_AUTO_UPDATE="true"
fi

# ── Telemetry consent ─────────────────────────────────────────────
# Telemetry is only ever enabled when the user was actually given the chance
# to decline it. The default is DISABLED: if no terminal is reachable there
# is no way to obtain consent, so nothing is collected. (Previously the value
# was preset to "true" and the prompt was gated on `[ -t 0 ]`, which is false
# under the documented `curl … | bash` install — telemetry was therefore
# enabled on that path without the prompt ever being shown.)
TELEMETRY_VALUE="false"
IS_FIRST_INSTALL=false
[ ! -f "$PREFS_FILE" ] && IS_FIRST_INSTALL=true

if [ "$IS_FIRST_INSTALL" = true ] && _can_prompt; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " ANONYMOUS USAGE TELEMETRY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " dev-team-agents collects anonymous usage data to help us"
    echo " understand which agents and commands are most useful."
    echo ""
    echo " What is collected: agent/command names, install events,"
    echo " session counts. No code, file paths, or personal data."
    echo " Full details: PRIVACY.md in the installed package."
    echo ""
    echo " You can opt out at any time by setting"
    echo "   \"telemetry\": false  in .dev-team-agents/user-data/preferences.json"
    echo ""
    printf " Enable anonymous telemetry? [Y/n]: "
    if _prompt_read _TELEMETRY_INPUT 60; then
        case "${_TELEMETRY_INPUT:-y}" in
            [nN]*) TELEMETRY_VALUE="false" ; echo "→ Telemetry disabled." ;;
            *)     TELEMETRY_VALUE="true"  ; echo "→ Telemetry enabled (opt out anytime in preferences.json)." ;;
        esac
    else
        # Timeout or EOF — silence is not consent.
        TELEMETRY_VALUE="false"
        echo ""
        echo "→ No answer received. Telemetry left DISABLED."
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
elif [ "$IS_FIRST_INSTALL" = true ]; then
    echo "→ NOTE: No terminal available to ask about anonymous telemetry, so it is DISABLED."
    echo "  Enable it later with \"telemetry\": true in .dev-team-agents/user-data/preferences.json"
    echo "  (see PRIVACY.md for exactly what would be collected)."
fi

if command -v python3 >/dev/null 2>&1; then
    python3 - "$PREFS_FILE" "$PREFS_DEFAULTS_FILE" "$PREFS_LANGUAGE" "$AUTO_UPDATE_VALUE" "$TELEMETRY_VALUE" "$IS_FIRST_INSTALL" "$LEGACY_AUTO_UPDATE" <<'PYEOF'
import sys, json, os

prefs_file, defaults_file, language, auto_update_str, telemetry_str, is_first_str, \
    legacy_auto_update_str = sys.argv[1:8]
auto_update = (auto_update_str == "true")
telemetry = (telemetry_str == "true")
is_first = (is_first_str == "true")
legacy_auto_update = (legacy_auto_update_str == "true")

# Load the canonical static default schema (single source of truth). If it is
# unreadable, fall back to a minimal set so the install still produces a file;
# the session-start backfill will complete any missing keys on next session.
try:
    with open(defaults_file) as f:
        defaults = json.load(f)
except (json.JSONDecodeError, IOError, FileNotFoundError):
    defaults = {}
# Overlay the prompted/dynamic values onto the static defaults
defaults["language"] = language
defaults["auto_update"] = auto_update
defaults["telemetry"] = telemetry

existing = {}
if os.path.exists(prefs_file):
    try:
        with open(prefs_file, 'r') as f:
            existing = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

# Merge: existing values win; missing keys get defaults
merged = {**defaults, **existing}
# On first install (no existing file), apply the prompted preferences
if is_first:
    merged["language"] = language
    merged["auto_update"] = auto_update
    merged["telemetry"] = telemetry
else:
    # Consent keys are opt-in and must never be switched on by a backfill.
    # An install whose preferences.json predates one of these fields never had
    # the chance to accept it, so the absent key means "no", not "use the
    # default". Only a brand-new file gets the schema's enabled default.
    for key in ("telemetry", "auto_update"):
        if key not in existing:
            merged[key] = False
    # …unless the legacy .auto-update flag records an explicit earlier opt-in.
    if legacy_auto_update:
        merged["auto_update"] = True

with open(prefs_file, 'w') as f:
    json.dump(merged, f, indent=2)
    f.write('\n')
PYEOF
    echo "→ User preferences: .dev-team-agents/user-data/preferences.json"
else
    # Fallback: write a plain JSON file without python3.
    # This heredoc is a hand-maintained MIRROR of
    # scripts/lib/preferences-defaults.json — there is no JSON parser on this
    # path to read the schema with. When you add or change a key there, change
    # it here too; the two drifted once already (qa_browser was missing).
    # Only ever written when no preferences.json exists, so it cannot clobber
    # a user's values and needs no consent-key guard.
    if [ ! -f "$PREFS_FILE" ]; then
        cat > "$PREFS_FILE" <<EOF
{
  "language": "$PREFS_LANGUAGE",
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "session_summary_max_days": 30,
  "session_summary_max_entries": 30,
  "docs_stale_after_days": 30,
  "auto_update": $AUTO_UPDATE_VALUE,
  "update_check_interval_hours": 24,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000,
  "telemetry": $TELEMETRY_VALUE,
  "worktree_active": true,
  "worktree_base_branch": null,
  "worktree_path": ".dev-team-agents/worktrees",
  "worktree_docker_isolate": true,
  "qa_browser": null
}
EOF
        echo "→ User preferences: .dev-team-agents/user-data/preferences.json"
    fi
fi

# Remove legacy .auto-update flag file (migrated to preferences.json)
if [ -f "$USER_DATA_DIR/.auto-update" ]; then
    rm -f "$USER_DATA_DIR/.auto-update"
    echo "→ Migrated .auto-update flag → preferences.json (auto_update field)"
fi

# ── Step 13: Send install telemetry event ────────────────────────────────────
_TELEMETRY_SEND="$INSTALL_DIR/scripts/helpers/telemetry-send.sh"
if [ -f "$_TELEMETRY_SEND" ]; then
    _INSTALL_EVENT="install"
    [ "$IS_FIRST_INSTALL" = true ] && _INSTALL_EVENT="first_install"
    bash "$_TELEMETRY_SEND" --queue "$_INSTALL_EVENT" \
        "{\"install_version\": \"$RESOLVED\"}" 2>/dev/null || true
    bash "$_TELEMETRY_SEND" --flush 2>/dev/null || true
fi

# ── Done ──────────────────────────────────────────────────────────
if [ -f "$PROJECT_ROOT/.gitignore" ] && grep -q "dev-team-agents" "$PROJECT_ROOT/.gitignore"; then
    echo ""
    echo "  NOTE: .gitignore contains 'dev-team-agents'."
    echo "  The new installer uses tarballs — no nested .git folder."
    echo "  Consider removing that entry and committing the files instead."
fi

echo ""
echo "✓ dev-team-agents $RESOLVED installed in this project"
echo ""
echo "Next steps:"
echo "  1. Run the setup-assistant:"
echo "       \"Help me set up this project with dev-team-agents\""
echo "  2. Commit the installation to your project:"
echo "       git add .claude/ && git commit -m \"chore: add dev-team-agents\""
echo "  3. To update later: .dev-team-agents/scripts/update.sh"
echo "  4. To pin a version: .dev-team-agents/scripts/update.sh v1.0.0"
echo ""
echo "  Claude CLI: agents available at .claude/agents/dev-team/"
echo "  opencode:   agents registered in .opencode/opencode.json"
echo "  Codex CLI:  agents available at .codex/agents/ (run install-provider.sh codex)"
echo "  Skills:     available in your provider's skill search path"
echo ""
if [ ! -f "$USER_DATA_DIR/graphify.json" ]; then
echo "---"
echo "Optional: Graphify (knowledge graph for this codebase)"
echo ""
echo "  Graphify indexes your codebase so agents can navigate code without"
echo "  reading every file — fewer tokens per task, faster responses."
echo ""
echo "  To enable it, ask your AI CLI:"
echo "    \"Set up Graphify for this project\""
echo "---"
fi
