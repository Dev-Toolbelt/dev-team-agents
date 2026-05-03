---
name: offline-first
description: Offline-first frontend standards — local storage schema design, sync queue strategy, conflict resolution policies, and reliable connectivity detection patterns.
---

## Storage Structure

- Define a clear schema for the local store (IndexedDB, SQLite via OPFS, etc.) — treat it as a real database with versioned migrations
- Mirror the API shape when practical; document intentional divergences in code comments
- Never store sensitive data (tokens, PII) in unencrypted client storage

## Sync Strategy

- Implement a sync queue: operations made offline are queued and replayed when connectivity is restored
- Use timestamps or vector clocks for conflict resolution — define a clear policy (last-write-wins, server-wins, or manual merge) and document it
- Handle partial sync failures: operations must be atomic or rollback-safe; a failed sync must not leave local state inconsistent
- Expose sync status to the user — they must know whether data is saved locally only or confirmed on the server

## Connectivity Detection

- Combine `navigator.onLine` with an actual fetch probe to a known endpoint — `navigator.onLine` alone is unreliable (returns `true` on captive portals and metered connections)
- React to `online`/`offline` browser events to trigger sync and update UI state accordingly
- Show clear offline indicators — never silently queue operations without informing the user
