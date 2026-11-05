# Monitoring and Diagnostics

Load when the task is diagnosing lost visibility, indexing gaps or crawl problems, when server logs or Search Console data are available, or when setting up SEO monitoring after launch. Sources: Google Search Console Help ([Page indexing](https://support.google.com/webmasters/answer/7440203), [URL Inspection](https://support.google.com/webmasters/answer/9012289), [Crawl Stats](https://support.google.com/webmasters/answer/9679690)), [Bing Webmaster Tools](https://www.bing.com/webmasters/help) and the [Bing Webmaster Guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a) (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

Code alone does not show what a crawler actually gets. A finding based on logs or Search Console says so; a finding inferred from code is marked "inferred".

## Testing tools

Which tool answers what, and who can run it (as last verified 2026-11-04). The evidence tag follows from the tool: Search Console and CrUX are `field`, Lighthouse is `lab`, a rendered fetch is `rendered`.

| Tool | Question it answers | Needs | Who runs it |
|---|---|---|---|
| [URL Inspection](https://support.google.com/webmasters/answer/9012289) (Search Console) | Is the URL indexed? Which canonical did Google choose? What does a live Googlebot fetch render? Is it blocked? | Network, Search Console login, verified property | User; share the result |
| [Rich Results Test](https://search.google.com/test/rich-results) | Which rich results the rendered page (smartphone or desktop) or a pasted snippet is eligible for, and errors in live types | Network, no login; a URL test needs the page publicly reachable (fetched as Google-InspectionTool) — use code input for unpublished pages | Agent with a browser tool, or user |
| [Schema Markup Validator](https://validator.schema.org/) | Is the JSON-LD valid schema.org, including types Google no longer reports (`schema-status.md`) | Network, no login | Agent with a browser tool, or user |
| Lighthouse / [PageSpeed Insights](https://pagespeed.web.dev/) | Lab diagnostics (LCP subparts, long tasks, layout shifts); PSI also shows CrUX field data for the URL or origin when there is enough traffic | Lighthouse: local Chrome, runs against a dev server. PSI: network, public URL; the PSI API takes an API key | Agent (Lighthouse CLI); PSI agent or user |
| CrUX — [CrUX Vis](https://cruxvis.withgoogle.com/), [CrUX API](https://developer.chrome.com/docs/crux/api), BigQuery | Field Core Web Vitals at p75 for a URL or origin, and trends | CrUX Vis: network, no login. CrUX API: a Google Cloud API key. BigQuery: a Google Cloud project | Agent with network (API only with a key the user supplies); otherwise user |
| [Search Console](https://search.google.com/search-console) reports | Page indexing, Crawl Stats, Core Web Vitals, rich-result reports, Manual actions, Security issues, Performance (§ Search Console) | Network, login, verified property | User; exports shared with the agent |
| [Bing Webmaster Tools](https://www.bing.com/webmasters/) | Bing's indexing, crawl and URL-inspection data | Network, login, verified site | User |

- Never sign in, or ask for credentials, on the user's behalf; ask the user to run login-only tools and share the output
- When no tool could run (offline, no access), tag the finding `unverified` and name the tool the user should run

## Search Console

| Report | Use it to |
|---|---|
| Page indexing | Find why URLs are not indexed — *Crawled/Discovered – currently not indexed*, *Duplicate without user-selected canonical*, *Alternate page with proper canonical*, *Soft 404*, *Blocked by robots.txt*, *Excluded by noindex* |
| URL Inspection | Compare the indexed version with a live test: rendered HTML, canonical Google chose vs the one declared, crawl status, mobile rendering |
| Crawl Stats | Requests per day, response codes, average response time and host status (`robots.txt` fetch, DNS, connectivity) — the evidence for crawl-budget or server-health findings |
| Sitemaps | Submitted URLs and fetch errors; indexed status via Page indexing filtered by sitemap |
| Core Web Vitals | Field data grouped by URL pattern (see SKILL.md § Core Web Vitals) |
| Rich results / enhancements | Structured-data errors per type |
| Generative AI performance | AI features in Search and Discover (SKILL.md § AI Search › Measuring) |
| Manual actions, Security issues | Must be empty; report anything here ahead of every other finding |

- A Google-selected canonical that differs from the declared one means conflicting signals — check internal links, sitemap and redirects (`crawl-index-control.md` § Canonical rules)
- Bing Webmaster Tools offers the equivalent reports for Bing, whose index is also used by some third-party search products; set it up alongside Search Console

## Server log analysis

Logs show every request crawlers make; Search Console reports aggregates. Filter to **verified** crawler IPs (`crawl-index-control.md` § CDN, WAF and bot protection) — User-Agent alone includes impostors.

| Question | What to extract |
|---|---|
| Is crawl spent on the right pages? | Share of crawler hits on indexable URLs vs parameter, faceted, redirected or erroring URLs |
| Are important pages crawled? | Indexable URLs with no crawler hit over 30 days (*heuristic*) |
| Is the server healthy for bots? | Share of `5xx`, `429` and slow responses served to crawlers, by time of day |
| Are redirects and errors leaking? | Top `3xx` sources still linked internally; top `404` URLs with inbound links |
| Which AI crawlers fetch the site? | Hits per token in `ai-crawlers.md` — confirm `robots.txt` policy matches reality |

When the CDN terminates requests, take logs from the CDN, not the origin — the origin never sees what the edge blocked or served from cache.

## Errors to watch

- `4xx`: fix internal links to `404`s; redirect removed URLs that still have backlinks or traffic to their closest equivalent
- `5xx` and timeouts: any sustained rise is urgent — Google slows crawling within days and later drops URLs
- Soft 404s and sudden drops in indexed pages usually follow a deploy (template `noindex`, broken canonical, JS-only content) — check recent changes first

## Core Web Vitals data

Thresholds live in `skills/architecture/performance-budgets/SKILL.md`. Points below (as last verified 2026-11-04).

| Point | What it means for a finding |
|---|---|
| The set is LCP, INP, CLS ([web.dev](https://web.dev/articles/vitals)) | No other metric is in the program, and none is named as a candidate. A tool reporting a "new" or "2.0" Core Web Vital is wrong |
| Soft navigations: enabled by default from Chrome 151 ([Chrome](https://developer.chrome.com/docs/web-platform/soft-navigations-experiment)) | The stable CrUX metrics are unchanged. Soft-navigation variants (`experimental_*_with_softnavs`) are in BigQuery and the CrUX API only, with graduation planned for May 2027. Search Console moves to them only after graduation ([web.dev](https://web.dev/blog/crux-experimental-soft-navs/)) |
| SPA caveat | Until graduation, an SPA's Search Console and stable CrUX figures mostly reflect the first page load. Say this in the finding, and use the experimental variants or RUM for route changes |
| CrUX Dashboard (Looker Studio) deprecated; October 2025 was its last dataset ([CrUX release notes](https://developer.chrome.com/docs/crux/release-notes)) | Use CrUX Vis, the CrUX API or BigQuery. Never cite dashboard data newer than that |
| In Search Console, use the Core Web Vitals and HTTPS reports ([page experience](https://developers.google.com/search/docs/appearance/page-experience)) | Field data grouped by URL pattern. This is the field-data source for the verdict |
| PSI mobile CPU throttling changed on 2024-12-05 ([PSI release notes](https://developers.google.com/speed/docs/insights/release_notes)) | Mobile lab TBT runs higher after that date. Never compare mobile lab TBT across it, and never call the jump a regression. Field data and desktop are unaffected |

## Diagnosing drops

Sources: [core updates](https://developers.google.com/search/docs/appearance/core-updates), [debugging traffic drops](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops), [data anomalies](https://support.google.com/webmasters/answer/6211453), [Search Analytics API data](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data).

**Rule out non-causes first:**
- Check the Data anomalies page. A logging error can look like a drop
- After a core update, wait at least a full week after the rollout completes. Then compare that week with the week before the rollout started. Otherwise compare equal periods (previous period or year over year), and check 16 months for seasonality
- Split by search type (Web, Image, Video, News). A drop in one type has a different cause than a drop across all of them
- Check Crawl Stats, Page indexing, Manual actions and Security issues. Sitewide technical faults show up fast; a page-level `noindex` shows up slowly
- Never recommend deleting content in bulk after an update. Google treats deletion as a last resort for content that can't be salvaged

**Decay and cannibalization from Search Console exports:**
- Work on **query + page** pairs. A page-only total mixes queries, and query-level data is aggregated per property, not per page
- Apply a minimum-traffic floor before calling a percentage drop. A fall from 4 clicks to 1 is noise (floor and thresholds are *heuristic*)
- Cannibalization signal: two or more URLs of the same site sharing impressions for one query, with the ranking URL flipping over time. This is a lead to review, not proof
- The API exposes at most **50K rows per day per search type**, sorted by clicks, and may drop some rows when grouping by page or query. A URL or query missing from an export is not proof that it lost ranking. Confirm it with a filtered query or URL Inspection

## Monitoring setup

Recommend, after launch: Search Console and Bing Webmaster Tools verified for the canonical host, sitemaps submitted, email alerts on, and an uptime/status check on key templates and `robots.txt`. Third-party crawlers (site audits) are diagnostics; their scores are never a finding on their own. No third-party tool sees Google's ranking data (SKILL.md § AI Search › Measuring), so label rank-tracking and "AI visibility" numbers as estimates.

## Analytics (advisory)

In GA4, the [Landing page report](https://support.google.com/analytics/answer/12931766) (Reports › Engagement › Landing page) compared or filtered by the [Session default channel group](https://support.google.com/analytics/answer/9756891) `Organic Search` shows how organic visitors engage and convert per landing page; Google's definition of that channel includes clicks from AI Overviews and AI Mode (as last verified 2026-11-04). Use it to pick pages to review after a drop or a launch. It is advisory: analytics numbers are never a gate finding on their own, and clicks and impressions come from Search Console.
