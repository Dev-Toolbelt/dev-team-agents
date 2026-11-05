# Framework Recipes

Load when a JavaScript framework or meta-framework is detected (Next.js, Nuxt, SvelteKit, Astro, Remix/React Router, Angular, a Vue or React SPA) or the site uses client-side routing. Sources: Google Search Central — [JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics); each framework's official docs, linked per row (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

What to report for server HTML, canonicals, soft 404s, `noindex` stickiness, `<a href>` links, lazy-loading and blocked bundles is in SKILL.md § JavaScript rendering and § Technical SEO Checklist; this file adds the fixes.

## JavaScript SEO pitfalls

| Pitfall | What to report | Fix |
|---|---|---|
| Routes or views keyed on URL fragments (`/#/products`) | Google does not reliably resolve fragment URLs, so those views are not separate pages | History API routing (`/products`); fragments only for in-page state |
| Client-side route change leaves the previous `<title>` and meta description | Each route the user can land on needs its own title and description — JS may set them | Update title and description per route (the framework head APIs below do this) |
| JS rewrites the canonical to a different URL than the server HTML | SKILL.md § JavaScript rendering | Emit the canonical server-side; if JS sets it, use the same value |
| SPA "not found" view on a `200` (soft 404) | SKILL.md § JavaScript rendering | JS redirect to a URL the server answers with `404`, or add `<meta name="robots" content="noindex">` with JS on the error view |
| Robots.txt disallows JS or CSS bundles | SKILL.md § Technical SEO Checklist | Allow the bundles |
| Long-lived cached bundles without fingerprints | Google's renderer may ignore caching headers and use stale JS/CSS | Content-hashed file names (`main.2bb85551.js`) |
| Content only in shadow DOM with nothing slotted | Google indexes only what is visible in the rendered HTML | Put content in light DOM via `<slot>` |

Rendering a route server-side or at build time (SSR/SSG) avoids most of these and also serves crawlers that do not run JS (`agent-readiness.md`).

## Per-framework recipe

| Framework | Title / meta / head | SSR / SSG | Canonical / robots | Sitemap |
|---|---|---|---|---|
| **Next.js (App Router)** — [metadata](https://nextjs.org/docs/app/getting-started/metadata-and-og-images), [`generateMetadata`](https://nextjs.org/docs/app/api-reference/functions/generate-metadata) | `export const metadata` or `generateMetadata()` in `layout`/`page` — Server Components only; `title.template` for the site-name suffix | Server-rendered by default; dynamic metadata may stream into `<body>` — Next.js says Googlebot reads it, HTML-limited bots get it in `<head>` (`htmlLimitedBots`) | `alternates.canonical` with `metadataBase` in the root layout; `robots: { index, follow, googleBot: {…} }`. Metadata objects merge shallowly — a child's `robots` replaces the parent's | `app/sitemap.ts` returning entries, `generateSitemaps()` to split ([docs](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap)); `app/robots.ts` |
| **Nuxt** — [SEO and meta](https://nuxt.com/docs/4.x/getting-started/seo-meta), [rendering](https://nuxt.com/docs/4.x/guide/concepts/rendering) | `useSeoMeta()` (typed), `useHead()`; `app.head` in `nuxt.config` is static only | Universal rendering by default; `routeRules` `prerender` per route; `nuxt generate` for a fully static site. `ssr: false` gives a client-only page | `useHead({ link: [{ rel: 'canonical', href }] })`; robots via `useSeoMeta`/`useHead` meta | No generator in Nuxt core docs — a server route or module (not verified here) |
| **SvelteKit** — [SEO](https://svelte.dev/docs/kit/seo), [page options](https://svelte.dev/docs/kit/page-options) | `<svelte:head>` per page, often fed from `load` data in the root layout | SSR by default; `export const prerender = true` for build-time HTML. `ssr = false` in the root layout makes the app an SPA shell | `<link rel="canonical">` in `<svelte:head>`; `trailingSlash` `'never'`/`'always'` — `'ignore'` creates duplicate URLs | `src/routes/sitemap.xml/+server.js` endpoint |
| **Astro** — [on-demand rendering](https://docs.astro.build/en/guides/on-demand-rendering/), [API reference](https://docs.astro.build/en/reference/api-reference/) | `<head>` in a layout component | Prerendered static HTML by default; `export const prerender = false` (with an adapter) or `output: 'server'` for on-demand | `new URL(Astro.url.pathname, Astro.site)` — needs `site` set in config | `@astrojs/sitemap` — needs `site`; does not list on-demand (SSR) dynamic routes ([docs](https://docs.astro.build/en/guides/integrations-guide/sitemap/)) |
| **React Router v7 / Remix** — [route module](https://reactrouter.com/start/framework/route-module), [pre-rendering](https://reactrouter.com/how-to/pre-rendering) | React 19 `<title>`/`<meta>` in the route component (recommended over the `meta` export); `meta` export replaces, not merges, parent meta | SSR by default; `prerender` in `react-router.config.ts` (`true` skips dynamic paths — list them). `ssr: false` without `prerender` is SPA Mode: one HTML file for every path | Canonical via `<link>` in the component or the `links` export (aggregated across routes) | No built-in generator — a resource route |
| **Angular** — [SSR](https://angular.dev/guide/ssr), [`Meta`](https://angular.dev/api/platform-browser/Meta) | `Title` and `Meta` services (`addTag`, `updateTag`) | Client-rendered unless `ng add @angular/ssr`; `RenderMode.Server` / `Prerender` / `Client` per route in `app.routes.server.ts` | No built-in canonical API — insert the `<link>` via `DOCUMENT`; robots via `Meta` | None built in |
| **Plain React or Vue SPA** — [React](https://react.dev/learn/creating-a-react-app), [Vue SSR](https://vuejs.org/guide/scaling-up/ssr.html) | Per-route head updates in JS only | None by default. Vue: content fetched asynchronously after a spinner may not be seen — SSR, or SSG for mostly static pages. React recommends a framework (Next.js, React Router) for SSR/SSG | Whatever the HTML shell carries — usually one canonical for every route, which is a finding | Build-time script |

A raw-HTML check per route (title, canonical, robots meta and main content present before JS) confirms the setting in each row; compare it with the rendered output as in `agent-readiness.md`.
