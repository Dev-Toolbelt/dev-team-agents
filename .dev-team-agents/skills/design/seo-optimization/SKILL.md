---
name: seo-optimization
description: Technical/on-page SEO, Core Web Vitals, structured data, GEO/LLM SEO, and quality-gate signals.
---

# SEO Optimization

Reference material for `seo-specialist`. Stack-agnostic — applies to any framework that renders HTML for a public, indexable surface.

Rules here follow primary sources (Google Search Central, schema.org, RFC 9309, llmstxt.org) where one exists. A number marked *heuristic* is a practitioner rule of thumb with no published source: it may raise an `ISSUE`, never a `BLOCKER`. References describe checks; severity is decided only by § Quality Gate Output Format.

## Conditional References

Load a reference only when its signal is present in the pages under review.

| Signal | Load |
|---|---|
| Any JSON-LD on the page, or structured data being added | `references/schema-status.md` |
| `Product`, `Offer`, a cart/checkout, a physical location, or a service area | `references/schema-ecommerce-local.md` |
| A sitemap is generated, edited, or reviewed | `references/sitemap-rules.md` |
| More than one locale or region | `references/hreflang.md` |
| `robots.txt` is edited, or the user states a policy on AI crawling/training | `references/ai-crawlers.md` |
| Editorial content (blog, guides, comparisons, location or programmatic pages) | `references/content-quality.md` |
| The site expects AI agents or agentic browsers to act on it, or content may be JS-only | `references/agent-readiness.md` |
| A shareable page (Open Graph tags) | `references/share-preview-check.md` |

## Detection Signals — When SEO Is Required

A project counts as "needs SEO" when any of these hold. Use this table to decide whether `seo-specialist` must be spawned, not just invited.

| Signal type | Examples |
|---|---|
| Project category | Institutional/marketing site, landing page, e-commerce/online store, blog, documentation portal, portfolio — any surface meant to be found via search or cited by an AI answer |
| File presence | `sitemap.xml`, `robots.txt`, `next-seo.config.*`, `astro.config.*` with `site:` set, `gatsby-config.js`, CMS content directories (`content/`, `posts/`, `blog/`) |
| Route shape | Product detail pages, category/listing pages, checkout funnel entry pages, blog post routes, `/blog/`, `/produtos/`, `/p/` |
| Dependency signals | `next-seo`, `react-helmet`, `vue-meta`, `schema-dts`, `astro-seo`, sitemap generator packages |
| Explicit request | User mentions SEO, ranking, Google, meta tags, structured data, sitemap, Core Web Vitals, ou "otimizar para IA/LLM" |

**Not required** for: internal admin panels, authenticated-only dashboards, CLIs, backend services with no rendered HTML, mobile-only apps with no web surface.

---

## Technical SEO Checklist

- `robots.txt` present, answering `200`, not blocking pages that should be indexed, and pointing to the sitemap — status-code semantics and group matching in `references/ai-crawlers.md`
- `robots.txt` only controls crawling — a disallowed URL can still be indexed from links. Use `noindex` (meta or `X-Robots-Tag`) to keep a page out, and authentication for anything private
- `sitemap.xml` generated (static or dynamic), includes all indexable routes, excludes noindex/private routes — limits and `lastmod` rules in `references/sitemap-rules.md`
- Canonical URL (`<link rel="canonical">`) on every page — prevents duplicate-content splitting
- A logical heading hierarchy (`h1` → `h2` → `h3`, no skipped levels). One `<h1>` per page is a convention, not a Google requirement — an `ISSUE` at most
- `hreflang` tags when the project serves more than one locale — rules in `references/hreflang.md`
- HTTPS enforced, no mixed content
- Clean, descriptive URLs (no query-string-only routing for canonical content, no unnecessary IDs)
- 404s return real `404` status, not `200` with a "not found" page (soft 404)
- Redirects use `301` for permanent moves, never chained more than one hop
- **Pagination** — Google has ignored `rel="next"`/`rel="prev"` since 2019. Each paginated page links to the next through a crawlable `<a href>` and carries a self-referencing canonical; never canonical page N to page 1. Infinite scroll needs paginated URLs behind it (also what keeps it reachable for agents)
- **Mobile-first parity** — the mobile rendering carries the same main content, title, robots meta, structured data and internal links as desktop; Google indexes the mobile version. Flag intrusive interstitials that cover the main content

### JavaScript rendering

- `title`, meta description, `canonical`, robots meta and JSON-LD belong in the **initial server HTML**. A canonical in the raw HTML that differs from the one JS injects is ambiguous, and Google may pick either
- A `noindex` in the raw HTML can stick even when JS later removes it — Google may skip rendering a page it was told not to index
- Non-`200` responses are not rendered, so a client-side "not found" view on a `200` is a soft 404
- Links must be `<a href>` elements; links that exist only as click handlers are not crawled
- Dynamic rendering (serving bots a different pre-rendered copy) is a workaround Google no longer recommends — prefer SSR, static generation, or hydration

## On-Page SEO Checklist

- `<title>` unique per page, about 50–60 characters (*heuristic* — truncation is by pixel width), primary keyword near the front
- Meta description unique per page, about 140–160 characters (*heuristic* — truncation is by pixel width, not character count), includes a reason to click, does not repeat the title, and is not one site-wide template with only the product name swapped
- Image `alt` text descriptive (not keyword-stuffed), decorative images use `alt=""`
- Internal linking uses descriptive anchor text, not "click here"
- Content answers the query in the first 1–2 sentences before elaborating (also serves GEO — see below)
- Editorial pages show who wrote them, how, and why (E-E-A-T), and match the page type the query's results already favour — checks in `references/content-quality.md`
- Open Graph (`og:title`, `og:description`, `og:image`, `og:url`) and Twitter Card tags present for shareable pages
- **Share preview check** — verify those tags in the HTML served to the `facebookexternalhit` crawler, not just in source. Procedure: `references/share-preview-check.md`

## Off-Page Signals (advisory, not gated)

- Structured internal linking supports topic authority — flag orphaned pages with no inbound internal links, and two pages targeting the same primary query (cannibalization — see `references/content-quality.md`)
- Flag broken outbound links found during review
- Backlink strategy, PR, and external outreach are outside this agent's scope — note when the user should involve marketing/growth, don't attempt to execute them

---

## Core Web Vitals

Thresholds (Good / Needs improvement / Poor bands), the FID→INP change and the generic image and resource fixes live in `skills/architecture/performance-budgets/SKILL.md` — load it for the numbers. What is specific to the SEO verdict:

- A page passes when the **75th percentile of field data** (real users, CrUX or RUM) is in the Good band. Lab numbers (Lighthouse) are diagnostics, not the verdict — say which one a finding is based on
- **LCP breaks into four subparts** — time to first byte, resource load delay, resource load duration, element render delay. Name the dominant one; the fix differs for each

Fixes beyond performance-budgets:
- The LCP image is never `loading="lazy"` and must be discoverable in the initial HTML (not set from JS or a CSS background)
- Non-LCP images: `decoding="async"`, or `aspect-ratio` when dimensions are unknown
- Web fonts: `font-display: swap` can itself shift layout when the fallback's metrics differ — prefer `optional`, or a fallback tuned with `size-adjust`/`ascent-override`
- Defer non-critical JS, break up long tasks (INP), avoid render-blocking CSS, reserve space for late-inserted banners and embeds (CLS)

---

## Structured Data (schema.org / JSON-LD)

Emit as `<script type="application/ld+json">`. Pick the type that matches the page's real content — never mark up content that isn't visible to the user (Google Rich Results Test and other engines penalize mismatches). Which types still earn a rich result, and what replaced the retired ones: `references/schema-status.md`.

| Page type | Schema type | Key fields |
|---|---|---|
| Homepage / brand | `Organization` | `name`, `url`, `logo`, `sameAs` (social profiles) |
| Landing / service page | `Service` or `WebPage` | `name`, `description`, `provider` |
| Product page | `Product` | `name`, `image`, `description`, `offers` (`price`, `priceCurrency`, `availability`), `aggregateRating` if reviews exist — merchant-listing fields in `references/schema-ecommerce-local.md` |
| Blog post / article | `Article` or `BlogPosting` | `headline`, `author`, `datePublished`, `dateModified`, `image` |
| FAQ section | `FAQPage` | `mainEntity` array of `Question`/`Answer` pairs — only for content genuinely visible as Q&A. **No rich result** outside well-known government and health sites since 2023; use it for machine readability only, never promise a SERP feature. User-submitted Q&A is `QAPage` |
| Navigation trail | `BreadcrumbList` | ordered `itemListElement` matching the visible breadcrumb |
| Local business | `LocalBusiness` (most specific subtype) | `address` or `areaServed`, `openingHours`, `telephone` — rules in `references/schema-ecommerce-local.md` |

**JSON-LD lint** — check every block before reporting `PASS`:
- `@context` is `https://schema.org`; every node has an `@type`; `@graph` members are objects
- URLs are absolute; dates and durations are ISO 8601; prices are numbers without a currency symbol
- No placeholder text (`TODO`, `Lorem ipsum`, `example.com`, `[Name]`) and no retired type
- No invented, self-serving or incentivised reviews — rules in `references/schema-ecommerce-local.md` § Reviews and ratings

Validate with structured-data testing tools before shipping when the project has one configured; otherwise flag as "unverified, spot-check recommended."

---

## GEO — SEO for LLMs / AI Search (Generative Engine Optimization)

Search is increasingly answered by AI systems (chat assistants, AI Overviews, agentic browsers) that read and cite pages rather than only ranking them. **Google's position is that optimizing for its AI features is ordinary SEO**: a page must be indexed and eligible for a snippet to appear in AI Overviews, there is no separate AI index, and no special markup or file is required. The controls are the usual ones — `nosnippet`, `data-nosnippet`, `max-snippet`, `noindex`. The practices below make content easier to extract and cite correctly, for Google and for other systems:

- **`llms.txt`** (optional) — a Markdown index of the site's key pages at the root, per llmstxt.org: an `#` title on the first line, a `>` one-paragraph summary, `##` sections of Markdown links with a one-line description each. Google states it does not use it, and no ranking or citation weight is documented; it helps coding agents reading developer docs and some non-Google tools. Never report its absence as a blocker. Keep it accurate — a stale `llms.txt` misdirects, and it must be served as text, not an HTML soft-404.
- **Answer-first structure** — state the direct answer to the likely query in the first sentence or two of a section, then elaborate. LLMs extract from the top of a block; burying the answer under preamble reduces citation accuracy.
- **Self-contained sections** — each `h2`/`h3` section should make sense read in isolation (LLMs often extract a section, not the whole page). Avoid "as mentioned above" references that only work in full-page context.
- **Explicit entities** — name the product, company, or concept by its full name near the top of the page instead of relying on pronouns or implied context established elsewhere.
- **Clean semantic HTML** — proper `<article>`, `<section>`, heading hierarchy, and lists (`<ul>`/`<ol>`) over div-soup; extraction quality tracks markup quality.
- **Structured data doubles as GEO signal** — the same JSON-LD that helps traditional search also gives LLM crawlers unambiguous facts (price, author, date) instead of forcing them to infer from prose.
- **Avoid content gated behind JS-only rendering** — rules in § JavaScript rendering above; the raw-HTML check for crawlers that do not run JavaScript is in `references/agent-readiness.md`.
- **`robots.txt` AI-crawler directives** — training crawlers, search/citation crawlers and user-triggered fetchers are **separate tokens**: blocking a training bot does not remove a site from AI answers, and blocking a search bot does. Ask the user for their policy; never block by default. Token list and robots.txt mechanics: `references/ai-crawlers.md`.
- **Agent readiness** — agentic browsers act through the accessibility tree, so the same native controls and accessible names that serve screen readers serve agents. Checks: `references/agent-readiness.md`.

---

## Quality Gate Output Format

Use this exact structure when reporting an SEO review (see `agents/seo-specialist.md` for when it is mandatory vs. advisory):

```
## SEO Quality Gate

### Technical SEO
[PASS / ISSUE / BLOCKER] — [finding]

### On-Page SEO
[PASS / ISSUE / BLOCKER] — [finding]

### Core Web Vitals
[PASS / ISSUE / BLOCKER] — [finding, with measured value if available]

### Structured Data
[PASS / ISSUE / BLOCKER] — [finding]

### GEO / LLM Readiness
[PASS / ISSUE / BLOCKER] — [finding]

### Verdict
[APPROVED / APPROVED WITH NOTES / BLOCKED]
```

`BLOCKER` = missing sitemap, `robots.txt` blocking indexable pages or answering a persistent `5xx`/`429`, missing canonical on a duplicated route, broken structured data, LCP/INP/CLS in the "Poor" band **on field data** (a lab-only Poor reading is an `ISSUE` marked "lab"), a soft-404, an indexable page whose title, canonical, robots meta or main content exists only after JavaScript runs **and** is also missing from the rendered output (confirmed in a rendering test), a generator about to publish near-identical pages that fail the swap test in `references/content-quality.md`, or a shareable page answering `403`/`429` to the `facebookexternalhit` crawler while a regular browser User-Agent gets `200` (see `references/share-preview-check.md`). Everything else non-passing is `ISSUE`. `BLOCKED` verdict when any `BLOCKER` is present.
