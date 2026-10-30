# Crawl and Index Control

Load when canonicals, `noindex`, redirects, status codes, URL parameters or faceted navigation are added or reviewed, when a site moves or changes URLs, or when a CDN/WAF sits in front of the site. Sources: Google Search Central — [crawl budget](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget), [faceted navigation](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation), [canonicalization](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [redirects](https://developers.google.com/search/docs/crawling-indexing/301-redirects), [site moves](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes), [HTTP status codes](https://developers.google.com/search/docs/crawling-indexing/http-network-errors), [verifying Googlebot](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

## Crawl budget

- Matters only for large or fast-changing sites — Google's guide targets roughly 1M+ unique pages whose content changes about weekly, or 10k+ pages whose content changes daily, or a large share of URLs stuck in *Discovered – currently not indexed*. Below that, never raise crawl budget as a finding
- What wastes it: faceted and parameter URL spaces, session IDs in URLs, soft 404s, long redirect chains, infinite calendars or spaces, slow or erroring responses
- `crawl-delay` in `robots.txt` is ignored by Googlebot. Google lowers its crawl rate on its own when the server answers `500`/`503`/`429` — use that for a temporary emergency only, never as standing configuration
- Evidence for a crawl-budget finding comes from logs or Search Console's Crawl Stats report (`monitoring.md`), not from guessing

## URL parameters and faceted navigation

Search Console's URL Parameters tool was retired in 2022 — never recommend it. Handle parameter URLs on the site itself:

| Parameter kind | Handling |
|---|---|
| Tracking (`utm_*`, `gclid`, session IDs) | Canonical to the clean URL; never link internally with them |
| Sort, view, page size | Canonical to the default variant; keep out of the sitemap |
| Facet combinations with no search demand | Disallow the pattern in `robots.txt`, or keep filter state in a URL fragment (`#`), which Google does not crawl as a separate URL. Filters rendered without crawlable `<a href>` (e.g. a form) are a common implementation of the same intent |
| Facets with real search demand (e.g. category + brand) | A stable, clean URL with unique content, self-canonical, linked and in the sitemap |

- Keep parameter order and casing consistent, and answer `404` for meaningless combinations (empty results) instead of `200`
- `robots.txt` disallow and `noindex` do not combine: a disallowed URL is never fetched, so its `noindex` is never seen

## noindex

Use `noindex` (meta robots or `X-Robots-Tag`) on pages that are crawlable but add no search value:

- Internal site-search results, thin tag/archive pages, filter results without demand, thank-you and confirmation pages, staging copies
- A page must be **crawlable** for `noindex` to work — never disallow it in `robots.txt` as well
- Never combine `noindex` with a `rel="canonical"` to another URL — the signals conflict; pick one
- A sitewide or template-level `noindex` on indexable pages (a leftover from staging) removes them from Search — confirm the pages are meant to be indexed, then report it — the gate lists it as a `BLOCKER`

## Canonical rules

- One `rel="canonical"` per page; prefer an absolute URL in the `<head>` of the server HTML (relative and JS-injected canonicals are accepted but discouraged) (or an HTTP `Link` header for non-HTML files such as PDFs)
- Self-referencing on the canonical version itself
- The target answers `200`, is indexable, and is not redirected, `noindex` or disallowed
- Canonical is a hint, not a directive — internal links, the sitemap, redirects and hreflang must all point at the same URL, or Google may pick another

## Duplicate URL consolidation

Every page resolves to one host and one form. Pick the canonical form and `301` every other variant to it:

| Variant | Example |
|---|---|
| Protocol | `http://` → `https://` |
| Host | `www.` vs bare domain |
| Trailing slash | `/page` vs `/page/` |
| Case | `/Page` vs `/page` (paths are case-sensitive) |
| Index files | `/index.html` → `/` |

Printer-friendly, AMP and syndicated copies carry a canonical to the original.

## Redirects

| Code | Use | Search effect |
|---|---|---|
| `301` / `308` | Permanent move | Strong signal the target becomes canonical |
| `302` / `307` | Temporary (A/B test, maintenance detour, geolocation) | Weak signal; the source usually stays canonical. A long-lived `302` for a permanent move is a finding |
| Meta refresh `0s` / JS redirect | Only when server redirects are impossible | Followed, but slower and less reliable |

- One hop: no chains (`A → B → C`) and no loops; update internal links to the final URL
- Redirect each old URL to its closest equivalent — mass-redirecting removed pages to the homepage is treated as a soft 404
- Keep migration redirects for at least one year (Google's guidance); longer while the old URLs still get traffic or links

### Site moves and URL changes

Map every old URL to its new URL before launch, ship `301`s on cut-over, update canonicals, internal links, hreflang and sitemaps to the new URLs, keep the old sitemap briefly so the redirects get crawled, and use Search Console's Change of Address tool for a domain or subdomain move (both properties verified). A migration without a URL map is a finding.

## Status codes

| Situation | Answer |
|---|---|
| Page does not exist | `404` |
| Page removed for good, no replacement | `410` — Google treats it like `404`; use it to signal the removal is intentional |
| Planned maintenance or overload | `503` with `Retry-After` — never `200` with a maintenance page (soft 404) and never `500` |
| Rate limiting a crawler | `429` or `503`; prolonged use drops URLs from the index |
| Persistent `5xx` | Google reduces crawling, then drops the URLs — on `robots.txt` this is a gate condition (see the Quality Gate) |

## CDN, WAF and bot protection

Bot-protection rules (rate limits, JS challenges, CAPTCHA pages, country blocks) often answer crawlers with `403`, `429` or a challenge page on `200`.

- Fetch an indexable page with Googlebot's User-Agent and with a browser User-Agent and compare status and body. A challenge page served on `200` to a **verified** crawler is a soft 404; seen only in a User-Agent test, it falls under the unverified rule below
- **Verify Googlebot** before allowlisting or reporting: reverse DNS of the IP resolves to `googlebot.com` (Google's special crawlers use `google.com`, user-triggered fetchers `googleusercontent.com` — neither is Googlebot), and the forward lookup returns the same IP — or match it against Google's published crawler IP ranges. Never allowlist by User-Agent alone; it is trivially spoofed
- Your own fetch never comes from Google's IPs, so it cannot be verified. Verified evidence comes from Search Console (URL Inspection live test, Crawl Stats) or from CDN/origin logs filtered to verified IPs (`monitoring.md`)
- A **verified** Googlebot receiving `403`/`429` or a challenge on indexable pages — the gate lists it as a `BLOCKER`; a User-Agent-only test is an `ISSUE` marked "unverified"
- Caching: support conditional requests (`ETag` / `Last-Modified` → `304 Not Modified`) so recrawls are cheap; never cache a `5xx` or a challenge page as the response for crawlers
