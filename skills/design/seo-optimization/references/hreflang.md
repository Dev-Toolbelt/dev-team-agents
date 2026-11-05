# International Sites and hreflang

Load when the site serves more than one language or region. Sources: Google Search Central — [localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions), [consolidate duplicate URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [managing multi-regional and multilingual sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites), [locale-adaptive pages](https://developers.google.com/search/docs/specialty/international/locale-adaptive-pages) (as last verified 2026-11-04).

## Site structure

Each locale gets its own URL. Google lists these options:

| Structure | Example | Trade-offs |
|---|---|---|
| Country-code TLD | `example.de` | Clear geotargeting, server location irrelevant, easy to separate; costly or unavailable, more infrastructure, registry rules, one country per domain |
| Subdomain on a gTLD | `de.example.com` | Quick to set up, can use other servers, easy to separate; the URL alone may not tell users whether `de` is a language or a country |
| Subdirectory on a gTLD | `example.com/de/` | Quick to set up, low upkeep on one host; locale may be unclear from the URL, one server location, harder to separate |
| URL parameter | `example.com?loc=de` | Not recommended by Google — hard to segment, locale unclear |

- Choosing among the first three is a business decision, not a finding; a parameter-only locale scheme is a finding
- Link every locale version to the others with crawlable links (a language or region selector) on every page

### Locale-adaptive pages

Serving different content on one URL by IP or `Accept-Language` (locale-adaptive) is risky: Googlebot does not send `Accept-Language`, and crawls mostly from US IP addresses (some from outside the US), so it may never see the other versions. Google recommends separate URLs per locale with `hreflang` instead. Do not redirect users automatically by IP or language without a way back.

## Rules

| Rule | Detail |
|---|---|
| Return tags | If page A lists B as an alternate, B must list A. A missing return tag makes that pair ignored — the most common failure |
| Self-reference | Each page lists itself among its alternates (recommended) |
| Canonical only | Alternates point at canonical URLs; a page whose canonical points elsewhere should not carry hreflang |
| Canonical per locale | Each locale page is its own canonical, or points to a page in the same language (the best substitute language when none exists). Never canonicalize a translated page to another language version |
| Canonical inside the set | The canonical URL should be one of the URLs in the hreflang set — Google prefers URLs that are part of an hreflang cluster when choosing a canonical |
| Translated main content | Localized versions count as duplicates when the main content is untranslated — do not create a locale page that only swaps the navigation or template |
| `x-default` | One per set, for the language-selector or fallback page |
| Absolute URLs | Always, with protocol |
| One method per URL set | HTML `<link rel="alternate" hreflang>`, an HTTP `Link:` header (for PDFs and non-HTML), or sitemap `xhtml:link` — mixing methods is allowed but invites contradictions |

## Codes

Format: `language[-Script][-REGION]`.

| Part | Standard | Example |
|---|---|---|
| Language | ISO 639-1, two letters | `pt`, `en`, `zh` |
| Script (optional) | ISO 15924 | `zh-Hant` |
| Region (optional) | ISO 3166-1 alpha-2 | `pt-BR`, `en-GB` |

## Common errors

| Wrong | Why | Right |
|---|---|---|
| `en-uk` | `UK` is not an ISO 3166-1 code | `en-GB` |
| `jp` | Country code used as language | `ja` (or `ja-JP`) |
| `eng` | Three-letter ISO 639-2 | `en` |
| `es-LA`, `en-EU` | Not a country | No region code covers a group of countries — list each (`es-MX`, `es-AR`…) or use the bare language `es` |
| `BR` alone | Region without language | `pt-BR` |

## Next.js (App Router)

Next.js docs, `generateMetadata`, updated 2026-08-19 (as last verified 2026-11-04):

- `metadata.alternates.languages` renders one `<link rel="alternate" hreflang>` per entry and nothing else — the docs show no automatic entry for the current page, so list the current locale explicitly (and `x-default` if used)
- Metadata merges shallowly across segments, so set `canonical` and `languages` together in the same segment (`framework-recipes.md`, Next.js row)

## Related

- Search Console's International Targeting report (country targeting) was retired in 2022 — hreflang, ccTLDs and on-page signals are what remain
- Translated pages need translated `title`, meta description and structured data, not only body text
