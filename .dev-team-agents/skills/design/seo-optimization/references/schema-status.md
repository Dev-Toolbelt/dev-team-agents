# Structured Data — Rich Result Status

Which schema.org types still earn a Google rich result. Markup without a rich result is still valid and still feeds other consumers (Bing, AI systems, knowledge graphs) — the finding is about the promise, not the markup. Re-check [Google's search gallery](https://developers.google.com/search/docs/appearance/structured-data/search-gallery) and the [Search Central documentation updates log](https://developers.google.com/search/updates) before reporting a status as current; this table changes and its dates are as last verified.

## Restricted or retired

| Type | Status | Since | Use instead / note |
|---|---|---|---|
| `HowTo` | No rich result | 2023-09 | Ordered list in visible content; keep markup only for machine readability |
| `FAQPage` | Rich result only for well-known government and health sites | 2023-08 | Visible Q&A in `<h2>`/`<h3>` + answer; never promise a FAQ snippet |
| Sitelinks search box (`WebSite` + `SearchAction`) | Feature removed; markup has no Google effect | 2024-11 | Nothing — harmless to keep |
| `BreadcrumbList` | Mobile results show only the domain; the trail remains on desktop | 2025-01 | Keep — it still informs the URL display and site structure |
| `ClaimReview`, `EstimatedSalary`, `LearningVideo`, `CourseInfo`, `VehicleListing`, `SpecialAnnouncement`, Book Actions | Rich result phased out (one Search Central announcement) | 2025-06 | `Course` list markup still works; `VideoObject` for video; otherwise ordinary page content |
| `Dataset` | Feeds Dataset Search only, not web results | — | Keep for dataset pages |

## Choosing between similar types

| Situation | Type |
|---|---|
| Questions written by the site, one answer each | `FAQPage` |
| A question users answer, several answers, votes | `QAPage` |
| Editorial article or news | `Article` / `NewsArticle` / `BlogPosting` |
| A list of products or items on a roundup page | `ItemList` of `ListItem` |

## Reporting

- Retired type present → report "no rich result; keep only if another consumer needs it"
- Markup that contradicts visible content, or an invalid block → broken structured data in the skill's gate
- A type whose status you could not confirm → state "status unverified" in the finding
