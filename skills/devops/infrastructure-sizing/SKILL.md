---
name: infrastructure-sizing
description: Right-sizing infrastructure — capability tiers, scaling triggers, anti-overengineering.
---

# Infrastructure Sizing

Match infrastructure to **measured** need, not to anticipated need. Every capability added before its trigger fires is paid for in cost, deploy time, debugging surface, and onboarding difficulty — permanently.

**Start small, measure, scale.**

---

## When to Load This Skill

- Choosing a hosting/runtime shape for a new service
- A request arrives to "move to Kubernetes", "add a queue", "go multi-region", "add a service mesh", or similar
- Reviewing an infrastructure proposal for cost or complexity
- An existing platform is straining and a tier change is under discussion

---

## Capability Tiers

Tiers describe **capabilities**, not products. Read the project's existing stack and pick the tier; the platform that delivers that tier is whatever the project (or its cloud provider) already uses.

| Tier | Sustained load | Capability required | What it means operationally |
|------|----------------|---------------------|-----------------------------|
| **T0 — Single host** | < 1k req/day | One machine running containers from a declarative multi-container file | Manual or scripted deploy; restart policy; backups; no autoscaling |
| **T1 — Optimized single host or smallest managed runtime** | 1k–10k req/day | Same as T0 with tuned resources, or the smallest managed container/app runtime | Managed TLS and health checks; still one logical instance |
| **T2 — Managed autoscaling container platform** | 10k–100k req/day | Horizontal autoscaling, rolling deploys, load balancing, per-instance health checks — all managed | Stateless app required; sessions and uploads must leave local disk |
| **T3 — Distributed architecture** | > 100k req/day | Multi-service scaling, independent deploy units, explicit failure isolation | Requires a team that can operate it; a cluster orchestrator is *one* option, not the definition of the tier |

> **Illustrative product examples only — never a recommendation:** T0/T1 are commonly a VPS or single cloud VM with a Compose-style file; T2 is commonly a managed container service (ECS/Fargate, Cloud Run, Container Apps, App Runner); T3 may be a managed orchestrator, a serverless composition, or a partitioned set of T2 services. Pick from what the project already runs and what the team can operate.

**Traffic is the entry heuristic, not the decision.** Adjust for: payload size, request duration, statefulness, compliance/isolation requirements, and the size of the team on call.

---

## Scaling Triggers — Move Up Only When One Fires

| Trigger | Observed as | Tier change it justifies |
|---------|-------------|--------------------------|
| Saturation | CPU/memory sustained > 70% at peak after tuning | T0 → T1 → T2 |
| Deploy downtime is unacceptable | Users see errors on every release | → T2 (rolling deploys) |
| Load is spiky and idle cost dominates | Peak/valley ratio > 5× | → T2 (scale-to-need) |
| Single-host failure is unacceptable | Availability target exceeds one machine's realistic uptime | → T2+ (redundancy) |
| Independent release cadence needed | Teams block each other on one deploy unit | → T3 (split services) |
| Regulatory or latency requirement per region | Data residency or a hard latency SLO in another region | → T3 (multi-region) |

If no trigger fires, the current tier is correct — regardless of how the platform looks compared to other projects.

---

## Anti-Overengineering Rules

Stated as capability comparisons — the products named are examples of the capability, not endorsements.

| Do not adopt | When the cheaper capability suffices | Cheaper capability |
|---|---|---|
| A cluster orchestrator | One host runs the workload within budget | Declarative multi-container file on a single host |
| An asynchronous message broker | Work is low-volume, tolerant of latency, or already synchronous | Scheduled job or a direct synchronous call |
| Multi-region deployment | One region plus tested restore meets the availability target | Single region + verified backups |
| A service mesh | Routing, TLS termination, and retries are handled at the edge | Reverse proxy / load balancer already in the stack |
| Serverless functions | Operations are long-running or fire at high constant frequency | A long-lived process (cost spikes and timeouts dominate otherwise) |
| A full third-party observability platform | The provider's built-in metrics/logs or a self-hosted stack answers the questions being asked | Provider-native monitoring or a self-hosted metrics stack |
| A dedicated cache tier | The database answers within the latency budget | Application-level or HTTP caching |
| A separate service | The boundary is not yet stable and one team owns both sides | A module inside the existing deployable |

**Corollary:** every "we'll need it later" argument must name the trigger from the table above that will fire, and roughly when. If no trigger can be named, the answer is "not yet".

---

## Cost & Reversibility Check

Before approving a tier increase, answer all four:

1. **Which trigger fired?** Cite the measurement, not the intuition.
2. **What does it cost per month** — infrastructure *plus* the operational time to run it?
3. **Who operates it at 3 a.m.?** A capability nobody on the team can debug is a liability, not a capability.
4. **How do we go back?** A tier change that cannot be reversed within a sprint needs an ADR (`skills/shared/adr/SKILL.md`).

---

## Downsizing

Sizing is bidirectional. Revisit when: traffic dropped, a feature was retired, autoscaling floor never rises, or a managed service replaced something self-run. Removing an unused tier is the cheapest performance and reliability work available.
