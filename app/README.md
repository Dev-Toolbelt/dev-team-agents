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

The header shows the app's own version (`app 0.1.0`, from `app/package.json`) beside the
store's (`store 2.49.0-dev.1`). Both are semantic versions on separate lines; the app's is bumped
with the app change it describes (`CLAUDE-md/versioning.md`). While the app version is a pre-release — `0.x`, or any version
with a suffix such as `-beta.1` — a **beta** badge sits next to it; the first stable
version the release step stamps drops it with no other change (`src/shared/appVersion.ts`).

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

## The window

The window opens at about 85% × 88% of the screen's work area (capped at 1600 × 1000), centred,
and does not shrink below 1024 × 680 — the size the kanban and the project table are laid out
for. Each figure is clamped to the work area, so a small display still gets a window that fits
(`src/main/windowSize.ts`).

## The Integrations screens

A top-level **Integrations** tab lists every integration the CLI knows about (GitHub, Jira) in
account mode. You see the token status (stored in the OS keychain), the account fields (API URL,
site, email, etc.), and buttons to test the connection and disconnect. Each card is rendered
generically from the adapter's descriptor in the CLI, so adding a new integration means adding
one Python adapter to `scripts/lib/devteam/integrations/`.

Per-project bindings (which repository, which Jira project) appear in an **Integrations** tab
alongside Preferences on each project's screen. It identifies the account on one line — "Signed in
as …" and the person's name (GitHub) or account and email (Jira) — and lists the project fields
with each control under its label. A `connect-here` hint appears when an integration is not yet connected
at the account level.

**Token input via stdin only.** When connecting an account, the app prompts for the token in a
write-only password field that is never pre-filled and shows only "Stored in <backend>" once
saved. The main process passes it to the CLI through stdin — never argv — so it does not land
in a shell history or a process listing. See ADR-0023.

## The Account screens

Accounts are mandatory (ADR-0029). The app asks the CLI `devteam auth check` once a CLI is found,
and the answer decides what the window shows. **The CLI owns the session**: the app only calls
named `devteam auth` commands, so no token, refresh token or licence ever reaches the renderer,
and the renderer's CSP stays `connect-src 'none'` / `img-src 'self' data:` (the avatar is the
person's initials, never a picture).

- **Sign in** — Google and GitHub (the CLI opens the system browser and waits up to five minutes
  for its loopback callback), an emailed 8-digit code, or email and password, with sign-up
  (the password, then the emailed code) and a forgotten-password reset (send a code, then the code
  and a new password).
- **Blocked** — a signed-in account that is not entitled (`trial_expired`, `banned`,
  `needs_online_check`, `invalid`) sees one plain sentence, "Check again" and "Sign out", and that
  their projects are untouched.
- **Gate mode** — in `enforce` the sign-in or blocked screen **replaces** the app; in `warn` the
  app stays usable under a dismissible banner that opens the Account tab. `gate_mode` is compiled
  into the CLI's `auth-config.json` and is not yet part of the `auth status` document, so the app
  reads it from the document when it appears and otherwise acts as `warn`.
- **Account tab** (and the initials button in the header) — display name, email change (a code to
  the new address, optionally one to the old), linked providers (link and unlink; the last one
  cannot be removed), password change, sign out, and account deletion, which needs the typed word
  "delete" and a fresh emailed code before anything is sent.

**Secrets travel on stdin only.** A code or a password is written to the child's stdin for that one
call (`src/cli/accountOperations.ts`) — no `devteam auth` flag can carry one, and
`COMMAND_SHAPES` refuses an operand that tries — and is redacted from everything the child
returns. Password **sign-up** is the one two-stage command (the CLI reads the password, sends the
code, then reads the code), so the main process holds that single child between "create account"
and "confirm" (`src/main/accountIpc.ts`, `SignUpFlow`) and ends it on cancel, on leaving the
screen or on quit. Fields are validated on submit with the CLI's own rules
(`src/shared/accountRules.ts`); failures are generic sentences chosen from the CLI's
`details.reason`, never its text (which carries the address), and never say whether an address is
registered. The screens are in English and Brazilian Portuguese, chosen from the OS language
(`src/renderer/account/strings.ts`).

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

A project already in the list can fall out of step with its registration: a v2 tree still vendored
beside a bind, or a `project.json` that is gone. Sync and Upgrade are refused there
(`details.reason` `v2-install` / `not-bound`), and instead of only naming a terminal command they
offer **Repair…** — the same dialog, opened on that project's directory. It migrates a v2 install,
or binds again, which restores `project.json` under the registered id rather than a new one.

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
to copy to a test machine, and writing their SHA-256 digests to `release/SHA256SUMS.txt`
(`scripts/checksums.mjs`, also `npm run checksums` on its own). Both scripts read the installer
list from `scripts/release-artifacts.mjs`. A build meant for publishing goes through `npm run dist:beta`
instead — see § Direct-download beta.

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

## Direct-download beta

[ADR-0027](../docs/development/adrs/0027-the-desktop-app-ships-an-unsigned-direct-download-beta-until-it-is-signed.md)
lets these unsigned installers be published as a GitHub Release, linked from the website, until the
app is signed. Never to the Homebrew cask or winget. The ADR holds the conditions and the risks; the
steps are:

1. Once per repository: turn on GitHub's immutable releases, so a published asset cannot be swapped
   after users have checked its digest.
2. Raise `version` in `package.json` (and `package-lock.json`), commit, and tag the commit
   `app-v<version>` — never `v<version>`, which starts the framework release workflow.
3. On a Mac, with a clean tree: `npm ci`, then `npm run dist:beta`. It refuses to build unless HEAD
   carries exactly that tag and nothing is uncommitted, then runs `dist:all`.
4. Create the Release from that tag **as a pre-release, not marked latest**
   (`gh release create app-v<version> --prerelease --latest=false …`), and upload the four installers
   plus `release/SHA256SUMS.txt`. Not the `-unsigned.zip`: it is for test machines and the digests do
   not cover it. GitHub's "latest release" must stay a framework `vX.Y.Z`: `devteam update`,
   `install.sh` and the update check read it (ADR-0028).

Text for the download page — adapt the wording, keep every point. Replace `<release URL>` with the
Release's address:

- **Beta, unsigned.** macOS and Windows cannot confirm who built these files, so they warn before the
  first launch. Download only from `<release URL>`.
- **The app needs the `devteam` CLI** and does nothing without it. No package exists yet, so install
  it from a clone of the repository (Python 3.9+ required):
  - macOS: in the clone, `python3 scripts/cli/devteam store install --from .`, then
    `ln -s "$PWD/scripts/cli/devteam" /usr/local/bin/devteam`. The app finds it there.
  - Windows: in the clone, `py -3 scripts\cli\devteam store install --from .`, then set the user
    environment variable `DEVTEAM_CLI_PATH` to the clone's `scripts\cli\devteam`. Python must be on
    PATH.
- **Check the download before opening it.** If the check fails, delete the file and stop — do not
  continue with the steps below.
  - macOS, in the download folder: `shasum -a 256 -c SHA256SUMS.txt --ignore-missing`. Continue only
    if your file's line ends in `: OK`; "no file was verified" means the file name does not match.
  - Windows PowerShell, in the download folder:
    `(Get-FileHash .\<installer>.exe -Algorithm SHA256).Hash` and compare it with the installer's line
    in `SHA256SUMS.txt`. PowerShell prints uppercase, the file lowercase; the letters are the same.
- **macOS, only for the verified file.** Drag the app to Applications and open it once. When macOS
  refuses, open System Settings → Privacy & Security and choose **Open Anyway** (Control-click → Open
  no longer works from macOS 15). If macOS instead says the app "is damaged", that is the quarantine
  flag on an unsigned download; with the checksum already passed, clear it for this app only:
  `xattr -dr com.apple.quarantine "/Applications/Dev Team Agents.app"`. Never run that command because
  another website or app tells you to — it is how fake apps get past Gatekeeper.
- **Windows, only for the verified file.** SmartScreen shows "Windows protected your PC" with
  **Unknown publisher**: choose **More info → Run anyway**. If it names any other publisher, stop. The
  installer is per-user and asks for no administrator rights. Pick the `x64` or `arm64` installer for
  your machine, or the one without a suffix, which carries both.
- **No auto-update.** Watch the repository's Releases and Security Advisories for new versions and
  fixes, then download and install over the old one.

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
- A sync's result — a row's, the selection's or **Sync all** — is a toast at the bottom right,
  never text inside the table. A failure stays until it is closed; a success that reported a
  notice keeps it for a while.
- Leaving the Projects tab closes an open project's settings unless they hold unsaved changes.
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
  sessions used, `N sessions (M active)`, To do / In progress / In Review / PR/MR Created / Done with counts and
  percentages, a stacked bar, and stale / abandoned badges. A period filter (today, 7 days, 30 days, all)
  narrows it by each session's last activity.
- **Kanban.** Click a card for five columns — To do, In progress, **In Review**, **PR/MR Created**, and Done —
  side by side in one row that scrolls horizontally when the window is too narrow for them, never stacking; each
  column scrolls its own cards under a heading that stays in view. The **PR/MR Created** column is always
  there and stays empty until a PR or MR is created; it shows tasks that have reached a pull request
  and are waiting for its merge. The done-retention setting does not hide them.
  Each task shows its session (provider and branch) and the time it has spent in its column,
  kept live between snapshots; the time spent in each step opens on hover **and** on keyboard focus.
  Task badges include PR/MR badges (`#N` for GitHub PR, `!N` for GitLab MR, clickable to open in the browser),
  issue badges (Jira `PROJ-12`, GitHub `owner/repo#45`, clickable), origin badges (plan step, **Agent** for
  spawned agent, or built-in tool list), and review state badges (findings count, **result not read**, **pending**,
  or neutral **In Review**). A **Failed** badge marks a spawned agent run that failed. A worktree mark appears
  only on a task started in a linked worktree; its tooltip (hover or keyboard focus) names the worktree path and branch.
  PR/MR and issue links open in your system browser on the configured tracker host (GitHub, GitLab, or Jira),
  protected by security validation. Filter by session or period, hide done tasks older than the retention, and
  show/hide tasks with findings. Sessions are compact chips — provider, optional PR/MR badge, title or branch,
  status icon — with the counts in the chip's tooltip. The Done column is tinted green. **← Board** returns to
  the overview, and so does leaving the tab.
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
