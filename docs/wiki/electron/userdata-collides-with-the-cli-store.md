# `app.getPath('userData')` can land inside another tool's data directory

**Tags:** electron, userData, getPath, productName, APP_NAME, Application Support, APPDATA, store, profile, second writer, setPath

Electron derives `app.getPath('userData')` from the app's `productName` under the platform's
per-user application-data directory — `~/Library/Application Support/<productName>` on macOS,
`%APPDATA%\<productName>` on Windows. It creates that directory and fills it with Chromium's
profile: `Cache`, `Code Cache`, `GPUCache`, `Local Storage`, `Session Storage`, `Preferences`,
`Trust Tokens`, `Network Persistent State`, and anything the app itself writes through
`getPath('userData')`.

A CLI or daemon that stores its own data under the same convention derives the same path from the
same name. When a desktop client is named after the tool it is a client of, the two resolve to one
directory, and the app becomes a second writer inside data the other tool owns. Neither choice is
wrong on its own, which is why this is invisible in review: it is a collision between two
independent, individually correct naming decisions, in two languages, in two files that never
reference each other.

In this repository `productName` is `dev-team-agents` and `scripts/lib/devteam/paths.py` uses the
same string as `APP_NAME`, so the store is `<appData>/dev-team-agents/{core,data}` and the app's
profile landed beside it.

## What it costs

- **A second writer in a single-source-of-truth tree.** ADR-0011 makes the CLI the only writer of
  the store; a profile directory inside it is not that, even when inert.
- **A store-wide operation sweeps the profile.** Anything that archives, exports, syncs, diffs or
  garbage-collects the store now includes browser caches — and a size or file-count check on the
  store reports a number that has nothing to do with the store.
- **It compounds with anything that points the CLI at `userData`.** Passing that directory as the
  CLI's working directory or `--path` — a reasonable way to make a GUI's answers deterministic —
  aims the tool at its own data directory.

## What to do

Set the path before `whenReady`, so nothing has resolved it yet:

```js
app.setPath('userData', join(app.getPath('appData'), `${app.getName()}-app`))
```

`getPath('appData')` is the per-user application-data root, so this keeps platform convention and
changes only the leaf. Any distinct suffix works; the requirement is that the app's directory is
not the other tool's and is not inside it.

## Checking it

Verify by launching, not by reading — the derivation happens at runtime and a stale profile from an
earlier run looks identical to a current one:

```bash
ls "$HOME/Library/Application Support/<productName>"      # expect no Cache/Preferences here
ls "$HOME/Library/Application Support/<productName>-app"   # expect the profile here
```

Nothing enforces the separation. Whoever changes `productName`, the CLI's application name, or
either platform's derivation has to check the two still differ, on every platform the app ships to.
