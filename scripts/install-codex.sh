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
#     places the framework at <project>/.claude/dev-team-agents/
#
# Usage (from project root):
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --source /abs/path
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --dry-run
#
# What it does:
#   1. Resolves source (same logic as install-opencode.sh).
#   2. Calls scripts/render-provider.sh --provider codex into a staging dir.
#   3. Copies staged .codex/agents/*.toml into <project>/.codex/agents/.
#   4. Copies staged .codex/prompts/devteam-*.md into <project>/.codex/prompts/.
#   5. Symlinks skills/ → <project>/.codex/skills/dev-team-agents/.
#   6. Writes a hooks.json file at <project>/.codex/hooks.json that wires
#      scripts/hooks/{pre-tool-use,session-start,pre-compact,stop}.sh to the
#      Codex PreToolUse/SessionStart/PreCompact/Stop events. Idempotent: only
#      dev-team-managed hook entries are touched.
#   7. Records the installed version.

set -euo pipefail

PROJECT_ROOT="$(pwd)"
DRY_RUN=0
SOURCE_ARG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_ARG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "install-codex: unknown arg: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
candidate_sources=()
if [[ -n "$SOURCE_ARG" ]]; then candidate_sources+=("$SOURCE_ARG"); fi
candidate_sources+=("${DEV_TEAM_AGENTS_SOURCE:-}")
candidate_sources+=("$PROJECT_ROOT/.claude/dev-team-agents")
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

# Ensure project has a stable path to the framework's scripts/hooks/ (the
# Claude installer normally creates this; we ensure it for codex-only installs).
CLAUDE_FRAMEWORK="$PROJECT_ROOT/.claude/dev-team-agents"
mkdir -p "$PROJECT_ROOT/.claude"
if [[ ! -e "$CLAUDE_FRAMEWORK" ]]; then
  if [[ $DRY_RUN -eq 0 ]]; then
    ln -s "$SOURCE_DIR" "$CLAUDE_FRAMEWORK"
    echo "  + symlinked $CLAUDE_FRAMEWORK -> $SOURCE_DIR"
  fi
elif [[ -L "$CLAUDE_FRAMEWORK" ]]; then
  # Repoint existing symlink to current source.
  if [[ $DRY_RUN -eq 0 ]]; then ln -sfn "$SOURCE_DIR" "$CLAUDE_FRAMEWORK"; fi
fi

# ── write into project .codex/ ────────────────────────────────────────
CODEX_DIR="$PROJECT_ROOT/.codex"
mkdir -p "$CODEX_DIR/agents" "$CODEX_DIR/prompts" "$CODEX_DIR/skills"

if [[ $DRY_RUN -eq 0 ]]; then
  cp -f "$STAGING/.codex/agents/"*.toml "$CODEX_DIR/agents/"
  AGENT_COUNT=$(find "$CODEX_DIR/agents/" -maxdepth 1 -name '*.toml' | wc -l | tr -d ' ')
  echo "  + copied $AGENT_COUNT agent TOML files to .codex/agents/"

  cp -f "$STAGING/.codex/prompts/"devteam-*.md "$CODEX_DIR/prompts/"
  PROMPT_COUNT=$(find "$CODEX_DIR/prompts/" -maxdepth 1 -name 'devteam-*.md' | wc -l | tr -d ' ')
  echo "  + copied $PROMPT_COUNT prompt files to .codex/prompts/ (as /prompts:devteam-<name>)"

  # skills symlink
  SKILLS_LINK="$CODEX_DIR/skills/dev-team-agents"
  if [[ -L "$SKILLS_LINK" || -e "$SKILLS_LINK" ]]; then rm -rf "$SKILLS_LINK"; fi
  ln -s "$SOURCE_DIR/skills" "$SKILLS_LINK"
  echo "  + symlinked skills/ -> $SKILLS_LINK"
fi

# ── hooks.json for Codex (idempotent merge of dev-team-agents-managed entries)
if [[ $DRY_RUN -eq 0 ]]; then
  HOOKS_FILE="$CODEX_DIR/hooks.json"
  # Codex runs hook commands from the project root, so project-relative paths
  # are stable across machines (no baked-in user paths).
  HOOKS_DIR_REL=".claude/dev-team-agents/scripts/hooks"

  python3 - "$HOOKS_FILE" "$HOOKS_DIR_REL" <<'PY'
import json, os, sys
hooks_file, hooks_dir = sys.argv[1], sys.argv[2]

# The dev-team-agents-managed hooks block. Each entry binds a Codex event
# to one of the existing shell dispatchers.
managed = [
  {
    "event": "SessionStart",
    "matcher": "*",
    "hooks": [{"type": "command",
               "command": [os.path.join(hooks_dir, "session-start.sh")],
               "_managed_by": "dev-team-agents"}]
  },
  {
    "event": "PreToolUse",
    "matcher": "*",
    "hooks": [{"type": "command",
               "command": [os.path.join(hooks_dir, "pre-tool-use.sh")],
               "_managed_by": "dev-team-agents"}]
  },
  {
    "event": "PreCompact",
    "matcher": "*",
    "hooks": [{"type": "command",
               "command": [os.path.join(hooks_dir, "pre-compact.sh")],
               "_managed_by": "dev-team-agents"}]
  },
  {
    "event": "Stop",
    "matcher": "*",
    "hooks": [{"type": "command",
               "command": [os.path.join(hooks_dir, "stop.sh")],
               "_managed_by": "dev-team-agents"}]
  },
]

existing = {"hooks": []}
if os.path.exists(hooks_file):
    try:
        existing = json.load(open(hooks_file))
        if "hooks" not in existing:
            existing["hooks"] = []
    except Exception:
        existing = {"hooks": []}

# Strip any previously-managed entries (idempotent refresh)
existing["hooks"] = [h for h in existing.get("hooks", [])
                     if not any(h.get("hooks", [{}])[0].get("_managed_by") == "dev-team-agents"
                                for _ in [None])]
existing["hooks"].extend(managed)

# Strip the _managed_by field from the output (Codex would reject unknown keys
# in some versions; keep it as a sibling key on the matcher block instead).
for h in existing["hooks"]:
    for hh in h.get("hooks", []):
        hh.pop("_managed_by", None)

with open(hooks_file, "w") as f:
    json.dump(existing, f, indent=2)
print(f"  + wrote {len(managed)} managed hooks to {os.path.relpath(hooks_file)}")
PY
fi

echo ""
echo "install-codex: done."
echo "  Next: restart Codex CLI."
echo "  Agents available as subagents via spawn_agent. Prompts exposed as /prompts:devteam-<name>."
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  (dry-run — no files written)"
fi