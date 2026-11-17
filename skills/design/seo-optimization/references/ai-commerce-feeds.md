# AI Commerce Feeds

Load when a product feed, catalog export or AI shopping surface (Google AI Mode or Gemini checkout, ChatGPT shopping, Perplexity shopping) is built or reviewed. Sources: [Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), Google Merchant Center Help ([UCP checkout](https://support.google.com/merchants/answer/16837055), [UCP onboarding](https://support.google.com/merchants/answer/16992327)), [Google UCP developer docs](https://developers.google.com/merchant/ucp), OpenAI Commerce ([submit product feeds](https://developers.openai.com/commerce/guides/submit-product-feeds), [product feed spec](https://developers.openai.com/commerce/specs/file-upload/products)) and Perplexity's [Shop like a pro announcement](https://www.perplexity.ai/hub/blog/shop-like-a-pro) (as last verified 2026-11-16).

Product and `Offer` field rules for JSON-LD (price format, `availability` URLs, identifiers, variants, out-of-stock handling) live in `schema-ecommerce-local.md` — this file covers the feeds and their parity with that markup.

## Destinations

| Destination | Feed | Eligibility | What it unlocks |
|---|---|---|---|
| Google — Merchant Center | Merchant Center product data | Any merchant with a Merchant Center account | Product data in AI responses and other Search results |
| Google — UCP checkout | The Merchant Center feed, plus the `native_commerce` attribute (`checkout_eligibility`) on each listing | Select merchants only; implementation first, then an interest form, then Merchant Center onboarding with a sandbox. Products eligible in the US, Canada and Australia; the Merchant Center integration rolls out in the US first | A "Buy" button on eligible listings in AI Mode and Gemini; the merchant stays seller of record. Native checkout is the default path, embedded (iframe) checkout is for approved merchants |
| OpenAI — ChatGPT | OpenAI product feed | Business claimed and identity verified in Business Hub (`chatgpt.com/business-hub`) before upload | Product eligibility in ChatGPT search; checkout only with a separately enabled integration |
| Perplexity — Merchant Program | Product specs shared through a signup form | Free; aimed at large retailers; Perplexity contacts the merchant after signup | Per Perplexity, "increased chances" of being a recommended product, Buy with Pro checkout, API access, a dashboard. No ranking formula is published |

Joining any program is the user's business decision: list it as an action for the user, never as a code finding.

## OpenAI product feed

| Point | Rule |
|---|---|
| Format | JSONL (one complete record per line), CSV or TSV; JSON objects inside CSV/TSV cells are serialized as JSON |
| Delivery | Manual upload, a hosted HTTPS URL, or SFTP, configured in the merchant portal. Each delivery is a full snapshot |
| Required fields | `item_id`, `title`, `description`, `url`, `brand`, `seller_name`, `image_url`, `availability`, `price`, `target_countries`, `store_country` |
| `item_id` | Stable across updates |
| `price` | `amount CURRENCY` (`79.99 USD`): decimal point, uppercase ISO 4217 code, no thousands separator, no more decimals than the currency allows, never rounded to a different payable amount |
| `gtin` | 8, 12, 13 or 14 digits with a valid check digit, leading zeros kept, no spaces or dashes. Omitted when the item has none — never invented |
| `is_eligible_search` | Omitted or empty means `true`; `false` also disables checkout |
| `is_eligible_checkout` | Omitted, empty or `false` means disabled. `true` takes effect only when search eligibility is `true` and checkout is enabled for the integration |
| Freshness | No fixed schedule; send current prices and availability, and update when a sale starts or ends or an item sells out or returns. Dates in the feed do not schedule changes |

The feed does not update carts or confirm purchases: the live site checks the current offer when the customer acts.

The OpenAI price format (`79.99 USD`) differs from JSON-LD (`"price": "79.99"` with `priceCurrency`). The generator formats per destination from one value; it never stores two prices.

## Architecture: one catalog generator

One source of product data produces every output. Two code paths that each read price or stock are the defect, whatever their current values.

| Output | Built from |
|---|---|
| PDP JSON-LD (`Product`/`Offer`) | Catalog generator |
| Google Merchant Center feed | Catalog generator |
| OpenAI product feed | Catalog generator |
| Visible PDP (price, stock, URL) | The same catalog read, at render time |

- Regenerate or push the feeds on every price or stock change, not on a fixed nightly schedule alone
- Keep the canonical PDP URL as the feed `url`/`link` — never a tracking or variant-parameter URL the page canonicalises away (`crawl-index-control.md` § URL parameters and faceted navigation)

## Parity check

Primary sources for the parity rule: structured data must be "a true representation of the page content" ([structured data general guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)), and Merchant Center compares the feed price with the landing page and its structured data ([Mismatched price](https://support.google.com/merchants/answer/14916353)) (as last verified 2026-11-16).

Run it as an automated test on a sample of products, and in review on any change to the catalog, PDP template or feed generator.

| Field | Visible page | JSON-LD | Google feed | OpenAI feed |
|---|---|---|---|---|
| Price | Displayed price after JS updates | `offers.price` + `priceCurrency` | price | `price` |
| Availability | Stock message and add-to-cart state | `offers.availability` | availability | `availability` |
| URL | Canonical URL | `url` / `offers.url` | link | `url` |
| GTIN | Shown on page when the product has one | `gtin` | gtin | `gtin` |

| Result | Report |
|---|---|
| All four agree | `PASS`, tagged `rendered` for the page and `inferred` for feeds read from code |
| Feeds come from a different code path than the JSON-LD, values agree today | `ISSUE` — two sources will drift; fix by routing both through the generator |
| Price or availability differs between JSON-LD and the visible page or feed, produced by the same code | Severity per SKILL.md § Quality Gate Output Format |
| Only a feed differs, and it is built outside the repo (platform app, agency export) | `ISSUE`, tagged `unverified`, with the Merchant Center or Business Hub diagnostics as an action for the user |
