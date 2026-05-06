Identify the current working context by running:
- `git branch --show-current` — active branch
- `git log main...HEAD --oneline` — commits introduced in this branch
- `git diff --name-only main...HEAD` — files changed vs main
- `git diff main...HEAD --stat` — change summary
- Check `.claude/.worktree-session` if present — active worktree

Use only this context to write the PR. Do NOT include changes from other branches or unrelated files.

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
- Base branch (default: main, or as specified in $ARGUMENTS via `base <branch>`)
- Draft status (default: false, set to true if $ARGUMENTS contains `draft`)

**NEVER run `gh pr create` without explicit user confirmation.**
Wait for the user to approve the draft before creating the PR.

$ARGUMENTS options:
- `review` — activate code-reviewer before creating
- `draft` — create as draft PR
- `base <branch>` — override the base branch
