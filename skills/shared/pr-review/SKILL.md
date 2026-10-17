---
name: pr-review
description: PR review — correctness, security, tests, performance, style.
---

# Pull Request Review

## PR Creation Standards

Apply these rules whenever creating or drafting a pull request:

- **Language**: all PR text (title, summary, bullet points, test plan) must be written in **English**.
- **No Claude attribution**: do not include "🤖 Generated with Claude Code", "Co-Authored-By: Claude", or any other mention of Claude or AI tooling in the PR body, title, or commit messages.
- **Authorship**: the PR and its commits must reflect only the authenticated git user. Never add Claude as a co-author or contributor.
- **Content**: PR descriptions should reflect what the human developer is shipping — written as if authored entirely by the team.

---

## Before Reviewing

Read in order:
1. PR description — understand the intent and scope
2. Linked issue or task — confirm alignment
3. Changed files list — get a mental map before reading diffs

## Review Checklist

### Correctness
- [ ] Implements what the task/issue describes — no more, no less
- [ ] Edge cases handled (empty input, null, boundary values, concurrent access)
- [ ] No silent failures (errors caught but not handled or logged)
- [ ] No race conditions in concurrent or async code
- [ ] Database operations are atomic where they need to be (transactions)

### Security
- [ ] No secrets, tokens, or credentials in code or comments
- [ ] User input validated and sanitized before use
- [ ] No SQL injection, XSS, command injection vectors
- [ ] Auth checks present on new endpoints/actions
- [ ] Sensitive data not logged

### Tests
- [ ] New logic has test coverage
- [ ] Tests assert behavior, not implementation details
- [ ] Edge cases and failure paths tested
- [ ] Tests are fast and deterministic (no sleep, no external calls in unit tests)

### Performance
- [ ] No N+1 queries in loops
- [ ] No synchronous blocking calls where async is appropriate
- [ ] Large datasets handled with pagination or streaming

### Code Quality
- [ ] Names are clear and intention-revealing
- [ ] No duplicated logic (DRY)
- [ ] Functions do one thing (SRP)
- [ ] No dead code or commented-out blocks
- [ ] Complexity is justified — no premature abstraction

### Documentation
- [ ] Public APIs have descriptions (if project convention requires)
- [ ] Complex logic has a comment explaining WHY (not what)
- [ ] README updated if setup or usage changed
- [ ] ADR written if an architectural decision was made

### Style & Conventions
- [ ] Follows the project's code style (`code-standards.md`)
- [ ] Commit messages follow Conventional Commits
- [ ] No debugging artifacts (console.log, dd(), var_dump(), etc.)

## Review Comment Format

Write comments that explain the problem and suggest a fix:

```
[BLOCKING] This query runs inside the loop — will cause N+1.
Move the query outside and use eager loading:
  $orders->load('items');

[SUGGESTION] Consider extracting this into a `calculateTax()` method
for readability and testability.

[NITPICK] Variable name `d` is unclear — `deliveryDate` would be better.
```

Labels:
- **BLOCKING** — must be fixed before merge
- **SUGGESTION** — improvement worth doing, not a blocker
- **NITPICK** — minor style point, take it or leave it
- **QUESTION** — asking for clarification, not a change request

## PR Comment Gate

Applies when the review target is a pull/merge request (not a local branch or path).

**Path** — chosen from the synthesized findings:

| Findings | Path | Body |
|----------|------|------|
| ≥1 BLOCKING | **Comment** | Items that violate a project rule (`CLAUDE.md`, `AGENTS.md`, ADRs, `docs/development/code-standards.md`, `docs/development/reuse-guidelines.md`, `docs/specs/`) or a harness standard (a canonical skill rule); none of them do → post nothing |
| No BLOCKING | **Approve** (per PR Approval Criteria below) | The rule-violating SUGGESTION items, or a single friendly line when there are none |

**Owner** — whoever presents the final synthesized findings runs the gate once: `/devteam:review` at its Step 8; a reviewer agent only when invoked directly, never when spawned by a command.

**Content** — one consolidated comment, never one per finding:

| Rule | Detail |
|------|--------|
| Mention | Every assignee, directly (`@user`); no assignee → the PR/MR author |
| Items | Only BLOCKING and SUGGESTION; drop NITPICK, QUESTION, and anything already fixed in the diff |
| Per item | Label, `path:line`, a short fenced excerpt of the offending code, the fix in one sentence, the violated rule's source |
| Tone | One friendly opening line, then the list; no praise filler, no closing summary |
| Language | The PR description's language; fallback `language` in `.dev-team-agents/resolved/preferences.json` |
| Attribution | None — same rules as PR Creation Standards above |

~~~markdown
@author-handle thanks for the PR! A few points before merge:

- **[BLOCKING]** `src/orders/service.ts:42` — query inside the loop (N+1, breaks `code-standards.md` § Data access):
  ```ts
  for (const o of orders) await repo.items(o.id)
  ```
  Load items once with `repo.itemsFor(orderIds)`.
~~~

**Confirmation** — show the full draft, then ask with `AskUserQuestion`. Never act without an explicit choice.

| Path | Options |
|------|---------|
| Comment | **Post (Recommended)** / **Edit** (apply the user's changes, show again) / **Don't post** |
| Approve | **Approve (Recommended)** / **Comment only** (post the body, no approval) / **Edit** / **Don't post** |

Drop **Approve** — offer only **Comment only** / **Edit** / **Don't post** — when the authenticated user is the PR/MR author (platforms reject self-approval) or has already approved it.

**Platform**

| Platform | Resolve people | Comment | Approve |
|----------|----------------|---------|---------|
| GitHub | `gh pr view <pr> --json author,assignees,reviews`; self: `gh api user --jq .login` | `gh pr comment <pr> --body-file <file>` | `gh pr review <pr> --approve --body-file <file>` |
| GitLab | `glab mr view <mr> --output json` (`author`, `assignees`); self: `glab api user` | `glab mr note <mr> --message "$(cat <file>)"` | `glab mr approve <mr>`, then the Comment command when the body has items |
| Other (Bitbucket, Azure DevOps…) | Available MCP or API | Available MCP or API | Available MCP or API |

CLI missing, unauthenticated, no API access, or approval rejected (insufficient permission) → print the draft ready to paste and continue; never fail the review over posting. Never request changes or merge from this gate. Write the body to a scratch file, not inline shell arguments.

## PR Approval Criteria

Approve when:
- All BLOCKING items are resolved
- No new security vulnerabilities introduced
- Tests pass
- Code is understandable without the author explaining it

Request changes when:
- Any BLOCKING item remains
- Test coverage meaningfully decreased
- Security concern not addressed
