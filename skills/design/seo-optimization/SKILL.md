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
| `robots.txt` edited; a `robots.txt` finding (a page blocked, a `5xx`/`429` answer, an AI-crawler rule); or the user states a policy on AI crawling/training | `references/ai-crawlers.md` |
| Editorial content (blog, guides, comparisons, location or programmatic pages) | `references/content-quality.md` |
| The site expects AI agents or agentic browsers to act on it, or content may be JS-only | `references/agent-readiness.md` |
| A shareable page (Open Graph tags) | `references/share-preview-check.md` |
| Canonicals, `noindex`, redirects, status codes, URL parameters or faceted navigation; a site move; a CDN/WAF in front of the site | `references/crawl-index-control.md` |
| Diagnosing lost visibility or indexing gaps; server logs or Search Console data available; post-launch monitoring; a Core Web Vitals finding on field data; choosing a testing tool | `references/monitoring.md` |
| A JS framework or meta-framework (Next, Nuxt, SvelteKit, Astro, Remix/React Router, Angular, Vue/React SPA) or client-side routing | `references/framework-recipes.md` |
| Affiliate/sponsored links, UGC (comments, forums, reviews), bot- or user-agent-specific serving, a hacked-site or Security issues report, an expired/acquired domain | `references/spam-security.md` |
| Title, meta description, snippet controls (`nosnippet`, `max-*`, `data-nosnippet`), favicon or `<head>`/layout templates edited; a title or snippet finding; Discover traffic | `references/search-appearance.md` |
| Images central to the page (galleries, product images), `<video>`, embedded players, `VideoObject`, image or video sitemaps | `references/media.md` |

## Detection Signals — When SEO Is Required

A project counts as "needs SEO" when any of these hold. Use this table to decide whether `seo-specialist` must be spawned, not just invited.

| Signal type | Examples |
|---|---|
| Project category | Institutional/marketing site, landing page, e-commerce/online store, blog, documentation portal, portfolio — any surface meant to be found via search or cited by an AI answer |
| File presence | `sitemap.xml`, `robots.txt`, `next-seo.config.*`, `astro.config.*` with `site:` set, `gatsby-config.js`, CMS content directories (`content/`, `posts/`, `blog/`) |
| Route shape | Product detail pages, category/listing pages, checkout funnel entry pages, blog post routes, `/blog/`, `/produtos/`, `/p/` |
| Dependency signals | `next-seo`, `react-helmet`, `vue-meta`, `schema-dts`, `astro-seo`, sitemap generator packages |
| Explicit request | User mentions SEO, ranking, Google, meta tags, structured data, sitemap, Core Web Vitals, or "otimizar para IA/LLM" |

**Not required** for: internal admin panels, authenticated-only dashboards, CLIs, backend services with no rendered HTML, mobile-only apps with no web surface.

## Audit Procedure

Run the steps in order; each feeds § Quality Gate Output Format. Never require network APIs or API keys — work from the repo, build output and local fetches. Steps that need Search Console (URL Inspection, Page indexing, Core Web Vitals report) are run by the user: list them as actions for the user instead of running them.

| # | Step | Evidence to collect | Gate section |
|---|---|---|---|
| 1 | **Scope** | Pages and templates in scope: one sample page per template, max 20 pages (*heuristic*); for a diff, the changed routes | — |
| 2 | **Crawl & index** | `robots.txt` content and status, status code per page, canonical, robots meta / `X-Robots-Tag`, sitemap presence and coverage | Crawl & Index |
| 3 | **Rendering** | Raw HTML (dev server + `curl`) vs rendered HTML (build output for SSG/SSR; a headless browser only if already installed); what exists only after JS | Technical SEO |
| 4 | **On-page** | Title, meta description, headings, `alt`, internal links, share-preview tags | On-Page SEO |
| 5 | **Structured data** | Every JSON-LD block (rendered DOM), its type, lint result | Structured Data |
| 6 | **Core Web Vitals** | Field data (CrUX/RUM/Search Console) if the user supplies it; else lab numbers marked `lab` | Core Web Vitals |
| 7 | **Content** | Authorship, intent match, duplicate/scaled pages, spam signals | Content |
| 8 | **AI search** | Snippet eligibility, AI-crawler rules, raw-HTML content | AI Search |
| 9 | **Share preview** | Tags and status served to `facebookexternalhit` | On-Page SEO |

Which reference each step loads is decided by § Conditional References alone.

---

## Technical SEO Checklist

- `robots.txt` present, answering `200`, not blocking pages that should be indexed, and pointing to the sitemap — status-code semantics and group matching in `references/ai-crawlers.md`
- `robots.txt` controls crawling, not indexing — keeping a page out (`noindex`, why it can't sit behind a Disallow): `references/crawl-index-control.md` § noindex
- `sitemap.xml` generated (static or dynamic), includes all indexable routes, excludes noindex/private routes — limits and `lastmod` rules in `references/sitemap-rules.md`
- Canonical URL (`<link rel="canonical">`) on every page — prevents duplicate-content splitting. Canonical, `noindex`, host-variant and parameter rules in `references/crawl-index-control.md`
- `robots.txt` never blocks the CSS, JS or images a page needs to render — Google renders pages and judges the rendered result
- A logical heading hierarchy (`h1` → `h2` → `h3`; no skipped levels is a *heuristic* accessibility convention, not a Google requirement). One `<h1>` per page is a convention, not a Google requirement, so its absence is never a gate condition
- `hreflang` tags when the project serves more than one locale — rules in `references/hreflang.md`
- HTTPS enforced, no mixed content
- Clean, descriptive URLs (no query-string-only routing for canonical content, no unnecessary IDs)
- 404s return real `404` status, not `200` with a "not found" page (soft 404)
- Redirects, maintenance responses and site moves — `references/crawl-index-control.md` § Redirects, § Status codes
- **Site architecture** — every indexable page is reachable through crawlable internal links (not only the sitemap or search); key pages within about 3 clicks of the homepage (*heuristic*); URL paths mirror the topic hierarchy where the site has one
- **Crawl budget** is a finding only on large or fast-changing sites — threshold and causes in `references/crawl-index-control.md`
- **Pagination** — Google has ignored `rel="next"`/`rel="prev"` since 2019. Each paginated page links to the next through a crawlable `<a href>` and carries a self-referencing canonical; never canonical page N to page 1. Infinite scroll needs paginated URLs behind it (also what keeps it reachable for agents)
- **Mobile-first parity** — the mobile rendering carries the same main content, title, robots meta, structured data and internal links as desktop; Google indexes the mobile version. Flag intrusive interstitials that cover the main content

### JavaScript rendering

- `title`, meta description, `canonical` and robots meta belong in the **initial server HTML**. JSON-LD is preferred there too, but JS-injected JSON-LD is processed by Google (`references/schema-status.md` § Authoring rules). A canonical in the raw HTML that differs from the one JS injects is ambiguous, and Google may pick either
- A `noindex` in the raw HTML can stick even when JS later removes it — Google may skip rendering a page it was told not to index
- Non-`200` responses are not rendered, so a client-side "not found" view on a `200` is a soft 404
- Links must be `<a href>` elements; links that exist only as click handlers are not crawled
- Lazy-loaded content must load when it enters the viewport (`loading="lazy"`, IntersectionObserver) — never only on scroll events, clicks or other interaction, which Googlebot does not perform
- Dynamic rendering (serving bots a different pre-rendered copy) is a workaround Google no longer recommends — prefer SSR, static generation, or hydration

## On-Page SEO Checklist

- `<title>` unique per page, about 50–60 characters (*heuristic* — truncation is by pixel width), primary keyword near the front
- Meta description unique per page, about 140–160 characters (*heuristic* — truncation is by pixel width, not character count), includes a reason to click, does not repeat the title, and is not one site-wide template with only the product name swapped
- Image `alt` text descriptive (not keyword-stuffed), decorative images use `alt=""`
- **Image SEO** — discoverability (`<img>`, not CSS backgrounds), formats, file names, stable URLs and image sitemaps: `references/media.md`. Compression: `skills/architecture/performance-budgets/SKILL.md`
- Internal linking uses descriptive anchor text, not "click here"
- Content answers the query early, before elaborating — for the reader, not as an AI technique (see § AI Search)
- Editorial pages show who wrote them, how, and why (E-E-A-T), and match the page type the query's results already favour — checks in `references/content-quality.md`
- **Share preview** — required tags, and their check in the HTML served to the `facebookexternalhit` crawler: `references/share-preview-check.md`

## Off-Page Signals (advisory, not gated)

- Structured internal linking supports topic authority — flag orphaned pages with no inbound internal links, and two pages targeting the same primary query (cannibalization — see `references/content-quality.md`)
- Flag broken outbound links found during review
- Backlink strategy, PR, and external outreach are outside this agent's scope — note when the user should involve marketing/growth, don't attempt to execute them

---

## Core Web Vitals

Thresholds (Good / Needs improvement / Poor bands), the FID→INP change and the generic image and resource fixes live in `skills/architecture/performance-budgets/SKILL.md` — load it for the numbers. What is specific to the SEO verdict:

- A page passes when the **75th percentile of field data** (real users, CrUX or RUM) is in the Good band. Lab numbers (Lighthouse) are diagnostics, not the verdict — say which one a finding is based on
- Field-data caveats (SPAs, soft navigations, lab TBT, the metric set): `references/monitoring.md` § Core Web Vitals data
- **LCP breaks into four subparts** — time to first byte, resource load delay, resource load duration, element render delay. Name the dominant one; the fix differs for each

Fixes beyond performance-budgets:
- The LCP image is never `loading="lazy"` and must be discoverable in the initial HTML (not set from JS or a CSS background)
- Non-LCP images: `decoding="async"`, or `aspect-ratio` when dimensions are unknown
- Web fonts: `font-display: swap` can itself shift layout when the fallback's metrics differ — prefer `optional`, or a fallback tuned with `size-adjust`/`ascent-override`
- Defer non-critical JS, break up long tasks (INP), avoid render-blocking CSS, reserve space for late-inserted banners and embeds (CLS)

---

## Structured Data (schema.org / JSON-LD)

Emit as `<script type="application/ld+json">`. Pick the type that matches the page's real content — never mark up content that isn't visible to readers: markup that doesn't match the visible content may not be shown as a rich result or can lead to a manual action ([structured data general guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies), as last verified 2026-11-04). Which types still earn a rich result (HowTo and FAQPage earn none), what replaced the retired ones, `@id` linking, safe JSON-LD insertion and JavaScript-injected markup: `references/schema-status.md`.

| Page type | Schema type | Key fields |
|---|---|---|
| Homepage / brand | `Organization` | `name`, `url`, `logo`, `sameAs` (social profiles) |
| Landing / service page | `Service` or `WebPage` | `name`, `description`, `provider` |
| Product page | `Product` | `name`, `image`, `description`, `offers` (`price`, `priceCurrency`, `availability`), `aggregateRating` if reviews exist — merchant-listing fields in `references/schema-ecommerce-local.md` |
| Blog post / article | `Article` or `BlogPosting` | `headline`, `author`, `datePublished`, `dateModified`, `image` |
| FAQ section | `FAQPage` (optional) | `mainEntity` array of `Question`/`Answer` pairs — only for content genuinely visible as Q&A. No Google rich result — status in `references/schema-status.md` |
| Navigation trail | `BreadcrumbList` | ordered `itemListElement` matching the visible breadcrumb |
| Local business | `LocalBusiness` (most specific subtype) | `address` or `areaServed`, `openingHours`, `telephone` — rules in `references/schema-ecommerce-local.md` |

**JSON-LD lint** — check every block before reporting `PASS`:
- `@context` is `https://schema.org`; every node has an `@type`; `@graph` members are objects
- URLs are absolute; dates and durations are ISO 8601; prices are numbers without a currency symbol
- No placeholder text (`TODO`, `Lorem ipsum`, `example.com`, `[Name]`) and no retired type
- No invented, self-serving or incentivised reviews — rules in `references/schema-ecommerce-local.md` § Reviews and ratings

Validate before shipping; tools and retired-type caveats in `references/schema-status.md`. Without a validation run, mark the finding `unverified`.

---

## AI Search — AEO / GEO

Search is increasingly answered by AI features (AI Overviews, AI Mode, chat assistants, agentic browsers) that retrieve pages and cite them. **Google treats AEO and GEO as names for ordinary SEO**: its AI features are grounded in the Search index through the same ranking and quality systems, and expand a query into related queries (*query fan-out*) to retrieve more pages. Source: [Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) (updated 2026-07-10, as last verified 2026-11-04). Judge any third-party AEO/GEO advice against that guide.

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

**Rejected third-party claims** — common in published SEO and GEO skills and tools, with no primary source. Beyond the rows above, never import one as a rule, a target or a finding:

| Claim | Why it is rejected |
|---|---|
| A 0–100 "GEO", "AI visibility", "citability" or "quality" score, or a pass mark on one | No search engine publishes such a score; a tool's number is its own model (§ Measuring) |
| Citation-uplift percentages for adding statistics, quotes or fixed-length passages | Lab results on synthetic engines, not measurements of any search engine; the passages are chunking (above) |
| Minimum word counts, readability targets (Flesch bands) or "unique content %" per page type | Google sets no length or readability rule; judge helpfulness (`references/content-quality.md`) |

### Measuring

- Use the **generative AI performance report** in Search Console ([help](https://support.google.com/webmasters/answer/16984139)) for AI features in Search and Discover — it is the only source of Google AI visibility data
- No third-party tool has access to Google's internal ranking or AI systems ([third-party SEO tools](https://developers.google.com/search/docs/fundamentals/third-party-seo)). Treat a tool that claims it, or promises AI placement, as unverified, and never cite its numbers as a finding
- Before attributing a drop in Search or AI visibility, follow `references/monitoring.md` § Diagnosing drops — data anomalies, the post-update wait, a search-type split and the export row limits

---

## Quality Gate Output Format

Use this exact structure when reporting an SEO review (see `agents/seo-specialist.md` for when it is mandatory vs. advisory). The steps that produce each section are in § Audit Procedure.

```
## SEO Quality Gate

### Technical SEO
<finding lines>

### Crawl & Index
<finding lines>

### On-Page SEO
<finding lines>

### Content
<finding lines>

### Core Web Vitals
<finding lines>

### Structured Data
<finding lines>

### AI Search (AEO / GEO)
<finding lines>

### Actions for the user
<Search Console, validator or log checks the agent could not run — one per `unverified` finding, naming the URL and what to look for>

### Verdict
[APPROVED / APPROVED WITH NOTES / BLOCKED]
```

Each finding is one line:

`[BLOCKER|ISSUE|PASS] [evidence] <location: URL or path:line> — <finding> → <fix> · impact: high|med|low · effort: S|M|L`

- **`PASS` lines** carry only the tag, evidence, location and finding — no fix, impact or effort
- **Order** — within each section, `BLOCKER` first, then by impact (high → low)
- **Section** — each Audit Procedure step names its gate section; robots.txt, status codes, canonical, `noindex` and sitemap findings go under Crawl & Index, never Technical SEO
- **Stack-specific fixes** — take the fix wording from `references/framework-recipes.md` when the stack is listed there

**Evidence tags** — every finding carries exactly one:

| Tag | Meaning |
|---|---|
| `field` | Real-user data: CrUX, RUM, Search Console |
| `lab` | Synthetic measurement: Lighthouse, PSI lab, local profiling |
| `rendered` | Checked in the rendered HTML/DOM |
| `raw` | Checked in the raw server response before JavaScript |
| `inferred` | Read from code or config, not observed in a response |
| `unverified` | Needs a check the agent could not run (Search Console, a validator, a verified-bot log) — list the step for the user |

**Severity.** `BLOCKER` = `robots.txt` blocking indexable pages or answering a persistent `5xx`/`429`, a sitewide or template-level `noindex` on pages meant to be indexed (see `references/crawl-index-control.md` § noindex), missing canonical on a duplicated route, broken structured data, LCP/INP/CLS in the "Poor" band **on field data** (a lab-only Poor reading is an `ISSUE` tagged `lab`), a soft-404, an indexable page whose title, canonical, robots meta or main content exists only after JavaScript runs **and** is also missing from the rendered output (confirmed in a rendering test), a generator about to publish near-identical pages that fail the swap test in `references/content-quality.md`, a shareable page answering `403`/`429` to the `facebookexternalhit` crawler while a regular browser User-Agent gets `200` (see `references/share-preview-check.md`), or a **verified** Googlebot receiving `403`/`429` or a challenge page on indexable pages — observed in Search Console or logs filtered to verified IPs, never a User-Agent-only test (see `references/crawl-index-control.md` § CDN, WAF and bot protection).

A missing sitemap is a `BLOCKER` only on a large site (more than about 500 pages, Google's threshold — [sitemaps overview](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview), as last verified 2026-11-04) or a site whose pages are not reachable through internal links; otherwise it is an `ISSUE`.

Everything else non-passing is `ISSUE` — except the absence of a practice listed in § AI Search › Not needed for Google, which is never a finding. `BLOCKED` verdict when any `BLOCKER` is present.
