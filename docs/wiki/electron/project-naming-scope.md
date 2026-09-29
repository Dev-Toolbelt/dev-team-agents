# Project name stored app-local, never visible to the CLI

**Origin:** project naming feature added to the Electron app | 2026-09-29
**Tags:** project, name, BindRequest, settings.json, app-local, not portable, machine-local, product naming

> The project name is declared, stored, and read only by the app — the CLI never sees it. Another machine binding the same repository sees only the directory basename.

---

## What it is

The Electron app can store a human-readable name for a bound project. The name is carried in `BindRequest.name` but stripped before the CLI is invoked via `bindProject()` in `app/src/main/ipc.ts`, and written to the app's own `settings.json` only after the bind succeeds.

## How it works

1. User types a name in the bind dialog (or accepts the default)
2. `bindProject()` copies the name out of `BindRequest`
3. `bind` is invoked without it — the CLI has no `--name` flag
4. When `result.ok`, `writeProjectName()` in `app/src/main/settings.ts` merges the name into `settings.json` — an atomic operation that swallows storage failures rather than failing a bind that already succeeded
5. Other screens read it with `readProjectNames()` and display it; fallback is the directory basename

## Gotchas

- **Storage failure is silent.** If `writeProjectName()` throws, the app logs it and continues — the bind is already done. The name simply will not persist.
- **Not in `project.json`.** The CLI's `project.json` is committed topology. A name passing through would have to become part of the framework's public surface. Staying app-local made it shippable without a `--bind-name` flag.
- **Another machine sees only the basename.** A fresh clone on a different machine runs `devteam list`, sees the directory, and `displayName()` in `Projects.tsx` falls back to basename. The name does not sync.
- **Not visible to any other provider.** An OpenAI or Codex client binding the same project sees no name at all.

## Why this shape

The CLI has no `--name` flag and `project.json` is committed. A name passed through argv would need to become part of the framework's public surface. Keeping it app-local and machine-local made it shippable now; promoting it to a CLI flag + a committed record is an open decision for a future session, not an oversight.

## References

- `app/src/main/ipc.ts` — `bindProject()` strips the name
- `app/src/main/settings.ts` — `writeProjectName()` / `readProjectNames()`
- `app/src/shared/api.ts` — `BindRequest.name` declared
- `app/src/renderer/screens/Projects.tsx` — `displayName()` reads it with fallback to basename
