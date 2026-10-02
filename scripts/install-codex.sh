#!/bin/bash
# install-codex.sh — Installs dev-team-agents support into a project for
# use with the OpenAI Codex CLI.
#
# Idempotent. Safe to re-run. Preserves any pre-existing .codex/config.toml
# and hooks.json; only merges the `[[agents]]` and hook entries declared by
# dev-team-agents.
#
# Prereqs:
#   · bash, python3
#   · either a local clone of dev-team-agents OR a prior install.sh run that
#     places the framework at <project>/.dev-team-agents/
#
# Usage (from project root):
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --source /abs/path
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --dry-run
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --list-targets
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --adopt
#
# Ownership (scripts/lib/provider-ownership.sh): an existing target path that
# dev-team-agents did not create is never overwritten or deleted. The installer
# exits 4 naming it, unless --adopt moves it to .dev-team-agents/quarantine/
# first. --owned <file> lists paths a caller (`devteam bind`) vouches for;
# --list-targets prints the project-relative paths an install would write.
#
# What it does:
#   1. Resolves source (same logic as install-opencode.sh).
#   2. Calls scripts/render-provider.sh --provider codex into a staging dir.
#   3. Copies staged .codex/agents/*.toml into <project>/.codex/agents/.
#   4. Copies staged .codex/skills/devteam-*/SKILL.md into <project>/.codex/skills/
#      so the workflows are available as explicit Codex skills (`$devteam-*`).
#   5. Reports legacy prompt aliases in <project>/.codex/prompts/ and
#      ~/.codex/prompts/ so older installs can converge to the skills-first
#      layout. It never deletes them.
#   6. Symlinks skills/ → <project>/.codex/skills/dev-team-agents/.
#   7. Writes a hooks.json file at <project>/.codex/hooks.json that wires
#      scripts/hooks/{pre-tool-use,post-tool-use,user-prompt-submit,session-start,
#      pre-compact,stop,session-end}.sh to the Codex PreToolUse/PostToolUse/
#      UserPromptSubmit/SessionStart/PreCompact/Stop/SessionEnd events. Idempotent: only
#      dev-team-managed hook entries are touched.
#   8. Records the installed version.

set -euo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/lib/python.sh"
# shellcheck source=lib/python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

PROJECT_ROOT="$(pwd)"
DRY_RUN=0
SOURCE_ARG=""
LIST_TARGETS=0
ADOPT=0
OWNED_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_ARG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --list-targets) LIST_TARGETS=1; DRY_RUN=1; shift ;;
    --adopt) ADOPT=1; shift ;;
    --owned) OWNED_FILE="$2"; shift 2 ;;
    *) echo "install-codex: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# --list-targets owns stdout: everything else goes to stderr.
if [[ $LIST_TARGETS -eq 1 ]]; then exec 3>&1 1>&2; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
candidate_sources=()
if [[ -n "$SOURCE_ARG" ]]; then candidate_sources+=("$SOURCE_ARG"); fi
candidate_sources+=("${DEV_TEAM_AGENTS_SOURCE:-}")
candidate_sources+=("$PROJECT_ROOT/.dev-team-agents")
candidate_sources+=("$SCRIPT_DIR/..")

SOURCE_DIR=""
for c in "${candidate_sources[@]}"; do
  [[ -z "$c" ]] && continue
  if [[ -f "$c/scripts/render-provider.sh" ]] && [[ -f "$c/agents/product-analyst.md" ]]; then
    SOURCE_DIR="$(cd "$c" && pwd)"
    break
  fi
done
if [[ -z "$SOURCE_DIR" ]]; then
  echo "install-codex: ERROR: could not locate dev-team-agents source." >&2
  echo "  Looked in: ${candidate_sources[*]}" >&2
  exit 1
fi

echo "dev-team-agents — Codex CLI installer"
echo "====================================="
echo "Project root:  $PROJECT_ROOT"
echo "Source dir:    $SOURCE_DIR"
if [[ $DRY_RUN -eq 1 ]]; then echo "Mode:          DRY-RUN (no writes)"; fi
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "install-codex: ERROR: python3 is required." >&2; exit 1
fi

# Cross-CLI plumbing (render-provider.sh + lib/*) is NOT bundled in slim Claude
# installs. Detect that and guide the user to the curl-pipe bootstrap.
RENDER_SCRIPT="$SOURCE_DIR/scripts/render-provider.sh"
if [[ ! -f "$RENDER_SCRIPT" ]]; then
  echo "install-codex: ERROR: source '$SOURCE_DIR' is missing cross-CLI plumbing." >&2
  echo "  This usually means the framework was installed via Claude's slim install.sh" >&2
  echo "  and the codex-specific files were intentionally not bundled." >&2
  echo "" >&2
  echo "  To bootstrap Codex CLI support into this project, run from its root:" >&2
  echo "    bash <(curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-provider.sh) codex" >&2
  echo "" >&2
  echo "  Or pass --source <path-to-dev-team-agents-clone> if you have a local clone." >&2
  exit 3
fi

# ── render ────────────────────────────────────────────────────────────
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

bash "$SOURCE_DIR/scripts/render-provider.sh" \
  --provider codex --source-dir "$SOURCE_DIR" --target-dir "$STAGING"

# ── ownership guard — before the first write ──────────────────────────
# shellcheck source=scripts/lib/provider-ownership.sh
source "$SCRIPT_DIR/lib/provider-ownership.sh"
TARGETS="$STAGING/.targets"
{
  for f in "$STAGING/.codex/agents/"*.toml; do
    [[ -e "$f" ]] && echo ".codex/agents/$(basename "$f")"
  done
  if [[ -d "$STAGING/.codex/skills" ]]; then
    find "$STAGING/.codex/skills" -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' \
      -exec basename {} \; | sort | sed 's|^|.codex/skills/|'
  fi
  echo ".codex/skills/dev-team-agents"
} > "$TARGETS"

if [[ $LIST_TARGETS -eq 1 ]]; then
  cat "$TARGETS" >&3
  exit 0
fi
po_require_inside codex "$PROJECT_ROOT" .codex .codex/agents .codex/skills .codex/hooks.json
po_guard "$PROJECT_ROOT" "$SOURCE_DIR" codex "$OWNED_FILE" "$TARGETS" "$ADOPT" "$DRY_RUN"
# A hooks.json this installer cannot merge into is refused before anything is written.
python3 "$(po_native_path "$SCRIPT_DIR/lib/codex_hooks_merge.py")" "$(po_native_path "$PROJECT_ROOT/.codex/hooks.json")" "" --check

# Ensure project has a stable path to the framework's scripts/hooks/ (the
# Claude installer normally creates this; we materialize it for codex-only
# installs). Sourced helper copies the slim Claude runtime subset into
# <project>/.dev-team-agents/ so Codex hooks.json paths resolve.
SCRIPT_DIR_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/lib" && pwd)"
# shellcheck source=scripts/lib/ensure-claude-framework.sh
source "$SCRIPT_DIR_LIB/ensure-claude-framework.sh"

if [[ $DRY_RUN -eq 0 ]]; then
  ensure_claude_framework "$PROJECT_ROOT" "$SOURCE_DIR"
  echo "  + materialized .dev-team-agents/ runtime subset (hooks/scripts/skills)"
fi


# ── write into project .codex/ ────────────────────────────────────────
CODEX_DIR="$PROJECT_ROOT/.codex"
mkdir -p "$CODEX_DIR/agents" "$CODEX_DIR/skills"

if [[ $DRY_RUN -eq 0 ]]; then
  cp -f "$STAGING/.codex/agents/"*.toml "$CODEX_DIR/agents/"
  AGENT_COUNT=$(find "$CODEX_DIR/agents/" -maxdepth 1 -name '*.toml' | wc -l | tr -d ' ')
  echo "  + copied $AGENT_COUNT agent TOML files to .codex/agents/"

  if [[ -d "$STAGING/.codex/skills" ]]; then
    find "$STAGING/.codex/skills" -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' | while read -r skill_dir; do
      skill_name="$(basename "$skill_dir")"
      rm -rf "$CODEX_DIR/skills/$skill_name"
      mkdir -p "$CODEX_DIR/skills/$skill_name"
      cp -f "$skill_dir/SKILL.md" "$CODEX_DIR/skills/$skill_name/SKILL.md"
    done
    SKILL_COUNT=$(find "$CODEX_DIR/skills" -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' | wc -l | tr -d ' ')
    echo "  + copied $SKILL_COUNT generated command skills to .codex/skills/ (as \$devteam-<name>)"
  fi

  # skills symlink
  SKILLS_LINK="$CODEX_DIR/skills/dev-team-agents"
  po_link_skills "$PROJECT_ROOT" "$SOURCE_DIR" "$SKILLS_LINK"
fi

# ── report legacy prompt aliases from old Codex layouts ──────────────────────
# Reported, never deleted: a file matching the old naming is indistinguishable
# from one the user wrote, and ~/.codex/prompts is outside the project entirely.
for LEGACY_PROMPTS_DIR in "$CODEX_DIR/prompts" "${HOME}/.codex/prompts"; do
  [[ -d "$LEGACY_PROMPTS_DIR" ]] || continue
  LEGACY_PROMPTS="$(find "$LEGACY_PROMPTS_DIR" -maxdepth 1 -type f -name 'devteam-*.md' 2>/dev/null | sort)"
  if [[ -n "$LEGACY_PROMPTS" ]]; then
    echo "  ! legacy prompt aliases found in $LEGACY_PROMPTS_DIR (superseded by \$devteam-* skills):" >&2
    while IFS= read -r legacy; do printf '      %s\n' "$legacy"; done <<< "$LEGACY_PROMPTS" >&2
    echo "    Remove them yourself if they came from an older dev-team-agents install." >&2
  fi
done

# ── hooks.json for Codex (idempotent merge of dev-team-agents-managed entries)
if [[ $DRY_RUN -eq 0 ]]; then
  HOOKS_FILE="$CODEX_DIR/hooks.json"
  # Hook commands stay project-relative (no baked-in user paths); `cmd()` below finds the
  # project root from wherever the session is.
  # One path for both layouts: a v2 install vendors `scripts/` here and a v3 bind
  # links it here. It used to prefer a v3 `core/` pointer when present — and a sync
  # that ran this installer before pruning that pointer wrote a path the same sync
  # then removed.
  HOOKS_DIR_REL=".dev-team-agents/scripts/hooks"

  python3 "$(po_native_path "$SCRIPT_DIR/lib/codex_hooks_merge.py")" "$(po_native_path "$HOOKS_FILE")" "$HOOKS_DIR_REL"
fi

# ── project AGENTS.md rule for visible SessionStart banner in Codex ─────────
if [[ $DRY_RUN -eq 0 ]]; then
  TARGET_AGENTS_MD="$PROJECT_ROOT/AGENTS.md"
  DTA_CODEX_BANNER_MARKER="<!-- dev-team-agents: codex-session-banner -->"

  if ! grep -qF "$DTA_CODEX_BANNER_MARKER" "$TARGET_AGENTS_MD" 2>/dev/null; then
    cat >> "$TARGET_AGENTS_MD" <<'AGENTSEOF'

<!-- dev-team-agents: codex-session-banner -->
## Codex Session Banner

When the `SessionStart` hook context contains a line exactly equal to `[DEVTEAM:SESSION_BANNER]`, reproduce the next three lines **verbatim, unmodified**, as the first thing in your **first reply of the session**.

Rules:
- Do not add any text before the banner.
- Do not translate, summarize, or reformat it.
- Do not fabricate the banner when the marker is absent.
- This rule applies to normal conversation too, not only `$devteam-*` skills.
AGENTSEOF
    echo "  + injected Codex session-banner echo rule into AGENTS.md"
  else
    echo "  + Codex session-banner echo rule already present in AGENTS.md"
  fi
fi

if [[ $DRY_RUN -eq 0 && -z "$OWNED_FILE" ]]; then
  po_record_ledger "$PROJECT_ROOT" codex "$TARGETS"
fi

echo ""
echo "install-codex: done."
echo "  Next: restart Codex CLI."
echo "  Agents available as subagents via spawn_agent. Command skills are exposed as \$devteam-<name>."
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  (dry-run — no files written)"
fi
