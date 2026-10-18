---
name: performance-budgets
description: Core Web Vitals, bundle budgets, Lighthouse CI, image optimization.
---

# Performance Budgets

## When to Load

Load for frontend or full-stack projects where user-perceived performance matters. Not applicable to backend-only services.

## Core Web Vitals (2024 thresholds)

| Metric | Good | Needs improvement | Poor | Measures |
|--------|------|-------------------|------|----------|
| **LCP** (Largest Contentful Paint) | ≤ 2.5s | 2.5–4s | > 4s | Loading |
| **INP** (Interaction to Next Paint) | ≤ 200ms | 200–500ms | > 500ms | Interactivity |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | 0.1–0.25 | > 0.25 | Visual stability |

**FID (First Input Delay)** was replaced by INP in March 2024.

## Bundle Size Budgets (recommended defaults)

| Asset | Budget | Measured as |
|-------|--------|-------------|
| Initial JS (critical path) | ≤ 200 KB | gzipped |
| Total JS | ≤ 500 KB | gzipped |
| Initial CSS | ≤ 50 KB | gzipped |
| Web fonts | ≤ 100 KB | total |
| Hero image | ≤ 200 KB | per viewport |

Adjust per project; record agreed budgets in `docs/development/performance-budgets.md`.

## Lighthouse CI

Integrate Lighthouse CI in the PR pipeline:

```yaml
# .github/workflows/lighthouse.yml (example)
- uses: treosh/lighthouse-ci-action@v11
  with:
    urls: |
      http://localhost:3000
    budgetPath: .lighthouserc.json
    uploadArtifacts: true
```

Minimum score gates (recommended):
| Category | Minimum |
|----------|---------|
| Performance | 80 |
| Accessibility | 90 |
| Best Practices | 90 |
| SEO | 80 |

## Image Optimization

| Format priority | When to use |
|-----------------|-------------|
| AVIF | Modern browsers; best compression |
| WebP | Broad support; fallback for no-AVIF |
| JPEG/PNG | Legacy fallback only |

Rules:
- Always use `width` and `height` attributes to prevent CLS
- Use `loading="lazy"` for below-fold images
- Use `fetchpriority="high"` on the LCP image
- Serve responsive images via `srcset` and `sizes`

## Resource Hints

| Hint | Use for | Risk |
|------|---------|------|
| `<link rel="preload">` | LCP image, critical font, hero CSS | Over-use delays other resources |
| `<link rel="prefetch">` | Next-page assets (navigation prediction) | Low priority; wastes bandwidth if wrong |
| `<link rel="preconnect">` | Third-party origins (CDN, fonts) | Only top 2–3 origins |
| `modulepreload` | ES modules needed for first interaction | Chrome-specific (ignored elsewhere) |

## Critical CSS

- Inline ≤ 14 KB of above-the-fold CSS in `<head>`
- Defer non-critical CSS with `media="print" onload="this.media='all'"`
- Tools: `critters`, `penthouse`, `critical`

## Long Animation Frames (LoAF)

New Chrome signal (2024). Flags tasks > 50ms that block the main thread. Detect with:
```javascript
new PerformanceObserver(list => {
  for (const entry of list.getEntries()) {
    if (entry.duration > 50) console.warn('LoAF:', entry);
  }
}).observe({ type: 'long-animation-frame', buffered: true });
```

## Decision Checklist

- [ ] Are Core Web Vitals targets defined for this project?
- [ ] Are bundle size budgets recorded in `performance-budgets.md`?
- [ ] Is Lighthouse CI running on PRs?
- [ ] Are images in AVIF/WebP with correct `width`/`height`?
- [ ] Is the LCP element identifiable and preloaded?
- [ ] Is there a CLS budget for dynamic content?
