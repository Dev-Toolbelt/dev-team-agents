# Crawl and Index Control

Load when canonicals, `noindex`, redirects, status codes, URL parameters or faceted navigation are added or reviewed, when a site moves or changes URLs, or when a CDN/WAF sits in front of the site. Sources: Google Search Central — [crawl budget](https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget), [faceted navigation](https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation), [canonicalization](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [redirects](https://developers.google.com/search/docs/crawling-indexing/301-redirects), [site moves](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes), [changing your hosting](https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes), [HTTP status codes](https://developers.google.com/search/docs/crawling-indexing/http-network-errors), [verifying Googlebot](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

## Crawl budget

- Matters only for large or fast-changing sites — Google's guide targets roughly 1M+ unique pages whose content changes about weekly, or 10k+ pages whose content changes daily, or a large share of URLs stuck in *Discovered – currently not indexed*. Below that, never raise crawl budget as a finding
- What wastes it: faceted and parameter URL spaces, session IDs in URLs, soft 404s, long redirect chains, infinite calendars or spaces, slow or erroring responses
- `crawl-delay` in `robots.txt` is ignored by Googlebot. Google lowers its crawl rate on its own when the server answers `500`/`503`/`429` — use that for a temporary emergency only, never as standing configuration
- Googlebot reads only the first **2 MB** of an HTML or other supported text file, uncompressed (PDF: 64 MB); each CSS, JS or other resource is fetched separately under the same cap, and content past it is not indexed — [Googlebot](https://developers.google.com/search/docs/crawling-indexing/googlebot) (as last verified 2026-11-04). An indexable page whose main content, canonical or structured data sits past 2 MB is a finding. Sitemaps have their own limit (`sitemap-rules.md`)
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
- Pick one control per facet pattern — `robots.txt` `Disallow` and `noindex` do not combine (§ noindex)

## noindex

Use `noindex` (meta robots or `X-Robots-Tag`) on pages that are crawlable but add no search value:

- Internal site-search results, thin tag/archive pages, filter results without demand, thank-you and confirmation pages, staging copies
- A page must be **crawlable** for `noindex` to work: `robots.txt` `Disallow` and `noindex` do not combine, because a disallowed URL is never fetched and its `noindex` is never seen. Never disallow a `noindex` page as well
- Never combine `noindex` with a `rel="canonical"` to another URL — the signals conflict; pick one
- A sitewide or template-level `noindex` on indexable pages (a leftover from staging) removes them from Search — confirm the pages are meant to be indexed, then report it; it is a gate condition in SKILL.md § Quality Gate Output Format

## Canonical rules

- One `rel="canonical"` per page, preferably an absolute URL in the `<head>` of the server HTML. Relative and JS-injected canonicals are accepted but discouraged. Non-HTML files such as PDFs use an HTTP `Link` header instead
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

### HTTPS

Sources: [web.dev — Enabling HTTPS](https://web.dev/articles/enable-https), Search Console [HTTPS report](https://support.google.com/webmasters/answer/11396518) (as last verified 2026-11-04).

- Every `http://` URL answers a `301` to its `https://` equivalent in one hop; canonicals, sitemaps, hreflang and internal links use `https://`
- HSTS (`Strict-Transport-Security` header) only once HTTPS is stable: start with a low `max-age` and raise it gradually — clients hard-fail certificate errors on an HSTS host
- No mixed content: an HTTPS page that loads `http://` scripts, styles, images or frames gets browser warnings or blocked resources
- Search Console's HTTPS report shows how many indexed URLs are HTTP vs HTTPS — the field evidence for this check

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

Map every old URL to its new URL before launch, ship `301`s on cut-over, update canonicals, internal links, hreflang and sitemaps to the new URLs, keep the old sitemap briefly so the redirects get crawled, and use Search Console's Change of Address tool for a domain or subdomain move (both properties verified). Old URLs with no new equivalent answer `404` or `410`. A migration without a URL map is a finding.

### Redesigns and re-platforming (no URL change)

A new design, CMS, framework, host or CDN with the same URLs. Google's [site-move](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes) and [hosting-change](https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes) guides supply the steps marked †; the rest is the comparison that catches template regressions (as last verified 2026-11-04).

- [ ] Staging is kept out of Search with `noindex`, a `robots.txt` `Disallow` or authentication — and every such block is removed at launch †
- [ ] Crawl the old site and the new one with the same crawler and diff per URL: status code, `<title>`, meta description, canonical, robots meta, `hreflang`, structured data, internal links, and main content in the rendered HTML
- [ ] Each new page keeps a self-referencing canonical †; internal links still resolve without redirects
- [ ] Any URL that does change gets a `301` to its closest equivalent and follows § Site moves and URL changes †
- [ ] Before launch, confirm the new firewall or CDN does not block Googlebot (§ CDN, WAF and bot protection) †
- [ ] Change one thing at a time where possible — Google advises moving the domain first, then changing the layout †
- [ ] After launch, watch Search Console Page indexing and Crawl Stats and the server logs (`monitoring.md`) †; a temporary dip in crawl rate right after a hosting move is normal †

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
- **Verify Googlebot** before allowlisting or reporting: reverse DNS of the IP resolves to `googlebot.com` (Google's special crawlers use `google.com`, user-triggered fetchers `googleusercontent.com` or `google.com` — none is Googlebot), and the forward lookup returns the same IP — or match it against Google's published crawler IP ranges. Never allowlist by User-Agent alone; it is trivially spoofed
- Your own fetch never comes from Google's IPs, so it cannot be verified. Verified evidence comes from Search Console (URL Inspection live test, Crawl Stats) or from CDN/origin logs filtered to verified IPs — tools in `monitoring.md` § Testing tools
- A **verified** Googlebot receiving `403`/`429` or a challenge on indexable pages is a gate condition in SKILL.md § Quality Gate Output Format; the same result from a User-Agent-only test is reported with the `unverified` tag
- **Web Bot Auth** (track, not a standard): agents sign requests with HTTP Message Signatures ([RFC 9421](https://datatracker.ietf.org/doc/rfc9421/)) — `tag="web-bot-auth"`, a `Signature-Agent` header pointing at the agent's key directory (`/.well-known/http-message-signatures-directory`). A WAF that verifies it can allowlist signed agents instead of trusting User-Agent. Still an IETF working-group draft — [`draft-ietf-webbotauth-httpsig-protocol`](https://datatracker.ietf.org/doc/draft-ietf-webbotauth-httpsig-protocol/) (as last verified 2026-11-04); its absence is never a finding, and a site publishes a key directory only if it operates an agent. Verified-IP rules for AI operators: `ai-crawlers.md` § Verifying a bot
- Caching: support conditional requests (`ETag` / `Last-Modified` → `304 Not Modified`) so recrawls are cheap; never cache a `5xx` or a challenge page as the response for crawlers
