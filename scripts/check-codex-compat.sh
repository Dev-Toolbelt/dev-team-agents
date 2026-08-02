#!/usr/bin/env bash
# check-codex-compat.sh — Lint rendered Codex output for forbidden terms.
# Scans .codex/skills/**/SKILL.md, .codex/agents/*.toml, and any leftover
# legacy prompt files for instructions that reference tools, paths, or
# concepts that do not exist in Codex CLI.
#
# Usage:
#   bash scripts/check-codex-compat.sh                    # scan .codex/ in current dir
#   bash scripts/check-codex-compat.sh /path/to/.codex    # scan specific dir
#   bash scripts/check-codex-compat.sh --fix              # auto-fix known issues
#
# Exit code:
#   0 — no issues found
#   1 — forbidden terms found (and not --fix)
#   2 — target directory not found

set -euo pipefail

TARGET="${1:-.codex}"
FIX_MODE=false
if [ "${1:-}" = "--fix" ]; then
    FIX_MODE=true
    TARGET="${2:-.codex}"
fi

if [ ! -d "$TARGET" ]; then
    echo "check-codex-compat: target not found: $TARGET" >&2
    exit 2
fi

ISSUES=0

# Forbidden patterns: if any of these appear, the output references
# tooling that Codex does not have natively.
FORBIDDEN_PATTERNS=(
    "AskUserQuestion"
    "TodoWrite"
    "_plain_text_"
    "_post_render_note"
    "**NOTE for Codex port"
    "Bodies using _plain_text_question_"
    "\`a plain text question\`"
    "\`a direct plain-text question\`"
    "a plain text question tool"
    "a direct plain-text question tool"
    "<!-- model:"
)

check_file() {
    local file="$1"
    local name
    name=$(basename "$file")
    for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
        if grep -qF "$pattern" "$file" 2>/dev/null; then
            echo "  ✗ $name: contains '$pattern'"
            ISSUES=$((ISSUES + 1))
            if $FIX_MODE; then
                local tmp
                tmp=$(mktemp)
                sed "s/$pattern//g" "$file" > "$tmp" && mv "$tmp" "$file"
                echo "    → fixed (removed '$pattern')"
            fi
        fi
    done
}

echo "check-codex-compat: scanning $TARGET for forbidden terms..."
echo ""

# Scan prompts
PROMPTS_DIR="$TARGET/prompts"
if [ -d "$PROMPTS_DIR" ]; then
    echo "--- prompts/ ---"
    for f in "$PROMPTS_DIR"/*.md; do
        [ -f "$f" ] && check_file "$f"
    done
fi

# Scan agents
AGENTS_DIR="$TARGET/agents"
if [ -d "$AGENTS_DIR" ]; then
    echo "--- agents/ ---"
    for f in "$AGENTS_DIR"/*.toml; do
        [ -f "$f" ] && check_file "$f"
    done
fi

# Scan hooks.json
HOOKS_FILE="$TARGET/hooks.json"
if [ -f "$HOOKS_FILE" ]; then
    echo "--- hooks.json ---"
    check_file "$HOOKS_FILE"
fi

# Scan generated/local skills
SKILLS_DIR="$TARGET/skills"
if [ -d "$SKILLS_DIR" ]; then
    echo "--- skills/ ---"
    find "$SKILLS_DIR" -type f -name 'SKILL.md' | while read -r f; do
        check_file "$f"
    done
fi

echo ""
if [ "$ISSUES" -eq 0 ]; then
    echo "check-codex-compat: clean ✓"
    exit 0
else
    echo "check-codex-compat: $ISSUES issues found"
    if $FIX_MODE; then
        echo "check-codex-compat: auto-fixes applied. Re-run to verify."
    else
        echo "check-codex-compat: run with --fix to auto-remove forbidden terms"
    fi
    exit 1
fi
