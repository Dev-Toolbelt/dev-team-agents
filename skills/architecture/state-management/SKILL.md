---
name: state-management
description: Frontend state management — where state lives, library selection, architecture review.
---

# State Management

## State Decision Tree

Apply this hierarchy before reaching for a library:

```
Is the state used by only one component?
  └─ Yes → useState / ref / signal (local state)

Is the state shared between a parent and a few children?
  └─ Yes → lift to the nearest common ancestor (prop drilling is fine up to 2 levels)

Is the state shared across distant components in the same feature?
  └─ Yes → Context / provide-inject / feature-scoped store

Is the state global app state (auth, theme, cart)?
  └─ Yes → global store (Zustand, Pinia, NgRx, etc.)

Is the state data fetched from a server?
  └─ Yes → server state library (TanStack Query, SWR, Apollo, RTK Query)
             NOT a global store — server state has its own lifecycle
```

**The most common mistake**: putting server data in a global store and manually managing loading/error/stale states. Let the server state library own it.

---

## Core Rules

### Server state ≠ client state
Server state (data that lives on a backend) must be managed by a dedicated library (TanStack Query, SWR, Apollo, RTK Query). Never copy it into a `useState` or store slice — it creates synchronization bugs and stale data.

### Derived state is not stored state
If a value can be computed from existing state, compute it — don't store it separately.

```ts
// bad — selectedCount gets out of sync
const [items, setItems] = useState([])
const [selectedCount, setSelectedCount] = useState(0)

// good — derived on render, always accurate
const selectedCount = items.filter(i => i.selected).length
```

### State as close to where it's used as possible
Global state has a maintenance cost. Resist the pull to globalize everything. Promote state up the tree only when a second consumer appears (YAGNI).

### Immutable updates
Never mutate state directly. Always produce a new reference. This enables reliable change detection in every framework.

### Actions over direct mutation
State changes must go through a defined action, mutation, or setter — not direct property assignment from outside the store. This makes state changes traceable and debuggable.

---

## Library Detection & Rules

### Zustand
- One store per domain (`useCartStore`, `useAuthStore`) — not one mega store
- Keep actions inside the store definition, not in components
- Use `subscribeWithSelector` for derived state that depends on a slice of the store
- Avoid storing non-serializable values (functions, class instances, DOM refs)

### Pinia (Vue)
- One store per feature — file name matches store name (`cart.ts` → `useCartStore`)
- Getters are the correct place for derived state — not computed properties in components that duplicate store data
- `$patch` for batch updates; avoid multiple `$state` mutations in sequence
- Stores are auto-disposed when all components using them unmount (unless `keepAlive`)

### NgRx (Angular)
- Feature state must be lazy-loaded with the feature module — never register all reducers at root
- Effects handle all async operations; reducers must be pure and synchronous
- Selectors are the only way to read state in components — never inject the store and access `.value` directly
- Use `createFeatureSelector` + `createSelector` for memoized derived state

### Redux Toolkit (React)
- Use `createSlice` — never write reducers manually
- `createAsyncThunk` for async operations; `createApi` (RTK Query) for server state
- Avoid storing UI state (modal open, tab selection) in Redux — keep it local
- Normalize relational data with `createEntityAdapter`

### Context API (React) / provide-inject (Vue)
- Suitable for low-frequency updates (theme, locale, auth user)
- Not suitable for high-frequency updates (counters, live data) — causes broad re-renders
- Split contexts by domain; one monolithic context causes every consumer to re-render on any change

---

## Anti-Patterns

| Anti-Pattern | Problem |
|---|---|
| Copying server response into a store slice | Duplicates state, creates staleness bugs |
| Storing derived values alongside source values | Source and derived drift out of sync |
| One global store for everything | Unrelated components re-render on unrelated changes |
| Direct state mutation (`state.count++`) | Breaks change detection in every framework |
| Reading store state inside `useEffect` dependencies | Creates infinite loops or stale closures |
| Async logic inside a reducer | Reducers must be pure; side effects belong in actions/effects/thunks |
