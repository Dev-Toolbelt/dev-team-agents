---
name: architecture-awareness
description: Architecture context before implementing — rendering model, service boundaries, layer depth.
---

# Architecture Awareness

## Routing Gate

**Read only the section that matches your context.** Loading this skill does not mean reading all of it.

| Consumer / context | Read |
|---|---|
| Agent implementing server-side code | **Backend Context** |
| Agent implementing browser UI | **Client Rendering Model** + **Frontend Context** |
| Agent implementing native or cross-platform mobile UI | **Mobile Context** |
| Work crosses layers (full-stack task) | Both matching sections |

**Always applies, regardless of section**: Layer Depth Contract (bottom of this file).

---

## Client Rendering Model

Detect the model before touching a view. It determines where state and routing live, not which library is used.

| Structural signal | Model | Consequence |
|---|---|---|
| A build step emits a JS bundle; server returns a shell HTML document; routes resolve client-side | **Decoupled client** | State, routing, and data fetching are client concerns; the server is a data API |
| Server returns fully-formed HTML per route; template files live beside controllers | **Server-rendered templates** | Routing, data, and views are one unit; JS enhances an already-working page |
| Server returns HTML for the first paint, then a client bundle takes over routing | **Hybrid / server-side rendering with hydration** | Every piece of code must declare which side it runs on; never assume browser globals exist |

If the signals conflict (both a bundle config and server-side templates), the project is hybrid or migrating — ask before choosing a side.

---

## Frontend Context

**Decoupled client** — the shipped bundle is a deliverable with a budget:
- Split code along route boundaries so an entry point loads only what its first screen needs
- Keep imports specific enough that unused exports can be dropped by the bundler (aggregating re-export modules defeat this)
- Serve images in a modern compressed format and size them to their rendered dimensions
- Measure before optimizing: run whatever bundle-analysis tool the project's bundler already provides (for example `vite-bundle-visualizer` or `webpack-bundle-analyzer`) rather than guessing at bloat
- Keep development and production build configuration explicitly separated — never ship development-only diagnostics

**Server-rendered templates** — the deliverable is HTML:
- Semantic markup first; the page must work before any script runs
- Render partials server-side rather than reconstructing them in JS
- Keep the JS footprint proportional to the enhancement it provides
- Coordinate with the `backend-developer`: routing, data, and views are handled together

**Hybrid** — for each module, state explicitly whether it runs on the server, the client, or both, and never reach for browser or server-only globals outside their side.

---

## Backend Context

| Structural signal | Model | Consequence |
|---|---|---|
| Views are rendered by a separate client; the server returns serialized data only | **API-first (decoupled)** | Focus on request/response contracts, validation, serialization, statelessness |
| Views are rendered by the same application that owns the routes and data | **Monolithic (server-rendered)** | Routing, controllers, and views change together |
| Multiple independently deployed services own separate data stores | **Distributed services** | Cross-service calls are network calls: define the contract, the timeout, and the failure behavior before writing them |

- In a monolith the backend/frontend boundary is thin — coordinate with `frontend-developer` or `ui-ux-designer` when work touches views.
- In distributed services, never read another service's data store directly; go through its published contract.

---

## Mobile Context

Bundle analysis and DOM-oriented rendering rules above do **not** apply. What matters:

| Concern | Rule |
|---|---|
| Client/server boundary | The app is an untrusted client — every authorization decision is made server-side, never in the app |
| Offline and connectivity | Decide, per screen, what happens with no network: cached, queued, or blocked. Do not leave it implicit |
| API contract shape | Round trips are expensive on mobile networks — prefer contracts that fill a screen in one call over chatty per-widget endpoints |
| State ownership | Distinguish device-local state (survives relaunch) from server-owned state (must be reconciled on resume) |
| Native boundaries | Cross-platform code calling into native modules is a layer boundary — keep the platform-specific part isolated behind one interface |

Platform UI conventions live in the platform skills, not here.

---

## Layer Depth Contract

**Before deciding on class structure**, check `architecture.md` for the layer depth defined for the module being implemented — the `software-architect` may have specified different depths per domain area (a shallower chain for simple CRUD modules, a full chain including a persistence-abstraction layer for complex ones). Follow what is documented; do not infer a depth from other modules.
