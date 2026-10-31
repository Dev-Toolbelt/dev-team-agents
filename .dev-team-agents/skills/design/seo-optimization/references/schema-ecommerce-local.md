# Structured Data — E-commerce and Local

Load when a page carries `Product`/`Offer`, a cart or checkout, a physical location, or a service area. Sources: Google Search Central product (merchant listing, product snippet) and local business documentation.

**Getting into AI answers.** Products and business details reach Google's AI responses through [Merchant Center](https://merchants.google.com/) feeds and a [Google Business Profile](https://business.google.com/), per the [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide). Markup below earns rich results; it is not a separate AI channel. When a store or location has neither, recommend them as an `ISSUE`; confirming they exist needs the user, not the code.

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
- AI-generated product images should carry the IPTC digital source type `trainedAlgorithmicMedia` in their metadata ([Google image metadata docs](https://developers.google.com/search/docs/appearance/structured-data/image-license-metadata))

## Local business

| Rule | Detail |
|---|---|
| Specific subtype | `Dentist`, `LegalService`, `Restaurant`… — not bare `LocalBusiness` when a subtype fits. `Attorney` is deprecated in favour of `LegalService` |
| Storefront vs service area | A business customers visit gets `address`; a service-area business (comes to the customer) uses `areaServed` and omits the street address it hides from its Business Profile |
| NAP consistency | Name, address and phone are identical across visible HTML, JSON-LD and the Google Business Profile |
| `geo` | Latitude/longitude with at least 5 decimal places |
| One location, one page | Each location has its own URL and a stable `@id`; a multi-location brand links them from the `Organization` with `department` or `subOrganization` |
| `openingHoursSpecification` | Matches the hours shown on the page, special hours included |

## Reviews and ratings

- Self-serving reviews (a business marking up ratings of itself on its own `LocalBusiness` or `Organization`) are not eligible for review snippets
- Review gating — asking only satisfied customers for reviews — violates Google's policy; flag any flow that filters who is asked
- Ratings must come from real users and be visible on the page; never mark up a competitor's product rating on a comparison page

## Location pages at scale

A page per city that differs only in the city name is a doorway page. Apply the swap test in `content-quality.md` § Scaled and programmatic pages; each page needs content specific to that location (address, staff, hours, local proof). Severity follows the skill's gate.
