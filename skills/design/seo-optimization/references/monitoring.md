# Monitoring and Diagnostics

Load when the task is diagnosing lost visibility, indexing gaps or crawl problems, when server logs or Search Console data are available, or when setting up SEO monitoring after launch. Sources: Google Search Console Help ([Page indexing](https://support.google.com/webmasters/answer/7440203), [URL Inspection](https://support.google.com/webmasters/answer/9012289), [Crawl Stats](https://support.google.com/webmasters/answer/9679690)) and [Bing Webmaster Tools](https://www.bing.com/webmasters/help).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

Code alone does not show what a crawler actually gets. A finding based on logs or Search Console says so; a finding inferred from code is marked "inferred".

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

## Monitoring setup

Recommend, after launch: Search Console and Bing Webmaster verified for the canonical host, sitemaps submitted, email alerts on, and an uptime/status check on key templates and `robots.txt`. Third-party crawlers (site audits) are diagnostics; their scores are never a finding on their own.
