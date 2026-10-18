---
name: data-fetching-integrity
description: Detect and prevent duplicate/redundant API calls in SPA/SSG frontends — tool-agnostic.
---

# Data-Fetching Integrity

Duplicate and redundant API calls waste the user's bandwidth and put unnecessary load on the
backend. This is a **behavioral discipline**, not a library feature — it applies whether the
project uses TanStack Query, SWR, Apollo, RTK Query, or plain `fetch`/`axios` with no library at
all. Detection and prevention below are framework-agnostic; do not gate this skill on any specific
tool being present.

## When to Load

Any frontend task in a SPA (client-rendered) or SSG (static-generated, hydrated client-side)
project where components fetch data from an API — implementing, reviewing, or validating.

## Symptoms to Detect

Treat each of these as a concrete, checkable defect — not a stylistic preference:

| Symptom | How it shows up | Why it's a defect |
|---|---|---|
| **Double-fire on mount** | The same request fires twice when a component mounts (common under React `StrictMode`'s double-invoke, or an effect with no guard) | Same data fetched twice for one render |
| **Re-fetch on every render** | A fetch call lives in the render body or in an effect with a dependency array that changes every render (inline object/array/function literal, unstable callback) | Request rate scales with render count instead of with actual data needs |
| **Sibling components fetching the same resource independently** | Two or more components each call the same endpoint with the same parameters, with no shared cache or lifting of the fetch to a common ancestor | N requests for 1 piece of data, and no guarantee they resolve to the same value |
| **Avoidable request waterfalls** | Component B's fetch depends on Component A's fetch result, but A and B are rendered sequentially instead of A's data being fetched once and passed down, or B's independent data being fetched in parallel | Total load time is the sum of round-trips instead of the max |
| **No de-duplication for concurrent identical requests** | Multiple call sites trigger the same in-flight request (same URL + params) before the first resolves, and each gets its own network round-trip | N-1 of the N requests are pure waste |
| **Fetch on every keystroke/scroll without debouncing** | Search-as-you-type, infinite scroll, or filter inputs call the API on every event instead of being debounced/throttled | Request volume scales with input events, not with intent |
| **Re-fetch after navigation back to an already-fetched view** | Returning to a screen re-fetches data that was already loaded moments ago, with no cache or staleness check | Redundant round-trip for data that hasn't changed |

## Root Causes (what to fix, not just what to flag)

- Fetch logic embedded directly in a component's lifecycle/effect with no ownership boundary —
  every consumer re-implements its own fetch instead of sharing one
- Missing or incorrect effect dependency arrays (fires more often than the data actually changes)
- No request-key based de-duplication (in-flight requests for the same key aren't shared)
- No cache layer at all, or a cache layer present but bypassed by hand-rolled component-local state
  that shadows it (see `skills/architecture/frontend-patterns/SKILL.md` and the Server State &
  Data Fetching rules already required of `frontend-developer`)
- Data-fetching triggered from multiple layers for the same event (e.g. a parent effect and a
  child effect both fetching in response to the same route change)

## Prevention Rules

Apply these regardless of stack:

1. **One fetch, one owner.** A given piece of server data has exactly one place responsible for
   fetching it — either the data-fetching library's cache (preferred, see the Server State table)
   or, in its absence, the lowest common ancestor that all consumers read from via props/context.
   Siblings never independently re-fetch the same resource.
2. **Guard effects against extra invocations.** Verify the effect's dependency array only changes
   when the fetch actually needs to re-run; don't pass inline literals that are recreated every
   render.
3. **De-duplicate concurrent identical requests.** If no server-state library owns this, key
   in-flight requests (e.g. a request-key → in-flight-promise map) so a second identical call
   attaches to the first instead of firing a new one.
4. **Debounce/throttle user-driven fetches.** Any fetch triggered by typing, scrolling, or resize
   events must be debounced or throttled — never fire-per-event.
5. **Respect freshness, don't blindly re-fetch.** Navigating back to a view with recently-fetched
   data should reuse it (per the library's staleness window, or an explicit TTL in a hand-rolled
   cache) rather than re-fetching unconditionally.
6. **Parallelize independent fetches.** If two pieces of data don't depend on each other, fetch
   them concurrently — never sequence them just because the code was written top-to-bottom.

## Verification (how to confirm the fix worked)

Open the browser's network panel (or equivalent devtools) for the flow under test and confirm:
- No two identical requests (same method + URL + params) within the same user action
- No request count that grows linearly with unrelated re-renders
- No sequential waterfall for data that has no actual dependency between the two calls
