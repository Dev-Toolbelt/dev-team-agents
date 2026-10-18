---
name: css-quality
description: CSS quality — specificity, magic numbers, responsive. Agnostic.
---

# CSS Quality

## Detect the Project's Styling Strategy First

Before writing any CSS, identify what the project already uses:

| Signal | Strategy |
|---|---|
| `tailwind.config.*`, `@apply`, utility classes in markup | Utility-first (Tailwind or equivalent) |
| `*.module.css` imports, `styles.module.*` | CSS Modules |
| `styled-components`, `@emotion/styled`, `css` template literals | CSS-in-JS |
| `.scss` / `.sass` files, `@mixin`, `@include` | Sass/SCSS |
| Global `styles.css` / `main.css`, BEM class names | Global CSS + BEM |

**Never mix strategies** in the same codebase unless the project explicitly documents it.

---

## Universal Rules (apply to every strategy)

### No magic numbers
Every numeric value that carries design meaning must be a token or variable.

```css
/* bad */
margin-top: 13px;
color: #3b82f6;

/* good */
margin-top: var(--spacing-3);
color: var(--color-primary);
```

Define tokens in a single source of truth (`:root` variables, a theme file, or Tailwind config). Duplication of raw values across files is a DRY violation.

### No `!important`
`!important` signals a specificity conflict that should be solved at the source. The only accepted exceptions: third-party override utilities and print stylesheets.

### No deeply nested selectors
Cap nesting at 3 levels. Deeper nesting creates high specificity that is hard to override and signals the component should be split.

```css
/* bad — depth 4 */
.card .header .title span { }

/* good */
.card-title { }
```

### Responsive: mobile-first by default
Use `min-width` breakpoints unless the project documents a desktop-first baseline. Mobile-first produces less CSS and is easier to override progressively.

```css
/* good */
.container { width: 100%; }
@media (min-width: 768px) { .container { width: 720px; } }
```

### Motion: respect user preferences
Any animation or transition must be wrapped in a `prefers-reduced-motion` guard.

```css
@media (prefers-reduced-motion: no-preference) {
  .card { transition: transform 200ms ease; }
}
```

### `will-change` sparingly
Declare `will-change` only immediately before an animation triggers, not as a permanent style. Overuse forces GPU layers and increases memory consumption.

---

## Strategy-Specific Rules

### Utility-first (Tailwind)
- Extract repeated utility combinations into a component or a `@layer components` class — not inline repetition across 10 files
- Never write custom CSS to replicate what a Tailwind utility already does
- Purge config must cover all template paths — unused utilities in production are a build quality issue

### CSS Modules
- One module per component file — no shared `styles.module.css` across components
- Use camelCase class names in the module so they work naturally as JS properties
- Avoid composing across module files (`composes: foo from '../other.module.css'`) — creates implicit coupling

### CSS-in-JS
- Never inline complex style objects directly in JSX — extract to a named `const` or a separate styles file
- Avoid dynamic styles that change on every render (new object reference each time) — memoize with `useMemo` or extract static styles outside the component

### Global CSS + BEM
- Block, Element, Modifier: `block__element--modifier`
- One block per file
- No element targeting a block from another file: `.card .button` is coupling, not composition

---

## Anti-Patterns

| Anti-Pattern | Problem |
|---|---|
| `color: red` / `margin: 5px` hardcoded | Breaks design token consistency |
| Overriding with `!important` | Masks a specificity bug |
| Mixing responsive strategies (some mobile-first, some desktop-first) | Unpredictable cascade |
| Animating `width`, `height`, `top`, `left` | Triggers layout — animate `transform` and `opacity` instead |
| CSS reset inside a component | Bleeds into global scope; use scoped styles |
| Selector like `div > ul > li > a` | Fragile — breaks with any markup change |
