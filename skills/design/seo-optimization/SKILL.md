---
name: seo-optimization
description: Technical/on-page SEO, Core Web Vitals, structured data, AI search (AEO/GEO), gate signals.
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
| Canonicals, `noindex`, redirects, status codes, URL parameters or faceted navigation; a site move; a CDN/WAF in front of the site | `references/crawl-index-control.md` |
| Diagnosing lost visibility or indexing gaps; server logs or Search Console data available; post-launch monitoring | `references/monitoring.md` |

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
- Canonical URL (`<link rel="canonical">`) on every page — prevents duplicate-content splitting. Canonical, `noindex`, host-variant and parameter rules in `references/crawl-index-control.md`
- `robots.txt` never blocks the CSS, JS or images a page needs to render — Google renders pages and judges the rendered result
- A logical heading hierarchy (`h1` → `h2` → `h3`, no skipped levels). One `<h1>` per page is a convention, not a Google requirement — an `ISSUE` at most
- `hreflang` tags when the project serves more than one locale — rules in `references/hreflang.md`
- HTTPS enforced, no mixed content
- Clean, descriptive URLs (no query-string-only routing for canonical content, no unnecessary IDs)
- 404s return real `404` status, not `200` with a "not found" page (soft 404)
- Redirects use `301`/`308` for permanent moves, never chained more than one hop; `503` with `Retry-After` for maintenance — redirect, status-code and site-move rules in `references/crawl-index-control.md`
- **Site architecture** — every indexable page is reachable through crawlable internal links (not only the sitemap or search); key pages within about 3 clicks of the homepage (*heuristic*); URL paths mirror the topic hierarchy where the site has one
- **Crawl budget** is a finding only on large or fast-changing sites — threshold and causes in `references/crawl-index-control.md`
- **Pagination** — Google has ignored `rel="next"`/`rel="prev"` since 2019. Each paginated page links to the next through a crawlable `<a href>` and carries a self-referencing canonical; never canonical page N to page 1. Infinite scroll needs paginated URLs behind it (also what keeps it reachable for agents)
- **Mobile-first parity** — the mobile rendering carries the same main content, title, robots meta, structured data and internal links as desktop; Google indexes the mobile version. Flag intrusive interstitials that cover the main content

### JavaScript rendering

- `title`, meta description, `canonical`, robots meta and JSON-LD belong in the **initial server HTML**. A canonical in the raw HTML that differs from the one JS injects is ambiguous, and Google may pick either
- A `noindex` in the raw HTML can stick even when JS later removes it — Google may skip rendering a page it was told not to index
- Non-`200` responses are not rendered, so a client-side "not found" view on a `200` is a soft 404
- Links must be `<a href>` elements; links that exist only as click handlers are not crawled
- Lazy-loaded content must load when it enters the viewport (`loading="lazy"`, IntersectionObserver) — never only on scroll events, clicks or other interaction, which Googlebot does not perform
- Dynamic rendering (serving bots a different pre-rendered copy) is a workaround Google no longer recommends — prefer SSR, static generation, or hydration

## On-Page SEO Checklist

- `<title>` unique per page, about 50–60 characters (*heuristic* — truncation is by pixel width), primary keyword near the front
- Meta description unique per page, about 140–160 characters (*heuristic* — truncation is by pixel width, not character count), includes a reason to click, does not repeat the title, and is not one site-wide template with only the product name swapped
- Image `alt` text descriptive (not keyword-stuffed), decorative images use `alt=""`
- **Image SEO** — images meant to rank are `<img>` elements (not CSS backgrounds), with descriptive file names, stable URLs, responsive `srcset`, and listed in an image sitemap when discovery is hard (`references/sitemap-rules.md`). Compression and formats: `skills/architecture/performance-budgets/SKILL.md`
- Internal linking uses descriptive anchor text, not "click here"
- Content answers the query early, before elaborating — for the reader, not as an AI technique (see § AI Search)
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

## AI Search — AEO / GEO

Search is increasingly answered by AI features (AI Overviews, AI Mode, chat assistants, agentic browsers) that retrieve pages and cite them. **Google treats AEO and GEO as names for ordinary SEO**: its AI features are grounded in the Search index through the same ranking and quality systems, and expand a query into related queries (*query fan-out*) to retrieve more pages. Source: [Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) (updated 2026-07-14). Judge any third-party AEO/GEO advice against that guide.

### Eligibility

- The page is indexed and eligible to appear in Search **with a snippet** — `noindex`, `nosnippet` and `max-snippet:0` remove it from AI features; `data-nosnippet` excludes a passage
- The site is included in the generative AI features of Search in Search Console ([settings help](https://support.google.com/webmasters/answer/16908024)) — confirm with the user; it is not visible from the code
- Content is crawlable, publicly accessible and passes the § Technical SEO Checklist — meeting every requirement still does not guarantee crawling, indexing or an AI appearance, so never promise one

### What works

The same practices that serve readers serve AI features — report them as SEO, not as AI tricks:

- **Unique, people-first content** — first-hand experience and expertise a model could not produce by summarising existing pages. Checks in `references/content-quality.md`
- **Clear organisation** — paragraphs, sections and descriptive headings; answer the reader's question early, and name the product, company or concept in full near the top. These help readers and non-Google systems; Google states it needs no special writing style
- **Semantic HTML** — `<article>`, `<section>`, heading hierarchy, real lists. Preferred, not required to be perfect; it also serves assistive technology and agents
- **Images and video** that follow image and video SEO guidance
- **Page experience** — renders on every device, low latency, main content easy to tell apart from the rest; duplicate content kept low
- **JavaScript** that follows § JavaScript rendering — Google renders unblocked JS; the raw-HTML check for crawlers that do not run it is in `references/agent-readiness.md`
- **Merchant and local data** through Merchant Center feeds and a Google Business Profile — `references/schema-ecommerce-local.md`
- **`robots.txt` AI-crawler directives** for non-Google operators — training, search and user-triggered bots are separate tokens; never block by default. `references/ai-crawlers.md`
- **Agent readiness** — `references/agent-readiness.md`

### Not needed for Google

Google's guide names these as unnecessary for its AI features. Never recommend one as a Search improvement, and never raise its absence as an `ISSUE` or `BLOCKER`:

| Practice | Google's position |
|---|---|
| `llms.txt` or any other "AI file" | Not used by Search; neither helps nor hurts. It may still serve coding agents and non-Google tools — optional, per llmstxt.org (`#` title, `>` summary, `##` link sections), kept accurate and served as text, never an HTML soft-404 |
| Chunking pages into short blocks | Not needed; there is no ideal page length — size pages for the audience |
| Rewriting content in an "AI style" or for every keyword variant | Not needed; the systems understand synonyms and intent |
| AI-specific structured data | None exists, and structured data is not required for AI features. Keep it for rich results (§ Structured Data) |

**Counterproductive** — the guide also names two tactics that work against a site. Their *presence* is a finding: an `ISSUE`, or the swap-test `BLOCKER` in § Quality Gate Output Format for a page generator:

- Pages generated for each query variation or fan-out query — scaled content abuse (`references/content-quality.md`)
- Seeking inauthentic mentions — blocked by spam systems; ranking rests on content quality

### Measuring

- Use the **generative AI performance report** in Search Console ([help](https://support.google.com/webmasters/answer/16984139)) for AI features in Search and Discover — it is the only source of Google AI visibility data
- No third-party tool has access to Google's internal ranking or AI systems. Treat a tool that claims it, or promises AI placement, as unverified, and never cite its numbers as a finding

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

### AI Search (AEO / GEO)
[PASS / ISSUE / BLOCKER] — [finding]

### Verdict
[APPROVED / APPROVED WITH NOTES / BLOCKED]
```

`BLOCKER` = missing sitemap, `robots.txt` blocking indexable pages or answering a persistent `5xx`/`429`, a sitewide or template-level `noindex` on pages meant to be indexed (see `references/crawl-index-control.md` § noindex), missing canonical on a duplicated route, broken structured data, LCP/INP/CLS in the "Poor" band **on field data** (a lab-only Poor reading is an `ISSUE` marked "lab"), a soft-404, an indexable page whose title, canonical, robots meta or main content exists only after JavaScript runs **and** is also missing from the rendered output (confirmed in a rendering test), a generator about to publish near-identical pages that fail the swap test in `references/content-quality.md`, a shareable page answering `403`/`429` to the `facebookexternalhit` crawler while a regular browser User-Agent gets `200` (see `references/share-preview-check.md`), or a **verified** Googlebot receiving `403`/`429` or a challenge page on indexable pages — observed in Search Console or logs filtered to verified IPs, never a User-Agent-only test (see `references/crawl-index-control.md` § CDN, WAF and bot protection). Everything else non-passing is `ISSUE` — except the absence of a practice listed in § AI Search › Not needed for Google, which is never a finding. `BLOCKED` verdict when any `BLOCKER` is present.
