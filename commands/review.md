Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

## Step 0 — Resolve review target

If `$ARGUMENTS` already names a target (a branch, a PR link/number, a path, or a free-text scope), use it and skip this step.

If `$ARGUMENTS` is **empty**, ask the user with `AskUserQuestion` (single-select) what to review:

> "What should I review?"
- **Current local branch** — review the diff of the active branch against its base branch (default)
- **Another local branch** — ask which branch (free-text), then review its diff against the base branch
- **A pull request link** — ask for the PR URL (GitHub, GitLab, Bitbucket, etc.), then fetch and review that PR's diff
- **Other** — let the user type a custom scope (specific files, a commit range, a folder)

Act strictly on the chosen target:

- **Current local branch** → proceed with the scope detected by `current-context`.
- **Another local branch** → `git diff <base>...<branch>` for that branch; restrict the review to those files.
- **A pull request link** → use the platform CLI/API to fetch the diff (`gh pr diff <url-or-number>` for GitHub; for GitLab/Bitbucket use the available MCP/CLI or fetch the diff). Review the PR changeset. Do not post comments unless the user asks.
- **Other** → review exactly the scope the user described.

Once the target is resolved, load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to the resolved changeset to determine which conditional agents below to spawn.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT review inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn in parallel:
- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md` — overall code quality, routes internally to backend-reviewer and/or frontend-reviewer based on what changed
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architectural consistency and design decisions
- `security-specialist` at `.claude/agents/dev-team/security-specialist.md` — security vulnerabilities and OWASP concerns
- `qa-specialist` at `.claude/agents/dev-team/qa-specialist.md` — validate behavior against acceptance criteria and assess regression risk

Also spawn if the task involves database changes:
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — query efficiency, schema correctness, migration safety

Also spawn if the diff includes mobile files (ios/, android/, *.swift, *.kt, App.tsx, pubspec.yaml, *.dart):
- `mobile-developer` at `.claude/agents/dev-team/mobile-developer.md` — review mobile-specific code quality, platform APIs, memory management, and lifecycle patterns

Task: $ARGUMENTS

---

## Step 9 — Apply findings (mandatory)

After all spawned agents complete and return their findings, present a synthesized summary of all findings (grouped by agent) to the user.

Then use `AskUserQuestion` (single-select) to ask:

> "Apply the review findings?"
- **Apply all findings** — automatically apply every suggested change to the codebase
- **Apply selected findings** — ask which findings to apply and apply only those
- **Skip, just show the summary** — do not modify any files; print the full review report

If the user chooses to apply, execute the changes directly (edit files, create commits if files were modified). Do not delegate back to agents — apply the changes yourself based on the findings already collected.

If the user chooses to skip, print a one-line confirmation: "Findings noted. No files were modified."
