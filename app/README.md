# The desktop client — running it locally

A pure client of the `devteam` CLI (ADR-0015). It spawns nothing else, bundles no second
CLI, and is **dev-only**: `install.sh`'s `KEEP_ROOT` allowlist drops `app/`, so this tree
never reaches a user's project.

## Install

```bash
cd app
npm ci
```

**Plain `npm ci`, without `--ignore-scripts`.** That flag is what CI uses
(`.github/scripts/ci/05-app.sh`), deliberately — a runner should not execute arbitrary
postinstall scripts — and CI never launches the app, so it never needs what the flag
skips. Locally you do.

`electron`'s postinstall is what downloads the ~270 MB Electron binary. Skip it and the
build still succeeds (TypeScript and Vite do not need the binary) but launching fails
with:

```
Error: Electron failed to install correctly, please delete node_modules/electron and try installing again
```

**Do not follow that advice** — reinstalling the same way reproduces it. Fetch the binary
instead:

```bash
node node_modules/electron/install.js
```

Confirm with `./node_modules/.bin/electron --version`, which prints a version only when
the binary is actually there.

## Run

The app has to find a `devteam` CLI, and it will not invent one. In a checkout where the
CLI is not installed on `PATH`, point at the one in this repository:

```bash
DEVTEAM_CLI_PATH=/absolute/path/to/dev-team-agents/scripts/cli/devteam npm start
```

`DEVTEAM_CLI_PATH` is the first step of the resolution order in `src/cli/resolve.ts`
(configured path → `PATH` → this platform's channel locations). It is scoped to the one
process and leaves nothing to undo, which is why it beats putting `devteam` on `PATH` for
a one-off run.

Finding a file named `devteam` is not enough: the app runs `devteam version --json` on
each candidate and rejects anything that answers without a `compat` block, so another
program with the same name cannot be mistaken for the CLI.

## Verify

```bash
npm run verify   # typecheck + lint + test
```

The suite spawns real fake-CLI fixtures rather than mocking the spawn layer. On Windows
those fixtures cannot be POSIX shebang scripts, so `test/fixtures/launcher.c` is compiled
at test time into a real PE — see its header, and `launcher-build.ts` for the compiler
probe. No compiler means those tests skip; it never fails the suite for a toolchain
reason.

## The app's own data

`~/Library/Application Support/dev-team-agents-app/` — `settings.json` (`cliPath`) and
`client-schemas.json` (the ADR-0014 declaration). Deliberately **not** the store root:
Electron's default `userData` collided with `dev-team-agents/` exactly, so `main.ts`
calls `app.setPath('userData', …)` to move it aside.
