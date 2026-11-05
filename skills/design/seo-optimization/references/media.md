# Images and Video

Load when images are central to the page (galleries, product images), or the page has a `<video>`, an embedded player, `VideoObject` markup, or an image or video sitemap. Sources: Google Search Central — [image SEO](https://developers.google.com/search/docs/appearance/google-images), [video SEO](https://developers.google.com/search/docs/appearance/video), [video structured data](https://developers.google.com/search/docs/appearance/structured-data/video) (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

`alt` basics, lazy-loading and the LCP image are in SKILL.md § On-Page SEO Checklist and § Core Web Vitals; sitemap extension tags in `sitemap-rules.md` § Extensions; compression and formats for speed in `skills/architecture/performance-budgets/SKILL.md`.

## Images

| Check | What to report |
|---|---|
| Discoverable | Images meant to rank set as CSS backgrounds (Google doesn't index CSS images); `<picture>`/`srcset` without a fallback `src` |
| Supported format | Formats outside BMP, GIF, JPEG, PNG, WebP, SVG, AVIF; a file extension that doesn't match the file type |
| `alt` text | Missing, generic or keyword-stuffed on content images — Google calls it the most important image attribute |
| File name | Generic names (`IMG00023.JPG`, `image1.jpg`) instead of short descriptive ones |
| Context | The image far from text that describes it; no caption where one would help |
| Stable URL | The same image under a different URL on each page or build (cache-busting query per request) |
| Representative image | No `og:image`, `primaryImageOfPage` or `mainEntity` image, or a logo/text image used as it |
| Discovery | Images Google is unlikely to find (JS galleries, CDN hosts) not in an image sitemap — image sitemaps may list URLs on other domains |

AI-generated images: IPTC metadata rule in `schema-ecommerce-local.md`.

## Video

A **watch page** is a page whose main purpose is one video (a landing or episode page). A blog post that reviews an embedded video is not one. The watch page itself must be indexed before its video is.

| Check | What to report |
|---|---|
| Embedded in HTML | Video not in `<video>`, `<embed>`, `<iframe>` or `<object>`; loaded only after a click; behind a URL fragment; hidden behind other elements |
| JS-injected player | The player missing from the rendered HTML (URL Inspection) |
| Thumbnail | Missing, under 60×30 px, unsupported format (same list as images), or blocked by `robots.txt` or login |
| Video file | `contentUrl` not fetchable at a stable URL, or a data URL — needed for previews and key moments |
| Unique metadata | `name`, `description` or `thumbnailUrl` repeated across videos |

### `VideoObject`

| Required | Recommended |
|---|---|
| `name`, `thumbnailUrl`, `uploadDate` (ISO 8601; a time zone is recommended) | `contentUrl` (preferred) or `embedUrl`, `description`, `duration`, `expires`, `hasPart`, `interactionStatistic` (not `interactionCount`), `regionsAllowed` / `ineligibleRegion` |

Markup must match the visible video and the video sitemap.

### Key moments and live

| Feature | Markup | Notes |
|---|---|---|
| Your own chapters | `Clip` with `name`, `startOffset`, `url` (same path + time parameter); `endOffset` recommended | All Search languages |
| Automatic chapters | `SeekToAction` with `potentialAction.target` containing `{seek_to_second_number}` and `startOffset-input` | Limited language list; Google must fetch the file |
| LIVE badge | `BroadcastEvent` via `publication` with `isLiveBroadcast: true`, `startDate`, `endDate` | Indexing API is permitted here (`sitemap-rules.md` § Discovery) |
| Opt out of key moments | `nosnippet` | Also removes snippets (`search-appearance.md`) |

To remove a video: `404` or `noindex` on the watch page, or an `expires` / `<video:expiration_date>` in the past — never on videos that are not expiring. Monitor with the Video indexing and Video rich result reports in Search Console.
