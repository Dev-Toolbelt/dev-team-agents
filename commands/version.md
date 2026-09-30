---
description: Print the installed dev-team-agents version, in the session-start banner layout
model: haiku
---

You are running the **`/devteam:version`** command.

Its job: print the same `[DEVTEAM:SESSION_BANNER]` block `scripts/hooks/session-start.sh` prints at session start, on demand, at minimum token cost. One bash call, one exact-format echo — no agent spawn, no skill load, no analysis, no commentary before or after.

> This command operates on the local installation, not a git branch — it does **not** load `current-context` and has no Plan Gate.

---

## Step 1 — Read state and print the banner

Run this exactly, substituting nothing:

```bash
bash -c '
ROOT=""
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
[ -n "$GIT_COMMON_DIR" ] && ROOT="$(cd "$GIT_COMMON_DIR/.." 2>/dev/null && pwd)"
[ -n "$ROOT" ] || ROOT="$PWD"

# Paths are resolved by the same helper session-start.sh uses, so a bound project reads its
# machine-local state.json (state-dir pointer) and the resolved preference projection.
unset STATE_FILE USER_DATA_DIR
for LIB in "$ROOT/.dev-team-agents/scripts/hooks/lib/data-dirs.sh" "$ROOT/scripts/hooks/lib/data-dirs.sh"; do
  [ -f "$LIB" ] && . "$LIB" && break
done
if command -v devteam_state_dir >/dev/null 2>&1; then
  STATE_FILE="$(devteam_state_dir "$ROOT")/state.json"
  PREFS_FILE="$(devteam_prefs_file "$ROOT")"
else
  STATE_FILE="$ROOT/.dev-team-agents/user-data/state.json"
  PREFS_FILE="$ROOT/.dev-team-agents/user-data/preferences.json"
fi

DT_VERSION="$(grep -oE "\"installed_version\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$STATE_FILE" 2>/dev/null | grep -oE "[^\"]+\"?$" | tr -d "\"")"
if [ -z "$DT_VERSION" ]; then
  DT_VERSION="$(grep -m1 -oE "^## \[[0-9]+\.[0-9]+\.[0-9]+\]" "$ROOT/CHANGELOG.md" 2>/dev/null | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")"
fi
[ -n "$DT_VERSION" ] || DT_VERSION="unknown"
case "$DT_VERSION" in v*) ;; *) DT_VERSION="v${DT_VERSION}" ;; esac

USER_LANG="$(grep -oE "\"language\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$PREFS_FILE" 2>/dev/null | grep -oE "[^\"]+\"?$" | tr -d "\"")"
[ -n "$USER_LANG" ] || USER_LANG="en"

AUTO_UPDATE_LABEL="No"
grep -qE "\"auto_update\"[[:space:]]*:[[:space:]]*true" "$PREFS_FILE" 2>/dev/null && AUTO_UPDATE_LABEL="Yes"

WORKTREE_LABEL="No"
grep -qE "\"worktree_active\"[[:space:]]*:[[:space:]]*true" "$PREFS_FILE" 2>/dev/null && WORKTREE_LABEL="Yes"

echo "[DEVTEAM:SESSION_BANNER]"
echo "DevTeam Agents • ${DT_VERSION} (github.com/Dev-Toolbelt/dev-team-agents)"
echo "─────────────────────────────────────────────────"
echo "Language: ${USER_LANG} | Auto Update: ${AUTO_UPDATE_LABEL} | Worktree: ${WORKTREE_LABEL}"
'
```

Output exactly what the script prints. Nothing before it, nothing after it.
