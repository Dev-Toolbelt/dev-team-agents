#!/usr/bin/env bash
# Graphify plugin: (re)build graphify-out/ from the configured source paths.
#
#   refresh.sh                 rebuild unconditionally (the "Rebuild graph" action)
#   refresh.sh --force         same, explicit
#   refresh.sh --if-changed    rebuild only when a source path changed structurally
#                              (added/deleted/renamed files) since the last build
#   --quiet                    suppress progress output (errors are always printed)
#
# Config: see lib/config.sh. State: graphify_last_run / graphify_last_run_at in the
# machine-local state.json (DEVTEAM_STATE_DIR, else resolved like the hooks do).
set -euo pipefail

FORCE=1
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --if-changed) FORCE=0 ;;
    --force) FORCE=1 ;;
    --quiet|-q) QUIET=1 ;;
    *) echo "refresh.sh: unknown argument '$arg'" >&2; exit 2 ;;
  esac
done

log() { [ "$QUIET" -eq 1 ] || echo "$@" >&2; }

# Physical path: in a bound project .dev-team-agents/plugins is a symlink to the core.
SELF_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SELF_DIR")"
CORE_DIR="$(cd -P "$PLUGIN_DIR/../.." && pwd)"

# shellcheck source=plugins/graphify/lib/config.sh
. "$PLUGIN_DIR/lib/config.sh"
# shellcheck source=scripts/lib/state.sh
. "$CORE_DIR/scripts/lib/state.sh"
# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "$CORE_DIR/scripts/hooks/lib/data-dirs.sh"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository." >&2
  exit 1
fi

PROJECT_ROOT="${DEVTEAM_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_ROOT"

# ── Dependency checks ─────────────────────────────────────────────────────────
if ! command -v graphify >/dev/null 2>&1; then
  log "graphify is not installed - nothing to do."
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "'jq' not found." >&2
  echo "   macOS: brew install jq   ·   Linux: apt-get install jq" >&2
  exit 1
fi

# ── Load config ───────────────────────────────────────────────────────────────
if ! CONFIG_JSON="$(graphify_config_json "$PROJECT_ROOT")"; then
  log "graphify is not configured for this project - nothing to do."
  exit 0
fi

OUTPUT_PATH="graphify-out"

# state.json is machine-local. The state-dir pointer lives in the main checkout,
# so resolve from there, not --show-toplevel.
if [ -n "${DEVTEAM_STATE_DIR:-}" ]; then
  STATE_DIR="$DEVTEAM_STATE_DIR"
else
  MAIN_ROOT="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"
  unset STATE_FILE USER_DATA_DIR
  STATE_DIR="$(devteam_state_dir "$MAIN_ROOT")"
fi

SOURCES=()
while IFS= read -r line; do
  [ -n "$line" ] && SOURCES+=("$line")
done < <(graphify_cfg_list "$CONFIG_JSON" targetPaths)
if [ ${#SOURCES[@]} -eq 0 ]; then
  echo "'targetPaths' is missing or empty in the graphify config - set the source paths first." >&2
  exit 1
fi

MANIFESTS=()
while IFS= read -r line; do
  [ -n "$line" ] && MANIFESTS+=("$line")
done < <(graphify_cfg_list "$CONFIG_JSON" manifestPaths)

# ── Change detection ──────────────────────────────────────────────────────────
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
STATE_FILE="$STATE_DIR/state.json"
LAST_BUILD_COMMIT="$(state_get graphify_last_run "$STATE_FILE")"

# Returns 0 if the given filepath falls under any targetPath
in_target_paths() {
  local fp="$1"
  for src in "${SOURCES[@]}"; do
    [[ "$fp" == "$src" || "$fp" == "$src/"* ]] && return 0
  done
  return 1
}

# Returns 0 if git status shows structural changes (A/D/R/??) inside targetPaths
has_uncommitted_structural_changes() {
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    local xy="${line:0:2}"
    local fp="${line:3}"
    fp="${fp## }"
    # Renames: "R  old -> new" - take new path
    [[ "$xy" == R* || "$xy" == *R ]] && fp="${fp##* -> }"
    case "$xy" in
      "??"|A*|*A|D*|*D|R*|*R) in_target_paths "$fp" && return 0 ;;
    esac
  done < <(git status --porcelain 2>/dev/null)
  return 1
}

HAS_STRUCTURAL="$FORCE"

if [ "$FORCE" -eq 0 ]; then
  if [ ! -d "$OUTPUT_PATH" ]; then
    log "$OUTPUT_PATH not found - first-time build."
    HAS_STRUCTURAL=1
  fi

  if [ "$HAS_STRUCTURAL" -eq 0 ] && has_uncommitted_structural_changes; then
    HAS_STRUCTURAL=1
  fi

  if [ "$HAS_STRUCTURAL" -eq 0 ] && [ -n "$CURRENT_COMMIT" ]; then
    if [ -z "$LAST_BUILD_COMMIT" ]; then
      for src_dir in "${SOURCES[@]}"; do
        if [ -n "$(git log --diff-filter=ADR --name-only --format="" -- "$src_dir" 2>/dev/null | head -n1)" ]; then
          HAS_STRUCTURAL=1
          break
        fi
      done
    elif [ "$CURRENT_COMMIT" != "$LAST_BUILD_COMMIT" ]; then
      for src_dir in "${SOURCES[@]}"; do
        if [ -n "$(git diff --diff-filter=ADR --name-only "$LAST_BUILD_COMMIT"..HEAD -- "$src_dir" 2>/dev/null | head -n1)" ]; then
          HAS_STRUCTURAL=1
          break
        fi
      done
    fi
  fi

  if [ "$HAS_STRUCTURAL" -eq 0 ]; then
    log "Graph is up to date - no structural change in the source paths."
    exit 0
  fi
fi

mkdir -p "$STATE_DIR"

# ── Build ─────────────────────────────────────────────────────────────────────
# shellcheck disable=SC2317,SC2329  # invoked indirectly via trap
cleanup() { rm -rf "$PROJECT_ROOT/graphify-src"; }
trap cleanup EXIT

log "Building graphify-src..."
rm -rf graphify-src
mkdir -p graphify-src

for src in "${SOURCES[@]}"; do
  if [ ! -e "$src" ]; then
    echo "Required source '$src' not found in $PROJECT_ROOT." >&2
    exit 1
  fi
  mkdir -p "graphify-src/$(dirname "$src")"
  rsync -a "$src/" "graphify-src/$src/"
done

for manifest in ${MANIFESTS[@]+"${MANIFESTS[@]}"}; do
  [ -z "$manifest" ] && continue
  if [ ! -f "$manifest" ]; then
    echo "Manifest '$manifest' not found - skipping." >&2
    continue
  fi
  cp "$manifest" "graphify-src/$manifest"
done

log "Running Graphify..."
graphify update graphify-src

if [ ! -d "graphify-src/$OUTPUT_PATH" ]; then
  echo "Graphify did not produce output at 'graphify-src/$OUTPUT_PATH'." >&2
  exit 1
fi

log "Moving $OUTPUT_PATH to project root..."
# graphify protects the cache dir with a macOS `deny delete` ACL, which makes `rm -rf` fail with EACCES.
# Strip ACLs first (no-op on Linux).
if [ -e "$OUTPUT_PATH" ]; then
  chmod -R -N "$OUTPUT_PATH" 2>/dev/null || true
fi
rm -rf "$OUTPUT_PATH"
mv "graphify-src/$OUTPUT_PATH" "./$OUTPUT_PATH"

# Record the commit and time of this build (used to skip redundant rebuilds and by status.sh)
state_set graphify_last_run "$CURRENT_COMMIT" "$STATE_FILE"
state_set graphify_last_run_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$STATE_FILE"

log "Done."
exit 0
