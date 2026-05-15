Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

## Step 0a — Conventional Commits pre-flight

Before drafting the PR body, detect the default branch and the project's commit pattern:

```bash
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null \
              || git config init.defaultBranch 2>/dev/null \
              || git remote show origin 2>/dev/null | awk '/HEAD branch/{print $NF}' \
              || echo "main")
```

**Before validating against Conventional Commits, detect the project's commit pattern:**

```bash
# Sample last 10 commits to detect project pattern
CC_RATIO=$(git log --oneline -10 | grep -cE "^[a-f0-9]+ (feat|fix|chore|docs|style|refactor|perf|test|build|ci)(\(.+\))?:" 2>/dev/null || echo 0)
if [ "$CC_RATIO" -lt 5 ]; then
    echo "ℹ Project does not appear to use Conventional Commits (${CC_RATIO}/10 matching commits). Skipping CC validation."
    # Skip the validation below
fi
```

If the project does use Conventional Commits (`CC_RATIO` is 5 or more), run a quick sanity check on the branch's commit history:

```bash
git log ${DEFAULT_BRANCH}..HEAD --format="%s" 2>/dev/null | head -20
```

Scan for commit messages that do **not** match the Conventional Commits pattern (`^(feat|fix|docs|refactor|perf|test|ci|build|chore|style)(\(.+\))?: .+`). If any non-conforming messages are found, report them to the user:

> "The following commits don't follow the Conventional Commits format: [list]. Proceed anyway, or would you like to amend them first?"

Do not block the PR — this is advisory only.

---

## Step 0b — Detect PR template

Before drafting the PR body:

1. Check if `.github/PULL_REQUEST_TEMPLATE.md` exists
2. If it exists:
   - Read it
   - Use it as the scaffold for the PR body
   - Fill each section with content derived from `git diff ${DEFAULT_BRANCH}...HEAD` and recent commits
   - Preserve the template structure exactly (checklist items, headers, HTML comments)
   - Auto-check checklist items that are verifiably true (e.g., "✅ Updated docs" if diff touches `docs/`)
3. If it does not exist:
   - Use the default structure (current behavior): Summary, Test plan, and checklist

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT write the PR description inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn:
- `technical-writer` at `.claude/agents/dev-team/technical-writer.md` — reads the commits and diff, writes the PR title and description based solely on what changed in this branch

If and only if $ARGUMENTS contains the word `review`, also spawn before creating the PR:
- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md` — final quality gate before opening the PR

---

**No Claude attribution**: the PR title, body, and all commit messages must not contain "🤖 Generated with Claude Code", "Co-Authored-By: Claude", or any other reference to Claude or AI tooling. Commits must reflect only the authenticated git user. Pass this requirement explicitly to any spawned agent.

After the technical-writer (and optionally code-reviewer) complete, present the PR draft to the user:
- Title
- Description body
- Base branch (default: `$DEFAULT_BRANCH`, or as specified in $ARGUMENTS via `base <branch>`)
- Draft status (default: false, set to true if $ARGUMENTS contains `draft`)

**NEVER run `gh pr create` without explicit user confirmation.**
Wait for the user to approve the draft before creating the PR.

$ARGUMENTS options:
- `review` — activate code-reviewer before creating
- `draft` — create as draft PR
- `base <branch>` — override the base branch
