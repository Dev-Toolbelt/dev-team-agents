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
USER_DATA_DIR=".dev-team-agents/user-data"
STATE_FILE="$USER_DATA_DIR/state.json"
PREFS_FILE="$USER_DATA_DIR/preferences.json"

DT_VERSION="$(grep -oE "\"installed_version\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$STATE_FILE" 2>/dev/null | grep -oE "[^\"]+\"?$" | tr -d "\"")"
if [ -z "$DT_VERSION" ]; then
  DT_VERSION="$(grep -m1 -oE "^## \[[0-9]+\.[0-9]+\.[0-9]+\]" CHANGELOG.md 2>/dev/null | grep -oE "[0-9]+\.[0-9]+\.[0-9]+")"
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
