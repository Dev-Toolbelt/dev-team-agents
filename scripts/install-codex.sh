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
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --user-prompts
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --source /abs/path
#   bash <path-to-dev-team-agents>/scripts/install-codex.sh --dry-run
#
# What it does:
#   1. Resolves source (same logic as install-opencode.sh).
#   2. Calls scripts/render-provider.sh --provider codex into a staging dir.
#   3. Copies staged .codex/agents/*.toml into <project>/.codex/agents/.
#   4. Copies staged .codex/skills/devteam-*/SKILL.md into <project>/.codex/skills/
#      so the workflows are available as explicit Codex skills (`$devteam-*`).
#   5. Optionally copies staged .codex/prompts/devteam-*.md into ~/.codex/prompts/
#      when `--user-prompts` is passed, for slash-command autocomplete as
#      `/prompts:devteam-<name>`.
#   6. Removes legacy project-local prompt aliases from <project>/.codex/prompts/
#      so older installs converge to the skills-first layout.
#   7. Symlinks skills/ → <project>/.codex/skills/dev-team-agents/.
#   8. Writes a hooks.json file at <project>/.codex/hooks.json that wires
#      scripts/hooks/{pre-tool-use,session-start,pre-compact,stop}.sh to the
#      Codex PreToolUse/SessionStart/PreCompact/Stop events. Idempotent: only
#      dev-team-managed hook entries are touched.
#   9. Records the installed version.

set -euo pipefail

PROJECT_ROOT="$(pwd)"
DRY_RUN=0
SOURCE_ARG=""
USER_PROMPTS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_ARG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --user-prompts) USER_PROMPTS=1; shift ;;
    *) echo "install-codex: unknown arg: $1" >&2; exit 2 ;;
  esac
done

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
if [[ $USER_PROMPTS -eq 1 ]]; then echo "User prompts:  ENABLED (~/.codex/prompts)"; fi
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

  LEGACY_PROMPTS_DIR="$CODEX_DIR/prompts"
  if [[ -d "$LEGACY_PROMPTS_DIR" ]]; then
    find "$LEGACY_PROMPTS_DIR" -maxdepth 1 -type f -name 'devteam-*.md' -delete
    if [[ -z "$(find "$LEGACY_PROMPTS_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
      rmdir "$LEGACY_PROMPTS_DIR" 2>/dev/null || true
    fi
    echo "  + removed legacy project-local prompt aliases from .codex/prompts/"
  fi

  # skills symlink
  SKILLS_LINK="$CODEX_DIR/skills/dev-team-agents"
  if [[ -L "$SKILLS_LINK" || -e "$SKILLS_LINK" ]]; then rm -rf "$SKILLS_LINK"; fi
  ln -s "$SOURCE_DIR/skills" "$SKILLS_LINK"
  echo "  + symlinked skills/ -> $SKILLS_LINK"
fi

# ── optional user-level prompt aliases for slash-command autocomplete ─────────
if [[ $USER_PROMPTS -eq 1 ]]; then
  USER_PROMPTS_DIR="${HOME}/.codex/prompts"
  mkdir -p "$USER_PROMPTS_DIR"
  if [[ $DRY_RUN -eq 0 ]]; then
    cp -f "$STAGING/.codex/prompts/"devteam-*.md "$USER_PROMPTS_DIR/"
    PROMPT_COUNT=$(find "$USER_PROMPTS_DIR" -maxdepth 1 -name 'devteam-*.md' | wc -l | tr -d ' ')
    echo "  + copied $PROMPT_COUNT prompt files to $USER_PROMPTS_DIR/ (as /prompts:devteam-<name>)"
  fi
fi

# ── hooks.json for Codex (idempotent merge of dev-team-agents-managed entries)
if [[ $DRY_RUN -eq 0 ]]; then
  HOOKS_FILE="$CODEX_DIR/hooks.json"
  # Codex runs hook commands from the session cwd (the project root), so
  # project-relative paths are stable across machines (no baked-in user paths).
  HOOKS_DIR_REL=".dev-team-agents/scripts/hooks"

  python3 - "$HOOKS_FILE" "$HOOKS_DIR_REL" <<'PY'
import json, os, sys
hooks_file, hooks_dir = sys.argv[1], sys.argv[2]

# Per Codex spec (developers.openai.com/codex/hooks), the shape is:
#   { "hooks": { "<Event>": [ { "matcher": "...", "hooks": [ { type, command, ... } ] } ] } }
# — an OBJECT keyed by event name, each value an array of matcher groups.
# Each hook `command` is a STRING, not an array.
MANAGED_EVENTS = ("SessionStart", "PreToolUse", "PreCompact", "Stop")
MANAGED_MARKER  = "_dev_team_agents_managed"

def cmd(script):
    return f"bash {hooks_dir}/{script}"

# Each managed hook carries a statusMessage with the MANAGED_MARKER so we can
# idempotently strip our own entries on re-install without touching user hooks.
# (Codex spec does NOT define a per-hook id field — statusMessage is the
# documented human-readable surface; we encode our marker there.)
managed_groups = {
    event: [
        {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": cmd({
                        "SessionStart": "session-start.sh",
                        "PreToolUse":   "pre-tool-use.sh",
                        "PreCompact":   "pre-compact.sh",
                        "Stop":         "stop.sh",
                    }[event]),
                    "statusMessage": f"dev-team-agents {event.lower()} hook {MANAGED_MARKER}",
                }
            ],
        }
    ]
    for event in MANAGED_EVENTS
}

existing = {"hooks": {}}
if os.path.exists(hooks_file):
    try:
        existing = json.load(open(hooks_file))
        if not isinstance(existing.get("hooks"), dict):
            existing = {"hooks": {}}
    except Exception:
        existing = {"hooks": {}}

# Strip any previously-managed entries (idempotent refresh) — detect ours by
# the encoded marker in statusMessage.
hooks_obj = existing["hooks"]
for event in list(hooks_obj.keys()):
    groups = hooks_obj[event]
    if not isinstance(groups, list):
        continue
    kept = []
    for grp in groups:
        hook_list = grp.get("hooks", []) if isinstance(grp, dict) else []
        is_managed = any(
            isinstance(h, dict) and MANAGED_MARKER in (h.get("statusMessage", "") or "")
            for h in hook_list
        )
        if not is_managed:
            kept.append(grp)
    if kept:
        hooks_obj[event] = kept
    else:
        hooks_obj.pop(event, None)

# Merge managed groups into existing (append into each event's array).
for event, groups in managed_groups.items():
    hooks_obj.setdefault(event, []).extend(groups)

with open(hooks_file, "w") as f:
    json.dump(existing, f, indent=2)
print(f"  + wrote {len(MANAGED_EVENTS)} managed hook events to {os.path.relpath(hooks_file)}")
PY
fi

echo ""
echo "install-codex: done."
echo "  Next: restart Codex CLI."
echo "  Agents available as subagents via spawn_agent. Command skills are exposed as \$devteam-<name>."
if [[ $USER_PROMPTS -eq 1 ]]; then
  echo "  User-local prompt aliases were installed at ~/.codex/prompts as /prompts:devteam-<name>."
else
  echo "  Optional: re-run with --user-prompts to install /prompts:devteam-<name> aliases in ~/.codex/prompts."
fi
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  (dry-run — no files written)"
fi
