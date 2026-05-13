# Workflow — Design

Use this workflow for design-system audits, new component design, UX redesigns, and visual consistency work. The primary agent is `ui-ux-designer`.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:design` runs this workflow.

---

## Step 0: Load Context

Load `skills/shared/current-context/SKILL.md` to detect the active branch and scope. If already loaded by a command wrapper, this step is a no-op.

---

## Step 1: Scope & Discovery (ui-ux-designer)

```
Prompt: "As the ui-ux-designer, [describe the design task — e.g., 'audit the checkout flow
         for consistency', 'design a new onboarding screen', 'update the design system with
         a new color palette'].
         Start by loading project context and existing design documentation."
```

The `ui-ux-designer` will:
- Load existing design system docs (`.claude/docs/design/design-system.md` if present)
- Present a plan covering: what to audit, what to produce, which components are in scope
- Wait for approval before generating any output

**Design mode vs. Development mode:**
- **Design mode**: scope analysis + new specs + design system documents. No code changes.
- **Development mode**: audit existing implementation against design system. May produce change requests.

State which mode you want explicitly if the workflow could be either.

▶ CHECKPOINT — await: design scope plan

---

## Step 2: Design Output (ui-ux-designer)

Depending on the task type:

**For new components or screens:**
```
Prompt: "As the ui-ux-designer, produce the design spec for [component/screen]:
         - Component hierarchy and props
         - Responsive breakpoints
         - Interaction states (hover, active, disabled, error, loading)
         - Accessibility requirements (WCAG AA minimum)
         - Motion/animation notes (if applicable)"
```

**For design-system audits:**
```
Prompt: "As the ui-ux-designer, audit the current implementation against the design system.
         List: (1) compliant components, (2) deviations with severity, (3) recommended fixes."
```

**For UX flow redesigns:**
```
Prompt: "As the ui-ux-designer, redesign the [flow name] UX. Produce:
         - User journey steps
         - Screen-by-screen flow description
         - Key interaction patterns
         - Rationale for each major decision"
```

▶ CHECKPOINT — await: design output + user review

---

## Step 3: Technical Feasibility (software-architect — conditional)

Run when the design involves significant technical decisions (new state management approach, layout engine change, animation performance concerns).

```
Prompt: "As the software-architect, review the design spec for technical feasibility.
         Identify any constraints the frontend stack imposes and suggest implementation approaches."
```

Skip this step for minor component updates or purely visual changes.

---

## Step 4: Implementation Handoff (conditional)

If the design output will be immediately implemented in the same session:

```
Prompt: "As the frontend-developer (or mobile-developer), implement the design spec:
         [attach spec from Step 2]. Follow the ui-ux-designer's component hierarchy
         and interaction states exactly."
```

If implementation is deferred:
- Save the design spec to `.claude/docs/design/`
- Summarize in session-summary

---

## Step 5: Design Review (ui-ux-designer — conditional)

After implementation (Step 4), run a review pass to verify design fidelity:

```
Prompt: "As the ui-ux-designer, review the implementation against the design spec.
         Check: pixel alignment, color tokens, spacing, interaction states, accessibility."
```

---

## Step 6: Documentation (technical-writer — optional)

If the work introduces or modifies design system components:

```
Prompt: "As the technical-writer, update the design system documentation at
         .claude/docs/design/design-system.md to reflect the new or modified components."
```

---

## Step 7: Commit & PR (if implementation occurred)

```
Prompt: "/devteam:commit"
```

Then optionally:

```
Prompt: "Please open a PR for these design changes."
```

---

## Workflow Closure

☐ Design scope defined and approved
☐ Design spec or audit report produced
☐ Technical feasibility confirmed (if applicable)
☐ Implementation matches spec (if Step 4 ran)
☐ Design system docs updated
☐ Session summary written

**Related workflows:**
- Frontend implementation follows design? → `/devteam:frontend` + `workflows/fullstack.md`
- Mobile feature requires design? → `workflows/mobile.md` (design is Step 1 there)
- Major architecture change triggered by design? → `/devteam:architect`

---

## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Design conflicts with existing project standards | Re-run `ui-ux-designer` with explicit project constraints; escalate to `software-architect` if unresolved |
| Implementation deviates significantly from spec | Return to Step 5 (review); spawn `frontend-developer` with specific remediation instructions |
| No existing design system to audit against | Start with design mode to create one; scope as a separate task before the main workflow |
