# Structured Data — Rich Result Status

Load when any JSON-LD is on the page or structured data is being added. Which schema.org types still earn a Google rich result. Markup without a rich result is still valid and still feeds other consumers (Bing, AI systems, knowledge graphs) — the finding is about the promise, not the markup. Google states that using retired types outside Google Search is not affected and that the retirements do not change rankings ([announcement](https://developers.google.com/search/blog/2025/06/simplifying-search-results)). Re-check [Google's search gallery](https://developers.google.com/search/docs/appearance/structured-data/search-gallery) and the [Search Central documentation updates log](https://developers.google.com/search/updates) before reporting a status as current; this table changes (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

## Restricted or retired

| Type | Status | Since | Use instead / note |
|---|---|---|---|
| `HowTo` | No rich result, desktop or mobile | 2023-09 | Ordered list in visible content; keep markup only for machine readability |
| `FAQPage` | No rich result for any site — retired 2026-05-07, docs removed 2026-06-15 | 2026-05 | Visible Q&A in `<h2>`/`<h3>` + answer. Still a valid schema.org type for other consumers; never promise a FAQ snippet |
| Sitelinks search box (`WebSite` + `SearchAction`) | Feature removed; markup has no Google effect | 2024-11 | Nothing — harmless to keep. `WebSite` itself is still used for site names (§ Authoring rules) |
| `BreadcrumbList` | Mobile results show only the domain; the trail remains on desktop | 2025-01 | Keep — it still informs the URL display and site structure |
| `ClaimReview` | No rich result in Search; still supported by Google's Fact Check Explorer | 2025-06 | Keep on fact-check pages that want Fact Check Explorer listing; no Search benefit |
| `EstimatedSalary` | Retired; docs removed 2025-09-09 | 2025-06 | Individual job pages: `JobPosting` with `baseSalary` (the employer's actual salary, not an estimate) |
| `LearningVideo` | Retired; docs removed 2025-09-09 | 2025-06 | `VideoObject` |
| Course Info (single-course detail) | Retired; docs removed 2025-09-09 | 2025-06 | Course list — `Course` items, at least three, with `ItemList` on summary pages |
| `SpecialAnnouncement` | Retired 2025-07-31; docs removed 2025-09-09 | 2025-04 | `Event` for a dated happening; otherwise ordinary `Article` / `WebPage` content |
| `VehicleListing` | Retired; docs removed 2025-09-09 | 2025-06 | Ordinary page content |
| Practice Problem | Retired; docs removed 2026-01-06 | 2025-11 | Ordinary page content |
| `Dataset` | Feeds Dataset Search only, not Google Search results | 2025-11 | Keep for dataset pages |

Replacement types in the last column are the nearest live feature, not a mapping Google publishes — pick one only when the page's visible content fits it.

## Choosing between similar types

| Situation | Type |
|---|---|
| Questions written by the site, one answer each | Visible Q&A headings; `FAQPage` optional — no rich result in Google |
| A question users answer, several answers, votes | `QAPage` |
| Editorial article or news | `Article` / `NewsArticle` / `BlogPosting` |
| An author, creator or "About me" page | `ProfilePage` with `mainEntity` = `Person` (or `Organization`) |
| A list of products or items on a roundup page | `ItemList` of `ListItem` |

## Authoring rules

- **Link entities by `@id`** — give `Organization`, `WebSite`, `Person` and `Article` a stable `@id` URI and reference it (`"author": {"@id": …}`) instead of repeating the object ([JSON-LD 1.1 § Node identifiers](https://www.w3.org/TR/json-ld11/#node-identifiers)); several nodes can share one block through `@graph`. Google's [ProfilePage example](https://developers.google.com/search/docs/appearance/structured-data/profile-page) links an `Article` author to the profile's `mainEntity` this way
- **Author pages** — mark an internal author page as `ProfilePage` + `Person` and point `Article.author.url` at it ([Article](https://developers.google.com/search/docs/appearance/structured-data/article)); add `sameAs` for external profiles
- **Site name** — `WebSite` with `name` and `url` (optional `alternateName`) on the home page of the domain or subdomain ([site names](https://developers.google.com/search/docs/appearance/site-names))
- **Raw-HTML insertion escapes `<`** — JSON-LD written through raw HTML (React `dangerouslySetInnerHTML`, template `|safe`/`raw` filters) with plain `JSON.stringify` is an XSS vector when any value is user-controlled; replace `<` with `\u003c` or use a serializing library ([Next.js JSON-LD guide](https://nextjs.org/docs/app/guides/json-ld))
- **JavaScript-injected JSON-LD counts** — Google processes structured data present in the DOM when it renders the page ([Generate structured data with JavaScript](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript)). Inspect the rendered DOM (Rich Results Test with the URL input, or rendered HTML); never report "no structured data" from an unrendered `curl`/fetch. For `Product` price and availability, server-rendered markup is preferred — the same doc says JS-generated markup can make Shopping crawls less frequent and less reliable

## What to report

- Retired type present → report "no rich result; keep only if another consumer needs it" — never recommend removal as a Search fix
- Rich Results Test and Search Console rich-result reports dropped the six 2025 retirements (`ClaimReview` through `VehicleListing`) on 2025-09-09 and Practice Problem from 2026-01 — never send a user there to validate a retired type, and never read its absence from those reports as an error; use the [Schema Markup Validator](https://validator.schema.org/) for syntax. Other tools: `monitoring.md` § Testing tools
- `FAQPage` recommended as a way to win a Google Search feature → a finding: the FAQ rich result is retired
- Raw-HTML JSON-LD built from user-controlled values without escaping `<` → a security finding
- Markup that contradicts visible content, or an invalid block → broken structured data in the skill's gate
- A type whose status you could not confirm → state "status unverified" in the finding
