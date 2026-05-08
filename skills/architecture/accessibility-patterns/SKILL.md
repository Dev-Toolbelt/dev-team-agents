---
name: accessibility-patterns
description: Accessibility patterns for WCAG compliance. Load only when explicitly required.
---

# Accessibility Patterns

> **When to load this skill**: only when the project requires WCAG compliance (documented in project context), the user explicitly requests accessibility work, or an audit tool (axe, Lighthouse) flags specific violations. Do not apply these patterns as default constraints on every task.

---

## Focus Management

Focus must be explicitly managed whenever the UI changes in ways the browser cannot handle automatically.

| Scenario | Required action |
|---|---|
| Modal / dialog opens | Move focus to the first interactive element inside, or the dialog container |
| Modal / dialog closes | Return focus to the trigger element that opened it |
| SPA route navigation | Move focus to the main heading or the `<main>` landmark of the new page |
| Inline error appears | Move focus to the error summary or the first invalid field |
| Dynamic content inserted (toast, alert) | Announce via a live region — do not move focus |

---

## ARIA Usage Rules

- **Prefer native HTML over ARIA**: `<button>` beats `<div role="button">`. ARIA fills gaps that semantic HTML cannot.
- **Do not add ARIA to elements that already have the right semantics**: `<button aria-role="button">` is redundant noise.
- **Every interactive custom component needs a role, a name, and a state**:
  - `role` — what it is (`combobox`, `tab`, `tree`)
  - accessible name — `aria-label`, `aria-labelledby`, or visible text
  - state — `aria-expanded`, `aria-selected`, `aria-checked` as appropriate

### Common pattern reference

| Component | Role | Required states |
|---|---|---|
| Tabs | `tablist` / `tab` / `tabpanel` | `aria-selected`, `aria-controls` |
| Accordion | `button` + `region` | `aria-expanded`, `aria-controls` |
| Combobox / autocomplete | `combobox` + `listbox` | `aria-expanded`, `aria-activedescendant` |
| Modal | `dialog` | `aria-modal="true"`, `aria-labelledby` |
| Alert / toast | `alert` or `status` | live region (`aria-live="polite"` or `"assertive"`) |
| Progress bar | `progressbar` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |

---

## Live Regions

Use live regions for content that changes without a focus move (notifications, status updates, async results).

```html
<!-- polite: announced after the user finishes their current action -->
<div aria-live="polite" aria-atomic="true">3 results found</div>

<!-- assertive: interrupts immediately — use only for errors or critical alerts -->
<div role="alert">Your session has expired.</div>
```

**Rules**:
- Render the live region container on initial load (empty); inject content into it dynamically — do not render and inject simultaneously or the announcement is missed
- `aria-atomic="true"` announces the full region on each update; omit it when only the new portion should be read

---

## Keyboard Navigation

Every interactive element must be reachable and operable by keyboard alone.

| Key | Expected behavior |
|---|---|
| `Tab` / `Shift+Tab` | Moves focus forward / backward through focusable elements |
| `Enter` / `Space` | Activates buttons, links, checkboxes |
| `Escape` | Closes modals, dropdowns, popovers |
| Arrow keys | Navigates within composite widgets (menus, tabs, radio groups, grids) |

**Focus trap**: when a modal is open, `Tab` must cycle within it — focus must not escape to the background. Use a focus trap utility rather than implementing it manually.

---

## Skip Links and Landmarks

- Add a visible-on-focus skip link as the first element in the page: `<a href="#main-content">Skip to main content</a>`
- Every page must have at least: one `<main>`, one `<header>`, one `<nav>` (if navigation is present)
- Multiple `<nav>` elements must be distinguished with `aria-label`: `aria-label="Primary"`, `aria-label="Breadcrumb"`

---

## Testing Accessibility

- **automated**: integrate `axe-core` (via `jest-axe`, `@axe-core/playwright`, or Storybook a11y addon) — catches ~30–40% of issues automatically
- **keyboard test**: navigate the feature with keyboard only before declaring done
- **screen reader test**: spot-check with VoiceOver (macOS/iOS), NVDA (Windows), or TalkBack (Android) for custom interactive components
- **contrast**: verify with browser DevTools or a contrast checker — target 4.5:1 for text, 3:1 for large text and UI components
