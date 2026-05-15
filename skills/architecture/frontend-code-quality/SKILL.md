---
name: frontend-code-quality
description: Base code quality standards for frontend development — component size, state management, semantic HTML, accessibility, performance, loading states, metadata, KISS/YAGNI/DRY principles, type safety, and prop sprawl rules. Loaded by frontend-developer as the authoritative quality baseline.
---

# Frontend Code Quality Standards (Base Defaults)

These apply unless the project overrides in `code-standards.md`:

- **Component size**: one component does one thing; split when > ~150 lines
- **State proximity**: keep state as close to where it's used as possible
- **No business logic in components**: move to hooks, composables, or services
- **Semantic HTML**: use the right element for the right job (`button`, `nav`, `article`, etc.)
- **Accessibility**: minimum WCAG 2.1 AA — contrast ratio 4.5:1, keyboard navigable, ARIA where HTML semantics are insufficient
- **Performance**: optimize for **Largest Contentful Paint (LCP) < 2.5 s** — the threshold Google defines as "good" and the industry benchmark below which bounce rates and conversion losses become significant. Every extra second of load time measurably increases abandonment. Concretely: lazy-load below-the-fold content, don't block rendering, preload critical assets, minimize layout shifts (CLS), and defer non-critical JS
- **No inline styles** unless the project uses CSS-in-JS as a convention
- **Loading states**: every API call or async operation must show a loading indicator while in flight — skeleton, spinner, disabled button, or equivalent; the implementation depends on context but user feedback is mandatory
- **Page metadata**: update `<title>`, meta description, Open Graph tags, and favicon whenever the page or its context changes; use the framework's head manager (React Helmet, VueUse/head, Nuxt `useHead`, Angular `Title`/`Meta`, etc.)
- **package.json metadata**: keep `name`, `version`, `description`, `author`, and `homepage` accurate and up to date
- **KISS**: prefer the simplest solution that correctly solves the problem — complexity requires explicit justification
- **YAGNI**: don't build abstractions, props, or features until they are actually needed
- **DRY**: every piece of logic has one authoritative source — extract duplicated logic before it spreads to a third place
- **Type safety** (where the language supports it): avoid untyped escape hatches (`any` or equivalent); declare prop types and return types explicitly; never use forced type assertions without a guard — treat the type system as a first-class quality tool
- **Prop sprawl**: a component with more than 5–7 props is a design smell — consider decomposing into smaller components, grouping related props into a configuration object, or moving state up or down the tree

## Related Architecture Skills

| Concern | Skill |
|---------|-------|
| Design patterns & violation criteria | `skills/architecture/design-patterns/SKILL.md` |
| Component structure (container/presentational, smart/dumb) | `skills/architecture/component-patterns/SKILL.md` |
| Naming & file structure | `skills/architecture/naming-conventions/SKILL.md` |
| CSS & styling quality (tokens, specificity, responsive, motion) | `skills/architecture/css-quality/SKILL.md` |
| State management (decision tree, library rules) | `skills/architecture/state-management/SKILL.md` |
| Code comments policy | `skills/shared/comments-policy/SKILL.md` |
