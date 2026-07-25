---
name: design-system-audit
description: Design system audit — visual patterns, consistency; Design/Consultive.
---

# Design System Audit

## Purpose

Before creating or modifying any UI, understand the existing visual language of the project. This audit produces a snapshot of the current design state that guides all subsequent UI work.

---

## Step 1 — Detect Existing Design System

Look for:

```
# Config files
tailwind.config.js / tailwind.config.ts
theme.js / tokens.js
design-tokens.json
_variables.scss / variables.css
styles/theme.*

# Component libraries in package.json
"@mui/material", "@chakra-ui/react", "antd", "shadcn", 
"mantine", "headlessui", "radix-ui", "bootstrap",
"daisyui", "flowbite", "primevue", "vuetify"

# Design files referenced in README
Figma links, Zeplin links, Storybook URL

# Existing component directory
src/components/ui/
src/components/base/
src/design-system/
```

---

## Step 2 — Audit Existing Patterns

Read 10–15 components/pages and extract the actual patterns in use:

### Color Palette
```
Primary:    [color value]   usage: CTAs, links
Secondary:  [color value]   usage: secondary actions
Neutral:    [scale]         usage: text, borders, backgrounds
Semantic:   success/warning/error/info [values]
```

### Typography
```
Font family: [name]
Scale: xs / sm / base / lg / xl / 2xl / ...
Weight usage: regular for body, semibold for headings, bold for CTAs
Line height: [value]
```

### Spacing System
```
Base unit: [4px / 8px / etc.]
Scale: [values used]
Pattern: [consistent use of spacing or chaotic?]
```

### Component Inventory
```
Buttons: [variants in use — primary, secondary, ghost, danger]
Inputs: [types — text, select, checkbox, radio]
Cards: [structure — has shadow? border? padding?]
Navigation: [top nav, sidebar, breadcrumbs]
Modals / Drawers: [exists? consistent behavior?]
Tables: [used? responsive?]
Feedback: [toast/snackbar, alerts, empty states, loading states]
```

### Responsiveness
```
Breakpoints: [values if defined]
Approach: [mobile-first or desktop-first]
Observed: [consistent or inconsistent across pages?]
```

---

## Step 3 — Identify Gaps and Inconsistencies

Document explicitly:

```
CONSISTENT: [list of patterns used uniformly]
INCONSISTENT: [list of patterns with multiple competing implementations]
MISSING: [patterns needed but not present — e.g., empty states, error states]
PROBLEMATIC: [accessibility issues, low contrast, missing focus states]
```

---

## Step 4 — Produce Design Context Document

When in **Design Mode** (pre-build), generate `docs/design/design-system.md`:

```markdown
# Design System — [Project Name]

## Status
[From scratch / Extending [library] / Audited existing]

## Color Tokens
| Token | Value | Usage |
|-------|-------|-------|
| --color-primary | #... | CTAs, links |
| --color-text | #... | Body text |

## Typography
| Style | Size | Weight | Usage |
|-------|------|--------|-------|
| Heading 1 | 2rem | 700 | Page titles |

## Spacing
Base: 4px. Scale: 4, 8, 12, 16, 24, 32, 48, 64px

## Components
[component list with variants]

## Patterns to Follow
[what to do]

## Patterns to Avoid
[what not to do — deviations, deprecated patterns]
```

---

## UX Principles Applied in Consultive Mode

When working alongside the `frontend-developer`, validate new UI against:

1. **Consistency** — Does this match the existing visual language?
2. **Hierarchy** — Is the most important element visually dominant?
3. **Feedback** — Does every user action produce visible feedback?
4. **Error recovery** — Are errors human-readable? Is there a clear path to recover?
5. **Accessibility** — Minimum contrast ratio 4.5:1 (text), focus states visible, keyboard navigable
6. **Mobile** — Does this work on a 375px viewport?

Suggest improvements when any of these are violated — but always check `project-context` first for existing guidelines.

---

## Design System Creation (Design Mode)

When building a design system from scratch, produce `docs/design/design-system.md` with the following sections:

### Color System
```
Primary: [value] — CTAs, interactive elements, brand color
Secondary: [value] — secondary actions, accents
Neutral scale: 50–950 — text, borders, backgrounds
Semantic: success (#...), warning (#...), error (#...), info (#...)
```
Ensure minimum contrast ratios: 4.5:1 for text, 3:1 for UI components (WCAG 2.1 AA).

### Typography
```
Font: [name] — [why this font]
Scale: 12/14/16/18/20/24/30/36/48px
Weights: 400 (body), 500 (labels), 600 (subheadings), 700 (headings)
Line height: 1.5 (body), 1.2 (headings)
```

### Spacing System
```
Base unit: 4px
Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96px
```

### Component Inventory
Document every reusable component with:
- Variants (primary, secondary, ghost, danger, etc.)
- States (default, hover, active, disabled, loading, error)
- Sizes (sm, md, lg where applicable)

### User Flows
For each major flow: step-by-step description with screen transitions, decision points, and error paths.

---

## `anthropic-skills:frontend-design` Integration

This skill is used alongside the `frontend-design` skill (installed automatically by `scripts/install.sh`), which provides component patterns, layout techniques, and visual design guidance. Load it at the start of every design session — it is required, not optional.
