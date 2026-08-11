---
description: Show git status, staged/unstaged changes, and last 5 commits as formatted tables
argument-hint: [branch-name]
model: haiku
---

You are running the **`/devteam:status`** command.

Its job: print a token-efficient, formatted snapshot of the current git state — branch/worktree, unstaged changes, staged changes, last 5 commits, and totals. One bash call, no agent spawn, no skill load, no analysis, no commentary before or after.

If `$ARGUMENTS` is non-empty, it names a branch to inspect instead of the current one. Pass it to the script below as the positional argument exactly as received — do not validate or reformat it yourself, the script handles an unknown branch name.

> This command operates on the local git state, not a task scope — it does **not** load `current-context` and has no Plan Gate.

---

## Step 1 — Gather state and print the tables

Run this exactly, substituting only `$ARGUMENTS` for the positional argument:

```bash
bash -c '
TARGET_BRANCH="${1:-}"

if [ -n "$TARGET_BRANCH" ] && ! git rev-parse --verify --quiet "refs/heads/${TARGET_BRANCH}" >/dev/null; then
  echo "## \`/devteam:status\`"
  echo ""
  echo "⚠️ Branch \`${TARGET_BRANCH}\` does not exist locally."
  exit 0
fi

CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo "detached")"
BRANCH="${TARGET_BRANCH:-$CURRENT_BRANCH}"

# A linked worktree checked out for BRANCH lets status/diff run against it; otherwise
# unstaged/staged are working-tree concepts and only apply to the branch actually checked out here.
WORKTREE_PATH=""
if [ "$BRANCH" != "$CURRENT_BRANCH" ]; then
  WORKTREE_PATH="$(git worktree list --porcelain 2>/dev/null | awk -v b="refs/heads/${BRANCH}" "/^worktree /{p=\$2} /^branch /{if (\$2==b) print p}")"
fi

IS_WORKTREE="No"
WORKTREE_LABEL="No"
if [ -n "$WORKTREE_PATH" ]; then
  IS_WORKTREE="Yes"
  WORKTREE_LABEL="Yes (\`$(basename "$WORKTREE_PATH")\`)"
  cd "$WORKTREE_PATH" || exit 1
elif [ "$BRANCH" = "$CURRENT_BRANCH" ]; then
  git rev-parse --git-common-dir 2>/dev/null | grep -q "worktrees" && IS_WORKTREE="Yes"
  [ "$IS_WORKTREE" = "Yes" ] && WORKTREE_LABEL="Yes (\`$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")\`)"
fi

echo "## \`/devteam:status\`"
echo ""
echo "**Branch:** \`${BRANCH}\` · **Worktree:** ${WORKTREE_LABEL}"
echo ""

if [ "$BRANCH" != "$CURRENT_BRANCH" ] && [ -z "$WORKTREE_PATH" ]; then
  echo "_\`${BRANCH}\` has no checked-out worktree — unstaged/staged changes are working-tree state and only apply to the branch actually checked out. Showing commits and history for \`${BRANCH}\` only._"
  echo ""
fi

STATUS=""
if [ "$BRANCH" = "$CURRENT_BRANCH" ] || [ -n "$WORKTREE_PATH" ]; then
  STATUS="$(git status --porcelain=v1 2>/dev/null)"
fi

build_table() {
  local title="$1" col="$2"
  local mod add del mod_f add_f del_f untracked_f
  mod_f="$(echo "$STATUS" | awk -v c="$col" "substr(\$0,c,1)==\"M\"{print substr(\$0,4)}")"
  add_f="$(echo "$STATUS" | awk -v c="$col" "substr(\$0,c,1)==\"A\"{print substr(\$0,4)}")"
  del_f="$(echo "$STATUS" | awk -v c="$col" "substr(\$0,c,1)==\"D\"{print substr(\$0,4)}")"
  if [ "$col" -eq 2 ]; then
    untracked_f="$(echo "$STATUS" | awk "substr(\$0,1,2)==\"??\"{print substr(\$0,4)}")"
    [ -n "$untracked_f" ] && add_f="$(printf "%s\n%s" "$add_f" "$untracked_f" | grep -v "^$")"
  fi
  mod="$(echo "$mod_f" | grep -c . || true)"
  add="$(echo "$add_f" | grep -c . || true)"
  del="$(echo "$del_f" | grep -c . || true)"
  local total=$((mod + add + del))

  echo "### ${title} (${total} files)"
  echo ""
  if [ "$total" -eq 0 ]; then
    echo "_Nothing to show_"
  else
    echo "| Type | Count | Files |"
    echo "|------|:-----:|-------|"
    [ "$mod" -gt 0 ] && echo "| 🟡 Modified | ${mod} | $(echo "$mod_f" | paste -sd, - | sed "s/,/, /g") |"
    [ "$add" -gt 0 ] && echo "| 🟢 Added | ${add} | $(echo "$add_f" | paste -sd, - | sed "s/,/, /g") |"
    [ "$del" -gt 0 ] && echo "| 🔴 Deleted | ${del} | $(echo "$del_f" | paste -sd, - | sed "s/,/, /g") |"
  fi
  echo ""
}

HAVE_WORKTREE="No"
[ "$BRANCH" = "$CURRENT_BRANCH" ] || [ -n "$WORKTREE_PATH" ] && HAVE_WORKTREE="Yes"

if [ "$HAVE_WORKTREE" = "Yes" ]; then
  build_table "📝 Unstaged Changes" 2
  build_table "✅ Staged Changes" 1
fi

echo "### 📜 Last 5 Commits"
echo ""
echo "| Hash | Message | Author | Date |"
echo "|------|---------|--------|------|"
git log -5 "$BRANCH" --pretty=format:"| \`%h\` | %s | %an | %ad |" --date=format:"%Y-%m-%d %H:%M" 2>/dev/null
echo ""
echo ""

if [ "$HAVE_WORKTREE" = "Yes" ]; then
  NUMSTAT="$(git diff --numstat 2>/dev/null; git diff --cached --numstat 2>/dev/null)"
  ADDS="$(echo "$NUMSTAT" | awk "{s+=\$1} END{print s+0}")"
  DELS="$(echo "$NUMSTAT" | awk "{s+=\$2} END{print s+0}")"
  TOTAL_FILES="$(echo "$STATUS" | grep -c . || true)"

  echo "### 📊 Summary"
  echo ""
  echo "| Metric | Value |"
  echo "|--------|:-----:|"
  echo "| Total files changed | ${TOTAL_FILES} |"
  echo "| Additions (+) | ${ADDS} |"
  echo "| Deletions (−) | ${DELS} |"
fi
' _ "$ARGUMENTS"
```

Output exactly what the script prints, as markdown. Nothing before it, nothing after it.
