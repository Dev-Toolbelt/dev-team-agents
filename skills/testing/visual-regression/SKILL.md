---
name: visual-regression
description: Visual regression testing — screenshot diffing, Playwright/Chromatic, baseline management, and CI integration.
---

## Tools

| Tool | Best for | Hosting |
|---|---|---|
| **Playwright** screenshot comparison | Custom workflows; full-page and component screenshots; already in stack | Self-hosted |
| **Storybook + Chromatic** | Design system components; story-level diffing; team review UI | SaaS (Chromatic) |
| **Percy** | Cross-browser visual testing; integrates with many CI platforms | SaaS |
| **Applitools Eyes** | AI-powered diffing; reduced false positives; enterprise scale | SaaS |
| **Loki** | Storybook-only; lightweight; open source | Self-hosted |

**Recommendation:** use Playwright for integration-level flows; use Chromatic for component/design system work.

---

## When to Use

| Use visual regression for | Do NOT use for |
|---|---|
| Design system components (Button, Card, Modal) | Every component — adds test maintenance burden |
| Marketing and landing pages | Logic-heavy components with no visual output |
| Critical user flows (checkout, onboarding) | Components that change every sprint |
| Responsive layout breakpoints | Feature flags that render entirely different UIs |

**Principle:** visual regression tests are high-signal, low-quantity. Prefer 20 meaningful screenshots over 200 noisy ones.

---

## Baseline Management

- Update baselines **only after explicit design/product approval** of the visual change
- Tag the commit that updates baselines: `git tag visual-baseline-YYYY-MM-DD`
- Document baseline changes in the PR description: what changed and why
- Never update baselines to silence CI — investigate the diff first

### Playwright baseline update
```bash
# Regenerate all baselines
npx playwright test --update-snapshots

# Update a specific test file
npx playwright test tests/visual/button.spec.ts --update-snapshots
```

### Chromatic baseline acceptance
- Baselines are accepted via the Chromatic UI — requires a human reviewer, not automated
- Only maintainers with "Approver" role can accept baselines in production Storybook

---

## Diff Thresholds

| Difference | Action |
|---|---|
| 0% – 0.1% | Acceptable — sub-pixel anti-aliasing variation |
| 0.1% – 1.0% | Always review — may be font rendering, shadow, or real regression |
| > 1.0% | Treat as a regression until proven otherwise; block merge |

### Playwright threshold config
```typescript
// playwright.config.ts
export default defineConfig({
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.001,  // 0.1% threshold
      threshold: 0.2,             // per-pixel color tolerance (0–1)
    },
  },
});
```

---

## CI Integration

### Trigger rules
- Run visual regression on PRs targeting `main`
- Do NOT run on every push to feature branches — expensive and noisy
- Run on a schedule (nightly) against `main` to catch environmental drift

### Merge gate
- Visual failures **block merge** unless:
  1. The diff is explicitly accepted in the review tool (Chromatic/Percy), OR
  2. A maintainer overrides with a documented reason in the PR

### GitHub Actions (Playwright)
```yaml
visual-regression:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm ci
    - run: npx playwright install --with-deps chromium
    - run: npx playwright test tests/visual/
    - uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: visual-regression-diff
        path: test-results/
```

**Always upload diff artifacts on failure** — reviewers need to see what changed without re-running locally.

---

## Flakiness Management

| Cause | Fix |
|---|---|
| Animation not complete at screenshot time | Wait for animation end: `await page.waitForTimeout(300)` or disable animations in test |
| Font loading inconsistency | Use `page.waitForLoadState('networkidle')` or self-host fonts in tests |
| Dynamic content (dates, counts) | Mock or freeze dynamic data before screenshotting |
| OS font rendering differences | Run all visual tests in the same Docker image |

---

## Checklist

- [ ] Visual tests run only on PRs targeting main
- [ ] Baselines updated only after design approval
- [ ] Diff threshold set to 0.1% max
- [ ] Diff artifacts uploaded on failure
- [ ] Animations disabled or awaited in test setup
- [ ] Visual failures block merge without explicit acceptance
