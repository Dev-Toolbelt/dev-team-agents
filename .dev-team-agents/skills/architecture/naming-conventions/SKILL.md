---
name: naming-conventions
description: Naming and file structure — framework-agnostic with per-framework notes.
---

# Naming Conventions

## Core Rules

| Thing | Convention | Example |
|---|---|---|
| Component | PascalCase | `UserCard`, `OrderSummary` |
| Hook / Composable | camelCase, prefixed `use` | `useOrders`, `useAuthState` |
| Service / class | PascalCase | `OrderService`, `AuthClient` |
| Utility function | camelCase, verb-first | `formatDate`, `parseAmount` |
| Constant | SCREAMING_SNAKE_CASE | `MAX_RETRIES`, `API_BASE_URL` |
| CSS class (BEM) | kebab-case | `order-card__title--active` |
| CSS custom property | kebab-case, prefixed | `--color-primary`, `--spacing-md` |
| Event handler prop | camelCase, prefixed `on` | `onSubmit`, `onItemSelect` |
| Internal handler | camelCase, prefixed `handle` | `handleSubmit`, `handleItemSelect` |
| Boolean prop/var | prefixed `is`, `has`, `can`, `should` | `isLoading`, `hasError`, `canEdit` |
| Enum / union literal | PascalCase (type) + SCREAMING (value) | `Status.PENDING` |

---

## File Naming

| File type | Convention | Example |
|---|---|---|
| Component file | PascalCase | `UserCard.tsx`, `UserCard.vue` |
| Hook file | camelCase | `useOrders.ts` |
| Service file | camelCase or PascalCase (match class) | `orderService.ts` |
| Test file | same name + `.test` / `.spec` | `UserCard.test.tsx` |
| Style module | same name + `.module.css` | `UserCard.module.css` |
| Index barrel | `index.ts` | only at feature boundary |

**Barrel files (`index.ts`)**: use only at the public boundary of a feature folder. Never create barrels inside a feature just to shorten import paths — they prevent tree-shaking and obscure where code lives.

---

## Folder Structure

Prefer **feature-based** over **type-based** once the project exceeds ~5 components.

```
src/
├── features/
│   └── orders/
│       ├── components/     ← UI components scoped to this feature
│       ├── hooks/          ← composables / hooks scoped to this feature
│       ├── services/       ← API calls, business logic
│       ├── types.ts        ← feature-local types
│       └── index.ts        ← public API of the feature
├── shared/
│   ├── components/         ← reusable across features
│   ├── hooks/
│   └── utils/
└── app/                    ← routing, providers, global layout
```

**Rules**:
- A component in `features/orders` must not import directly from `features/users` — go through `shared/`
- `shared/` components must have zero feature-specific knowledge
- Only promote to `shared/` when a second feature needs it (YAGNI)

---

## Framework Notes

### React
- File extension: `.tsx` for components, `.ts` for everything else
- Co-locate styles, tests, and stories with the component file
- Named exports for components; default export only at route level (Next.js / Remix convention)

### Vue
- Single-file components: `PascalCase.vue`
- Multi-word component names only — avoids clashes with native HTML elements (`UserCard`, not `Card`)
- `composables/` folder for `use*` files; `stores/` for Pinia stores

### Angular
- Follow Angular CLI naming: `feature-name.component.ts`, `feature-name.service.ts`, `feature-name.module.ts`
- One class per file; file name must match the class name in kebab-case
- Suffix every class with its role: `Component`, `Service`, `Pipe`, `Directive`, `Guard`, `Resolver`

### Svelte
- File name is the component name: `UserCard.svelte`
- Stores in `stores/` folder; suffix with `Store` if ambiguous (`cartStore.ts`)

---

## Anti-Patterns

| Anti-Pattern | Problem |
|---|---|
| `data`, `info`, `util`, `helper` as names | Too generic — describe what it does, not that it exists |
| `handleClick` on every button | Describe the intent: `handleAddToCart`, `handleDeleteUser` |
| `isLoading2`, `newValue`, `temp` | Temporary names that survive into production |
| Abbreviations beyond 3 letters | `usr`, `ord`, `cfg` — spell it out |
| Inconsistent casing in the same codebase | Pick a convention and enforce it via linter |
| Deep nesting: `components/ui/base/atoms/Button` | Flatten — depth signals over-engineering |
