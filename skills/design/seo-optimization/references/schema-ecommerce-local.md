# Structured Data — E-commerce and Local

Load when a page carries `Product`/`Offer`, a cart or checkout, a physical location, or a service area. Sources: Google Search Central product (merchant listing, product snippet) and local business documentation, and the [ecommerce guide](https://developers.google.com/search/docs/specialty/ecommerce) (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

**Getting into AI answers.** Products and business details reach Google's AI responses through [Merchant Center](https://merchants.google.com/) feeds and a [Google Business Profile](https://business.google.com/), per the [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide). Markup below earns rich results; it is not a separate AI channel. When a store or location has neither, recommend them as a finding; confirming they exist needs the user, not the code.

## Product and Offer

| Field | Rule |
|---|---|
| `offers` | One `Offer` per purchasable variant on a product page; `AggregateOffer` is for pages listing several sellers, and does not qualify for merchant listings |
| `price` | Number greater than zero, no currency symbol or thousands separator (`"1299.90"`) |
| `priceCurrency` | ISO 4217 code (`BRL`, `USD`) |
| `availability` | Full schema.org URL (`https://schema.org/InStock`), matching what the page shows |
| Identifier | `gtin` (8/12/13/14), `mpn` + `brand`, or `sku` — at least one, matching the visible product |
| `shippingDetails`, `hasMerchantReturnPolicy` | Recommended for merchant listings; may be set once at the organization level instead |
| `aggregateRating` / `review` | Only reviews collected for this product and visible on the page |
| Variants | `ProductGroup` with `hasVariant` and `variesBy` when one page carries sizes or colours |

- Price and availability in markup must equal the rendered page, including after a JS price update — a mismatch can get listings disapproved
- AI-generated product titles and descriptions go in Merchant Center's `structured_title` / `structured_description` with `digital_source_type` set to `trained_algorithmic_media` ([AI-generated content](https://support.google.com/merchants/answer/14743464)). If a feed sends both `title` and `structured_title`, only `title` is used ([title](https://support.google.com/merchants/answer/6324415)) — AI text left in plain `title` is unlabelled
- Variant URLs: each variant gets its own URL (path segment or query parameter); with optional variant parameters the URL without them is canonical, and variant pages carry a canonical to the product URL ([URL structure](https://developers.google.com/search/docs/specialty/ecommerce/designing-a-url-structure-for-ecommerce-sites))
- AI-generated product images should carry the IPTC digital source type `trainedAlgorithmicMedia` in their metadata ([Google image metadata docs](https://developers.google.com/search/docs/appearance/structured-data/image-license-metadata))

## Availability and removed products

Sources: [launching an ecommerce site](https://developers.google.com/search/docs/specialty/ecommerce/how-to-launch-an-ecommerce-website), [site moves](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes), [schema.org `ItemAvailability`](https://schema.org/ItemAvailability) (as last verified 2026-11-04).

| Situation | Handling |
|---|---|
| Temporarily out of stock | Keep the page on `200` and indexable; set `availability` to `https://schema.org/OutOfStock` (or `BackOrder`, `PreOrder` when true) and show it on the page; send the same state to Merchant Center. Never disable add-to-cart as the way to stop purchases — mark the product out of stock |
| Permanently gone, a close replacement exists | `301` to the closest equivalent (successor model, same product in a new URL) |
| Permanently gone, no equivalent | `404` or `410`. A page kept live for support or reference uses `availability` `https://schema.org/Discontinued` |
| Many removed products | Never redirect them all to the homepage or one category — Google may treat that as a soft 404 (`crawl-index-control.md` § Redirects) |

## Category pages

Source: [ecommerce site structure](https://developers.google.com/search/docs/specialty/ecommerce/help-google-understand-your-ecommerce-site-structure), [URL structure](https://developers.google.com/search/docs/specialty/ecommerce/designing-a-url-structure-for-ecommerce-sites) (as last verified 2026-11-04).

- A crawlable path runs menu → category → subcategory → product, with `<a href>` links; a category that does not link to all its products leaves some to the sitemap or feed
- Link to every product meant to be indexed; link best sellers from prominent pages to signal importance
- Paginated listings: one URL per page — SKILL.md § Technical SEO Checklist › Pagination
- An empty category: `404` if the site removes it from browse, otherwise `noindex` while it has no items
- Filter and sort URLs: `crawl-index-control.md` § URL parameters and faceted navigation

## Local business

| Rule | Detail |
|---|---|
| Specific subtype | `Dentist`, `LegalService`, `Restaurant`… — not bare `LocalBusiness` when a subtype fits. `Attorney` is deprecated in favour of `LegalService` ([schema.org](https://schema.org/Attorney)) (as last verified 2026-11-04) |
| Storefront vs service area | A business customers visit gets `address`; a service-area business (comes to the customer) uses `areaServed` and omits the street address it hides from its Business Profile |
| NAP consistency | Name, address and phone are identical across visible HTML, JSON-LD and the Google Business Profile |
| `geo` | Latitude/longitude with at least 5 decimal places |
| One location, one page | Each location has its own URL and a stable `@id`; a multi-location brand links them from the `Organization` with `department` or `subOrganization` |
| `openingHoursSpecification` | Matches the hours shown on the page, special hours included |

## Reviews and ratings

- Self-serving reviews (a business marking up ratings of itself on its own `LocalBusiness` or `Organization`) are not eligible for review snippets
- Review gating — asking only satisfied customers for reviews — violates Google's policy; flag any flow that filters who is asked
- Ratings must come from real users and be visible on the page; never mark up a competitor's product rating on a comparison page
- Never copy, scrape or aggregate reviews or ratings from other sites into `aggregateRating` — ratings are sourced directly from users
- Fake reviews, and incentivized reviews (money, discounts, free products) without clear and prominent disclosure, must not appear on the page or in markup ([review snippet guidelines](https://developers.google.com/search/docs/appearance/structured-data/review-snippet), added 2026-07-24) (as last verified 2026-11-04)

## Location pages at scale

A page per city that differs only in the city name is a doorway page. Apply the swap test in `content-quality.md` § Scaled and programmatic pages; each page needs content specific to that location (address, staff, hours, local proof).
