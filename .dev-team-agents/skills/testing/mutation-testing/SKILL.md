---
name: mutation-testing
description: Mutation testing — code mutations to measure test suite quality.
---

## What It Measures

Code coverage tells you which lines were *executed*. Mutation testing tells you whether your tests actually *catch bugs*.

A **mutant** is a small, automated change to the production code (e.g., `>` → `>=`). If your test suite still passes after that change, the mutant **survived** — meaning no test would catch that bug in real code.

**Mutation score** = (mutants killed / total mutants) × 100

---

## Tools by Language

| Language | Tool | Notes |
|---|---|---|
| JavaScript / TypeScript | [Stryker](https://stryker-mutator.io/) | Supports Jest, Vitest, Jasmine, Mocha |
| Java / Kotlin | [PITest](https://pitest.org/) | Maven + Gradle plugins; fast incremental mode |
| Python | [Mutmut](https://github.com/boxed/mutmut) | Simple CLI; integrates with pytest |
| PHP | [Infection](https://infection.github.io/) | PHPUnit + Pest; mutation badge support |
| Ruby | [Mutant](https://github.com/mbj/mutant) | Supports RSpec; strict coverage mode |

---

## Mutation Score Targets

| Score | Interpretation | Action |
|---|---|---|
| ≥ 80% | Healthy test suite | Maintain; review survivors in critical paths |
| 60–79% | Acceptable; room to improve | Identify weakest modules; add targeted assertions |
| < 60% | Weak assertions throughout | Significant test quality problem; prioritize fixes |

A high line-coverage score with a low mutation score is a red flag — tests are running the code but not asserting the outcomes.

---

## Common Mutant Types

| Mutant | Example | What it reveals |
|---|---|---|
| Arithmetic operator swap | `a + b` → `a - b` | Missing assertion on computed value |
| Boundary condition | `x > 0` → `x >= 0` | Off-by-one not tested at the boundary |
| Boolean negation | `isValid` → `!isValid` | Condition outcome not asserted |
| Return value deletion | `return result` → `return null` | Caller does not assert the return value |
| Logical connector swap | `&&` → `\|\|` | Combined conditions not tested independently |

---

## Where to Apply

**Apply mutation testing to:**
- Business-critical logic (pricing, tax, discount calculations)
- Validation rules (input sanitization, form validation)
- Authorization and permission checks
- State machine transitions
- Data transformation pipelines

**Skip or deprioritize:**
- UI components and rendering logic (high mutant count, low signal)
- Boilerplate (getters/setters, simple DTOs)
- Generated code
- Infrastructure glue (database connectors, HTTP clients)

---

## CI Integration

- Do **not** run on every commit — mutation testing is slow (minutes to hours depending on suite size).
- Run on a **nightly schedule** or as a **pre-release gate**.
- On PRs: optionally run only on changed files (Stryker and PITest both support incremental mode).
- Publish mutation reports to a dashboard or artifact store; track score trend over time.

---

## Acting on Surviving Mutants

A surviving mutant = a specific test gap. The correct response is a **targeted assertion**, not generic additional tests.

Steps:
1. Read the surviving mutant: what exact change survived?
2. Identify which behavior is not being asserted.
3. Write one assertion that would kill that specific mutant.
4. Re-run to confirm the mutant is now killed.

Do not chase 100% mutation score — some survivors are acceptable (e.g., equivalent mutants that produce identical behavior). Focus effort on critical paths.
