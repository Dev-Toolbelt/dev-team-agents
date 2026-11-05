# A running dev build of the app swallows a new launch

**Origin:** Canvas view (ADR-0063) manual check from a worktree | 2026-11-05
**Tags:** electron, requestSingleInstanceLock, single instance, npm start, npx electron, worktree, old window, feature missing, pgrep, electron download

> If a dev build of the app from any checkout is already running, a new `npm start` builds, exits 0 at once and only focuses the old window, which shows the old code.

---

## What it is

`app/src/main/index.ts` calls `app.requestSingleInstanceLock()`. The lock is per app identity, not per checkout, so a dev build left open in the main checkout (for example an `npm start` running for days) holds it for every worktree.

## How it works

1. `npm start` or `npx electron .` in a worktree builds without error.
2. The new process fails to take the single-instance lock and exits 0 immediately.
3. The running instance receives `second-instance` and focuses its own window.
4. That window runs the old checkout's code, so the feature you just built looks missing.

Check for a running instance before launching:

```bash
pgrep -fl "node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
```

The path in each result names the checkout that owns the process. Quit that instance, then launch again.

## Gotchas

- Exit code 0 and a clean build log give no hint that nothing new started.
- The first `npm start` in a fresh worktree also downloads the Electron binary (about 270 MB, `node_modules/electron/install.js`) before any window opens. A long silent wait there is the download, not a hang.

## References

- `app/src/main/index.ts` (`requestSingleInstanceLock`)
