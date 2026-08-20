---
description: Draft and create a pull request
argument-hint: [review] [draft] [base <branch>] [commit|skip-commit|abort-on-dirty]
model: haiku
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

## Step -1 — Uncommitted changes pre-flight

Before any other action, run:

```bash
git diff --cached --name-only   # staged files
git diff --name-only            # unstaged modified files
```

If either command returns output (there are staged or unstaged changes):

1. Inform the user: "There are uncommitted changes in the working tree."
2. Resolve the path in this order:
   - If `$ARGUMENTS` contains `commit`, choose **Commit them now**
   - Else if `$ARGUMENTS` contains `skip-commit`, choose **Skip and continue**
   - Else if `$ARGUMENTS` contains `abort-on-dirty`, choose **Abort**
   - Else ask (via `AskUserQuestion`):

   > "There are uncommitted changes. What would you like to do before creating the PR?"
   - **Commit them now** — run the full commit routine below, then continue to Step 0a
   - **Skip and continue** — proceed to Step 0a without committing
   - **Abort** — stop the command entirely

If the user chooses **Commit them now**, execute the following routine inline (same logic as `devteam:commit`):

### Commit routine

1. Load `skills/shared/conventional-commits/SKILL.md`.
2. Read the target project's `CLAUDE.md` (root or `.claude/CLAUDE.md`) to detect the commit pattern. If a project-specific pattern is documented, follow it; otherwise use Conventional Commits.
3. Run `git status --short`, `git diff --cached --stat`, and `git diff --stat` to identify staged vs. unstaged files. Do NOT auto-stage — only commit what is already staged, unless `$ARGUMENTS` contains `all` or `--all` (then run `git add -A` first).
4. Group staged files into logical commits by layer (data/schema → domain → persistence → infrastructure → application → interface → tests → config/CI → docs). Skip empty layers. Bundle single-context changes into one commit.
5. For each group, write a commit message following the detected pattern. Never add `Co-Authored-By:`, AI attribution, or any non-user authorship footer.
6. Before executing each commit, run lint/type-check/tests if no pre-commit hook is already configured (same gates as in `devteam:commit` Step 4.5). If a gate fails, ask with `AskUserQuestion` (single-select): **Fix and re-stage** (recommended), **Commit anyway**, or **Abort**.
7. Present the proposed commit plan to the user and execute the commits unless the user says to stop.
8. After all commits, run `git log --oneline -5` and show the result.

Once the commit routine completes successfully, continue to Step 0a.

If there are **no** staged or unstaged changes, skip directly to Step 0a.

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

Check for the marker `/devteam:learn` writes:

```bash
cat .dev-team-agents/.learn-last-run 2>/dev/null
```

If the marker is absent, or its recorded commit hash is not an ancestor of the current `HEAD` (i.e. commits landed since the last learn run), tell the user before finishing:

> "This session hasn't run `/devteam:learn` since its last recorded commit — consider running it to capture decisions from this branch before they're lost. Run `/devteam:learn` now?"

Ask via `AskUserQuestion` (Yes / No). If yes, hand off by telling the user to invoke `/devteam:learn` (do not spawn it inline — it is a separate command with its own plan gate).

---

$ARGUMENTS options:
- `review` — activate code-reviewer before creating
- `draft` — create as draft PR
- `base <branch>` — override the base branch
- `commit` — when uncommitted changes exist, run the commit routine automatically before continuing
- `skip-commit` — when uncommitted changes exist, continue without committing them first
- `abort-on-dirty` — when uncommitted changes exist, stop instead of asking
