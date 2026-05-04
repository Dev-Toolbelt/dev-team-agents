---
name: discovery-mode
description: Patterns for rigorous collaborative discovery before any implementation. Load this in any agent that operates in DISCOVERY — product-analyst, software-architect. Covers HARD-GATE, interaction style, scope decomposition, incremental validation, YAGNI, spec self-review, and user review gate.
---

# Discovery Mode Patterns

## HARD-GATE

<HARD-GATE>
Do NOT produce any backlog, architecture document, implementation plan, or take any implementation action until you have presented the design or scope and the user has explicitly approved it. This applies to every project regardless of perceived simplicity.
</HARD-GATE>

**Anti-pattern: "This Is Too Simple To Need Discovery"**
Every project goes through this process. A single endpoint, a config change, a utility function — all of them. The simpler the project, the shorter the spec. But the gate must be passed.

---

## One Question at a Time

When clarifying interactively with the user (not generating a client-facing document):

- Ask **one question per message**
- **Prefer multiple-choice** over open-ended — it is faster to answer
- If a topic requires multiple questions, break them across separate messages
- Focus each question on: purpose, constraints, or success criteria
- Only one question per message — if more exploration is needed, sequence them

---

## Scope Decomposition Check

Before asking detailed questions, assess the overall scope:

- If the request describes multiple independent subsystems (e.g., "build a platform with chat, billing, file storage, and analytics"), **flag this immediately**
- Do not spend questions refining details of a project that needs decomposition first
- Help the user split into sub-projects: what are the independent pieces, how do they relate, what order to build them?
- Then run the full discovery flow for the **first** sub-project only — each sub-project gets its own spec, plan, and implementation cycle

---

## Propose 2-3 Approaches

Before committing to a direction, present alternatives:

1. Identify 2-3 meaningfully different approaches with their trade-offs
2. **Lead with your recommendation** and explain why
3. Present conversationally — not as an equal-weight menu
4. The user can redirect; don't wait for them to ask for alternatives

Applies to: scoping strategies, architectural patterns, technology choices, and any decision with multiple valid paths.

---

## Incremental Validation

When presenting a design, spec, or architecture:

- Present **one section at a time**
- Ask "Does this look right so far?" before moving to the next section
- Straightforward sections can be 2-3 sentences; complex sections up to 200-300 words
- Revise a section when feedback comes before advancing to the next

---

## YAGNI

Remove unnecessary features from all designs ruthlessly:

- Only include what was explicitly requested or is clearly necessary
- If a feature sounds useful but wasn't asked for, flag it and let the user decide — do not include it silently
- Do not design for hypothetical future requirements

---

## Spec Self-Review

After writing any spec, overview, or architecture document, do a **silent inline review** before presenting it to the user. Fix issues directly — no need to narrate the review process.

| Category | What to Look For |
|----------|------------------|
| Placeholders | Any "TBD", "TODO", incomplete sections, vague requirements |
| Consistency | Internal contradictions, conflicting requirements between sections |
| Clarity | Requirements ambiguous enough to cause wrong implementation |
| Scope | Focused enough for a single plan — not covering multiple independent subsystems |
| YAGNI | Unrequested features, over-engineering, future-proofing that wasn't asked for |

Only flag issues that would cause real problems during implementation planning. Minor wording and style preferences are not issues.

---

## User Review Gate

After the spec self-review passes, **always** ask the user to review the written document before proceeding:

> "Document written to `<path>`. Please review it and let me know if you want any changes before we move on."

Wait for explicit approval. If changes are requested, apply them and re-run the self-review. Only proceed once the user approves.
