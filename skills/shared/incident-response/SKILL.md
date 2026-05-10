---
name: incident-response
description: Incident response runbook — severity classification, communication, investigation, mitigation, and post-mortem process.
---

## Severity Levels

| Severity | Definition | Response Time | Example |
|----------|-----------|---------------|---------|
| SEV1 | Complete outage — service unavailable for all users | Immediate | Site down, payments failing 100% |
| SEV2 | Major feature down — core functionality broken for most users | 15 min | Login broken, checkout not processing |
| SEV3 | Degraded performance — feature impaired or slow for a subset of users | 1 hour | Search slow, notifications delayed |
| SEV4 | Minor issue — cosmetic bug or edge-case failure with low impact | Next business day | UI glitch, rare error for <1% users |

---

## First 5 Minutes

1. **Declare the incident** — state the severity, impacted surface, and known symptoms
2. **Assign Incident Commander (IC)** — one person owns communication and coordination; others investigate
3. **Open an incident channel** — create a dedicated Slack/chat channel (e.g., `#inc-2026-05-10-checkout`)
4. **Send initial status** — post to status page and stakeholder channel within 5 minutes:

```
[SEV1 INCIDENT] - <short description>
Impact: <who is affected>
Status: Investigating
IC: @<name>
Next update: <time>
```

---

## Investigation Loop

Repeat until service is restored:

```
Symptom → Hypothesis → Test → Mitigation → Verify
```

- **Symptom**: what the monitoring/alert is showing (error rate, latency spike, etc.)
- **Hypothesis**: most likely cause based on recent deploys, traffic patterns, or known issues
- **Test**: check logs, metrics, traces to confirm or rule out the hypothesis
- **Mitigation**: apply the smallest change that restores service (rollback, feature flag, traffic shift)
- **Verify**: confirm metrics return to baseline before closing the loop

---

## Communication Cadence

| Severity | Update Frequency | Channels |
|----------|-----------------|----------|
| SEV1 | Every 15 min | Status page + stakeholder channel + incident channel |
| SEV2 | Every 30 min | Status page + stakeholder channel |
| SEV3 | Hourly | Incident channel |
| SEV4 | On resolution | Ticket comment |

Update format:
```
[UPDATE - HH:MM] Impact: <current state> | Action: <what's being done> | ETA: <if known>
```

---

## Mitigation-First Rule

- **Restore service before finding root cause** — rollback, disable the flag, reroute traffic, scale up
- Document all actions taken with timestamps in the incident channel
- Root cause analysis happens during post-mortem, not during active incident
- A working workaround is a valid mitigation; clean fixes come later

---

## Post-Mortem

- Write within **48 hours** of resolution while memory is fresh
- **Blameless**: the goal is to understand system failures, not assign fault to individuals
- Required for all SEV1 and SEV2 incidents; optional but encouraged for SEV3

### Post-Mortem Template

```markdown
## Summary
One-paragraph description of the incident and its impact.

## Timeline
- HH:MM — event / action taken
- HH:MM — event / action taken

## Root Cause
What was the direct technical cause?

## Contributing Factors
- Infrastructure / config state that made this possible
- Process gaps that delayed detection or response
- Dependencies that were involved

## Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| Fix X  | @name | YYYY-MM-DD |

## What Went Well
- Detection was fast
- Rollback procedure worked as expected
```

---

## On-Call Handoff

When handing off an active incident to the next on-call:

- Update the incident doc with current status and open questions
- Write a short **Current State** summary: what is known, what is still broken, what has been ruled out
- List everything that has been tried and whether it helped
- Tag the incoming on-call in the incident channel and confirm they have access to all relevant dashboards
