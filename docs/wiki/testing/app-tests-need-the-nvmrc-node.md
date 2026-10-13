# App Renderer Tests Need the Node Version in app/.nvmrc

**Origin:** ADR-0029 account login and sign-up QA | 2026-10-13
**Tags:** vitest, jsdom, undici, markAsUncloneable, Failed to start forks worker, Node 20, nvmrc, engines, app tests, renderer tests

> Read this first: "Failed to start forks worker" under `app/` means the shell runs the wrong Node version, not that vitest is broken. Run app tests on Node 24.21.0.

---

## What it is
The Electron app in `app/` runs its renderer tests (vitest with jsdom) on the Node version pinned in `app/.nvmrc`. A shell that defaults to an older Node fails before any assertion runs.

## How it works
1. `app/package.json` sets `engines.node >=24.15.0`. `app/.nvmrc` pins `24.21.0`.
2. jsdom 30.1.1 requires Node `^22.22.2 || ^24.15.0 || >=26`.
3. The undici bundled with jsdom calls `webidl.util.markAsUncloneable`. That function does not exist on Node 20, so the vitest fork worker dies during startup.
4. vitest 4.1.11 itself accepts Node 20, so the message points at the wrong layer.

## Gotchas
- The error text does not mention Node or jsdom. Check `node -v` first.
- Run tests with either:
  - `cd app && nvm use && npx vitest run <path>`
  - `PATH=$HOME/.nvm/versions/node/v24.21.0/bin:$PATH npx vitest run <path>`
- CI is unaffected. `.github/scripts/ci/05-app.sh` pins Node from `app/.nvmrc`.

## References
- `app/package.json` (`engines`), `app/.nvmrc`
- `app/test/renderer/account.test.tsx`, `app/test/renderer/onboarding.test.tsx`
- `.github/scripts/ci/05-app.sh`
