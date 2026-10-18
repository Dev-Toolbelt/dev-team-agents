---
description: Draft and create a pull request
argument-hint: [review] [draft] [base <branch>] [skip-commit|abort-on-dirty]
model: haiku
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

## Step -1 — Uncommitted changes pre-flight

Load `skills/shared/git-workflow/SKILL.md` and run its **Dirty-Tree Pre-flight** before any other action: with uncommitted changes, the `/devteam:commit` flow runs automatically (no "commit now?" question), then this command continues to Step 0a and opens the PR. `skip-commit` and `abort-on-dirty` opt out.

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

List them, then ask with `AskUserQuestion` (single-select): **Proceed anyway** (recommended — this is advisory) or **Amend them first**.

Do not block the PR — this is advisory only.

---

## Step 0b — Detect PR template

Before drafting the PR body:

1. Check if `.github/PULL_REQUEST_TEMPLATE.md` exists
2. If it exists:
   - Read it
   - Use it as the scaffold for the PR body
   - Fill each section from `git diff ${DEFAULT_BRANCH}...HEAD --stat`, `git log ${DEFAULT_BRANCH}...HEAD`, and recent commits. Do not pull the full unscoped diff into context — a PR body is a summary, not a diff reproduction. Pull a targeted `git diff ${DEFAULT_BRANCH}...HEAD -- <path>` only for the handful of files whose specific content the template section actually needs (e.g. a "breaking changes" section quoting an API signature)
   - Preserve the template structure exactly (checklist items, headers, HTML comments)
   - Auto-check checklist items that are verifiably true (e.g., "✅ Updated docs" if diff touches `docs/`)
3. If it does not exist:
   - Use the default structure (current behavior): Summary, Test plan, and checklist

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT write the PR description inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

Always spawn:
- `technical-writer` — reads the commits and diff, writes the PR title and description based solely on what changed in this branch

If and only if $ARGUMENTS contains the word `review`, also spawn before creating the PR:
- `code-reviewer` — final quality gate before opening the PR

---

**No Claude attribution**: the PR title, body, and all commit messages must not contain "🤖 Generated with Claude Code", "Co-Authored-By: Claude", or any other reference to Claude or AI tooling. Commits must reflect only the authenticated git user. Pass this requirement explicitly to any spawned agent.

After the technical-writer (and optionally code-reviewer) complete, present the PR draft to the user:
- Title
- Description body
- Base branch (default: `$DEFAULT_BRANCH`, or as specified in $ARGUMENTS via `base <branch>`)
- Draft status (default: false, set to true if $ARGUMENTS contains `draft`)

**NEVER run `gh pr create` without explicit user confirmation.**
Wait for the user to approve the draft before creating the PR.

---

## Post-create — Watch GitHub Actions

Creating a PR pushes the branch, which counts as an explicit push. Before `gh pr create` runs the push, load `skills/shared/github-actions/SKILL.md` and follow it in full: check its preconditions (gh authenticated + `.github/workflows/*` present, using the cached `ci_cd_detected` preference), then its quiz step — ask the user whether to watch CI or just push, per that skill's Flow § 0. On failure while watching, run its capped diagnose→fix→re-push loop, reporting a one-line summary each cycle. If the preconditions fail, skip silently and push normally.

## Post-create — Session summary (opening a PR is a finalization signal)

After `gh pr create` succeeds, apply the Session Summary Rule from `CLAUDE.md` right now rather than waiting for session end: check `git status --porcelain`, `git diff --cached`, and today's commits — the same detection `scripts/hooks/lib/session-summary-detect.sh` uses. If there is a signal and `.dev-team-agents/user-data/session-summary.md` has no entry for today, write one (Done/Decisions/Next, in English) before finishing the command.

## Post-create — Nudge `/devteam:learn` if not run this session

Run the canonical learn-nudge check in `commands/merge.md` § Step 4, with the current `HEAD` as the working branch tip. Hand off as that step says — never spawn `/devteam:learn` inline.

---

$ARGUMENTS options:
- `review` — activate code-reviewer before creating
- `draft` — create as draft PR
- `base <branch>` — override the base branch
- `commit` — accepted for compatibility; committing uncommitted changes first is now the default (Dirty-Tree Pre-flight)
- `skip-commit` — when uncommitted changes exist, continue without committing them first
- `abort-on-dirty` — when uncommitted changes exist, stop instead of committing
