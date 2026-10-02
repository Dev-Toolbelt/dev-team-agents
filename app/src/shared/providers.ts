/**
 * The providers `devteam` binds and installs skills for. One list for the whole app.
 *
 * Mirrors `ALL_PROVIDERS` in `scripts/lib/devteam/providers.py`, which is the source of
 * truth; `test/providers.test.ts` parses that file and fails when this one drifts. Every
 * screen, IPC validator and type in the app derives from here rather than spelling the
 * list out, so adding a provider is one edit plus the test telling you where the CLI went.
 *
 * Type-only consumers import `Provider`; nothing here touches `electron` or `node:*`.
 */
export const PROVIDERS = ['claude', 'opencode', 'codex'] as const;

export type Provider = (typeof PROVIDERS)[number];
