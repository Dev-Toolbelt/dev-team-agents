# Workflow — Security Patch

Use when a security vulnerability is identified — through a CVE, security audit finding, or bug report.

---

## Step 1: Assess Severity

```
Prompt: "As the security-specialist, assess this vulnerability: [description / CVE / finding].
         What is the severity, what is the attack surface, and is there evidence of exploitation?"
```

For **CRITICAL**: escalate immediately, consider taking the affected feature offline, notify stakeholders before proceeding.

---

## Step 2: Patch (backend-developer / devops-specialist)

```
Prompt: "As the backend-developer, implement the security fix for [vulnerability].
         Minimize scope — touch only what's needed."
```

For dependency vulnerabilities:
```
Prompt: "As the devops-specialist, upgrade [package] to [version] that patches CVE-XXXX.
         Check for breaking changes and test the upgrade."
```

---

## Step 3: Security Review (security-specialist)

```
Prompt: "As the security-specialist, verify that the patch fully addresses the 
         vulnerability and doesn't introduce new attack vectors."
```

---

## Step 4: Code Review + QA

```
Prompt: "As the code-reviewer, review the security patch for correctness."

Prompt: "As the qa-specialist, verify the patch doesn't regress any existing functionality."
```

---

## Step 5: Deploy (devops-specialist)

```
Prompt: "As the devops-specialist, what's the fastest safe deploy strategy for 
         this security patch? Consider: [environment / traffic / rollback options]"
```

Security patches often justify faster deploy cycles — coordinate with the team on the timeline.

---

## Step 6: Post-Incident

```
Prompt: "As the technical-writer, document this vulnerability, the fix applied, 
         and the timeline in .claude/docs/development/security-incidents.md"
```

Document:
- What was the vulnerability
- When it was discovered and by whom
- What was the impact / blast radius
- How it was fixed
- How to prevent similar issues
