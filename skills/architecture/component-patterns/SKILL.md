---
name: component-patterns
description: Component architecture — container/presentational patterns for React, Vue, Angular, Svelte.
---

# Component Patterns

## Container / Presentational (Smart / Dumb)

The core idea: separate **what data comes from** (container) from **how it looks** (presentational). Presentational components receive everything via props/inputs — they own no side effects and no data fetching.

| Aspect | Container (Smart) | Presentational (Dumb) |
|---|---|---|
| Responsibility | Fetch data, manage state, handle business logic | Render UI, emit user events |
| Dependencies | API clients, stores, router | None beyond UI primitives |
| Reusability | Low — tied to a specific domain | High — usable anywhere |
| Testability | Test behavior + integration | Test with prop snapshots / storybook |
| State | Owns or subscribes to state | Receives everything via props/inputs |

**When to split**: as soon as a component both fetches data AND renders UI, extract the rendering into a presentational child. This makes the UI testable without mocking the network.

---

## Rules

- **One reason to change**: if a component would change for a UI tweak AND for an API change, split it.
- **No business logic in templates**: move conditionals, transforms, and computations to hooks, composables, or services — not inline in JSX/template.
- **Props down, events up**: data flows down via props/inputs; user intent flows up via callbacks/emits/outputs.
- **Max ~150 lines per component**: a component that exceeds this is doing too much; split before it grows further.
- **Prop sprawl**: more than 5–7 props is a design smell — consider decomposition or a configuration object.
- **No cross-feature imports**: a component in `features/orders` must not import directly from `features/users`; go through a shared layer.

---

## React

```tsx
// Container — owns data fetching and state
function OrderListContainer() {
  const { data, isLoading, error } = useOrders()
  if (isLoading) return <Spinner />
  if (error) return <ErrorMessage error={error} />
  return <OrderList orders={data} />
}

// Presentational — pure render, fully testable with props alone
function OrderList({ orders }: { orders: Order[] }) {
  return (
    <ul>
      {orders.map(o => <OrderItem key={o.id} order={o} />)}
    </ul>
  )
}
```

**React-specific rules**:
- Custom hooks are the idiomatic container layer — prefer `useOrders()` over class-based containers.
- Wrap page-level components in an `ErrorBoundary`; presentational components should not catch errors themselves.
- Use `React.memo` on stable presentational components to avoid unnecessary re-renders from parent state changes.

---

## Vue

```vue
<!-- Container -->
<script setup lang="ts">
const { orders, isLoading, error } = useOrders()
</script>
<template>
  <Spinner v-if="isLoading" />
  <ErrorMessage v-else-if="error" :error="error" />
  <OrderList v-else :orders="orders" />
</template>

<!-- Presentational -->
<script setup lang="ts">
defineProps<{ orders: Order[] }>()
</script>
<template>
  <ul>
    <OrderItem v-for="o in orders" :key="o.id" :order="o" />
  </ul>
</template>
```

**Vue-specific rules**:
- Composables (`useX`) are the Vue equivalent of React hooks — put all fetching and state logic there.
- Use `defineProps` with explicit types; avoid prop drilling beyond two levels — use `provide`/`inject` or a store.
- Emit events with `defineEmits` and typed payloads; never mutate a prop directly.

---

## Angular

```typescript
// Container — smart component, injects service
@Component({
  selector: 'app-order-list-container',
  template: `
    <app-spinner *ngIf="isLoading" />
    <app-error-message *ngIf="error" [error]="error" />
    <app-order-list *ngIf="!isLoading && !error" [orders]="orders" />
  `
})
export class OrderListContainerComponent implements OnInit {
  orders: Order[] = []
  isLoading = false
  error: Error | null = null

  constructor(private orderService: OrderService) {}

  ngOnInit() {
    this.isLoading = true
    this.orderService.getOrders().subscribe({
      next: orders => { this.orders = orders; this.isLoading = false },
      error: err => { this.error = err; this.isLoading = false }
    })
  }
}

// Presentational — dumb component, only @Input / @Output
@Component({
  selector: 'app-order-list',
  template: `<app-order-item *ngFor="let o of orders" [order]="o" />`
})
export class OrderListComponent {
  @Input() orders: Order[] = []
}
```

**Angular-specific rules**:
- Container components inject services; presentational components declare only `@Input` and `@Output`.
- Use `OnPush` change detection on presentational components — they receive immutable inputs, so there's no need for the default dirty-check cycle.
- Global error handling goes in a class that implements `ErrorHandler` and is provided at the root level (`{ provide: ErrorHandler, useClass: AppErrorHandler }`); do not swallow errors silently.
- Prefer `async` pipe over manual subscriptions to avoid memory leaks from forgotten `unsubscribe()` calls.

---

## Svelte

```svelte
<!-- Container -->
<script lang="ts">
  import { onMount } from 'svelte'
  let orders: Order[] = []
  let isLoading = true

  onMount(async () => {
    orders = await fetchOrders()
    isLoading = false
  })
</script>

{#if isLoading}<Spinner />{:else}<OrderList {orders} />{/if}

<!-- Presentational -->
<script lang="ts">
  export let orders: Order[]
</script>
<ul>{#each orders as o}<OrderItem order={o} />{/each}</ul>
```

**Svelte-specific rules**:
- Presentational components export only typed props; avoid `$:` reactive declarations that reach outside the component boundary.
- Use Svelte stores (`writable`, `derived`) as the shared-state layer rather than passing deeply nested props.
- Wrap route-level components in `<svelte:boundary>` (Svelte 5) for error isolation.

---

## Anti-Patterns

| Anti-Pattern | Problem |
|---|---|
| Fetching inside a presentational component | Makes the component untestable without network mocking |
| Business logic in template expressions | Hard to test, hard to read |
| Prop drilling beyond two levels | Use a store, context, or composable instead |
| God component | One component handling routing, fetching, form state, and rendering |
| Direct store mutation in presentational components | Breaks the unidirectional data flow contract |
