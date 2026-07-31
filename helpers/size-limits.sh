#!/usr/bin/env bash
# Usage: bash helpers/size-limits.sh [--warn-only] [--quiet]
#
# Validates line-count limits declared in CLAUDE.md:
#   agents/    — max ~200 lines each
#   skills/    — max ~500 lines each (SKILL.md files only; references/ excluded)
#   commands/  — max ~200 lines each (shipped verbatim into user projects)
#
# Exits 0 if all pass (or if --warn-only is set).
# Exits 1 on violations in strict mode (default).
#
# Flags:
#   --warn-only  print violations but exit 0 (for gradual CI rollout)
#   --quiet      suppress success output when clean

set -euo pipefail

WARN_ONLY=false
QUIET=false
for arg in "$@"; do
  case "$arg" in
    --warn-only) WARN_ONLY=true ;;
    --quiet)     QUIET=true ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/agents"
SKILLS_DIR="$REPO_ROOT/skills"
COMMANDS_DIR="$REPO_ROOT/commands"

# 200 lines of agent CONTENT, plus 11 lines of fixed-size model-identity
# boilerplate every agent carries: the `model:`/`effort:` frontmatter keys, the
# `<!-- run-banner -->` table, and the `## Before You Finish` closing section
# (see skills/shared/model-identity/SKILL.md). None of it is authored content —
# it is identical in shape across all 17 agents and the renderer rewrites parts
# of it per provider — so it is excluded from the budget by raising the ceiling
# rather than by charging the longest agents for it.
#
# The content budget is still 200. Raise this ONLY when a new mandatory block
# is added to every agent, and then by exactly that block's size. Never raise
# it to make one long agent fit — move that agent's reference material into a
# skill instead.
AGENT_LIMIT=211
SKILL_LIMIT=500
# Commands are thin orchestration wrappers that spawn agents — they should never
# be longer than the richest content type in the repo. 200 is the ceiling already
# established for agents, ~4x the current command median (~50 lines), and above
# all but one shipped command today.
COMMAND_LIMIT=200

VIOLATIONS=()

# ── Check agents ──────────────────────────────────────────────────────────────
while IFS= read -r f; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt "$AGENT_LIMIT" ]; then
    rel="${f#"$REPO_ROOT"/}"
    VIOLATIONS+=("  · $rel: $lines lines (limit: $AGENT_LIMIT)")
  fi
done < <(find "$AGENTS_DIR" -name "*.md" | sort)

# ── Check skills (SKILL.md only; skip references/ subdirs) ───────────────────
while IFS= read -r f; do
  rel="${f#"$REPO_ROOT"/}"
  [[ "$rel" == *"/references/"* ]] && continue
  lines=$(wc -l < "$f")
  if [ "$lines" -gt "$SKILL_LIMIT" ]; then
    VIOLATIONS+=("  · $rel: $lines lines (limit: $SKILL_LIMIT)")
  fi
done < <(find "$SKILLS_DIR" -name "SKILL.md" | sort)

# ── Check commands (shipped verbatim to .claude/commands/devteam/) ───────────
if [ -d "$COMMANDS_DIR" ]; then
  while IFS= read -r f; do
    lines=$(wc -l < "$f")
    if [ "$lines" -gt "$COMMAND_LIMIT" ]; then
      rel="${f#"$REPO_ROOT"/}"
      VIOLATIONS+=("  · $rel: $lines lines (limit: $COMMAND_LIMIT)")
    fi
  done < <(find "$COMMANDS_DIR" -name "*.md" | sort)
fi

# ── CLAUDE.md size check ──────────────────────────────────────────────────────
CLAUDE_MD_LINES=$(wc -l < "$REPO_ROOT/CLAUDE.md" 2>/dev/null || echo 0)
CLAUDE_MD_WARN=600
CLAUDE_MD_FAIL=700

if [ "$CLAUDE_MD_LINES" -ge "$CLAUDE_MD_FAIL" ]; then
    VIOLATIONS+=("  · CLAUDE.md: $CLAUDE_MD_LINES lines (limit: $CLAUDE_MD_FAIL)")
elif [ "$CLAUDE_MD_LINES" -ge "$CLAUDE_MD_WARN" ]; then
    VIOLATIONS+=("  ⚠ CLAUDE.md: $CLAUDE_MD_LINES lines (warning threshold: $CLAUDE_MD_WARN)")
fi

# ── Output ────────────────────────────────────────────────────────────────────
SEPARATOR="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#VIOLATIONS[@]} -eq 0 ]; then
  [ "$QUIET" = false ] && echo "size-limits: clean ✓"
  exit 0
fi

echo ""
echo "$SEPARATOR"
echo " SIZE LIMITS"
echo "$SEPARATOR"
echo ""
if [ "$WARN_ONLY" = true ]; then
  echo " WARN — Files exceeding declared limits (non-blocking):"
else
  echo " ERRORS — Files exceeding declared limits:"
fi
for v in "${VIOLATIONS[@]}"; do
  echo "$v"
done
echo ""
echo " Agents: max $AGENT_LIMIT lines | Skills: max $SKILL_LIMIT lines | Commands: max $COMMAND_LIMIT lines"
echo " Move long reference material to a references/ subdirectory."
echo "$SEPARATOR"

[ "$WARN_ONLY" = true ] && exit 0
exit 1
