# Workflow — Security Patch

Use when a security vulnerability is identified — through a CVE, security audit finding, or bug report.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

---

## Step 1: Assess Severity

```
Prompt: "As the security-specialist, assess this vulnerability: [description / CVE / finding].
         What is the severity, what is the attack surface, and is there evidence of exploitation?"
```

The `security-specialist` presents an assessment plan (what to examine, scoring criteria) and waits for approval. The output is a severity report — no code changes happen at this step.

For **CRITICAL**: escalate immediately, consider taking the affected feature offline, notify stakeholders before proceeding.

---

## Step 2: Patch (backend-developer / devops-specialist)

```
Prompt: "As the backend-developer, implement the security fix for [vulnerability].
         Minimize scope — touch only what's needed."
```

The developer will:
- Present a plan (root cause, exact files to change, blast radius)
- Explicitly list what will NOT be touched
- Wait for your approval before writing any code

For dependency vulnerabilities:
```
Prompt: "As the devops-specialist, upgrade [package] to [version] that patches CVE-XXXX.
         Check for breaking changes and test the upgrade."
```

The `devops-specialist` presents a plan (upgrade steps, breaking change risk, test strategy) before touching any config or lock file.

---

## Step 3: Test Run

Run the full test suite to verify the patch (or dependency upgrade) didn't break existing functionality:

```
Prompt: "As the backend-test-specialist, run the full test suite and report any
         failures introduced by the security patch."
```

If no automated tests exist, the `qa-specialist` does a manual regression pass on the affected area instead.

---

## Step 4: Security Review (security-specialist)

```
Prompt: "As the security-specialist, verify that the patch fully addresses the
         vulnerability and doesn't introduce new attack vectors."
```

The `security-specialist` presents a verification plan and waits for approval. Output is a structured security report.

---

## Step 5: Code Review + QA (parallel)

**Run in parallel (send both prompts in one message):**
| Step | Agent | Par. |
|------|-------|------|
| 5a | code-reviewer | A |
| 5b | qa-specialist | A |

```
Prompt: "As the code-reviewer, review the security patch for correctness."

Prompt: "As the qa-specialist, verify the patch doesn't regress any existing functionality."
```

Both agents present their respective plans and wait for approval before running checks.

▶ **CHECKPOINT — await: code-reviewer (5a), qa-specialist (5b)**
Both reports must be clear before proceeding to deploy.

---

## Step 6: ROLLBACK PLAN — Document Before Deploying

Before the `devops-specialist` executes any deploy, document the rollback plan. This must exist in writing before the deploy begins:

```
Prompt: "As the devops-specialist, document the rollback plan for this security patch:
         (1) the exact command or procedure to revert the deployment,
         (2) who to notify if a rollback is triggered,
         (3) how long to monitor post-deploy before declaring the patch stable."
```

Capture the output in `.claude/docs/development/security-incidents.md` or your deploy notes. Do not proceed to deploy without this.

---

## Step 7: Deploy (devops-specialist)

```
Prompt: "As the devops-specialist, what's the fastest safe deploy strategy for
         this security patch? Consider: [environment / traffic / rollback options]"
```

The `devops-specialist` presents a deploy plan (steps, rollback procedure, verification commands) and waits for your approval before executing anything.

Security patches often justify faster deploy cycles — coordinate with the team on the timeline.

---

## Step 8: Post-Incident

```
Prompt: "As the technical-writer, document this vulnerability, the fix applied,
         and the timeline in .claude/docs/development/security-incidents.md"
```

The `technical-writer` presents a plan (document structure, sections to include) and waits for approval. The incident report is written in **English**.

Document:
- What was the vulnerability
- When it was discovered and by whom
- What was the impact / blast radius
- How it was fixed
- How to prevent similar issues

**Commit and PR**: run `/devteam:commit` to commit the patch with a clear security-scoped commit message. Open a PR if GitHub is configured:
```
Prompt: "Please open a PR for this security patch."
         → Agent will present a plan and ask for consent before creating the PR.
```

If the vulnerability was caused by a bug in application logic (not just a dependency), see `workflows/bug-fix.md` for the complementary bug-fix workflow.

---

## Workflow Closure

Before closing out the session, verify:

- [ ] Severity assessment documented by `security-specialist`
- [ ] Patch implemented with minimal blast radius
- [ ] Full test suite passed (or manual regression completed)
- [ ] Security-specialist confirmed patch fully addresses the vulnerability
- [ ] Code review and QA passed
- [ ] Rollback plan documented in writing before deploy
- [ ] Deploy completed and monitoring period underway
- [ ] Incident documented in `.claude/docs/development/security-incidents.md`
- [ ] Commits made and PR opened (if GitHub is configured)
- [ ] Session summary written to `.claude/user-data/session-summary.md`
