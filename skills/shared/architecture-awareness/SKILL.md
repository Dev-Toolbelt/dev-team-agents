---
name: architecture-awareness
description: Canonical reference for understanding project architecture context — monolith vs microservices, SPA vs server-rendered, API boundaries, and layer responsibilities. Loaded by coding agents to understand system structure before implementing changes.
---

# Architecture Awareness

## Frontend Context

**Decoupled SPA**: React, Vue, Svelte, Angular consuming an API. Focus on component design, state management, data fetching, routing, and build optimization. When working on a decoupled SPA, suggest or apply:
- Code splitting: lazy-load routes and heavy components
- Tree-shaking: avoid barrel imports that defeat it
- Asset optimization: compress images, use modern formats (WebP/AVIF)
- Bundle analysis: run `vite-bundle-visualizer`, `webpack-bundle-analyzer`, or equivalent to identify bloat
- Environment configs: ensure dev and prod builds are clearly separated

**Server-rendered templates**: Blade, Twig, ERB, Jinja, Handlebars — HTML is rendered server-side, JavaScript enhances. Focus on semantic HTML, progressive enhancement, partial rendering, and minimal JS footprint.

In server-rendered contexts: coordinate with the `backend-developer` since routing, data, and views are handled together.

---

## Backend Context

**Decoupled (API-first)**: REST or GraphQL API consumed by a separate frontend. Focus on request/response contracts, validation, serialization, and statelessness.

**Monolithic (server-rendered)**: Backend renders views directly (Laravel+Blade, Django+Templates, Rails+ERB, etc.). Handle routing, controllers, views, and partial rendering together.

In monoliths, the distinction between backend and frontend is thinner — coordinate with the `frontend-developer` or `ui-ux-designer` when the work touches views.

**Before deciding on class structure**, check `architecture.md` for the layer depth defined for the module being implemented — the `software-architect` may have specified different depths per domain area (simplified `Controller → Service → Model` for CRUD modules, full `Controller → Service → Repository → Model` for complex ones). Follow what's documented; don't infer.
