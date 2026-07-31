---
name: scoped-test-execution
description: Run only tests covering the touched code; full suite only on explicit user request.
---

# Scoped Test Execution

**Rule:** when finishing a task, run **only the tests that cover what you touched**. Never run the project's full suite on your own initiative. The full run belongs to CI, or to the user running it manually.

Rationale: a full suite costs wall-clock time and tokens on every task, and re-verifies code the task never touched. Scoped runs give the same signal for the work at hand.

---

## The Only Exception

The full suite runs **only** when the user explicitly asks for it in this session — "run the whole suite", "run all the tests", "rode a suíte inteira".

No other signal authorizes it. Not a fast suite, not a wide refactor, not a change to shared code, not a scoped test that failed, not a release or a merge. When the request is ambiguous ("make sure nothing broke", "validate everything"), **do not escalate** — run the scoped set and say in your report that you can run the full suite if the user confirms.

---

## Deriving the Scope

1. List what changed: `git diff --name-only` (plus `--cached` and untracked files when relevant).
2. For each changed source file, include its mirror test file (`src/foo/bar.ts` → `tests/foo/bar.test.ts`, `app/Service.php` → `tests/ServiceTest.php` — follow the project's own convention).
3. Add the tests of **direct dependents**: grep for who imports or uses the changed symbol, and include their tests. Scope means "the blast radius of this change", not "the file I edited".
4. When a changed file has no test, say so in the report — do not silently substitute a full run.

**Reduced scope is not empty scope.** If step 2 and step 3 yield nothing, you still verify the change some other way (a targeted test you write, a manual check) and report what you did.

---

## Runner Filters

| Stack | Scoped command |
|-------|----------------|
| Jest | `npx jest <paths…>` · `npx jest --findRelatedTests <changed-files…>` |
| Vitest | `npx vitest run <paths…>` · `npx vitest related <changed-files…>` |
| Playwright / Cypress | `npx playwright test <spec…>` · `npx cypress run --spec <glob>` |
| pytest | `pytest <path>` · `pytest <path>::<Class>::<test>` · `pytest -k "<expr>"` |
| PHPUnit / Pest | `vendor/bin/phpunit <path>` · `--filter '<pattern>'` |
| Go | `go test ./pkg/<changed>/...` · `-run '<Regexp>'` |
| Gradle / JUnit | `./gradlew test --tests '<FQCN>'` |
| Flutter | `flutter test test/<path>` |
| RSpec | `bundle exec rspec <path>:<line>` |
| Xcode | `xcodebuild test -only-testing:<Target>/<Class>` |
| Cargo | `cargo test <filter>` |

When the project defines its own scoped script in `CLAUDE.md`, `package.json`, or a `Makefile`, that command wins over the table.

---

## Coverage Runs

Coverage reports (SonarQube quality gates, LCOV artifacts) are **CI artifacts**. Generate coverage locally only when the user asks, or when a scoped run is already producing it for free. A quality-gate threshold is never a reason to trigger a full local run.

---

## Reporting

Close the task with one line naming what ran and what did not:

```
Tests: ran 12 tests across auth/session (scoped to the change). Full suite delegated to CI.
```

If the project has no CI, say so instead: `Full suite not run — no CI configured; run it locally when you want the complete check.`

---

## What This Rule Never Does

- It does not weaken a gate: a **scoped test that fails blocks the task**. Report the failure, fix it, or hand it back — never widen the run to bury it, and never skip or delete the failing test.
- It does not change what CI runs. Pipelines authored by `devops-specialist` keep executing 100% of the suite.
- It does not reduce what you **write**. Test authoring scope is governed by `skills/testing/test-strategy/SKILL.md`; this skill governs only what you **execute**.
