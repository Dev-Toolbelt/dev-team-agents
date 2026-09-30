#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

cd "$PROJECT_ROOT"

# shellcheck source=scripts/lib/state.sh
. "$SCRIPT_DIR/lib/state.sh"
# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "$SCRIPT_DIR/hooks/lib/data-dirs.sh"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ Not inside a git repository." >&2
  exit 1
fi

# ── Dependency checks ─────────────────────────────────────────────────────────
if ! command -v graphify >/dev/null 2>&1; then
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "❌ 'jq' not found." >&2
  echo "   macOS: brew install jq   ·   Linux: apt-get install jq" >&2
  exit 1
fi

# ── Load config ───────────────────────────────────────────────────────────────
CONFIG_FILE="$PROJECT_ROOT/.dev-team-agents/user-data/graphify.json"
if [ ! -f "$CONFIG_FILE" ]; then
  exit 0
fi

OUTPUT_PATH="graphify-out"
# The commit a build reflects is recorded next to the graph it describes, so it is
# per checkout: every linked worktree has its own graphify-out/, and a marker shared
# through the main checkout's state.json would let one worktree's build stand in for
# another's. It is versioned with the graph, which is what it describes.
BUILD_MARKER="$OUTPUT_PATH/.build-commit"

SOURCES=()
while IFS= read -r line; do
  [ -n "$line" ] && SOURCES+=("$line")
done < <(jq -r '.targetPaths[]? // empty' "$CONFIG_FILE")
if [ ${#SOURCES[@]} -eq 0 ]; then
  echo "❌ 'targetPaths' missing or empty in $CONFIG_FILE." >&2
  exit 1
fi

MANIFESTS=()
while IFS= read -r line; do
  [ -n "$line" ] && MANIFESTS+=("$line")
done < <(jq -r '.manifestPaths[]? // empty' "$CONFIG_FILE")

# ── Change detection ──────────────────────────────────────────────────────────
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
LAST_BUILD_COMMIT="$(tr -d '[:space:]' 2>/dev/null < "$BUILD_MARKER" || true)"
if [ -z "$LAST_BUILD_COMMIT" ]; then
  # Earlier versions kept the marker as the graphify_last_run key of state.json,
  # which described the main checkout. Honour it there only; a linked worktree
  # without a marker falls through to the full-history scan below.
  # A linked worktree has its own git dir; the main checkout's is the common dir.
  # Compared as directories, not paths, so it also holds in a submodule or with
  # --separate-git-dir, where the git dir is not <root>/.git.
  GIT_DIR_ABS="$(git rev-parse --absolute-git-dir)"
  COMMON_DIR_ABS="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
  if [ "$(cd "$GIT_DIR_ABS" && pwd -P)" = "$COMMON_DIR_ABS" ]; then
    # devteam_state_dir honours an inherited STATE_FILE/USER_DATA_DIR as an
    # override; drop them so the state-dir pointer decides.
    unset STATE_FILE USER_DATA_DIR
    LAST_BUILD_COMMIT="$(state_get graphify_last_run "$(devteam_state_dir "$PROJECT_ROOT")/state.json")"
  fi
fi

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
    # Renames: "R  old -> new" — take new path
    [[ "$xy" == R* || "$xy" == *R ]] && fp="${fp##* -> }"
    case "$xy" in
      "??"|A*|*A|D*|*D|R*|*R) in_target_paths "$fp" && return 0 ;;
    esac
  done < <(git status --porcelain 2>/dev/null)
  return 1
}

HAS_STRUCTURAL=0

# Force build when output directory is absent
if [ ! -d "$OUTPUT_PATH" ]; then
  echo "📦 $OUTPUT_PATH not found — first-time build."
  HAS_STRUCTURAL=1
fi

# Check uncommitted structural changes in targetPaths
if [ "$HAS_STRUCTURAL" -eq 0 ] && has_uncommitted_structural_changes; then
  HAS_STRUCTURAL=1
fi

# Check committed structural changes since last build
if [ "$HAS_STRUCTURAL" -eq 0 ] && [ -n "$CURRENT_COMMIT" ]; then
  if [ -z "$LAST_BUILD_COMMIT" ]; then
    # No prior build marker — scan full git history for structural changes
    for src_dir in "${SOURCES[@]}"; do
      if [ -n "$(git log --diff-filter=ADR --name-only --format="" -- "$src_dir" 2>/dev/null | head -n1)" ]; then
        HAS_STRUCTURAL=1
        break
      fi
    done
  elif [ "$CURRENT_COMMIT" != "$LAST_BUILD_COMMIT" ]; then
    # New commits since last build — check diff between builds
    for src_dir in "${SOURCES[@]}"; do
      if [ -n "$(git diff --diff-filter=ADR --name-only "$LAST_BUILD_COMMIT"..HEAD -- "$src_dir" 2>/dev/null | head -n1)" ]; then
        HAS_STRUCTURAL=1
        break
      fi
    done
  fi
fi

if [ "$HAS_STRUCTURAL" -eq 0 ]; then
  exit 0
fi

# ── Build ─────────────────────────────────────────────────────────────────────
# shellcheck disable=SC2317,SC2329  # invoked indirectly via trap
cleanup() { rm -rf "$PROJECT_ROOT/graphify-src"; }
trap cleanup EXIT

echo "🔄 Building graphify-src..." >&2
rm -rf graphify-src
mkdir -p graphify-src

for src in "${SOURCES[@]}"; do
  if [ ! -e "$src" ]; then
    echo "❌ Required source '$src' not found in $PROJECT_ROOT." >&2
    exit 1
  fi
  mkdir -p "graphify-src/$(dirname "$src")"
  rsync -a "$src/" "graphify-src/$src/"
done

# `${arr[@]+…}`: bash 3.2 (macOS) treats an empty array as unbound under `set -u`.
for manifest in ${MANIFESTS[@]+"${MANIFESTS[@]}"}; do
  [ -z "$manifest" ] && continue
  if [ ! -f "$manifest" ]; then
    echo "⚠️  Manifest '$manifest' not found — skipping." >&2
    continue
  fi
  cp "$manifest" "graphify-src/$manifest"
done

echo "🧠 Running Graphify..." >&2
graphify update graphify-src

if [ ! -d "graphify-src/$OUTPUT_PATH" ]; then
  echo "❌ Graphify did not produce output at 'graphify-src/$OUTPUT_PATH'." >&2
  exit 1
fi

echo "📦 Moving $OUTPUT_PATH to project root..." >&2
# graphify protects the cache dir with a macOS `deny delete` ACL, which makes `rm -rf` fail with EACCES.
# Strip ACLs first (no-op on Linux).
if [ -e "$OUTPUT_PATH" ]; then
  chmod -R -N "$OUTPUT_PATH" 2>/dev/null || true
fi
rm -rf "$OUTPUT_PATH"
mv "graphify-src/$OUTPUT_PATH" "./$OUTPUT_PATH"

# Record the commit this build reflects (used to skip redundant rebuilds)
printf '%s\n' "$CURRENT_COMMIT" > "$BUILD_MARKER"

echo "✅ Done!" >&2
exit 0
