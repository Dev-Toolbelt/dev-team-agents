#!/usr/bin/env bash
# Graphify plugin: (re)build graphify-out/ from the configured source paths.
#
#   refresh.sh                 rebuild unconditionally (the "Rebuild graph" action)
#   refresh.sh --force         same, explicit
#   refresh.sh --if-changed    rebuild only when a source path changed structurally
#                              (added/deleted/renamed files) since the last build
#   --quiet                    suppress progress output (errors are always printed)
#
# Config: see lib/config.sh. The commit a build reflects is recorded in
# graphify-out/.build-commit, per checkout; the legacy graphify_last_run key of the
# machine-local state.json is read only in the main checkout, when no marker exists.
#
# Concurrent runs are serialised by a lock in the checkout's git dir: a second
# `--if-changed` run exits 0 ("already running"), a forced one exits 1.
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

SOURCES=()
while IFS= read -r line; do
  [ -n "$line" ] && SOURCES+=("$line")
done < <(graphify_safe_paths "$PROJECT_ROOT" "$CONFIG_JSON" targetPaths)
if [ ${#SOURCES[@]} -eq 0 ]; then
  if [ -n "$(graphify_cfg_list "$CONFIG_JSON" targetPaths)" ]; then
    echo "No valid 'targetPaths' remain in the graphify config - every entry was refused." >&2
  else
    echo "'targetPaths' is missing or empty in the graphify config - set the source paths first." >&2
  fi
  exit 1
fi

MANIFESTS=()
while IFS= read -r line; do
  [ -n "$line" ] && MANIFESTS+=("$line")
done < <(graphify_safe_paths "$PROJECT_ROOT" "$CONFIG_JSON" manifestPaths)

# ── Change detection ──────────────────────────────────────────────────────────
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
# The marker sits next to the graph it describes, so it is per checkout and versioned
# with the graph; a marker shared through the main checkout's state.json would let one
# worktree's build stand in for another's.
BUILD_MARKER="$OUTPUT_PATH/.build-commit"
# The marker is committed with the graph, so it is untrusted: only a plain hex object name
# is ever handed to git; anything else counts as absent.
COMMIT_RE='^[0-9a-f]{7,64}$'
LAST_BUILD_COMMIT="$(head -c 200 "$BUILD_MARKER" 2>/dev/null | tr -d '[:space:]' || true)"
if [ -n "$LAST_BUILD_COMMIT" ] && ! [[ "$LAST_BUILD_COMMIT" =~ $COMMIT_RE ]]; then
  echo "Ignoring $BUILD_MARKER: not a commit hash." >&2
  LAST_BUILD_COMMIT=""
fi
if [ -z "$LAST_BUILD_COMMIT" ]; then
  # Earlier versions kept the marker as the graphify_last_run key of state.json, which
  # described the main checkout. Honour it there only; a linked worktree without a
  # marker falls through to the full-history scan below. A linked worktree has its own
  # git dir, the main checkout's is the common dir (compared as directories, so it also
  # holds in a submodule or with --separate-git-dir).
  GIT_DIR_ABS="$(git rev-parse --absolute-git-dir)"
  COMMON_DIR_ABS="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
  if [ "$(cd "$GIT_DIR_ABS" && pwd -P)" = "$COMMON_DIR_ABS" ]; then
    if [ -n "${DEVTEAM_STATE_DIR:-}" ]; then
      LEGACY_STATE_DIR="$DEVTEAM_STATE_DIR"
    else
      # devteam_state_dir honours an inherited STATE_FILE/USER_DATA_DIR as an override;
      # drop them so the state-dir pointer decides.
      unset STATE_FILE USER_DATA_DIR
      LEGACY_STATE_DIR="$(devteam_state_dir "$PROJECT_ROOT")"
    fi
    LAST_BUILD_COMMIT="$(state_get graphify_last_run "$LEGACY_STATE_DIR/state.json")"
    if [ -n "$LAST_BUILD_COMMIT" ] && ! [[ "$LAST_BUILD_COMMIT" =~ $COMMIT_RE ]]; then
      echo "Ignoring the legacy graphify_last_run value: not a commit hash." >&2
      LAST_BUILD_COMMIT=""
    fi
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

# ── Lock ──────────────────────────────────────────────────────────────────────
# Per checkout (a linked worktree has its own git dir) and never tracked or ignored-by-
# hand. mkdir is the atomic primitive; a lock whose recorded pid is gone is stale.
LOCK_DIR="$(git rev-parse --absolute-git-dir)/graphify-refresh.lock"
LOCK_HELD=0
# pid plus the process start time: a recycled pid has a different start time.
proc_start() { ps -o lstart= -p "$1" 2>/dev/null | tr -s ' ' || true; }
lock_holder_alive() {
  local pid start
  pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  start="$(cat "$LOCK_DIR/start" 2>/dev/null || true)"
  [ -z "$start" ] || [ "$start" = "$(proc_start "$pid")" ]
}
acquire_lock() {
  local stale
  for _ in 1 2 3; do
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      proc_start "$$" > "$LOCK_DIR/start"
      echo "$$" > "$LOCK_DIR/pid"
      LOCK_HELD=1
      return 0
    fi
    lock_holder_alive && return 1
    # Half-created (no pid yet): give a fresh one a moment.
    if [ ! -s "$LOCK_DIR/pid" ]; then
      sleep 1
      lock_holder_alive && return 1
    fi
    # Take over by renaming: rename succeeds for exactly one contender, so two processes
    # can never both delete the stale lock and then both create their own. If the lock we
    # moved turns out to be live (someone re-created it in between), put it back.
    stale="$LOCK_DIR.stale.$$"
    if mv "$LOCK_DIR" "$stale" 2>/dev/null; then
      if [ -s "$stale/pid" ] && kill -0 "$(cat "$stale/pid" 2>/dev/null)" 2>/dev/null \
        && { [ ! -s "$stale/start" ] || [ "$(cat "$stale/start")" = "$(proc_start "$(cat "$stale/pid")")" ]; }; then
        mv "$stale" "$LOCK_DIR" 2>/dev/null || rm -rf "$stale"
        return 1
      fi
      rm -rf "$stale"
    fi
  done
  return 1
}
if ! acquire_lock; then
  if [ "$FORCE" -eq 0 ]; then
    log "graphify refresh is already running - skipping."
    exit 0
  fi
  echo "Another graphify refresh is already running in this checkout; try again when it finishes." >&2
  exit 1
fi

# ── Build ─────────────────────────────────────────────────────────────────────
# shellcheck disable=SC2317,SC2329  # invoked indirectly via trap
cleanup() {
  rm -rf "$PROJECT_ROOT/graphify-src"
  # A kill between the two moves of the output swap left the previous graph aside.
  if [ -n "${OLD_OUT:-}" ] && [ -e "$PROJECT_ROOT/$OLD_OUT" ] && [ ! -e "$PROJECT_ROOT/$OUTPUT_PATH" ]; then
    mv "$PROJECT_ROOT/$OLD_OUT" "$PROJECT_ROOT/$OUTPUT_PATH" 2>/dev/null || true
  fi
  if [ -n "${OLD_OUT:-}" ] && [ -e "$PROJECT_ROOT/$OUTPUT_PATH" ]; then rm -rf "${PROJECT_ROOT:?}/$OLD_OUT"; fi
  if [ "$LOCK_HELD" -eq 1 ]; then rm -rf "$LOCK_DIR"; fi
}
trap cleanup EXIT
# bash runs the EXIT trap on TERM/INT only when the signal is handled: exit through it.
trap 'exit 143' TERM
trap 'exit 130' INT
OLD_OUT=""

log "Building graphify-src..."
rm -rf graphify-src
mkdir -p graphify-src

for src in "${SOURCES[@]}"; do
  if [ ! -e "$src" ]; then
    echo "Required source '$src' not found in $PROJECT_ROOT." >&2
    exit 1
  fi
  mkdir -p -- "graphify-src/$(dirname "$src")"
  rsync -a -- "$src/" "graphify-src/$src/"
done

# rsync -a copies symlinks as links. Drop every one that does not resolve inside the
# copy, so graphify can never read a file outside what the config named.
SRC_REAL="$(_graphify_realpath "$PROJECT_ROOT/graphify-src")"
if command -v python3 >/dev/null 2>&1; then
  # One interpreter for all links; a fork per link is slow on a large tree.
  find graphify-src -type l -print0 | python3 -c '
import os, sys
root, quiet = sys.argv[1], sys.argv[2] == "1"
for raw in sys.stdin.buffer.read().split(b"\0"):
    if not raw:
        continue
    link = os.fsdecode(raw)
    resolved = os.path.realpath(link)
    if resolved != root and not resolved.startswith(root + os.sep):
        if not quiet:
            sys.stderr.write("Dropping symlink %r: it points outside the copied sources.\n" % link[len("graphify-src/"):])
        try:
            os.remove(link)
        except OSError:
            pass
' "$SRC_REAL" "$QUIET"
else
  while IFS= read -r -d '' link; do
    resolved="$(_graphify_realpath "$link")"
    if [[ "$resolved" != "$SRC_REAL"/* ]]; then
      log "Dropping symlink '${link#graphify-src/}': it points outside the copied sources."
      rm -f -- "$link"
    fi
  done < <(find graphify-src -type l -print0)
fi

for manifest in ${MANIFESTS[@]+"${MANIFESTS[@]}"}; do
  [ -z "$manifest" ] && continue
  if [ ! -f "$manifest" ]; then
    echo "Manifest '$manifest' not found - skipping." >&2
    continue
  fi
  mkdir -p -- "graphify-src/$(dirname "$manifest")"
  cp -- "$manifest" "graphify-src/$manifest"
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
# Swap without a window where no graph exists: set the old one aside, move the new one in,
# and only then delete the old one (cleanup restores it if the process is killed in between).
if [ -e "$OUTPUT_PATH" ]; then
  chmod -R -N "$OUTPUT_PATH" 2>/dev/null || true
  OLD_OUT="$OUTPUT_PATH.old.$$"
  rm -rf "$OLD_OUT"
  mv "$OUTPUT_PATH" "$OLD_OUT"
fi
if ! mv "graphify-src/$OUTPUT_PATH" "./$OUTPUT_PATH"; then
  echo "Could not move the new $OUTPUT_PATH into place; keeping the previous one." >&2
  exit 1
fi
if [ -n "$OLD_OUT" ]; then
  chmod -R -N "$OLD_OUT" 2>/dev/null || true
  rm -rf "$OLD_OUT"
  OLD_OUT=""
fi

# Record the commit this build reflects (skips redundant rebuilds; read by status.sh).
printf '%s\n' "$CURRENT_COMMIT" > "$BUILD_MARKER"

log "Done."
exit 0
