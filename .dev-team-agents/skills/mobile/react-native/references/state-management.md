---
name: react-native-state-management
description: React Native state management — Zustand, Redux Toolkit, Jotai, TanStack Query decision table and rules.
---

## Decision Table

Choose based on complexity — do not over-engineer:

| Complexity | Recommendation | Detection |
|-----------|---------------|-----------|
| Local UI state | `useState` / `useReducer` | — |
| Shared simple state | **Zustand** | `zustand` dep |
| Complex / normalized | **Redux Toolkit** | `@reduxjs/toolkit` dep |
| Atomic / fine-grained | **Jotai** | `jotai` dep |
| Server state | **TanStack Query** | `@tanstack/react-query` dep |

## Rules

- Never store server state in Redux or Zustand — use TanStack Query or SWR; the cache is the source of truth
- Persist only non-sensitive state with `redux-persist` or `zustand/middleware/persist` + `AsyncStorage`
- Never persist auth tokens in AsyncStorage — use `expo-secure-store` or `react-native-keychain`
