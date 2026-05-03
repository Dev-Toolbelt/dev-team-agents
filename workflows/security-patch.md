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

## Step 3: Security Review (security-specialist)

```
Prompt: "As the security-specialist, verify that the patch fully addresses the
         vulnerability and doesn't introduce new attack vectors."
```

The `security-specialist` presents a verification plan and waits for approval. Output is a structured security report.

---

## Step 4: Code Review + QA

```
Prompt: "As the code-reviewer, review the security patch for correctness."

Prompt: "As the qa-specialist, verify the patch doesn't regress any existing functionality."
```

Both agents present their respective plans and wait for approval before running checks.

---

## Step 5: Deploy (devops-specialist)

```
Prompt: "As the devops-specialist, what's the fastest safe deploy strategy for
         this security patch? Consider: [environment / traffic / rollback options]"
```

The `devops-specialist` presents a deploy plan (steps, rollback procedure, verification commands) and waits for your approval before executing anything.

Security patches often justify faster deploy cycles — coordinate with the team on the timeline.

---

## Step 6: Post-Incident

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
