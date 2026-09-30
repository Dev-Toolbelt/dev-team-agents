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

`test/real-cli.test.ts` runs against `scripts/cli/devteam` and skips when the CLI or python3
is missing — locally. Under `CI=true` a missing CLI fails the file instead, so the contract
cannot go untested behind a green run. The CI gate (`.github/scripts/ci/05-app.sh`) also runs
`npm run build` and checks the three entry points it must emit.

## The app's own data

`~/Library/Application Support/dev-team-agents-app/` — `settings.json` (`cliPath`) and
`client-schemas.json` (the ADR-0014 declaration). Deliberately **not** the store root:
Electron's default `userData` collided with `dev-team-agents/` exactly, so `main.ts`
calls `app.setPath('userData', …)` to move it aside.

`settings.json` also records `openAtLogin`, the user's start-at-login choice — only the choice;
whether the OS registered it is read live and is what the UI shows. A write never replaces a
`settings.json` that fails to read: fix or remove the file, and the next write recreates it.

Diagnostics go to `main.log` in the OS log directory (`~/Library/Logs/Dev Team Agents/` on
macOS, `%APPDATA%\Dev Team Agents\logs\` on Windows): CLI resolution and stream restarts,
uncaught errors, and a renderer or helper process that died. It rotates to `main.old.log` at
1 MB, so it never holds more than two files.

## Notifications and running in the background

Hooks queue notifications; this app shows them (ADR-0017). The main process runs one
`devteam notifications watch` and turns each record into a native notification titled with the
project's name, acknowledging it as it is shown. Because the stream lives in the main process:

- **closing the window hides it** — the tray (Windows) / menu-bar icon (macOS) reopens the app,
  shows recent notifications, pauses banners, or quits. Without a tray icon, closing quits on
  Windows (nothing could bring a hidden window back); macOS keeps the Dock;
- **a backlog** of more than three notifications, piled up while the app was closed, arrives as
  one summary banner; every one of them is in the bell;
- **one instance only** — launching it again shows the running one;
- **start at login** is opt-in, from the bell's panel, and shows what the OS actually recorded.

### Manual check, packaged build

Automated tests cover the supervisor, the stream, the bell and the login-item logic against a
simulated OS. What only a packaged build on a real desktop can show is checked by hand —
`npm run dist:mac` (or `npm run dist:win`), install, then:

| # | Do | Expect |
|---|----|--------|
| 1 | Open the app, then close its window | The app keeps running: menu-bar / tray icon present, no Dock icon (macOS) |
| 2 | In a bound project, append a record to its queue (see below), or work in Claude Code until a notice fires | A native notification titled with the project's **name** (never an id) within ~2 s |
| 3 | Click the notification | The window opens on that project's settings |
| 4 | Append a `critical` record | It stays on screen (Windows); on macOS, persistence follows System Settings → Notifications → Banners/Alerts |
| 5 | Quit from the tray, reopen | The notification from step 2 is **not** shown again (acknowledged on display) |
| 6 | Launch the app a second time while it runs | The running window comes forward; no second tray icon |
| 7 | Bell → **Start at login** on, log out and in | The app starts hidden. If macOS refuses the unsigned app, the panel says so (`not-registered` / `requires-approval`) |
| 8 | Bell → **Pause system notifications**, append a record | No banner; the record is in the bell |

A record to append by hand (the project's state directory is the path in its `.dev-team-agents/state-dir`):

```bash
echo '{"id":"'$(date +%s)'-1-1","ts":'$(date +%s)',"project_id":"<id>","session_id":"manual","level":"warning","code":"manual.test","message":"Manual check","dedupe_key":"","expires_at":0}' >> "$(cat .dev-team-agents/state-dir)/notifications.jsonl"
```

**Project preferences are not app data.** The settings screen (click a project's name) reads
`devteam prefs list` and writes through `devteam prefs set|unset --scope project`, so every
change lands in the store's project layer and in the project's `resolved/preferences.json`,
exactly as if it had been made in a terminal. The app keeps no copy of any preference.

## The Board screen

Agents keep a todo list through their provider's own tool; hooks record it per session
(ADR-0018) and this screen shows it. The main process runs one `devteam tasks watch`, keeps the
latest snapshot per project, and pushes it to the window, so the board is current with the window
closed and reopened. It is read-only: nothing here edits, moves or deletes a task.

- **Overview.** One card per project that has at least one task: its name, the providers its
  sessions used, `N sessions (M active)`, To do / In progress / Done with counts and percentages,
  a stacked bar, and stale / abandoned badges. A period filter (today, 7 days, 30 days, all)
  narrows it by each session's last activity.
- **Kanban.** Click a card for three columns. Each task shows its session (provider and branch)
  and the time it has spent in its column, kept live between snapshots; the time spent in each
  step opens on hover **and** on keyboard focus. Filter by session or period, and hide done tasks
  older than the retention. Each session has a status (active, idle, ended) and a **Copy resume
  command** button; the text copied is the command the CLI sent for that session, never a string
  the window supplies.
- **Board settings** (app-local, in `settings.json`, not preferences): `boardStaleAfterMinutes`
  (default 60, 5 to 1440) is passed to the CLI as `--stale-after`; `boardDoneRetentionDays`
  (default 7, 1 to 365) is the kanban's default retention.

## The Global Skills screen

The **Global Skills** tab manages the *global* (user-level) skills of Claude Code, Codex and opencode:
list, inspect, install and remove. It is a client of `devteam skills list|show|install|remove`
and writes only through `install` and `remove`, both in `compat.MUTATING`, so they are
withheld like every other write action when the schema declaration could not be written.

Two rules keep the renderer out of the filesystem. **The file picker runs in the main
process**, inside the `installSkill` IPC handler: the renderer asks for a *kind* of source
(folder, archive, or the previous one for a retry after a conflict) and receives only the
result, so it never holds a path it could send back. **Removal is aimed by name and root id**
and the main process checks the pair against a fresh `skills list` before it builds an argv;
a `managed` skill is refused there and not offered in the UI. A removed folder is moved to
the store's quarantine, never deleted, and a symlink is only unlinked.
