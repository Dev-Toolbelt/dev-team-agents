# Worktree Node Tests Need Node 22.18 and the Main node_modules

**Origin:** context-delivery worktree test run | 2026-10-25
**Tags:** node 22.18, node 20, tests/js, opencode-plugin.test.mjs, linked worktree, node_modules, npm run typecheck, nvm

> Read this first: the root-level `tests/js/opencode-plugin.test.mjs` imports a TypeScript plugin and needs Node 22.18 or newer, and a linked worktree has no `app/node_modules`. The app Node pin is covered in `testing/app-tests-need-the-nvmrc-node.md`.

---

## What it is
Two checks fail in a linked worktree on a machine whose default Node is 20: the JS plugin test and the `app/` checks that need installed dependencies. Both are environment problems, not code problems.

## How it works
1. `tests/js/opencode-plugin.test.mjs` imports the TypeScript plugin directly. It needs Node 22.18 or newer.
2. The machine default is Node 20, which skips or fails that test.
3. Run it with a newer binary, for example:
   `~/.nvm/versions/node/v24.21.0/bin/node --test tests/js/opencode-plugin.test.mjs`
4. A linked worktree is a separate checkout, so `app/node_modules` (gitignored) is absent.
5. For `npm run typecheck` and `npx vitest run` in the worktree, link the main checkout's modules:
   `ln -s <main-checkout>/app/node_modules <worktree>/app/node_modules`
6. Remove the symlink after the run. It is untracked, but it still points at another checkout.

## Gotchas
- The symlink makes the worktree use the main checkout's installed packages. Do not run `npm install` in the worktree while the link exists; it writes through the link into main.
- A test that passes on Node 24 can still fail under the Node 20 default. Check `node -v` before reading a failure as a code bug.
- `app/` tests with the Node 20 default die with `Failed to start forks worker`. The fix is the `.nvmrc` pin in `testing/app-tests-need-the-nvmrc-node.md`, not this entry.

## References
- `tests/js/opencode-plugin.test.mjs`
- `app/.nvmrc`, `app/package.json` (`engines`)
- `testing/app-tests-need-the-nvmrc-node.md`
