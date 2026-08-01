---
name: frontend-done-checklist
description: Pre-delivery checklist for frontend tasks — run it before declaring any task complete.
---

# Frontend Done Checklist

Run through every item before declaring a task complete:

- [ ] Matches the design system (colors, spacing, typography, component patterns)
- [ ] Responsive — tested at 375px (mobile), 768px (tablet), 1280px+ (desktop)
- [ ] Accessible — keyboard navigable, no missing ARIA labels, sufficient contrast
- [ ] No console errors or warnings
- [ ] No hardcoded strings for international projects (use i18n keys)
- [ ] LCP measured (Lighthouse or DevTools) — target < 2.5 s
- [ ] Linters pass
- [ ] No debug artifacts
- [ ] Browser console: no errors; warnings that require disproportionate effort may be skipped but must be noted
- [ ] No `dangerouslySetInnerHTML` / `v-html` with unsanitized content
- [ ] No auth tokens or PII stored in `localStorage` / `sessionStorage`
- [ ] No type errors — type checker passes with no new errors or warnings (where the language supports it)
- [ ] Tests covering the change pass — load `skills/shared/scoped-test-execution/SKILL.md` **before** invoking any test runner and derive the scope from it; the full suite runs only if the user explicitly asked in this session
- [ ] Bundle impact reviewed — no new dependency added without checking its size and necessity
- [ ] Commit message follows project convention — if none is defined, load and follow `skills/shared/conventional-commits/SKILL.md`
- [ ] No Claude attribution in commit messages or PR body — never add "Co-Authored-By: Claude", "🤖 Generated with Claude Code", or any AI/Claude reference; authorship belongs only to the authenticated git user
