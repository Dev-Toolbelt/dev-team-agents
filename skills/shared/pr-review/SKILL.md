---
name: pr-review
description: Pull Request review checklist and standards. Use when reviewing or preparing a PR — covers correctness, security, tests, performance, documentation, and style. Produces structured review comments.
---

# Pull Request Review

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
