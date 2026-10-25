# Agent Readiness

Load when the site expects AI agents or agentic browsers to read or act on it, or when content may only exist after JavaScript runs. Many agentic browsers read pages through the accessibility tree and the DOM, so most of these checks are accessibility checks — for WCAG rules load `skills/architecture/accessibility-patterns/SKILL.md`.

## Content without JavaScript

Some AI crawlers do not execute JavaScript. Fetch the page as raw HTML (no rendering) and compare it with the rendered page.

| Result | Report |
|---|---|
| Main content, title, canonical and JSON-LD present in raw HTML | `PASS` |
| Raw HTML carries only an app shell (empty root element, "enable JavaScript") on an indexable page | `ISSUE` for non-rendering crawlers; run a rendering test — if the rendered output also lacks it, the gate lists it as a `BLOCKER` |
| Some content (reviews, prices, tabs) only after JS | `ISSUE` |

A raw HTML page with fewer than about 150 visible words on a content page is a signal worth checking, not a verdict (*heuristic*).

## Acting on the page

| Check | Why it matters to an agent |
|---|---|
| Native `<button>` and `<a href>`, not clickable `<div>`s | Agents find actions by role |
| Every input and icon-only button has an accessible name | Unnamed controls cannot be chosen reliably |
| Targets large enough to hit reliably (WCAG 2.2 target size) | Coordinate-based agents miss small targets |
| No transparent overlay above controls; cookie banners dismissable | Overlays intercept clicks |
| Menus open on click or focus, not only on hover | Many agents do not hover |
| Primary actions in the same place and wording across templates | Agents generalise from one page to the next |
| Landmarks (`<header>`, `<nav>`, `<main>`, `<footer>`) | Lets an agent skip to the content |
| No CAPTCHA in front of public content | Blocks every agent, including legitimate ones |

## Optional machine-readable delivery

- A Markdown version of a page (a `.md` alternate or `Accept: text/markdown` negotiation) is optional; no major consumer is documented. If content is negotiated on `Accept`, the response must send `Vary: Accept` so caches do not serve Markdown to browsers
- `llms.txt` rules live in the skill's GEO section

Emerging agent protocols (agent cards, commerce manifests, browser-exposed tool APIs) are drafts with no confirmed consumer: mention them only when the user asks, as "track, don't implement yet".
