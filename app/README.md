# The desktop client — running it locally

A pure client of the `devteam` CLI (ADR-0015). It spawns nothing else, bundles no second
CLI, and is **dev-only**: `install.sh`'s `KEEP_ROOT` allowlist drops `app/`, so this tree
never reaches a user's project.

## Install

```bash
cd app
npm ci
```

Use the Node version in `.nvmrc` (`nvm use`): it matches the Node that the pinned Electron
embeds, and Electron 40+ refuses to install on anything below Node 22.12.

**Install scripts are allow-listed.** npm 11+ blocks dependency install scripts unless
`allowScripts` in `package.json` names them. The list pins `esbuild` and
`electron-winstaller` (needed by `dist:win`) to the versions that were reviewed, and
denies `fsevents`, which ships prebuilt. After a bump of one of those packages, review the
new version and re-approve it with `npm install-scripts approve <pkg>`; until then npm
skips its script and warns. CI runs `npm ci --ignore-scripts`
(`.github/scripts/ci/05-app.sh`), which skips them all.

Electron no longer downloads its ~270 MB binary at install time: the first `npm start`
fetches it. To fetch it ahead of time, for example before going offline:

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

## The Integrations screens

A top-level **Integrations** tab lists every integration the CLI knows about (GitHub, Jira) in
account mode. You see the token status (stored in the OS keychain), the account fields (API URL,
site, email, etc.), and buttons to test the connection and disconnect. Each card is rendered
generically from the adapter's descriptor in the CLI, so adding a new integration means adding
one Python adapter to `scripts/lib/devteam/integrations/`.

Per-project bindings (which repository, which Jira project) appear in an **Integrations** tab
alongside Preferences on each project's screen, showing the read-only account status and the
project-specific fields. A `connect-here` hint appears when an integration is not yet connected
at the account level.

**Token input via stdin only.** When connecting an account, the app prompts for the token in a
write-only password field that is never pre-filled and shows only "Stored in <backend>" once
saved. The main process passes it to the CLI through stdin — never argv — so it does not land
in a shell history or a process listing. See ADR-0023.

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

## Writing UI text

Support text — descriptions, hints, tooltips, notices — follows the reuse guideline
`app_support_copy` in `docs/development/reuse-guidelines.md`: two lines at most, what happens and
what to do next.

## Binding a project that already has dev-team-agents v2

Choosing a directory in the bind dialog asks `devteam migrate` for a plan before anything else. A
directory with no v2 install (exit 2) binds as it always did. One with a v2 install — vendored at
`.dev-team-agents/`, or the pre-v2.1.0 shape at `.claude/dev-team-agents/` — gets **Review migration**
instead of Bind: the plan, with the providers and mode on screen, then **Migrate**, which runs
`migrate --apply --untrack` with exactly those options. The old framework goes to a dated quarantine,
memory is kept, and the old paths leave git's index; the result says so, and the commit is yours. A
pre-v2.1.0 project lands on layout 1 — use Upgrade on its row to move the memory into the store.

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

Every `dist:*` script starts with `clean`, which empties `release/`: running `dist:win` after
`dist:mac` deletes the `.dmg`. To get both, run `npm run dist:all` — one build, one
`electron-builder --mac --win` pass. It needs a macOS host, since a `.dmg` cannot be built
elsewhere. It ends by zipping the four installers into
`release/dev-team-agents-<version>-unsigned.zip` (`scripts/zip-release.mjs`), the single file
to copy to a test machine.

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

## Project folders

The Projects table shows each project's name (its path is the name's tooltip, and a `missing` badge
sits beside the name when the directory is gone) and, from `list --json`'s `preferences`, an On/Off
badge for Auto-update, Worktree and Notifications — a dash when the CLI did not report the value.
Pin and Unbind are on the project's own screen; Unbind asks for an explicit acknowledgement first.

The Projects screen groups bound projects into folders (ADR-0021). Like a project's display name
(ADR-0016), folders are the app's own record — `projectFolders` in `settings.json` — and never
reach the CLI, `project.json` or the store. They are per machine.

- **New folder** above the table; **Rename…**, **Delete folder…** from a folder's `⋯` menu. Deleting
  a folder moves its projects out to the top level; it never unbinds anything.
- Like a file manager, projects in no folder are listed at the top level below the folders, with
  no header of their own, and projects inside a folder are indented under it.
- **Move** a project by dragging its handle onto a folder, or onto the top-level projects to take it
  out of one; when the top level is empty, a drop strip appears while dragging. The row's folder
  button is the keyboard path to the same result. Dragging a selected row carries the whole
  selection.
- **Select** rows, a whole folder, or everything shown; the bar that appears moves, removes from a
  folder, or syncs the selection one project at a time (**Stop after this one** ends it between
  projects). Bulk actions act only on rows on screen: never on rows a filter hides or a collapsed
  folder holds — selecting a collapsed folder opens it. While any sync runs, every other sync
  button waits.
- A collapsed folder stays collapsed across restarts; a text filter opens it while it has matches,
  and hides folders that have none.

One level of folders today. The model in `src/shared/projectFolders.ts` is a tree
(`parentId`) capped by `MAX_FOLDER_DEPTH`; subfolders mean raising that constant, with no change to
the stored format. The main process validates every save against the same module, writes a copy
rebuilt from the model's own fields, and writes nothing it refuses; the screen then undoes the
change and says why. If the folders cannot be read, the screen shows projects ungrouped and blocks
every folder change until a retry succeeds, so a failed read can never be saved over the real
grouping.

## The Board screen

Agents keep a todo list through their provider's own tool; hooks record it per session
(ADR-0018) and this screen shows it. The main process runs one `devteam tasks watch`, keeps the
latest snapshot per project, and pushes it to the window, so the board is current with the window
closed and reopened. It is read-only: nothing here edits, moves or deletes a task.

- **Overview.** One card per project that has at least one task: its name, the providers its
  sessions used, `N sessions (M active)`, To do / In progress / Done with counts and percentages,
  a stacked bar, and stale / abandoned badges. A period filter (today, 7 days, 30 days, all)
  narrows it by each session's last activity.
- **Kanban.** Click a card for three columns, or an optional fourth **In Review** column when a review is
  active. Each task shows its session (provider and branch) and the time it has spent in its column,
  kept live between snapshots; the time spent in each step opens on hover **and** on keyboard focus.
  Task badges show its origin (a plan step, a spawned agent with an **Agent** badge, or a built-in tool list) and review state; tasks in review show a findings badge (count of issues found, or **result not read**). A **Failed** badge marks a task that could not be created or updated. Filter by
  session or period, hide done tasks older than the retention, and show/hide tasks with findings.
  Each session has a status (active, idle, ended) and a **Copy resume command** button; the text
  copied is the command the CLI sent for that session, never a string the window supplies.
- **Board settings** (app-local, in `settings.json`, not preferences): `boardStaleAfterMinutes`
  (default 60, 5 to 1440) is passed to the CLI as `--stale-after`; `boardDoneRetentionDays`
  (default 7, 1 to 365) is the kanban's default retention.

## The Global Skills screen

The **Global Skills** tab manages the *global* (user-level) skills of Claude Code, Codex and opencode:
list, inspect, install and remove. It is a client of `devteam skills list|show|install|remove`
and writes only through `install` and `remove`, both in `compat.MUTATING`, so they are
withheld like every other write action when the schema declaration could not be written.

Two rules keep the renderer out of the filesystem. **The file picker runs in the main
process**, inside the `installSkill` IPC handler: the renderer asks either to `pick` (one
native picker for a folder, a `.md` file, or a `.zip`/`.skill` archive. A `.md` goes to the CLI
as the file, and the CLI decides whether it stands for its folder or is a single-file skill.
On Windows and Linux, where Electron cannot offer files and folders in one dialog, a folder is
chosen through its `SKILL.md`) or to reuse the `previous` pick for a retry after a conflict, and receives only the
result, so it never holds a path it could send back. **Removal is aimed by name and root id**
and the main process checks the pair against a fresh `skills list` before it builds an argv;
a `managed` skill is refused there and not offered in the UI. A removed folder is moved to
the store's quarantine, never deleted, and a symlink is only unlinked.
