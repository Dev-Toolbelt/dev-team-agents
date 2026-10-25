# hreflang

Load when the site serves more than one language or region. Source: Google Search Central, "Tell Google about localized versions of your page".

## Rules

| Rule | Detail |
|---|---|
| Return tags | If page A lists B as an alternate, B must list A. A missing return tag makes that pair ignored — the most common failure |
| Self-reference | Each page lists itself among its alternates (recommended) |
| Canonical only | Alternates point at canonical URLs; a page whose canonical points elsewhere should not carry hreflang |
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

## Related

- Search Console's International Targeting report (country targeting) was retired in 2022 — hreflang, ccTLDs and on-page signals are what remain
- Do not redirect users automatically by IP or `Accept-Language` without a way back; crawlers come mostly from the US and would never see the other versions
- Translated pages need translated `title`, meta description and structured data, not only body text
