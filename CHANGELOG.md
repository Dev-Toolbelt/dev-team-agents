# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **A v2 project is migrated from the app's bind dialog, with no terminal.** Choosing a directory asks `devteam migrate` for a plan: no v2 install (exit 2) binds as before; a v2 install gets *Review migration* (the plan with the options on screen) and *Migrate*, which quarantines the old framework, keeps its memory, binds, and takes the old paths out of git's index — leaving one commit for the user. Found binding a real pre-v2.1.0 project, which the app could only refuse.
  - **`devteam migrate` converts both v2 shapes.** The pre-v2.1.0 one (`.claude/dev-team-agents/`) no longer needs `migrate-to-root.sh` first: its tree is quarantined, `.claude/user-data/` moves to `.dev-team-agents/user-data/` (layout 1, so `upgrade` offers the store next), `.claude/docs/` stays and joins `context_paths`, its `settings.json` hook entries are rewritten in place instead of duplicated, and links into the old tree the bind does not recreate are unlinked. An unregistered `project.json` left by a refused bind is adopted.
  - **`devteam migrate --apply --untrack`** runs `git rm -r --cached` on exactly the paths the plan listed — the index only, never the working tree, nothing committed. The one command that runs git on a user's repository, and only when asked (ADR-0015 amendment); a failure is reported in `untrack_problem`, not raised.
- **Task board — optional In Review column and review window tracking (ADR-0018 amendment 2026-09-30).** Tasks can move from In progress to an optional In Review column when a review/QA agent, review command (`/devteam:review`, `/devteam:qa`), or explicit prompt request triggers a review window. The window captures which tasks are under review, tracks review outcomes through a `review-result` marker emitted by the four review/QA agents, and releases tasks when findings = 0 (passed) or when all findings are fixed. The kanban always shows the four columns (To do, In progress, In Review, Done); a task enters In Review only through a review window and leaves when the review passes or its findings are fixed. Triggers: review/QA agents (`qa-specialist`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer`) spawn detection via `PreToolUse` on `Agent`/`Task` (Claude), `PostToolUse` on `wait_agent` (Codex), or plugin `tool.execute.before` on `task` (opencode); review/QA commands via `UserPromptSubmit` (Claude/Codex) or plugin `chat.message` (opencode); explicit keywords (review, revisar, revisão, QA, testar, test) in prompts with negation awareness. Notifications: `tasks.review_findings` when a review records findings > 0. Hook events: Claude `PostToolUse` (marker: `TodoWrite\|TaskCreate\|TaskUpdate\|Agent\|Task`), Codex `PreToolUse`/`PostToolUse`/`SessionEnd`, opencode plugin `tool.execute.before`/`tool.execute.after` / `chat.message` / `session.idle`. Session records gain `reviews[]` array tracking review windows, pending markers, and outcomes.
- **Plugins: optional, per-project integrations declared by a manifest (ADR-0019).** A plugin is `plugins/<name>/plugin.json` in the core — requirements, config fields, actions, a status probe and hooks — validated against `plugins/_schema/plugin.schema.json`; the CLI, the hooks and the desktop app all read it and none names a plugin, so a new plugin is a new directory and nothing else (`plugins/README.md`). Settings are committed per project at `.dev-team-agents/plugin-settings/<name>.json`, shared by the team, and written locked and atomically. `devteam plugin list|show|enable|disable|config get|set|unset|run` (all `--path`, `--json`) is the surface: `enable` refuses a missing binary with exit 3 and its install hint, and seeds the config from the plugin's detect action; `run` executes only actions a shipped manifest declares, with a fixed interpreter and working directory, and a failing script is `ok: false` with the log tail rather than a CLI error. The written shape is `plugin_settings: 1` in the ADR-0014 gate. Hooks are dispatched generically by `pre-tool-use/02d-plugins.sh` (a pure-bash check, nothing forked when no plugin is enabled) and `stop/99a-plugins.sh`. `plugins/` is linked at `.dev-team-agents/plugins` in a bound project, as an optional core tree so older installed versions stay valid.
- **Desktop app — a Plugins tab on the project screen.** Opening a project now shows Preferences and Plugins. Each plugin is a card rendered from `plugin list`: a status badge, missing requirements with their install hint, an enable switch that says the setting is committed for the whole team, a config form built from the manifest's fields (including a list editor for path lists), and one button per action. A detect-style action fills the form's draft instead of saving; a long action shows its running state, duration and log. Every write is checked against the project's own `plugin list` answer before the CLI runs, and the five writing `plugin` commands are gated like the others.
- **Plugins are hardened against the repository they run in.** Settings are committed, so a cloned project chooses them: Graphify refuses absolute, `..`, leading-`-` and out-of-project source paths and strips copied symlinks that escape; every settings write locks its whole read-modify-write; `plugin run` kills the script's process group when the CLI is terminated, and the app terminates in-flight CLI calls on quit; `plugin list` reports invalid manifests instead of dropping them; the PreToolUse dispatcher emits one plugin hook's output. Graphify's build marker is `graphify-out/.build-commit` (per checkout, accepted only as a hex commit id), a refresh holds a per-checkout lock taken over atomically when stale, swaps `graphify-out/` so an interrupted build never leaves the project without a graph, and refuses `.git`, `.dev-team-agents`, `.worktrees`, its own output directories and the project root as source paths. A terminated `plugin run` gets SIGTERM and a 3 s grace before SIGKILL, and quitting the app cancels only running plugin actions, letting writes finish. The Plugins tab lists manifests the CLI reported as invalid.
- **Graphify's card reads at a glance, and paths are picked, not typed.** Status facts can carry a `tone` the app draws as a badge: `graphify-out/graph.json` shows a green *present* or an amber *missing*, and *Last build* is just the local `YYYY-MM-DD HH:MM`. A path setting can declare a `picker` (`directory` or `file`): the app opens the operating system's own dialog inside the project, the main process turns the choice into a project-relative path and refuses anything outside the project, `.git` or `.dev-team-agents`, and the path is added only on **Add**. Both keys are optional additions to `plugin.json` and the `plugin list` payload. The project screen no longer repeats the inheritance notice above its tabs.
- **Plugin cards are collapsible, and the Skills tab is "Global Skills".** Each plugin shows only its title, status badge, description, Enable switch and a chevron until expanded; the body stays mounted while collapsed, so drafts and running actions survive, and a card with unsaved edits or a running action stays open. The top-level tab that manages the providers' user-level skills now reads "Global Skills", matching its screen.
- **The Plugins tab explains an empty list.** A project on a core version older than the plugin system got "This version of dev-team-agents ships no plugins" and nothing to act on. It now names the version the project resolves to and says how to get plugins: `devteam update` for an unpinned project, `devteam pin --release` then `devteam sync` for a pinned one.
- **`helpers/plugin-lint.sh`** validates every manifest against the schema rules, checks that every script stays inside its plugin directory and parses, and runs in CI.
- **Task board — every agent's todo list appears on a cross-project Kanban board.** Agents keep a todo list for every session (Claude Code `TaskCreate`/`TaskUpdate`, Codex `update_plan`, opencode `todowrite`); hooks automatically capture and normalize them into per-session records, machine-local under `<state-dir>/task-board/`. The desktop app shows a **Board** with three columns (To do, In progress, Done), cards for each task with time spent in the current step, session context (branch, provider), and metadata (stale flag, duration history). `devteam tasks list` and `watch` are the CLI equivalents. Codex fires `PreToolUse` for `update_plan`, confirmed in the Codex source and pinned by a test replaying its exact payload. Notifications: `tasks.session_done` when a session's last open task completes; `tasks.session_abandoned` when a session ends with open tasks (Claude only). ADR-0018.
  - **Capture per provider:**
    - **Claude Code**: `PostToolUse` hook (matcher: `TodoWrite\|TaskCreate\|TaskUpdate`) → `post-tool-use/01-task-board.sh` (incremental for Task*, replace for TodoWrite)
    - **Claude Code**: `SessionEnd` hook → `session-end.sh` (marks session ended, raises abandoned notification)
    - **Codex / opencode**: reuse `PreToolUse` dispatcher, filter on tool name in bash before forking
  - **The record:** one file per session (`<state-dir>/task-board/<session-key>.json`), machine-local and never deleted. Tasks track status history (append-only, capped at 50 entries), duration per step, and ownership (main agent or subagent id). Derived state (stale, abandoned, per-step time) is computed on read from timestamps and configurable thresholds.
  - **Board settings:** app-local (stale threshold in minutes, done retention in days), like the project display name (ADR-0016). Not in `preferences.json`.
- **Notifications reach the user — through the desktop app.** Every trigger the framework had (context window near or past its limit, many turns with no commit, a stale `project.md` or session summary, a stale or never-run health check, `devteam upgrade` pending, broken links, an update available or applied, the tip of the day) was printed as a boxed `DEV TEAM AGENTS` banner on a hook's stdout — which no provider shows the user: `SessionStart` stdout is model context and `Stop` stdout is not displayed. Hooks now raise each one through `scripts/hooks/lib/notify.sh` into a per-project `notifications.jsonl` (suppression, dedupe, TTL, 200-line cap, no python), and the desktop app shows it as a native notification titled with the project's **name**, acknowledged as it is shown so it never appears twice, with a bell in the header holding the history (ADR-0017). Same hooks, same queue, under Claude Code, Codex and opencode. `stop/04-notifier.sh` is re-enabled on current paths, forks python once per Stop instead of up to six times, and raises each notice once per session or once per day instead of on every turn above a threshold.
  - **CLI:** `devteam notifications list`, `ack` (gated write; seen marks live in a separate file the CLI writes under a lock, so it never rewrites the queue a hook is appending to) and `watch` — a long-running stream that ends on stdin EOF or SIGTERM. `list` and `watch` need the machine layout, like `list`.
  - **App, background mode:** the stream lives in the main process, so closing the window hides it instead of quitting; a tray / menu-bar icon reopens it, lists recent notifications, pauses banners, or quits; one instance only; **start at login** is opt-in and shows what the OS recorded rather than the choice alone — on this unsigned build macOS reports `not-registered`, and the app says so.
  - **Verified on a packaged build**, not only in tests: a notice queued in a bound project is shown and acknowledged within ~1.5 s, including with the window closed; a restart does not replay it; a second launch brings the running instance forward; quitting leaves no `watch` process behind. The checklist is in `app/README.md`.
- **Global skills for Claude, Codex and opencode — `devteam skills list|show|install|remove`, and a Skills screen in the desktop app.** Lists every user-level skill each provider reads (`~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`, `~/.config/opencode/skills`), one row per physical directory with the providers that read it, and flags symlinks, framework-managed links and malformed `SKILL.md` files. `install` takes a folder, a `.md` file (a `SKILL.md` stands for its folder only when the folder carries the skill's name; otherwise that single file is the skill, so a `SKILL.md` lying in Downloads never copies Downloads) or a `.zip`/`.skill` archive, validates the frontmatter and the archive before writing, covers the chosen providers with the fewest roots (opencode also reads the Claude and `.agents` roots, so it gets no duplicate), stages every copy before swapping any into place and rolls back on failure, and refuses a name conflict (exit 4, `details.reason` `exists` or `managed`) unless `--replace`; `--link` symlinks a folder instead of copying it. `remove` never deletes: a folder goes to the store's quarantine, a symlink is unlinked and its target reported. Names are matched among a root's real entries, so `..` or a path can never reach outside it. `install`/`remove` are gated like every other write. The directory map lives in `scripts/lib/global-skill-roots.json`. ADR-0020.
- **Desktop app — every project preference is editable from a settings screen.** Clicking a project's name opens its settings: the 21 keys of `preferences-defaults.json` in six groups (General, Context & session, Memory & docs, Worktrees, Notifications, QA & CI), each with the control its type calls for — switches, numeric fields with units and digit grouping (`200,000 tokens`) plus presets, selects with a validated "Other…", radio cards for `worktree_commit_action`, and a nullable text field where empty means *auto-detect*. Validation happens as you type and nothing invalid reaches the CLI: ranges, BCP 47 tags, git branch names, a worktree directory that must stay inside the project, and the context warning required to sit below the critical level, drawn as a bar in tokens. **Every value shows which layer it came from** (`Default`, `Global`, `This project`, `Not opted in`), and a project-layer value offers *Reset to inherited*. Edits are staged behind a save bar (⌘S), leaving with unsaved edits asks first, and a save that fails part-way names the keys already written — the batch is not a transaction. **Writes go to the project layer only** (`prefs set/unset --scope project`); the main process checks every key against the project's own `prefs list` and every value against the same rules table the screen validates with, and turning `telemetry` or `auto_update` on asks in a native dialog the renderer cannot answer. *Reset to inherited* names the value it brings back, and the form is locked from Save until the reload confirms what was written. `prefs set` and `prefs unset` join the app's gated commands (ADR-0015 amendment). `suppress_notifications` is on/off only, because the CLI cannot write the per-type list form; `transcript_multiplier` is shown read-only as deprecated.
- **The project surface reads like a product, and is searchable.** Every change here came from running the app rather than reading it. Names replace UUIDs in the Projects table, the bind result and the upgrade dialog, with the `project_id` kept beside each in muted text — it is the identity the CLI actually understands, and a user debugging from the terminal needs it. **A project with no stored name falls back to its directory's basename, so no row renders a bare UUID**, including one bound from the terminal and never named in the app. The bind dialog leads with `Link (recommended)`, capitalises the mode titles, and relabels providers to the names people know them by (Claude Code (Anthropic), Codex (OpenAI), Opencode) while the values sent to the CLI stay untouched, because those are arguments and not display strings. A chosen directory gets a bordered confirmation carrying an icon and the word "chosen" — green alone is invisible to a colour-blind user and absent to a screen reader. Filtering over the loaded list: free text across name and path, a select for mode, checkboxes for providers with any-of semantics, because three checkboxes needing all three checked to show a single-provider project reads as broken the first time someone tries it. "No bound project matches these filters" is a different sentence from "nothing is bound yet".
  - **Project names are the app's own record, and the contract says so.** The framework has no concept of one: `devteam bind` takes no `--name` and `project.json` carries `schema`, `project_id`, `layout` and `context_paths` only. So the name lives in the app's `settings.json` keyed by `project_id`, it **never reaches the CLI's argv**, and it is stored only once a bind has succeeded — a failed bind leaves no name behind and a refused path never reaches storage. The limit is stated rather than left to be discovered: the name lives on one machine, does not travel with the project, and no other client sees it. Making it portable means a field in the committed `project.json` and a flag on `bind`, which is a change to the framework's public surface that a UI affordance is not on its own a reason to make.

### Changed
- **Desktop app — the Projects screen's actions sit with the table.** Sync all and Refresh moved beside New folder, in the same compact outline style, with icons (Refresh spins while the list reloads). The screen is titled "Projects", and "Bind…" reads "New project" with a plus icon. With no projects there is no table toolbar, so Refresh stays in the header.
- **Desktop app — the Projects table trades its Path column for Auto-update, Worktree and Notifications badges, and Pin and Unbind move onto the project screen.** The path is still reachable: it is the tooltip on the project name, and the red `missing` / `not checked` state sits beside the name. Each new column is a green *On* or muted *Off* badge from the project's resolved preferences, `—` when the CLI did not say; a muted-types list on `suppress_notifications` reads *On* with the types in a tooltip. Pin… and Unbind… are buttons in the project screen's header (Sync, Upgrade and Move to folder stay on the row); Unbind now needs an explicit "I understand" checkbox before its button enables, says that `project.json` and the project's memory are kept, and returns to the list once it succeeds.
  - **`devteam list --json` records gain `preferences`** (additive, ADR-0014): `{auto_update, worktree_active, suppress_notifications}` resolved for each project, each `null` when the version does not resolve or the layer is unreadable, so the table needs one call rather than one `prefs list` per row.
- **The bind dialog refuses a directory that is already bound.** Choosing a bound project — or a directory inside one, which the CLI would resolve to that project — turns the chosen-directory box red, says which project it is, hides the form and keeps Bind disabled, without asking the CLI anything. Paths are compared by whole components, so a sibling with the same prefix is not mistaken for the bound project.
- **The desktop app's dialogs fit the window.** A dialog is capped at the window's height; Bind and Upgrade keep their header and buttons in place and scroll only the body, so Bind / Migrate is always on screen. The bind form is tighter: the directory's Change… button sits inside the chosen-directory box, providers share one row, and the four modes are a two-column grid of option cards, each still carrying its consequence as its accessible description. The v2 notice's title no longer truncates.
- **Graphify is the first plugin.** Its refresh, detection, status and hint live in `plugins/graphify/`; enable and configure it with `devteam plugin enable graphify` or the app's Plugins tab. `detect` proposes source paths and manifests from the project's stack without writing anything, and `rebuild` forces a build and records its commit and time for the status line. **Refresh at session end is back as the opt-in `auto_refresh` setting, off by default** — the per-session cost that disabled it stays a per-project choice. A legacy `.dev-team-agents/user-data/graphify.json` is moved into `plugin-settings/graphify.json` by `bind` and `sync` (new file written first, then the old one removed), and read as enabled until then. `graphify-setup` now drives the CLI instead of writing the file by hand.
- **The desktop app says less when all is well, and shows where you are.** The "Compatible with this store" banner is gone: only an unknown or incompatible store earns one. The catalog no longer explains an unresolved project. A project's settings nav highlights the section being read, following the scroll and a click, with `aria-current="location"`. Table header rows no longer tint on hover, and every table's body rows are striped.
- **The desktop app has a new icon: the folder, `/d` and the asterisk on a white rounded tile.** It replaces the bare asterisk in the macOS bundle (`icon.icns`), the Windows installer and the Windows/Linux window icon (`icon.png`), and the development dock icon. The tile follows Apple's icon grid (824px on a 1024px canvas, 185px radius, soft shadow) so the dark `/d` stays legible on a dark Dock, and is committed as a brand source (`logo-icone-app.png`) generated from the original art by `build/make-icon.sh --tile`; the default path still needs only `sips` and `iconutil`. The brand guide records the app icon as its own composition — the symbol elsewhere stays the asterisk.
- **The desktop app's catalog is sorted, and skills are grouped by category.** Agents and commands list in alphabetical order; skills appear under one heading per category — categories alphabetical, `uncategorized` last, entries alphabetical within each — with a new category select that composes with the text filter. Ordering uses a fixed `en` collator, so it is the same on every machine. The Category column is gone, since the group heading carries it. All of it is client-side over the listing already fetched.
- **A bound project reaches the framework through `.dev-team-agents/scripts` and `/templates`, not a `core` pointer.** Each is a link into the resolved store version (a copy in copy mode), created for every provider, not only Claude — the Codex `hooks.json` and the opencode plugin call the same hook path. `.claude/settings.json` now names `.dev-team-agents/scripts/hooks`, the path a v2 install used, so the file no longer differs between layouts; the next `sync` retires the `core` link and rewrites its `core/scripts/hooks` entries in place, which is a one-time diff to `settings.json` in every bound project. A real directory at either path is a v2 tree: `bind` and `sync` now refuse such a project with exit 4 and point at `devteam migrate`, reversing last round's promise that a project bound over v2 keeps syncing — linking beside the tree is impossible and leaving it would run the hooks from the old v2 scripts.
- **The desktop app is "Dev Team Agents", and its build detail lives in the native About window.** Menus, window title, About panel, the macOS bundle display name and the Windows shortcut now read `Dev Team Agents`; `productName` and every artifact name are unchanged. The About tab added a day earlier is replaced by the platform's own About window (macOS app menu; a new Help → About on Windows), carrying the CLI path and source, store version, json contract, write actions and build, with the dock icon. The app's settings directory is pinned to `dev-team-agents-app` rather than derived from the app's name, so renaming did not orphan stored project names. The catalog lists names in the brand colour without the markdown view behind them (removed for now), no longer prints a project UUID, and every scrollbar follows the app's theme.
- **The desktop app shows no UUID anywhere, and its header carries only what matters on every screen.** The `project_id` that sat in muted text beside each name — in the Projects table, the bind result, and the pin, unbind and upgrade dialogs — is gone; `devteam list` in a terminal is where a debugger gets it. The header keeps the brand, the `unsigned build` warning and the store version; the CLI path and source, json contract, write actions and app build moved to a new **About** tab (recorded as an ADR-0015 amendment). The Projects table's *Resolves to* column is now **Version**, with a green icon when a project is on the store's current version and an amber one when it is not, each with a tooltip that is also its accessible name — and neither when the store has no current version, because "outdated" relative to nothing is not a claim the payload supports. Every action button has a tooltip (a withheld reason replaces it), row actions stay on one line, the providers filter label lines up with the other two, and the bind dialog shows only the directory picker until a directory is chosen.

### Deprecated
- **`scripts/graphify-refresh.sh` and `scripts/hooks/pre-tool-use/02-graphify-hint.sh`** are wrappers for one minor version: the first prints a notice and runs the plugin's refresh with `--if-changed`, the second is a no-op once a project has plugin settings. Use `devteam plugin run graphify rebuild`. The unused `stop/_disabled-99-graphify-refresh.sh` is removed; its logic is the plugin's Stop hook.

### Security
- **Desktop app: a dropped HTML file no longer gets the app's bridge, and a pin can no longer point a project at an arbitrary directory.** Audit `docs/audit/app-audit-2026-09-30.md`. Dropping an `.html` file on the window navigated to it, because `file:` was allowed wholesale, and the preload then handed that page every write channel. Navigation is now allowed only to the renderer's own `index.html`, `file:` requests only under the renderer's directory, and every IPC handler refuses a sender that is not that page's main frame. The chain it closed ran through `pin`: the version was never validated, and the CLI joined it onto the versions directory, so `/abs` or `../..` bound a project to foreign hook scripts. The app now accepts only a plain version name, and so does the CLI: `devteam pin` and `bind --pin` exit 2 on anything else, and a bad pin already in the registry is an environment error `doctor` reports instead of following. Also: `DEVTEAM_APP_DEV_SERVER` is ignored in a packaged build and matched by exact origin, DevTools are off in a packaged build, and the packaged binary sets Electron fuses (no `ELECTRON_RUN_AS_NODE`, `NODE_OPTIONS` or `--inspect`, asar integrity checked, app code only from the asar).

### Fixed
- **The update check no longer offers a downgrade, or the version already installed.** `session-start.sh` treated any difference between `installed_version` and the latest release tag as an update, so a build ahead of the release (`2.48.900`) was offered `v2.48.0`, and a project on the release got a daily notice for it, since the tag carries a `v` the stored version does not. The same check gates auto-update, so with `auto_update` on, an install ahead of the release was **downgraded** to it rather than just notified. `uc_is_newer` in `scripts/hooks/lib/update-check.sh` now compares major.minor.patch numerically, ignoring the `v` and a pre-release or build suffix, and raises nothing for an unparseable version. The notice shows both versions without the `v`. Covers Claude Code, opencode and Codex, which all run the same `session-start.sh`.
- **`devteam bind` no longer touches the project's own opencode and Codex files.** The "never overwrite what bind did not create" guarantee held only for Claude Code. The opencode and Codex installers overwrote a project agent sharing a framework name (`cp -f`), deleted `.codex/skills/devteam-*` and a real `…/skills/dev-team-agents` directory, and deleted `devteam-*.md` from `.codex/prompts/` and `~/.codex/prompts/`; the bind then recorded `.codex/agents`, `.codex/skills`, `.opencode/agents`, `.opencode/skills` and `.opencode/plugins` as whole directories, so `unbind` quarantined the project's own agents and skills with them, `.git/info/exclude` hid new project files from git, and `.codex/hooks.json` was quarantined with the project's hooks in it. Now every provider follows one rule (ADR-0022): the installers answer `--list-targets`, `bind`'s preflight refuses a project-owned path at any target before the first write (exit 4, like Claude), the manifest records files instead of directories, `.codex/hooks.json` is a merged file (`codex-hooks`: committed, and `unbind` removes only the marked hook groups), and legacy prompt aliases are reported, never deleted. An existing directory-level manifest migrates on the next `sync` without moving anything of the project's. Run standalone, the installers keep a ledger in `.dev-team-agents/.provider-owned-<provider>`, refuse a conflict with exit 4, and accept `--adopt` to move conflicting paths to `.dev-team-agents/quarantine/` first — which `update.sh` passes. `tests/test_provider_ownership.py` runs the real installers for every provider in `providers.ALL_PROVIDERS` and fails if one is added without a case.
- **Every bind mode serves every provider.** `devteam bind --mode vendored` skipped the opencode and Codex installers, so a vendored project got nothing for them; it now installs them, with relative links and hook paths into the vendored tree so the committed result works on any clone. Two bugs of the same kind are fixed with it: under a `link` or `copy` bind the Codex skills link pointed at `.dev-team-agents/skills`, which a v3 bind never creates, so Codex saw no framework skills; and the installers wrote an unrecorded `.dev-team-agents/VERSION` and recreated `.dev-team-agents/user-data/` in a bound project. Vendored mode also refuses a project-owned path now, for Claude as well, instead of quarantining it (ADR-0022 amendment).
- **A first bind over a pre-v2.1.0 install failed halfway and left the project harder to migrate.** Found binding a real project from the app. That shape keeps the framework at `.claude/dev-team-agents/`, which the v2 refusal never looked at, so the bind went ahead and collided on the link the old installer had committed (`.claude/agents/dev-team`) — after writing `project.json`, and after the symlink probe had created `.dev-team-agents/`. `migrate-to-root.sh`, the one tool for that shape, refuses to move onto an existing `.dev-team-agents/`, so the failed bind blocked its own way out. `bind`, `migrate` and `doctor` now share one detector: the bind is refused in every mode, before anything is written, and pointed at `devteam migrate`, which converts that shape itself (see Added). Independently, every collision a bind can hit is checked before `project.json` is written, the probe removes the directory it created, and the "already exists" hint names `devteam bind` for a project that has nothing to sync yet.
- **Hook-only `devteam tasks` commands no longer hang on an open stdin.** `tasks record` (and the new `review-open`/`review-result`/`mark`) read stdin to EOF, so any caller that inherited a stdin nobody closed — the JSON contract sweep, a shell — waited forever. The payload is now read with a 5 s bound (`HOOK_STDIN_TIMEOUT`); hooks pipe and close, so they are unaffected.
- **The opencode plugin's `runHook` spawned the script but passed stdin via `exec`'s ignored `input` option, so every hook read empty stdin until timeout.** Plugin hooks now exec the script with stdin attached, fixing reviews, QA requests, and any plugin action from opencode.
- **The credential guard read heredoc bodies as commands, and missed commands after them.** It split a Bash command on `|`, `;` and `&` before discarding heredoc bodies, and flattened newlines to spaces. A session-summary entry that mentioned `credentials.local.json` in a markdown table, or after a `;` next to a word like "read" or "open", was refused as a dump; and anything on the line after a heredoc terminator was cut away with the body, so a real dump there passed. Heredoc bodies are now dropped by delimiter before segmenting, newlines separate segments as they do in the shell, and an unterminated `<<` (arithmetic, a quoted `<<`) keeps the text visible. `tests/test_credential_guard.py` is the guard's first test suite.
- **Desktop app: writes are no longer killed mid-way, and the UI can no longer get stuck.** From the same audit. Write commands (`bind`, `sync`, `upgrade --apply`, `skills install`, …) ran under the 20 s read timeout, so a slow one was killed half-applied and left a store lock every write then tripped over for five minutes; they now get five minutes. A timed-out call whose grandchild still held the pipes never settled; it now settles 500 ms after the process exits. In the renderer: unsaved settings of one project could reappear — and be saved — in the next project opened; a rejected IPC call left buttons, forms and the startup screen pending forever; a render error blanked the whole window (there are now error boundaries per screen and at the root); a failed project list had no retry; and closing the unbind, upgrade or bind dialog any way but "Done" left the list stale. `settings.json` is no longer rewritten over a file that failed to read (a hand-edited `cliPath` was lost), and its writes are serialised. A packaged build now keeps a rotating `main.log` for diagnosis. CI builds the app (`npm run build`) instead of only type-checking it, a missing CLI fails the real-CLI tests under `CI=true` rather than skipping them, and `npm run dist:win` exists for the Windows target.
- **`/devteam:health-check` wrote to the v2 paths in a bound project, so its own overdue warning never cleared.** It recorded `last_health_check` in `.dev-team-agents/user-data/state.json` while `session-start.sh` reads the `state.json` behind the `state-dir` pointer. On a project that had run `devteam upgrade`, categories 3 and 8 also recreated `user-data/` (a directory the upgrade retired) and backfilled a `preferences.json` nothing reads, and categories 9–11 looked for `state.json`, the local credentials file and the session summary where they no longer are — category 11 creating an empty session summary there. `setup-health-check/references/checks-list.md` now opens by resolving the state, memory and preference paths through `scripts/hooks/lib/data-dirs.sh` and whether state has moved to the store (`IN_STORE`), then routes a bound project's categories 1–3, 5 and 7–11: `devteam doctor` for links and scripts, `state_migrate_legacy` on the resolved state directory for legacy markers, `devteam sync` for a stale preference projection or `.gitignore` block, `devteam prefs set` for a value, and `devteam cred check` / `devteam cred import` for credentials. It never writes the resolved preferences, and never creates `user-data/` once state is in the store. Before an upgrade the `user-data/` `.gitignore` entry stays required, because that directory still holds the credentials file. A project that is not bound runs exactly as before.
- **`graphify-refresh.sh` records its build next to the graph, per checkout.** The script wrote the commit of its last build to `user-data/state.json`, and the health check read an older `.graphify-last-run` file the script no longer writes, so its "graph behind HEAD" check never fired. A first fix moved the marker into the main checkout's resolved `state.json`, which shared it across linked worktrees while each keeps its own `graphify-out/` — a worktree's build then made the main checkout skip a rebuild it needed. The marker is now `graphify-out/.build-commit`, versioned with the graph it describes; the old `graphify_last_run` key is read once as a fallback, in the main checkout only. Health-check Category 5d reads the new marker and reports the graph as behind only when a file was added, deleted or renamed under `targetPaths` — the script's own rebuild test — instead of after every commit. Also fixed: an empty `manifestPaths` aborted the build under `set -u` on bash 3.2 (macOS). `tests/test_graphify_refresh.py` covers all of it, including the worktree case.
- **The work-feedback gate lost its keys in an upgraded or imported project.** `skills/shared/work-feedback/SKILL.md` looked for the local credentials file only under `.dev-team-agents/user-data/`. After `devteam upgrade` that file lives in the directory the `state-dir` pointer names, and after `devteam cred import` the two `work_feedback_*` keys live in the credential reference files — so the gate fell back to its defaults and a `work_feedback_active: false` was ignored. It now reads the state directory first, then `<credentials>/<project_id>.json` and `global.json`, with the Read tool (the credential guard hook stops a shell read of the first file). The claim that the health check guarantees the keys exist is gone: in a bound project nothing recreates them.
- **`helpers/orphan-skill-scan.sh` reported three skill citations as duplicate loads.** "The Hard rule in `…/test-pyramid/SKILL.md`" in both test agents and "the dirty-worktree guard in `…/worktree/SKILL.md`" in `commands/merge.md` cite a rule in a skill the file already loads; `rule in` and `guard in` join the prose connectors the scan ignores, and every connector now has to start a word, so "safeguard in" or "foresee" no longer hides a load. A skill loaded twice is still reported.
- **`/devteam:version` printed `vunknown` and default preferences in a bound project.** It read `state.json` and `preferences.json` from `.dev-team-agents/user-data/`, the v2 location; a bound project keeps `state.json` behind the `state-dir` pointer and its preferences in `resolved/preferences.json`. The command now resolves both through `scripts/hooks/lib/data-dirs.sh`, the helper the session-start banner uses, from the main checkout root so it also works from a linked worktree or a subdirectory; outside a git repository it falls back to the current directory.
- **A project bound over a v2 install silently lost its preferences, and `devteam upgrade` then refused it.** The cascade reads the project layer from the store on every layout, so `.dev-team-agents/user-data/preferences.json` stopped applying the moment a project was bound — agents and the desktop app saw defaults and global values only — and `upgrade` later met the same file name at its destination and refused. `bind` and `sync` now import it: declared keys whose value fits the default's type go into the project layer, are read back, and only then is the file moved to the store's quarantine (`imported-preferences`) — never deleted. A value the project layer already holds wins; unknown or ill-typed keys are reported and stay in the quarantined copy. `bind --json`/`sync --json` gain `preferences_import` (additive, `null` without a file), the CLI prints one line for it, and the app's bind result says what was imported. ADR-0008 amendment.
- **The packaged macOS app aborted at launch** (`FATAL: Unable to find helper app`). Setting `CFBundleName` to "Dev Team Agents" made Electron look for `Dev Team Agents Helper.app`, while electron-builder names the helpers after `productName` (`dev-team-agents Helper.app`). No test runs a packaged build, so every suite passed; it was found by opening the `.dmg` build to check notifications. `CFBundleDisplayName` alone now carries the name (Finder, Dock); the bold menu-bar title of a packaged build reads `dev-team-agents` until `productName` changes.
- **Two `notifications watch` children could run at once.** A restart that landed while the first start was still awaiting its child found no handle to stop. Each start now carries a generation; a child from a superseded start is stopped as soon as it exists. Found on the packaged build, pinned by a test.
- **A code review of the notification work found four defects and ten smaller ones; all are fixed, each with a test.**
  - **A failing `watch` could never say why.** Under `--json` its error was an indented document, so the app read `{` as a protocol error and retried forever, and the exit-3 "unavailable" state was unreachable. The error is now one `{"event": "error", …}` line, even for a failure raised before parsing ends. The app lets a non-zero exit code win over an unparseable line, giving the child a second to exit on its own instead of killing it at once.
  - **One record with `"ts": null` broke `list`, `ack` and `watch`** until 200 newer lines trimmed it out, because the sort raised. Record keys are now type-checked, and a mistyped record is skipped like a malformed line.
  - **A control character in a message (an ANSI escape, a `\b`) made an invalid line**, and the notification vanished without a trace. `notify.sh` strips them.
  - **On Windows the login item was read back without the `--hidden` it was registered with**, so the app would have reported "not recorded" right after it was recorded. The check was against Electron's own typings, since `args` defaults to `[]`. Registering and reading back now share one `loginItemOptions()`.
  - **App:**
    - The losing instance of a double launch no longer reaches `whenReady`.
    - Concurrent notifications share one `devteam list` to name their project, and a failed listing is not cached.
    - A backlog of more than three records gets one summary banner, and acks run one at a time.
    - The backoff resets only after a child has stayed up for 30 s.
    - Closing the window quits instead of hiding when there is no tray to come back through. Windows `session-end` counts as a real quit.
    - A click on a notification is no longer lost when it lands before a fresh window has subscribed: the renderer takes the pending project once it listens.
    - A request that arrives over open settings is announced, then honoured when the user leaves them.
    - The bell is ordered by the record's time.
  - **CLI and hooks:**
    - `watch --interval` refuses anything below 0.01 s.
    - `watch` forgets ids its queues no longer report.
    - Append and trim in `notify.sh` run under a short `mkdir` lock.
    - Without a session id, the notifier's once-per-session keys fall back to once per day instead of `…:0`, which fired once and never again.
- **None of the framework's 138 project-relative paths resolved in a bound project, and two Stop gates were silently off.** The `core` pointer was documented as what made `.dev-team-agents/scripts/…` and `…/templates/…` work, but the text was never rewritten to `core/…`, so every one of them — `new-adr.sh` in `CLAUDE.md`, `graphify-refresh.sh`, `lib/state.sh`, the plan and ADR templates — pointed one directory too shallow. `03c-reuse-lint.sh` and `03d-design-token-lint.sh` look for their lint at that path and `exit 0` when it is missing, so the reuse-rule and design-token gates never ran in any v3 project. The test written for the pointer walked through it, which is the one path the text does not use; `tests/test_runtime_links.py` now binds this repository's real tree and fails on any cited path that does not resolve.
- **The v2 installers refuse to run in a bound project.** With `scripts/` linked at its documented path, `update.sh` would have re-vendored a v2 tree over the bind, `rollback.sh` restored one, `fix-symlinks.sh` repointed `.claude/` at directories a bind does not create, and a health-check `chmod +x` written through the link into the immutable store. `scripts/lib/bound-project-guard.sh` stops them on `project.json` and names the `devteam` command; `/devteam:update`, `/devteam:symlinks`, the update notice and the broken-symlink notice branch the same way, and the health-check fix patterns open with the v3 table. `ensure-claude-framework.sh` keyed "do not mirror" on the `core` pointer; it now keys on `project.json` or a linked `scripts`, since its `cp` would otherwise write through the new link into the store.
- **`bind` hid `.claude/settings.json` from git, so the hooks never reached a teammate.** The local exclude block listed every manifest path, the `settings` kind included — but that file is the project's own, merged into rather than generated. On a project that had not committed it yet, `git status` never showed it and `git add -A` skipped it; a project migrated from v2 escaped only because the file was already tracked. The block now takes only `bind.MACHINE_LOCAL_KINDS`, the same allowlist `doctor` uses for "must not be tracked", and the next `bind` or `sync` drops the line from an existing block. An existing test had pinned the defect ("git sees nothing under `.claude`") and now asserts the settings file is the one thing left to commit.
- **A project bound over a v2 install kept the v2 tree in git, and `doctor` said `ok`.** Found on a real project bound from the desktop app. `bind` replaced the relative links a v2 `install.sh` had committed with links into this machine's store — still tracked, so `.git/info/exclude` could not hide them — and left the vendored `.dev-team-agents/{agents,commands,skills,scripts,templates}` in place; `doctor` only looked for a v2 shape before `project.json` existed. The `bind` command now refuses a v2 install and points at `devteam migrate` (`--mode vendored` exempt; `sync` unaffected, because the check is in the command rather than in `bind()`). `doctor` reports a leftover v2 tree on a bound project, and both `doctor` and `migrate` list the machine-local bind artifacts git still tracks with the exact `git rm -r --cached` — never running it, and never naming `.claude/settings.json`, which is the project's own file.
- **The bind dialog reopened showing the last bind's result instead of a fresh form.** Found by the user binding a second project. The success path closed the dialog through the parent rather than through the dialog's own reset, so the previous "… is bound" summary stayed mounted. The whole form now resets on every open, pinned by a test — a defect of this shape comes straight back otherwise.
- **`projectNames()` was added to the bridge without an entry in `CHANNELS`**, so its channel string was declared twice as a literal, once in the main process and once in the preload, with nothing checking that they matched. That is exactly the drift `CHANNELS` exists to prevent for every other channel.
- **The desktop app's Windows leg stopped being a smoke test.** It ran **179 of 229** assertions when the runners were added; it now runs **203**, and the CI run is green on all three platforms. The blocker was structural: the fake-CLI fixtures are POSIX shebang scripts, and `invoke.ts` spawns the resolved path directly with `shell: false` — a security property, not a preference — so Windows, which honours no `#!` line and refuses `.cmd`/`.bat` without a shell, could not execute them at all. `app/test/fixtures/launcher.c` is a real Windows PE compiled from source at test time (never checked in) that runs `node <script> <args…>` and returns the child's exit code; `PASS_THROUGH_ENV` was **not** widened to carry a test variable, which was the tempting shortcut and would have let arbitrary code into a spawned child. No compiler on the runner means the affected tests skip, never a red suite.
  - Four platform defects were found closing it, each by measurement rather than inference. `CreateProcess` "must include the file name extension; no default extension is assumed", so a valid PE named `devteam` is not executed on Windows — the fixture now plants `devteam.exe`. Most of `resolve.test.ts` simulates `platform: 'darwin'`, which looks for an extensionless name the real host cannot produce, so those tests map to `'win32'` only when the host actually is Windows. `PATH` was joined with a hardcoded `':'` where Windows uses `;`. And the launcher re-joined argv with `_spawnv`, which does not escape an embedded double quote, so the handshake's inline `--client {"bind_manifest":1,…}` arrived mangled and the fixture died on `JSON.parse` writing nothing — the two failures were precisely and only the two scenarios that read an argv element. It now builds the command line with the documented rule the CRT's parser is the inverse of, **verified locally on macOS** rather than on the runner, because the quoting functions are plain C and the classic Windows argv bug is not worth discovering one CI round at a time.
  - **26 assertions still skip on Windows, for what the platform does not have rather than what the fixture cannot do**, and that is the honest residue: POSIX permission bits (NTFS has none, and `fs`'s emulated `mode` does not reflect ACLs), the SIGTERM escalation (`kill` there is `TerminateProcess`, immediate and unignorable, so there is nothing to escalate past), `HOMEBREW_PREFIX` (not a Windows concept, and `knownBinDirs('win32', …)` does not read it), the world-writable-directory refusal (`worldWritableDirProblem` is win32-disabled in production, so simulating `win32` would assert the opposite of the test's point), and `real-cli.test.ts`, whose subject is a python shebang script.
- **The app has its own icon, and the Windows installer has one at all.** The header showed the brand while the dock showed Electron's default atom, because `electron .` launches the stock binary — set now for development only, since a packaged build takes its icon from the bundle. Looking for the asset turned up the second half: `iconutil` is macOS-only and writes no `.ico`, so the Windows installer had no icon of its own. `build/make-icon.sh` now also emits a 1024px `build/icon.png` from the same padded canvas as the `.icns`, which electron-builder derives every other platform's icon from — no new tool, and no platform framed differently from another.
- **The header carries the brand lockup with the slogan cropped off.** It carried the symbol and the name as text because the brand guide warns against the slogan at a size that hurts its legibility; cropping the slogan removes that objection rather than overriding it. The crop is measured — decoding the transparent master's alpha gives the mark at rows 150..866 and the slogan at 1091..1274, so the cut lands in 224 rows of dead space — and `make-icon.sh` records the numbers and says to re-measure if the art is replaced. The brand pack has no transparent white-letter lockup, so the dark variant is the guide's own *negativa* on its solid black field, composited away with `mix-blend-screen` rather than a new treatment being invented for the mark.
- **CI runs on Windows and macOS, not only Linux.** All seven jobs ran on `ubuntu-latest`, so every Windows behaviour this repository claims was asserted by handing a pure function the string `'win32'` on a Linux host — and nothing had ever executed on Windows or macOS. The two jobs whose subject is portable now matrix over all three runners: `python` (the CLI's stdlib suite) and `app` (typecheck, lint, vitest), both with `fail-fast: false` so one platform failing cannot hide another's result. `lint`, `provider-contracts`, `slim-bootstrap`, `packaging` and `tag-name` stay ubuntu-only because their subjects are bash installers, shellcheck, ruby and jq. **This closes the execution gap, not the artifact gap** — `winget validate` and `winget install --manifest` still have never run, because they need an installer that has never been built.
- **The app diagnoses itself, not only the store.** `devteam doctor` covers the store, the machine, the registry and a project, and says nothing about the app — which it must not, because ADR-0015 makes the app a pure client and teaching the CLI to check its callers would invert that. So the app's own preconditions were observable and never evaluated, and the question a user actually asks ("is this app healthy, and is it too old for this store?") had no answer in the UI. `selfCheck()` is a pure synchronous function over values the bridge already returns — **no IPC channel, no preload surface, no new spawn** — reporting six categories (cli, version, declaration, settings, schemas, actions), with `status` as the worst level present. The Diagnosis screen now shows "This app" above "The store". It is what finally compares `min_app_version` against the app's own version, a value that had been read, displayed and never used. A store asserting no minimum stays `ok` rather than becoming a warning (that is today's state, on purpose); a handshake that did not answer is `warn`, because an unanswered handshake is not a passing one; a version string that cannot be ordered is reported as not comparable rather than silently passed.
- **The bind dialog recommends `link` and states what each mode costs.** Four bare radio labels, nothing preselected, and no hint that choosing `copy` means running `sync` by hand in every project after every update — which is the only thing the choice decides. `link` is now preselected and labelled recommended, each mode carries its consequence bound with `aria-describedby` so it is announced rather than merely adjacent, and both READMEs plus `CLAUDE-md/cli.md` say the same. **The CLI's `--mode` default stays `auto`**: it probes rather than trusting the platform name, so plain `devteam bind` on macOS or Linux already resolves to `link`, and changing a documented default of a public interface is a breaking change for scripted callers.
- **Desktop app — the project lifecycle is now writable (M4.3, second slice).** `bind`, `unbind`, `sync` (single and `--all`), `pin` (set and release) and `upgrade` (plan, then apply) are reachable from the Projects screen. ADR-0015 § 8 made this conditional on a real client having driven the declaration seam first; that condition is discharged, and the amendment records which commands remain deliberately unwired (`update`, `uninstall`, `store install|use|gc`, `export`/`import`, `migrate`, `prefs set|unset`, and every `cred` command) with the reason for each.
- **Two provenance rules behind the write surface.** Every write action names its target by `project_id`, resolved in the main process against the registry's own `list --json` answer before an argv exists — an id the registry does not know is refused with nothing spawned, so the renderer has no way to name a directory of its choosing. `bind` is the inverse, because it has no existing project to name: the main process opens the native directory picker itself and records the chosen path in a session-only offered set, and `bindProject` refuses any path not in that set.
- **`OperationResult.notice`** — a succeeding command's stderr, carried to the UI. `devteam bind` outside a git repository exits 0 with a complete payload and warns on stderr that the bind artifacts were added to no ignore file; the JSON has no field for it, so the app used to render a clean success and drop the one sentence that mattered.
- **Windows packaging shape for the app — decided: NSIS, per-user, unsigned by configuration.** `app/electron-builder.yml` gained a `win`/`nsis` block (previously absent on purpose, because the shape was undecided) and `packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/` holds the three-manifest scaffold, expressing the CLI dependency via `Dependencies.PackageDependencies` — winget's closest equivalent to the cask's `depends_on formula: "devteam"`. MSIX was rejected (refused outright when unsigned, not merely warned) and MSI (needs WiX for no benefit here). `packaging/README.md` carries the comparison and lists every placeholder with who must fill it. **Nothing has run `winget validate`** — Windows-only, and recorded as unverified.
- **Security scanner pass — the previously unverified tier is now measured** (`docs/reports/2026-09-29/00-security-scanners.md`). `gitleaks` 8.30.1 over the full history: **658 commits, 0 findings**. `osv-scanner` 2.6.0 over `app/package-lock.json`: 592 packages, one vulnerable (`extract-zip@2.0.1`, dev-only, two advisories, **no patched version published** — so there is no remedy at all, not merely no non-breaking one; the dependency path is `electron` → `extract-zip`, it ships in no artifact, and CI's `npm ci --ignore-scripts` never executes it). `semgrep` 1.176.0 over 416 files: 16 actionable findings, all one theme (GitHub Actions pinned to mutable major tags, registered as a fingerprint), and 17 false positives each verified line by line — including one whose suggested remedy would have made the store's secrets directory world-readable.

### JSON contract

Written under this fixed heading because ADR-0014 § 2 step 3 requires it whenever an output shape or an exit code moves. **Contract version: `1` → `1` (unchanged)** — the CLI is unreleased.

- **`devteam migrate` gains keys and a flag, and its pre-root refusal is gone.** Plan: `layout`, `install_dir`, `adopts_identity`, `memory_moves`, `context_paths_added`. Apply: `layout`, `adopted_identity`, `memory_moved`, `context_paths_added`, `retired_links`, `untracked`, `untrack_problem`. `--untrack` is new and exits 2 without `--apply`. A pre-v2.1.0 install is now migrated (exit 0) instead of refused (exit 4). Both key sets are pinned in `test_json_contract.AppFacingKeySetContractTest`, since the app reads them.
- **New:** `notifications list` (`{notifications, count}`, each record the nine queue keys plus `seen`), `notifications ack` (`{acknowledged, count}`), and `notifications watch`, whose `--json` stdout is **JSON Lines** — the second documented exception to "exactly one document" after `cred get`. Additive. A failing `watch` writes its error as one compact line with `"event": "error"` added to the usual error keys, and `--interval` below 0.01 is a usage error (exit 2).
- **`devteam sync` on a project bound over a v2 install: exit 0 → exit 4 (conflict)**, with the same `migrate` hint as `bind`. `bind --json` reports `scripts`/`templates` artifacts where it reported `core` — content, not shape; no key changed.
- **`devteam bind` on a v2 vendored install: exit 0 → exit 4 (conflict).** The old outcome succeeded while leaving the project half-migrated, so it was a defect rather than a decided outcome (ADR-0014 § 2's carve-out); the contract is also unreleased, so `json_contract` stays `1`.
- **`devteam migrate --json` gains `git_tracked_artifacts`** on both the plan and `--apply` payloads — committed links a bind replaces with machine-local ones, alongside the existing `git_tracked`. Additive.

### Fixed
- **Seven defects on Windows, every one found by the first execution of these suites on a Windows host** — the runners added in this same release paid for themselves before anything else did. macOS passed clean; Windows failed 33 of 420 python tests. **None was a test problem.**
  - **Native path separators reached strings that must be POSIX.** Relative paths were built with `Path` and emitted with `str()`. A git ignore pattern requires `/`, so `.dev-team-agents\core` in `.git/info/exclude` matched nothing and every Windows user's `git status` filled with bind artifacts. `bind-manifest.json` is how `unbind`, `doctor` and an idempotent re-bind recognise their own work, so a manifest written on Windows matched nothing anywhere. `vendored` mode's relative symlink target does not resolve in a POSIX clone, which is that mode's entire purpose. And `catalog --json` answered `agents\backend-developer.md` where every other platform answers `agents/backend-developer.md` — that one is the desktop app's contract under ADR-0011, so a Windows CLI was answering the app in a shape the contract does not describe.
  - **Absolute-path validation checked only the host's own flavour — a security gap.** `update` and `import` extract untrusted tarballs. `PurePosixPath("C:\Windows").is_absolute()` is `False` and `PureWindowsPath("/etc").is_absolute()` is `False`, so each platform waved through the other's escape shapes — including a drive-relative `\etc`, which pathlib calls relative and Windows resolves against whatever drive is current. `paths.is_absolute_on_any_platform()` takes the union and guards `project.validate()` and `update.safe_members()`. Pinned by tests that run on **every** host, because the gap was the flavour and not the platform.
  - **`devteam cred get` could hand back a secret with a trailing `\r`.** Its contract is "exactly the value and a newline, nothing else"; it wrote through text-mode stdout, which Windows translates. `TOKEN="$(devteam cred get …)"` strips a trailing `\n` and not a `\r`, so the carriage return rode inside the value into whatever consumed it.
  - **Any error message containing an em dash crashed on Windows.** A redirected stream defaults to the locale encoding there, commonly cp1252, and this codebase's own hints contain literal `—`.
  - **`doctor` reported `warn` on a perfectly healthy bind.** `os.readlink()` on Windows returns an absolute target carrying the `\\?\` extended-length prefix, which pathlib parses as a different anchor than `C:\`, so `relative_to()` raised on a symlink pointing exactly where it should.
  - **The app could resolve a `.cmd`/`.bat` shim it could never spawn.** `invoke.ts` uses `shell: false` — a security property, not a preference — and Node refuses to spawn `.cmd`/`.bat` without a shell, the hardening that closed CVE-2024-27980. Such a shim resolved and then failed on first use with an `EINVAL` naming no cause. It is now rejected with the constraint named; the names stay listed, because silence about a file sitting right there is worse than a rejection, and turning the shell on for this one case *is* the CVE.
  - **Every fixture holding a real git repository leaked on Windows.** Git marks its objects read-only and Windows refuses to unlink a read-only file, so `shutil.rmtree` failed with `WinError 5`.
- **One assertion was true only because CI had never run on Windows.** The `dpapi` probe was asserted unavailable "regardless of platform override"; on a real Windows host `ctypes.windll` exists and the probe correctly reports it available. `secrets.py` marked that backend UNVERIFIED precisely because it had never run on Windows. **It is now verified**: `SecretsDpapiRealRoundTripTest` drives the real `CryptProtectData`/`CryptUnprotectData` on the Windows runner — nine tests covering what no fake can reach, including that the stored blob is genuinely ciphertext (an assertion the existing reversible fake would fail), that `_dpapi_bytes_from_blob` copies out of the returned buffer before `LocalFree` releases it, and that a tampered blob is refused by DPAPI's own integrity protection rather than decrypting to something else. Proven to have executed rather than skipped: the Windows leg went from 422 tests / 30 skipped to 431 / 30, so all nine ran there, while macOS went to 431 / 9. Still unverified, and now named in the code rather than assumed covered: `_probe_dpapi()`'s failure branches, and behaviour under a roaming profile or a non-interactive service account.
- **`devteam doctor` sent a legacy project to the one command that cannot adapt it.** Every unbound directory got the same flat finding and the hint `Run devteam bind` — including a v2 vendored install and a pre-root `.claude/dev-team-agents/` install, for which `bind` is precisely the command that will not convert what is already there. The detection needed to tell them apart was already in the tree and unused: a v2 tree is now recognised with `migrate.detect()`, the same gate `migrate.plan()` uses rather than a second heuristic, and answered with `devteam migrate`; a `.claude/dev-team-agents/` tree is answered with `scripts/migrate-to-root.sh`. Reporting only — no repair runs and nothing joins `actions`.
- **A security claim that is false on Windows.** `secrets.py` described its fallback backend as "a mode-0600 JSON file". `os.chmod` on Windows can only flip the read-only attribute, so neither that 0600 nor the data store's 0700 directory mode is applied, and containment falls back to ACLs this code neither sets nor checks. It matters because a Windows user can land on this backend at all — `dpapi` is the one that should be reached there, and is now verified, so landing here means its probe failed. A 0600 claimed and not enforced is worse than one never claimed.
- **Three POSIX-only test groups now skip on Windows for a stated reason** rather than being made green by a weaker assertion: permission-bit assertions (NTFS has none, so `stat.S_IMODE()` reports a value the code never asked for), `test_release_bump.py` (its subject *is* a bash script, and two tests branch on `os.geteuid()`, which does not exist on Windows), and the staged-CLI run (Windows does not honour a `#!` line). The gates read the real host through `os.name`, never `paths.platform_key()` — that one is pinned by `DEVTEAM_PLATFORM` so a test can exercise another platform's store layout, which is the opposite question from what this filesystem can hold.
- **`fakeBridge`'s `buildInfo`, `resolveCli` and `handshake` were bare unconfigured `vi.fn()`s** in the renderer test support, so any screen that called them would have tripped over `undefined`. Given real defaults.
- **`devteam unbind` left behind the directories it emptied.** `.claude/agents`, `.claude/commands`, `.claude/skills` and `.dev-team-agents/resolved` stayed as empty directories — nothing broken, but four directories the project did not have before the bind and does not need after it. They are pruned deepest-first with `rmdir`, which is the whole safety argument: it refuses a directory that still holds anything, so a file a user put in `.claude/skills/` keeps its parent alive without the pruner needing to know about it. `.dev-team-agents/` itself always survives, because `project.json` and the two pointers live there. `removed_dirs` joins the payload — additive, so no `json_contract` bump under ADR-0014 § 2 — and the human output reports the count.
- **`devteam unbind` removed the pointers a layout-2 project needs to find its own memory.** `state-dir` and `memory-dir` were treated as generated projections and unlinked, the same as `resolved/preferences.json` — but `resolved` is regenerated from the preference cascade, and a pointer is not regenerated by anything after an unbind. The project was left saying `layout: 2` in `project.json` while nothing could resolve the store paths, so the next writer fell back to the in-project layout-1 path and created a fresh, empty `.dev-team-agents/user-data/state.json` beside a store copy holding the real state. They are now kept, reported in `kept`, and left in the local exclude block that the unbind otherwise clears — an entry unbind leaves behind still needs ignoring. Found by unbinding this repository, and verified by a full bind/unbind cycle on a throwaway project: pointers survive, no stub appears. `resolved/preferences.json` is still removed, asserted separately so the fix cannot drift into "keep every projection".
- **`devteam bind` refused on this repository, and `bind`/`sync` fought `upgrade` over `.gitignore`.** Two findings from actually running the commands. (1) `.claude/skills/release-prep/` shared its name with the shipped `skills/shared/release-prep/`, so bind refused at exit 4 rather than write a framework skill's symlink over a real directory. The two were never divergent duplicates — the shipped one is a generic checklist, the `.claude/` one a 10-step runbook for tagging *this* repository — so the fix is a rename to `repo-release-prep`, registered in `CLAUDE.md`, not a deletion. This resolves the twice-reopened fingerprint `ref-release-prep-skill-exists-twice-…`. (2) `bind` wrote the `.dev-team-agents/user-data/` ignore lines unconditionally, although a fresh bind records layout 2 and has no such directory — so every sync after an `upgrade` put back exactly what `upgrade` had retired, leaving a permanently dirty `.gitignore`. The entries are now layout-1 only, and the test that asserted the old behaviour was pinning the bug.
- **`devteam upgrade` did not exclude the layout-2 pointers it creates.** `.dev-team-agents/state-dir` and `memory-dir` hold an absolute path into one developer's store, so they can never be committed, and `upgrade` touched no ignore file after writing them. Narrower than it looks and the code says so: after a normal `link`-mode bind they are already excluded, because `bind` rebuilds the local exclude block from its artifact set and the pointers are artifacts. The case this closes is a block that does *not* have them — a `vendored` bind (which skips the exclude write), a checkout that became a git repository after it was bound, or a hand-edited block. The entries are unioned into the existing block rather than replacing it, which would have erased the 100+ artifact paths `bind` wrote. `git_exclude` joins the payload — additive, so no `json_contract` bump under ADR-0014 § 2 — and `local_exclude_file` moved from `bind` to `gitignore` now that two commands need it.
- **Write-action gating failed open.** Write buttons were enabled while `EnvironmentReport` had not yet arrived, which is precisely the window before the app has checked whether it can write its own schema declaration. It now fails closed, with the reason worded as a wait. The withheld reason also reaches assistive technology: a disabled button is not focusable, so a `title` on it alone was unreachable.
- **`EnvironmentReport.withheld[].command` had no specified format** — the one field both sides of the IPC contract must agree on with no type to enforce it, where a mismatch silently re-enables a withheld button. It is now pinned in the contract as the CLI's subcommand words, space-joined, matched exactly rather than by prefix.
- **`BuildInfo.noWriteActions` was typed as the literal `true`**, so admitting a write action required editing the type system itself. Replaced by `hasWriteActions: boolean`, with `mutatingCommandsRun` derived from the allow-list rather than hardcoded.
- **Leaked test temp directories.** `app/test/handshake.test.ts` cleaned up at the end of each test body, so a test failing earlier leaked a directory; moved to `onTestFinished`. 322 accumulated leftovers were removed, along with the Chromium profile Electron had written into the CLI's own store root before `app.setPath('userData', …-app)` fixed the collision, 173 keychain fixture items, and a stray `/private/tmp` bind that distorted every `devteam bind` under that directory.
- **`session-summary.md` had never been rotated** — 65 entries spanning 4.5 months, in a file agents load at startup. Trimmed to the 30-day window the Session Summary Rule specifies (14 entries); the other 51 were archived to `session-summary.archive.md` rather than deleted.
- **Stale test counts** in `docs/specs/v4-app-and-distribution.md`, in the three places that state them as current. The two dated Amendment Log entries keep their original numbers, because a log rewritten to match today stops being a log.
- **An installer URL placeholder that would have 404'd.** The app's winget manifest rendered the release tag's `v` prefix into the *filename* segment as well, but `nsis.artifactName` interpolates `${version}` without it.
- **Documentation corrections for M4.3 app slice**: Corrected test count from 102 to 133 in ADR-0015 amendment and `docs/specs/v4-app-and-distribution.md` (three instances); fixed `packaging/homebrew/devteam-app.rb` `zap` list to include `~/Library/Application Support/dev-team-agents-app` (the app's user data directory) and change logs path to `~/Library/Logs/dev-team-agents` (correct app name); clarified ADR-0015's "State of the tree" section to reflect that `app/` now exists; recorded in ADR-0015 § 5 that the resolution order table was corrected before commit, noting the divergence from what `app/src/cli/resolve.ts`'s comment claims; added amendment to ADR-0014 documenting the undocumented bypass where a declaration at or above the store's shapes passes unconditionally.

### Added
- **v3 milestone M1 — global core/data store, project bind and the `devteam` CLI.** The framework is installed once per machine instead of vendored into every project (325 files, ~2.3 MB, previously committed per repository). `scripts/cli/devteam` (python3, stdlib only) with the implementation in `scripts/lib/devteam/`: `path`, `version`, `store list|install|use|gc`, `bind`, `unbind`, `list`, `sync`, `pin`, `update`, `migrate`, `doctor`. Decisions recorded in ADR-0007 through ADR-0011; acceptance criteria in `docs/specs/v3-global-install.md`; reference in `CLAUDE-md/cli.md`.
- **Two stores with different lifetimes.** `core` holds `versions/<X.Y.Z>/` and a plain-text `current` pointer (not a symlink — that would put the Windows materialisation failure at the most load-bearing path in the design). `data` holds the registry, preferences, per-project directories and quarantine, and survives uninstall — on Windows it lives in the roaming profile. `$DEVTEAM_HOME` overrides both and is the test seam.
- **Per-project version pinning.** A project with no pin follows `current`; a pinned project stays put until released, so one `devteam update` can move nine projects and leave the tenth alone. `store gc` never removes `current` or a pinned version, and previews by default.
- **Three bind modes**, recorded in `registry.json` so a fallback is never silent: `link` (macOS/Linux), `copy` (Windows without native symlink support — `auto` probes rather than guessing from the platform name), and `vendored` (v2 behaviour, opt-in for CI, containers and air-gapped repos).
- **Committed project identity.** `.dev-team-agents/project.json` carries `schema`, `project_id` (UUID) and `context_paths`, so identity survives a re-clone, a directory move and a machine change. `devteam doctor` re-points a moved project by its identity, and **reports** rather than merges the fork case where two checkouts share one `project_id`.
- **`devteam migrate`** converts a v2 vendored install into a bind: previews unless `--apply`, moves the vendored trees into `data/quarantine/<date>/<project_id>/v2-install/` (never deletes), leaves `user-data/` and `docs/` untouched, and reports the `git rm -r --cached` the user must commit themselves.
- **`scripts/lib/devteam/quarantine.py`** — the No-Destruction Rule in code. Only symlinks (regenerable) are unlinked; every real file or directory dev-team-agents would otherwise remove is moved to a dated quarantine under the data store.
- **Python CI gate** (`.github/scripts/ci/03-python.sh`, blocking): byte-compile plus 78 unit tests. The repository previously had **no** python check at all — `01-lint.sh` runs shellcheck, which does not read `*.py`, and the most complex logic in the tree is now python.
- **`tests/`** — stdlib `unittest` suite for the CLI, stripped from the installed package by `scripts/lib/strip-tarball.sh`.

### Added — v3 milestone M2

- **Preference cascade in three personal layers**: shipped defaults → global user
  (`data/preferences.json`) → this project (`data/projects/<id>/preferences.json`). Resolved **on
  write** into `.dev-team-agents/resolved/preferences.json`, so agents keep doing one file read and no
  merge logic enters any agent body. `devteam prefs list|get|set|unset` reads and writes the layers —
  `list` names the layer each value came from, and writes never touch the projection.
- **Consent keys are withheld, not defaulted.** `telemetry` and `auto_update` resolve to `false`
  whenever no layer sets them, reported as `consent-withheld` rather than `defaults`, so "the user
  was never asked" stays distinguishable from "the user accepted the default". Carries over the v2
  `CONSENT_KEYS` rule into the cascade.
- **`layout` in `project.json`, and `devteam upgrade`** — a consented structure upgrade that moves a
  project's memory into the data store and leaves the project clean. `layout` is distinct from
  `schema`: `schema` is the file's format, `layout` is where the project's state lives. **No other
  command relocates memory**: `bind`, `sync`, `update` and `migrate` report a stale layout and stop.
  The upgrade previews unless `--apply`, copies every file, verifies each by sha256, and only then
  retires the original to quarantine; a populated destination aborts before anything is copied.
  Decision and the alternatives in ADR-0012.
- **A new project is born clean.** A bind that finds no `user-data/` creates the project on the
  current layout, so only projects that actually carry v2 memory ever have an upgrade to run.
- **`.dev-team-agents/state-dir`** — a one-line pointer with the absolute path of the project's state
  directory. `scripts/lib/state.sh` resolves it with a single file read, because asking the CLI would
  put a python subprocess inside every hook invocation.
- **`installed_version` is stamped by the bind.** `/devteam:version`, the session banner and
  telemetry read it from `state.json` and no v3 path wrote it, so a migrated project reported its v2
  number forever. Retiring the key and repointing those four readers stays open (ADR-0007); this
  makes them truthful now, without losing other keys in the file.
- **`context_paths` reaches the context loading order.** The first entry is the write root (`docs` by
  default); any additional entry is an extra knowledge folder, **read-only**. Documented in
  `skills/shared/project-context/SKILL.md` § Context Loading Order alongside how to resolve `layout`.
- **Store portability**: `devteam export` archives the data store (quarantine included);
  `devteam import` restores it, refusing a populated store without `--force` and rejecting unsafe
  archive members; `devteam uninstall` removes the core and **keeps** the data store unless given
  `--purge --yes`.
- **`data/` is split into a portable subtree and `data/machines/<machine-id>/` (ADR-0013).** An
  inventory of a populated store found exactly two record types carrying absolute paths —
  `registry.json` and `bind-manifest.json` — plus `state.json` carrying facts true only of the
  machine that wrote them (`installed_version` is *this* machine's core version). Those move under
  the machine subtree, together with `locks/` (a lock names a pid), the dot-markers (caches, ETags,
  day stamps) and `credentials.local.json` (values, not references — a secret that rides along in a
  routine export is a secret in one more place). What the user authored stays portable: preferences,
  session summaries, credential references, quarantine. `paths.is_machine_local_record()` is the one
  answer to which side a record belongs on.
- **`devteam export` is portable by default; `--all` includes this machine's records.** A portable
  archive plus each project's committed `project.json` is enough to rebuild a bind elsewhere with
  `devteam bind` — the registry and manifests are regenerated under the receiving machine's own
  identity instead of arriving full of paths that do not exist there. An import that carries no
  machine subtree keeps the receiving machine's own `machine-id` and `machines/`; promoting it
  verbatim would have left every bound project reading as unbound.
- **`devteam upgrade` splits the v2 memory directory as it copies** — `session-summary.md` and the
  project preferences to the portable subtree, `state.json`, the dot-markers and the secrets to the
  machine subtree. `.dev-team-agents/state-dir` names the machine one, because `state.json` is what
  reads through it.
- **`data/machine-id`** — one UUID per machine, created on first use with `O_EXCL` so concurrent first
  uses converge on one value. `DEVTEAM_MACHINE_ID` overrides it and is the seam that lets a test open
  the same store as another machine. Reported by `devteam path` and `devteam doctor`.
- **A store written before the split is relocated once**, from `cli.main` before any command reads the
  registry — otherwise every bound project would have read as unbound. Idempotent, `os.replace` per
  file so a record is never in neither place, and it quarantines rather than overwriting an occupied
  destination. It moves nothing inside any project.
- **No synchronisation exists or is implied.** ADR-0013 makes one possible; `export`/`import` stay
  explicit and manual.

### Added — v3 milestone M3

- **`devteam cred` — credentials as references, values in the OS secret store (ADR-0010).** v2 kept a
  plaintext `credentials.local.json` in the project tree, which conflates two different things: *which*
  credentials a project needs, which is worth reviewing and diffing, and *what they are*, which must
  never be either. The two are now separate. `data/credentials/global.json` and
  `data/credentials/<project_id>.json` hold references — `purpose`, `source`, `ref`, `scope` — and are
  portable precisely because they hold no value. Commands: `cred list`, `get`, `set`, `unset`,
  `import`, `check`, `backends`, with `--global` to act on the shared layer.
- **Three value backends, probed rather than guessed.** `keychain` on macOS through `security`, `dpapi`
  on Windows through `ctypes` and `CryptProtectData`, and `insecure` — a mode-`0600` JSON file that is
  **not encrypted** and is reported loudly by `devteam cred check` and `devteam doctor`, because a
  last resort that looks equivalent to the other two is a trap. The `age`/`sops` backend ADR-0010
  lists is **deferred and deliberately absent from `BACKENDS`** rather than present-but-unavailable:
  it needs a passphrase per run and the CLI has no interaction model for that, and a declared surface
  with no implementation drifts. `dpapi` is implemented but **unverified on real Windows hardware**.
- **A value never reaches argv.** `devteam cred set` reads it from stdin — a prompt without echo when
  interactive, the pipe otherwise. A secret in a command line is in the process table for every other
  user on the machine and in the shell history of this one. The `keychain` adapter passes it through
  `security`'s stdin for the same reason.
- **`devteam cred get` writes the value to stdout and nothing else, and refuses `--json`.** That makes
  `TOKEN="$(devteam cred get k)"` work without a parser, and it is a deliberate, documented exception
  to the `--json` contract: wrapping a secret in a document puts it into a structure a client is
  likely to log. An exception to a stated contract is recorded next to the contract rather than left
  to be discovered.
- **Every read is scope-checked and audited.** `data/machines/<machine-id>/projects/<project_id>/audit.log`
  is append-only JSONL: who, when, which key, which layer, what outcome — and never the value, nor
  anything derived from it, not a length or a hash or a prefix. A scope refusal and a missing value
  are audited too, since a failed read is exactly what an audit trail exists to show. The log is
  **machine-local**: it records reads that happened on *this* machine, and two machines appending to
  one portable log would need merge semantics nothing here has.
- **`devteam cred import` migrates a v2 file, opt-in, on a named path, and never scans for
  candidates.** Ordering is copy → verify → retire, the same one `devteam upgrade` uses: each value is
  stored and read back before anything is given up, and the original is **moved to quarantine**, never
  deleted. `work_feedback_active` and `work_feedback_interval_minutes` are not secrets and are carried
  across as plain values. The no-scanning rule has a proof case in this repository: its root-level
  `credentials.local.json` is read on purpose by `docs/prompts/posthog-metrics-report.md`, and an
  importer that looked for candidates would have moved somebody's working file.
- **A `PreToolUse` guard** (`scripts/hooks/pre-tool-use/03-credential-guard.sh`) refuses the obvious
  spelling of dumping a credential store and warns on echoing a resolved value. It is **hygiene and
  auditability, not a sandbox**, and the implementation says so in those terms: it matches command
  text, so `c""at`, a variable, base64, a python one-liner or a here-doc walk past it, and it sees
  only Bash tool calls — `Read`, `Grep` and MCP tools are invisible to it. It is tuned hard for
  precision because a false positive gets a hook deleted, and it carries an escape hatch
  (`DEVTEAM_CRED_READ_CONFIRMED=1` as a command prefix) for the same reason. What it buys is a loud,
  attributable stop on the spelling an agent reaches for by default, and a pointer at the one read
  that audits itself.
- **An unrecognised backend name is a finding, not a parse error.** Validation refused any `source`
  outside the built-in list, which meant a reference file written by a newer CLI, or restored from a
  machine with a backend this build lacks, made `devteam cred list` and `devteam doctor` fail hard on
  a file they should have been able to describe. It also made the resolver's own `unknown-source`
  finding unreachable — dead code, which is how the defect was noticed. Structure is validated; the
  set of known backends is reported, and a read of such an entry fails at use time with the backend's
  own error.
- **The guard also refuses a force-add of the v2 plaintext file.** ADR-0010 names the concrete blast
  radius in its own Context — one force-add away from a public repository — and a guard that covered
  reading but not committing would have missed the only failure that cannot be recalled. Three tiers:
  a named protected path with the force flag is refused; a sweep (`.`, `-A`, a directory, a glob) with
  the force flag is refused **only when something protected actually exists beneath the target**, so
  force-adding an ignored build artifact stays silent; and without the force flag nothing fires,
  because git already skips an ignored file. Read-only git subcommands (`log`, `show`, `diff`,
  `blame`, `grep`) stay silent — the two git subcommand lists, one exempting and one refusing, sit
  next to each other with a note that every other subcommand is in neither on purpose.
- **Deliberately uncovered, and recorded so the gap is not "fixed" into noise**: `git update-index
  --assume-unchanged`/`--skip-worktree`, and a `.gitignore` edit that un-ignores a protected path.
  Neither is decidable from command text — the first is one step of a sequence whose danger lives in
  the other steps, and the second depends on the interaction of every pattern in the file plus the
  nested ones below it, which means asking git after the fact rather than matching the edit.
- **`devteam doctor` reports credential drift**: a reference whose value is gone is a `fail` because
  the credential cannot be used at all; a value in the plaintext backend is a `warn` because it works
  and the user may have no alternative on their platform.

### Added — v3 milestone M4.1 (the contract the desktop app needs)

ADR-0011 makes the desktop app a **client of the CLI**: every screen invokes
`devteam <command> --json` and nothing about bind, preferences or credentials is
reimplemented in the app. The ADR states the price plainly — "a stable JSON contract on
every subcommand, with contract tests in CI" — and that contract was not tested, so M4
is split and the contract lands before the client. Building a pure client against an
unverified contract is building on sand.

- **`devteam catalog`** — `catalog` for a summary (valid with no subcommand, unlike
  `store`/`prefs`/`cred`), `catalog agents|skills|commands` for the entries, and
  `catalog show <name>` for one entry's metadata and body. It is the command behind the
  app's read-only browse screen, which had no command behind it at all, and it answers a
  question a terminal user also asks: which agents does this project actually have, and
  from which version. Three deliberate behaviours: it reads from the version the project
  is **bound to** rather than whatever tree you are standing in; it **creates nothing**,
  including not minting a machine identity; and a file with malformed frontmatter comes
  back flagged with its path instead of killing the listing, because a catalog that dies
  on one bad file is useless for finding the bad file. Frontmatter is read by a ~20-line
  stdlib reader rather than by adding a YAML dependency.
- **`devteam version --json` carries a `compat` block** —
  `{"json_contract", "min_app_version", "store_schemas"}`. ADR-0011's "compatibility is
  declared, not assumed": a client reads it before writing and degrades to read-only when
  the store carries a shape it does not understand. It **surfaces the schema numbers that
  already exist** (`project`, `project_layout`, `registry`, `bind_manifest`,
  `credentials`) rather than inventing a second versioning scheme beside them, and reads
  each from the module that owns it so no copy can go stale in the direction that tells a
  client it is safe to write. `unsupported_by()` treats a shape the client is **silent**
  about as unsupported: silence is not a claim of support, and treating it as one is how a
  client writes a structure it has never seen. `min_app_version` is `null` until an app
  ships — the field exists now so the first app can rely on reading it.
- **The `--json` contract is swept across the whole command surface**
  (`tests/test_json_contract.py`), with the commands **discovered from the parser** rather
  than a hardcoded list — a hardcoded list goes stale the moment someone adds a command,
  which is the exact failure the sweep exists to prevent, so the walk asserts its own
  integrity too. Every command, in three store states, must exit in {0,1,2,3,4}, put
  either nothing or exactly one parseable document on stdout, carry `ok`, and keep
  warnings on stderr in both modes. `update` and `uninstall` are excluded by name with a
  stated reason. `cred get`'s refusal of `--json` is pinned as **conforming** so nobody
  later "fixes" the sweep by making it emit the value. No violations were found.
- **`devteam compat`** — the reader the published numbers were missing. Bare, it reports what the
  store requires; with `--client '<json>'` or `--client-file <path>` it returns an explicit
  `may_write` boolean plus, when false, the blocking shapes with both numbers. An architecture review
  found that `compat.unsupported_by()` had no caller and no CLI surface, which matters more than it
  looks: if the framework only publishes schema numbers and leaves the comparison to the app, the
  compatibility rule **is** reimplemented in TypeScript — in the one place where getting it wrong
  means writing a structure the client does not understand. ADR-0011 forbids exactly that for bind,
  preferences and credentials; compatibility is not a special case. Incompatibility exits **1**,
  because a well-formed question with a real negative answer is "findings", the same meaning the code
  already carries for `doctor` and `sync`; malformed client input exits 2, a different failure class
  that must never read as a real "no". A client claiming a shape *higher* than the store's may write —
  a newer client on an older store is the direction that works.
- **The app-facing payload shapes are pinned key by key.** The sweep proved every command emits one
  well-formed document with `ok`; it did not prove the document still has the fields a client reads,
  so dropping `project_id` from `bind --json` passed every check — the exact regression ADR-0011 calls
  breaking. Sixteen commands now have their top-level key set pinned exactly, plus the record shape
  for the five list-shaped ones, because that is what a table in the UI binds to. A failure names what
  was added and what was removed separately and says that the decision is whether the change is
  breaking, not whether to update the expected value.
- **The Homebrew cask now depends on the formula.** The review found the two were independent
  installs, so nothing decided which `devteam` the app invokes — an older CLI writing a newer store is
  precisely the case `compat` exists to detect and the one nothing was preventing. The app must still
  call `devteam compat` before it writes, because a user can upgrade the store from a terminal without
  touching the app.
- **`cred check`'s payload no longer changes shape with the data.** `problems` appeared only when
  there were findings, so a client doing `payload.problems.length` would have worked until the day
  everything was fine. It is now always present, empty list included — `main()`'s exit-1 check is
  truthiness-based, so an empty list still means success. Found by the key-set pins on their first run,
  which is the whole point of having them.
- **`packaging/`** — a Homebrew formula for the CLI, a cask for the app, winget manifests
  (manifestVersion 1.12.0, confirmed against the schema files in `microsoft/winget-cli`
  rather than guessed), `.github/workflows/release.yml` which computes the tarball's
  `sha256` from the artifact rather than carrying a hand-written one, and
  `packaging/README.md` as the operator runbook.

  **None of it is verified, and it is labelled as such rather than presented as working.**
  macOS signing and notarisation need an Apple Developer ID; the Windows installer needs a
  code-signing certificate; a tap needs a published `homebrew-*` repository; winget
  publication is a reviewed pull request to `microsoft/winget-pkgs`; and there is no
  release tarball, so no real `sha256` exists. Placeholders are deliberately impossible to
  mistake for real values, because a plausible-looking fake hash ships without anyone
  noticing: Homebrew carries non-hex strings, and winget carries 64 literal zeros because
  its schema enforces a hex pattern and an unparseable string there would fail for the
  wrong reason. The runbook lists every placeholder and where its real value comes from.

  The formula's install set was verified by running the CLI from only the files it
  installs: the entry point plus the 25 python modules, with no other part of the
  framework present.

**The Electron app itself is not built.** It is M4.3, and it is blocked on signing
credentials the repository owner holds — not on anything in this repository.

### Added — v3 milestone M4.2 (proving the distribution scaffold)

M4.2 shipped the packaging files with nothing checking them: no CI job read
`packaging/` at all, the release workflow's formula rewrite lived inline in YAML where
only a real tag push could ever run it, and the only stated verification was three
commands `packaging/README.md` asked a human to type. This closes the gap between what
that directory looked like and what anything actually asserted about it.

- **`packaging/verify-formula-locally.sh`** — the Homebrew formula has now really been
  installed, **once, on one maintainer's machine**: a recorded run, not a channel. The
  script builds a tarball with `git archive … HEAD` — committed sources, not the working
  tree — in GitHub's tag-archive directory shape, creates a uniquely-named, git-less
  **throwaway tap**, and runs `brew style`, `brew audit --formula`,
  `brew audit --strict --online`, `brew install --build-from-source`, `brew test` and a
  smoke test of the installed binary, tearing down in a trap. The throwaway tap is the
  whole trick: `packaging/README.md` used to record `brew install`/`brew audit` as
  impossible here because no tap exists, and the premise was right but the conclusion
  was not. Homebrew 7 rejects a formula file that is **not inside a tap** (the path form
  itself is fine — this script's own install passes a path), separately disables
  `brew audit <path>` outright, and will not load a formula from an untrusted tap — so
  the script makes a tap, trusts it inside a sandboxed `trust.json`, and removes both.
  Requires Homebrew ≥ 7, checked in preflight. Run on macOS against Homebrew 7.0.6: the
  install block ran unmodified, `brew test` passed, and the installed `devteam` answered
  `path --json` and `version --json` with one `ok: true` document each and created no
  store. It verifies its own teardown — formula uninstalled, tap gone, the real
  `trust.json` and the tracked formula both byte-identical — because a verification
  script that changes the machine and says nothing about it is not one anybody will run
  twice. Two changes it does **not** undo, and says so: formulae Homebrew pulled in
  transitively are reported rather than removed (something else may now depend on them),
  and `brew style`/`brew audit` bootstrap ~100 MB of Homebrew dev gems into
  `Library/Homebrew/vendor/bundle`, which is permanent by design — deleting that tree
  would damage Homebrew's own state. `--keep` skips the **teardown only**; the
  `trust.json` and tracked-formula assertions are read-only and always run. It has a
  release mode (`--tag/--url/--sha256`) for a real released artifact.
- **`brew audit` found three real problems the file had been carrying**, now fixed and
  re-verified clean: `Formula[…].opt_bin` where `formula_opt_bin(…)` is wanted, and two
  `refute_predicate` assertions where `refute_path_exists` is wanted. `brew style` and
  `brew audit --formula` are clean afterwards, as is `brew audit --strict --online`.
  This is the argument for the script in one line — the formula had passed `ruby -c` for
  its whole life and was still wrong in three places.
- **`brew audit --new` is deliberately not run, and its result must not be quoted.** An
  earlier version of this entry claimed it was clean, which is the most misleading thing
  this milestone said. Every new-formula check in Homebrew 7's `FormulaAuditor` is gated
  on the core tap — the four git-forge notability checks reach it through
  `get_repo_data`'s `return unless @core_tap` (`formula_auditor.rb:858`), the rest
  directly — so on a private-tap formula `--new` is byte-identical to
  `--strict --online` and reports nothing about homebrew-core eligibility. And it would
  not pass if it were reached: `SharedAudits.github("Dev-Toolbelt", "dev-team-agents")`
  called directly returns `GitHub repository not notable enough (<30 forks, <30 watchers
  and <75 stars)`. So the stage is gone, replaced by `audit-strict`, which runs the two
  flags `--new` degrades to under their own name — and `--online` does buy real coverage
  in release mode, where the url is a live GitHub artifact. A stage whose "clean" means
  "the checks did not run" reads as an endorsement nobody earned.
- **The python dependency had already drifted, and the drift is now reported rather than
  remembered.** The formula declared `python@3.12` while homebrew-core's `python3` had
  moved to `python@3.14`, so every installer would have pulled a second, older python
  (~68 MB) for devteam alone. It is now `python@3.14`, and the version appears in exactly
  **one** place: `install` reads it back off the declared dependency instead of writing
  the interpreter basename out a second time, which is how the old pair got to disagree
  unnoticed. `verify-formula-locally.sh` parses that line, resolves
  `brew info --json=v2 python3`, and prints the two side by side on every run. The
  runbook listed "check this by hand before publishing" as a manual step; it no longer
  does.
- **`tests/test_packaging.py`** (12 tests) — the CI-portable half of the same question.
  It parses the formula's own `install` block to derive what the formula stages, so it
  cannot drift from it, stages exactly that, applies the `inreplace` shebang rewrite, and
  runs the CLI out of the staged tree through `subprocess` only — importing the `devteam`
  package would put the repository's `scripts/lib` on `sys.path` and quietly satisfy an
  import the payload is missing. Its bound is documented in the module: only the
  `.install` lines are read, so a later `rm_f` or `mv` in the same block is invisible and
  nothing here proves the block does not *subtract* from the payload. This
  **deliberately overlaps** the script above, and `packaging/README.md` documents it as
  two layers rather than duplication: the test runs on Linux wherever CI runs — every
  pull request and every push to `main`/tags, which is what `ci.yml`'s trigger covers,
  not "every push" — while the script is the real thing and needs `brew` on PATH.
  Neither can replace the other. The two are also not symmetrical about what they derive
  from the formula: the test derives the whole payload, the script derives only the
  python dependency and hardcodes the layout paths it asserts afterwards.
- **The release workflow's formula rewrite is out of the YAML.**
  `.github/scripts/release/bump-homebrew-formula.sh` holds what used to be two inline
  `run:` blocks, and `tests/test_release_bump.py` (23 tests) drives the real script
  against copies of the real formula: placeholder bump, idempotence, re-bumping an
  already-released formula, malformed tags and digests refused, a repo name carrying a
  regex metacharacter unable to match a different repo, and every untouched line asserted
  byte-identical. Inline it could only ever run by pushing a tag, so the case it was
  written for — a formula already carrying a *previous* release's tag and digest — was the
  least likely of all to be right. The write is now staged to a sibling temp file and
  renamed into place only after verification passes, so a failed run leaves the formula
  byte-identical instead of half-rewritten. Two further defects the extraction exposed
  are fixed: the url verification is now **repo-qualified** — it matches the whole
  `url "https://github.com/<repo>/archive/refs/tags/<tag>.tar.gz"` line, not the tag
  fragment, so a wrong `--repo` can no longer write this release's digest into a formula
  whose url already carried the requested tag and exit 0 — and a formula in which more
  than one `url "…"` or `sha256 "…"` would be rewritten is **refused** rather than
  rewritten on a guess about which digest is the stable one. A `bottle do` block still
  bumps correctly: its digests are keyword arguments and carry no `sha256 "` for the
  anchor to match. The two `-w` writability checks are diagnostics, not gates — `-w` sees
  neither an ACL nor a read-only mount — so `mktemp` keeps its own failure path.
- **`release.yml` gained a `macos-latest` job.** The bump job uploads the rewritten
  formula as an artifact; this job downloads it and asserts its `url` and `sha256` equal
  the digest that job computed, that the url ends in the right tag, and that **nothing
  else in the file changed** (both files normalised on those two values and diffed —
  which is exactly what the rewrite's own after-the-fact grep cannot see). It then runs
  `verify-formula-locally.sh` against the real released tarball and that digest, passed
  between the jobs as an output rather than re-downloaded. **It is not a gate**, and its
  own `RESIDUAL` block says so: the PR is opened by the bump job's last step, so it is
  already open while this job runs, and no branch rule marks the check required — a red
  check informs whoever merges. **Never executed.** No tag has been pushed since the
  workflow was added, and the Actions run remains the untested part: the tag-validation
  step, codeload timing and its retry loop, the PR creation, the artifact hand-off and the
  digest passed between jobs.
- **`packaging/` has a CI gate at all** — `.github/scripts/ci/04-packaging.sh` plus a
  `packaging` job in `ci.yml`, which runs on every pull request and every push to
  `main`/tags. (Not "every push": `ci.yml` scopes `push` to `main` and tags, so a branch
  with no open PR gets no CI at all — the workflow's own header states that trade-off.)
  `ruby -c` on both formulas; and for the winget manifests: YAML parse, classification by
  the **declared** `ManifestType` rather than the filename — which cannot distinguish
  `defaultLocale` from an additional `locale` manifest, and used to report a spec-correct
  extra locale file as six findings, all six wrong — the filename then checked against
  that type, the required-field set per type, no two manifests declaring the same
  `PackageLocale`, agreement of
  `PackageIdentifier`/`PackageVersion`/`ManifestVersion`, the version-**directory** name
  matching `PackageVersion`, digest format, and `InstallerUrl` ↔ version agreement that
  refuses a half-done bump in either direction. That last cluster exists for one
  documented edit: a version bump lands in four places by hand, coordinated by nothing.
  The `InstallerUrl` origin is checked unconditionally against a prefix **derived from**
  `scripts/install.sh`'s own `GITHUB_OWNER`/`GITHUB_REPO` — a file outside `packaging/`,
  so the edit that redirects the URLs cannot move the goalpost with them — and the tag is
  parsed out of the URL and compared for exact equality, not substring-matched, so
  `v1.0.0-rc1` no longer satisfies `1.0.0`. A 64-zero `InstallerSha256` **fails** once the
  version and the url tag are both real, with no manual promotion needed. A missing `ruby`
  or an unimportable `pyyaml` is exit 2, not a skip. Two advisories fire today and are
  meant to — the Homebrew placeholder is still in place and winget is still at the
  `0.0.0`/`vX.Y.Z` scaffold — anchored on the `url`/`sha256` **directives** rather than a
  whole-file grep, so they stop firing once real values land instead of matching the
  formulas' own explanatory prose forever. The promotion condition for each is recorded in
  the script.
- **`packaging/` and `.github/scripts/` are shellchecked at all.** `01-lint.sh`'s target
  set is now `scripts helpers .github/scripts packaging` — 67 `*.sh` files, up from 55.
  Neither directory was linted by any gate before, which means
  `verify-formula-locally.sh`, `04-packaging.sh` and `bump-homebrew-formula.sh` were all
  written unchecked.
- **`packaging/README.md` now separates what is proven from what is not, row by row**, and
  each proven row names the test or the recorded run that asserts it. The same split is
  re-marked in `docs/specs/v4-app-and-distribution.md`, whose `[MET]` legend now
  distinguishes a test that passes in CI from a recorded run on a maintainer's machine —
  this milestone produced the first criterion only the latter can assert.
- **A new section records the Windows installer shape without deciding it.**
  `DevToolbelt.Devteam.installer.yaml`'s `InstallerType: exe` stays an honest placeholder;
  replacing it with an unverified choice would be worse. Instead the runbook states three
  candidates — a signed `.exe`, `zip` + `NestedInstallerType: portable` around a built
  `devteam.exe`, and the same nest around the python sources plus a launcher with a
  `Dependencies.PackageDependencies` entry for python — and the exact test that
  discriminates each, so whoever has a Windows machine settles it in one sitting. The
  enums, the `NestedInstallerFiles` fields and the two `PackageDependencies` levels were
  read from `microsoft/winget-cli`'s v1.12.0 installer schema, cited in place. The open
  question between the last two is whether a `portable` nest accepts a non-`.exe` file
  such as a `.cmd` launcher: the schema does not constrain it, Microsoft's manifest
  documentation does not address it, and only `winget validate` and
  `winget install --manifest` on Windows answer it. Two bounding constraints from that
  same documentation are recorded with it — winget manifests support neither anchors,
  complex keys nor sets, and winget-pkgs requires that every tool support a silent install.

**Still unproven, and labelled as such:** no `homebrew-devteam` tap hosts the formula and
no release tarball has been installed from one — the one recorded `brew install` used
`git archive … HEAD`, not GitHub's codeload bytes; `release.yml` has never run; no Windows
installer has been built, so `winget validate` has never seen these manifests; and
`devteam-app.rb` has no artifact, so `brew audit --cask` has never been attempted. Be
precise about that last one: the missing `.dmg` blocks the install, the digest and the
codesign/notarisation checks, and nothing else. Static checking of the cask is not blocked
and is **not clean** — `brew style` reports four cask-cop findings today
(`Cask/StanzaOrder` ×2, `Cask/StanzaGrouping`, `Cask/ArrayAlphabetization`), none of them
fixed, recorded as a known state in `packaging/README.md`. Signing, notarisation, the tap
repository and the winget pull request remain blocked on accounts and third-party review
the repository owner holds.

### Added — the client write gate (M4, after M4.2)

`devteam compat` answered "may this client write?" and nothing made the answer binding — the gap
`docs/specs/v4-app-and-distribution.md` recorded as *"nothing on the framework side refuses a client
that never asks"*. Half of that sentence is now closed and the other half is closed **by decision**.
Decided in ADR-0014, which narrows ADR-0011 without touching its Decision; reference in
`CLAUDE-md/cli.md` § *The client write gate*.

- **A caller can declare what it understands, and is held to it.** `--client-schemas <PATH>` is global
  — accepted before or after the subcommand, like `--json` — and `DEVTEAM_CLIENT_SCHEMAS` names the
  same file in the environment, because a client invokes many commands per session and exporting once
  is the difference between a gate that is honoured and a gate that is honoured on the calls somebody
  remembered. **The flag wins over the variable**: the flag is on the invocation in front of you, the
  variable is ambient and inherited and the thing most likely to be stale. An empty or whitespace-only
  variable is treated as *unset*, not as an empty declaration — `export DEVTEAM_CLIENT_SCHEMAS=` is a
  shell saying "no value", and reading it as `{}` would refuse every write in that session with a
  message naming a file called `""`.
- **A declared client is refused every mutating command it cannot understand, at exit 4.** Not 1:
  `devteam compat`'s exit 1 is a *finding* — the question ran and answered — while a refused write ran
  nothing, and exit 1 in this CLI always means "ran and reported a problem it did not fix". The gate
  runs in `cli.main` after the parse and **before `store.adopt_machine_layout()`**, which is itself a
  store mutation, so a refusal leaves the store byte-identical — asserted by content digest of every
  path, not by name, because a gate that refused *after* rewriting the registry would be invisible to a
  listing. `details` carries `{command, declared_by, declaration_source, client_schemas, store_schemas,
  unsupported, may_write}` so a client branches on data rather than on the wording of a sentence, and
  `declared_by` names the seam actually used — a client whose wrapper three layers up exported the
  variable is told about the variable, not about a flag it never passed. Those seven keys are pinned **in
  both directions**, with every value asserted and not only the names: the spec had marked that clause met
  on all seven while three of them — `command`, `declaration_source`, `client_schemas` — were asserted by no
  test at all, and nothing held the key set either way. The gate's *position* is asserted too, on a
  fabricated pre-split store and across the whole of `compat.MUTATING`; before that fixture existed, moving
  the gate block below `adopt_machine_layout()` left every test in the file green.
- **A malformed declaration is exit 2, never silence.** A missing file, text that is not JSON, JSON
  that is not an object, a non-integer claim (including a boolean, which subclasses `int` in python), a
  file that is not decodable as UTF-8, and input nested too deeply for the JSON parser are each a usage
  error naming **the seam and the path** — `--client-schemas …`, `--client-file …` or
  `DEVTEAM_CLIENT_SCHEMAS …`, because a client whose wrapper exported the variable three layers up has to
  be told which seam is at fault rather than handed a path it never typed. Treating a corrupt declaration
  as no declaration is the fail-open case the gate exists to avoid. The last two cases are the ones that
  bite: `json.loads` raises `RecursionError` and `Path.read_text` raises `UnicodeDecodeError`, neither an
  `OSError` nor a `JSONDecodeError`, so both used to escape to `cli.main`'s catch-all — exit 3 with
  *"unexpected …"*, and under `--json` a traceback with an empty stdout, which a client branching on `$?`
  reads as an environment problem rather than as its own malformed question. Exactly one document goes out
  now, on every seam and on `devteam compat` itself.
- **`--client-schemas ""` is exit 2, not the anonymous path.** The empty **variable** still means unset —
  a shell cannot say "no value" any other way — but an empty **flag** is a caller that passed a value and
  got it wrong, almost always `--client-schemas "$SCHEMAS"` with `SCHEMAS` unset, the ordinary idiom a
  client wrapper has. A truthiness test on the flag let that fall through to the variable and resolve to
  "no declaration": the ungated path, and precisely the fail-open the seam's own docstring forbids. The
  asymmetry is asserted in both directions, including against `compat.client_declaration` in-process so it
  is pinned as a rule rather than only as an exit code, and asserted not to fall through to a *compatible*
  exported variable — which is how the mistake would have hidden behind an unrelated declaration.
- **The one-time pre-ADR-0013 layout relocation is not performed on an incompatible client's behalf, and
  one read-only command is refused at exit 3 instead of answering wrong.**
  `store.adopt_machine_layout()` rewrites `registry` and `bind_manifest` — the exact shapes such a caller
  just declared it cannot read — so it is suppressed; a terminal invocation, any anonymous caller and any
  *compatible* declaration still perform it, so no store is stranded. With the move skipped a read-only
  command answers against the layout on disk, which every one of them does correctly **except
  `devteam list`**: `paths.registry_file()` resolves only the post-split path, so `list` read no registry
  at all and reported every bound project as unbound — exit 0, `projects: []`, no error anywhere, the same
  silent failure as the stranded `state-dir` pointer that made `state_get` return an empty string for every
  key. `compat.NEEDS_MACHINE_LAYOUT` names it and nothing else, and the membership was **measured**: every
  read-only leaf run twice under the same declaration, once on each layout, with the refused set asserted
  *equal* to the table, so a command that starts reading a machine-local record fails the sweep instead of
  quietly joining the wrong side. The refusal is exit **3**, not 4 — the caller is entitled to read, and
  what is not ready is the environment, whose repair is the write the caller cannot accept — and it carries
  the refusal's seven `details` keys plus `machine_layout_pending: true`. Its hint names the fix that needs
  no client upgrade (run any command from a terminal with no declaration), and the three escape hatches that
  hint offers — `compat`, `version`, `path` — are asserted to answer on the un-relocated store.
- **All 35 parser leaves are classified** — 19 mutating, 16 read-only — in `compat.MUTATING` /
  `compat.READ_ONLY`, keyed by the same path tuples the contract sweep's discovery walk produces, with
  the reason beside every entry. `compat.is_mutating()` **fails closed**: a command in neither table
  counts as mutating, so forgetting to classify a new one cannot open a hole. Six entries are judgment
  calls, and five of them say so in the table: `cred get` is read-only (its audit line is the framework's
  own record, not one of the declared shapes — gating it would turn a write gate into a read denial and
  replace its documented `--json` exit-2 refusal with an exit 4), `doctor` is mutating (it repairs
  pointers and can reassign identity), `export` is mutating (it creates a restorable archive of shapes
  the client just said it cannot read), and `store gc`/`migrate` are mutating by what the command can do
  rather than by which flag one invocation passed. The sixth, `upgrade`, is mutating for that same
  per-command reason and is the one entry that does **not** record it — its reason reads only
  "relocates this project's memory into the store", although like the other two it previews without
  `--apply`.
- **No read-only command is refused as a write**, `compat` included. ADR-0011's rule is that an
  incompatible client *degrades to read-only*, so read-only is precisely what must keep working — a
  client a version behind can still read a credential value, and can still ask how far behind it is. The
  one exception, `devteam list` on a store that has not been relocated, is described above and is an exit-3
  environment refusal rather than a write denial: a wrong read is not a degraded read.
- **A caller that declares nothing keeps its full write access — deliberately.** No detection, no
  warning, no log entry, no flag needed by any write. An anonymous invocation is byte-for-byte a human
  at a terminal, and the human's CLI is the one thing this gate may not touch; identification is also
  not authentication, so a mandatory flag would guard only against the well-behaved client. This is why
  the gate **narrows** ADR-0011's rejected `--client-schemas` alternative instead of reversing it: that
  row rejected refusing a client that has *not* declared, and this refuses one that *has*. ADR-0014 § 3
  records the boundary and the two conditions that would justify reopening it.
- **`tests/test_client_gate.py`** — 52 tests (suite 396). The mutating sweep is driven from the classification
  rather than from a list in the test, so a command added tomorrow is covered the moment it is
  classified; the completeness check walks the real parser and fails on an unclassified leaf, a leaf in
  both tables, and an entry naming a command that no longer exists. The two most destructive commands
  are deliberately included with arguments that make a *broken* gate harmless (`update --ref
  not-a-version` fails ref validation before the first network call; `uninstall --purge` without
  `--yes` is refused by the command itself), because excluding them would leave the gate unproven
  exactly where it matters most.
- **ADR-0014 also decides two questions ADR-0011 left open.** `store_schemas()` is the **normative**
  compatibility statement and `min_app_version` is confined to a kill switch for a released app version
  that writes wrongly for a reason no shape number can express; `minFrameworkVersion` on the app side
  is advisory, since no framework code reads it and none is planned. And `json_contract` now has a
  deprecation policy: what obliges a bump, what explicitly does not (adding a key, a command or a flag;
  any human-mode output; the wording of an `error` or `hint`), one live value at a time, and a
  departing key marked in the payload it appears in for one full release before removal. The `deprecated`
  marker is **specified and not built** — there is nothing to deprecate at `json_contract: 1`, and the
  first deprecation implements it.

**Three claims in ADR-0011's own Risks table were not made stale by this work — they were false when
that table was written.** The amendment first said "now stale", which flatters the error. Every
contradicting artifact already existed at `ed87507`, the commit that wrote the rows:
`AppFacingKeySetContractTest` (`95fa346`), `cmd_compat()` calling `compat.unsupported_by()`
(`4818176`), and the cask's `depends_on formula: "devteam"` (`06fd509`) — all three ancestors of it. The
statements are now corrected as *false-when-written*, and counted as three across **two** rows. Also
struck: the claim that ADR-0011's *"Revisit when the app ships and 'which CLI does the app invoke' is
decided"* condition was "met by half". It is met in neither half — the app has not shipped, and
`depends_on formula:` guarantees the formula is *installed*, not which binary the app invokes, which is
what the cask's own comment means by "answerable". That line also predates the condition and nothing in
this change touched `packaging/`. The gate was built ahead of the condition deliberately, and the ADRs
now say so instead of borrowing credit for a dependency somebody else added.

### Added — v3 milestone M4.3 (the desktop client's first slice, and a JS gate to hold it)

M4.3 was the milestone every earlier entry deferred: `packaging/homebrew/devteam-app.rb` was a cask
for an app that did not exist, ADR-0011's channel table had an empty "app" column, and
`docs/specs/v4-app-and-distribution.md` marked the whole scenario `[UNBUILT]`. The client now exists
in source. **It ships to nobody, and that half has not changed** — the build is unsigned by
configuration, no release carries it, and `KEEP_ROOT` keeps `app/` out of every installed project.

- **`app/` — an Electron client that is a pure client of the CLI.** TypeScript, Vite, React,
  shadcn/ui and Tailwind v4, decided in **ADR-0015** (the stack, where the source lives, which
  process may spawn, which `devteam` is invoked, and what happens when none is found). **Zero
  runtime dependencies**: `dependencies` in `app/package.json` is empty, the renderer is bundled by
  Vite, and the main process imports only node builtins plus `electron`, so no `node_modules` tree
  is packaged.
- **The CLI is resolved, never bundled.** `app/src/cli/resolve.ts` tries an explicit path
  (`DEVTEAM_CLI_PATH`, then the app's settings file), then `PATH` in the shell's own order, then
  Homebrew's `bin` — the Finder-launch case, where a GUI app inherits no login shell's `PATH`. A
  candidate is accepted only if **running** `version --json` returns a conforming document carrying
  a `compat` block, so a different program named `devteam` is rejected at resolution rather than on
  every screen. There is no fallback binary: a bundled older CLI writing a newer store is the
  failure ADR-0011's second Risks row names.
- **Every invocation is declared, so ADR-0014's write gate binds this client.** The declaration is
  the app's **own frozen constant** (`APP_STORE_SCHEMAS`), never derived from a store — deriving it
  would compare the store's numbers with themselves and pass always. The main process attaches
  `--client-schemas` in one place, so no operation can omit it; the handshake declares the same
  constant inline on `devteam compat --client`, which cannot be a stale file. An incompatible answer
  is **exit 1, a verdict** rather than a failure, `may_write` is read and never inferred from
  `unsupported`, and the plain-language summary names each shape the app does not understand.
- **The renderer can ask for a screen, never a command.** `contextBridge` exposes named operations
  only; every argument vector is built in the main process from a closed `ALLOWED_COMMANDS` list
  (`version`, `compat`, `list`, `catalog` bare and its three kinds, `catalog show`, `doctor`), spawn
  is argv-array with `shell: false` stated explicitly, and a catalog name beginning with `-` is
  refused before it can be read as a flag.
- **The slice is not read-only, and says so instead of relabelling the command.** `devteam doctor`
  is in `compat.MUTATING` because it repairs what it finds, so the app carries it in a separate
  `GATED_COMMANDS` constant rather than filing it under read-only; `--reassign-identity` is never
  passed (asserted against the source), the declaration makes the framework refuse the call at exit
  4 when the store is ahead, and the UI header says **"no write actions"** rather than "read-only".
  ADR-0015 § 8 claimed the slice was read-only; its own amendment now corrects that, and records the
  distinction it turns on: the classification belongs to the **command**, not to the invocation.
- **`cred` is unreachable, not special-cased.** ADR-0010 keeps values out of any client, and the app
  never calls `cred get` — a test asserts no allowed command so much as starts with `cred`, so no
  secret can enter the process by any route the app has.
- **103 tests (102 passing, 1 skipped) under `app/test/`**, including `real-cli.test.ts`, which drives
  the **real** `scripts/cli/devteam` with `DEVTEAM_HOME` in a temp directory: the app's constant
  matches `store_schemas()` exactly, a declaration one behind is refused on a mutating command at
  exit 4 before anything on disk changes, and a final test asserts every read-only command leaves
  that directory **empty**. A fake proves the parser handles the shapes it was told about; only the
  real CLI proves the shapes were described correctly.
- **`.github/scripts/ci/05-app.sh` and the `app` job — the JavaScript gate this repository had
  none of.** ADR-0009's precedent applied to a second language: the gate lands in the same change as
  the language, not after it. Preflight (missing `app/` is a **failure**, not a skip), the node
  version proven against the single pin in `app/.nvmrc` and against `engines.node`, the
  typecheck/lint/test script contract asserted before the scripts are called, `npm ci` from the
  committed lockfile, and a **non-vacuity** check on the suite: test files must exist on disk, the
  `test` script must not carry `--passWithNoTests`, and the runner must report a positive count. No
  `app/**` path filter, deliberately — a change to `scripts/lib/devteam/` must exercise the only
  consumer of the `--json` contract. No build step: a gate that produces an unsigned `.dmg` is
  shipping, not checking.
- **`app/electron-builder.yml` — one artifact shape, unsigned and announced as such.** A universal
  `dev-team-agents.app` inside `dev-team-agents-<version>.dmg`, matching what the cask expects.
  `mac.identity: null` and `mac.notarize: false`, `CODE_SIGNED = false` as a greppable source
  constant, a loud banner at build time, on startup and in the UI — because a `.dmg` that looks
  shippable and is not is worse than no `.dmg`. No `win` block: adding one would imply a Windows
  packaging shape ADR-0011 still records as undecided.
- **M4.3 adversarial review: 14 findings fixed, 29 new tests, 73 → 102 passing.** An independent review
  of the M4.3 slice returned 14 findings, all now fixed. The test suite grew from 73 to 102 passing
  tests, covering CLI resolution order, invocation layer, declaration integrity, handshake accuracy,
  degradation on incompatibility, gated command behavior, and allow-list enforcement. Included in the
  fixes: Windows platform support in CLI resolution (winget's shim directories now searched), environment
  variable name and precedence corrected in ADR-0015 (now `DEVTEAM_CLI_PATH` before settings file),
  allow-list enforcement at spawn boundary rather than dead data, missing `cwd` required on every catalog
  call, `path_exists` reported as unknown rather than false when unresolved, declaration write failure
  now refuses mutating commands, application data directory collision resolved (`userData` now
  `<appData>/<name>-app`), exit-1 error document corrected, `setWindowOpenHandler` denies all external
  URLs, request filter narrowed to match stated rule, handshake result fabrication removed, stdout capped
  at 32MB, and Tailwind v4 source directive added for component directory (`@source '../components'`).

### Fixed — packaging, measured against the build that now exists

- **The cask's macOS floor was wrong in the dangerous direction.**
  `packaging/homebrew/devteam-app.rb` carried `depends_on macos: ">= :big_sur"` under a comment
  calling it "a guess, not a measured value". Measured: the pinned Electron's
  `Electron.app/Contents/Info.plist` declares `LSMinimumSystemVersion` **12.0**, so Electron 39 does
  not launch on Big Sur at all, and `">= :big_sur"` licensed `brew install` on a system where the app
  cannot start — which a user experiences as the app being broken rather than as unsupported. Now
  `">= :monterey"`, mirrored by `mac.minimumSystemVersion: '12.0'` in the build config, and recorded
  as a **per-release check**: the floor moves with every Electron major and nothing enforces the pair.
- **The cask's bundle id and app name stopped being placeholders.** Both are now read from
  `app/electron-builder.yml` (`appId`, `productName`) rather than guessed from an `Info.plist` that
  did not exist.
- **The cask's `version` and `app/package.json`'s `version` are one value in two files, and the
  coupling is now written down.** `dmg.artifactName: ${productName}-${version}.dmg` derives the dmg
  filename from the package's version while the cask's `url` derives the same filename from the
  cask's, so a release whose two strings differ downloads a filename nothing produced. Neither file
  is authoritative: **the `app-v*` git tag is**, per `packaging/README.md` § Version source of truth,
  and a build step must stamp the package from it. That step does not exist, so the two values are
  deliberately left disagreeing (`0.0.0` vs `0.0.0-unreleased`) rather than reconciled by hand into a
  matching pair that still describes no artifact.
- **`packaging/README.md` no longer says the app does not exist**, and is precise about what replaced
  that: a build exists and is unsigned; what is absent is a signed, notarised artifact at a real
  version. Its prerequisites, placeholder table and "what is unverified, and exactly why" table are
  updated row by row, including three new rows — whether the dmg filename the cask builds is the one
  the build produces, and the fact that **winget has no app manifest at all** while ADR-0011's channel
  table promises winget for the app as well as the CLI.
- **ADR-0011 and ADR-0014 gained forward references to ADR-0015**, as amendments appended after their
  existing ones; both files are additive-only, with no Decision body or Risks row altered. ADR-0011's
  "settle which CLI the app calls before it ships" instruction is recorded as **decided** (ADR-0015 § 5,
  implemented and asserted) with its residual unchanged, because the app still has not shipped;
  ADR-0014 § 3's reopening condition is recorded as **still unmet in both halves**, with the note that
  the honest declaring client it was narrowed to now exists and exercises the gate.
- **`docs/specs/v4-app-and-distribution.md` marks M4.3 `[PARTLY MET]`** — a fourth mark added to its
  legend, because `[MET]` and `[UNBUILT]` were both false in opposite directions. Every clause of the
  scenario carries its own verdict and the test that earns it; "renders the result", the absence of a
  bind rule or preference merge, the `cred get` special case and "every capability remains reachable
  from the CLI alone" are explicitly **not** moved. The scenario as a whole stays unmet: the client
  ships to nobody.

### Changed — as a consequence of the shared parser
- **Error-message wording inside `devteam compat` changed, and nothing else did.** `--client` and
  `--client-file` now go through the same parser as the new seam
  (`compat.parse_client_schemas` / `compat.load_client_schemas`), so every rejection names *which
  source* was at fault instead of saying "client" generically:

  | Case | Before | After |
  |------|--------|-------|
  | `--client '{oops'` | `client schemas are not valid JSON: …` | `--client is not valid JSON: …` |
  | `--client '[1,2]'` | `client_schemas must be a mapping of shape name to integer` | `--client is not a JSON object: got list` |
  | `--client '{"project":"1"}'` | `client value for 'project' is not an integer: '1'` | `--client: the value for 'project' is not an integer: '1'` |
  | `--client-file /nope.json` | `--client-file /nope.json could not be read: …` | unchanged — the seam attribution was briefly lost when the readers were merged, and is restored |

  The `hint:` lines moved with them (they no longer example `--client` specifically, because the same
  text now also serves the file and the environment variable). **No payload key and no output channel
  changed**, and every case in the table above was and remains exit 2 with the text in `error`. One
  parser was the point: two would have been free to disagree about what a valid declaration is, and the
  disagreement would surface as one seam accepting a file the other refuses. Per ADR-0014 § 2 none of the
  table obliges a `json_contract` bump — a client branches on `exit_code`, never on message text, and the
  flag, the variable and the refusal's `details` are additive.
- **`devteam compat --client '[]'` now carries a `hint`.** It used to re-wrap a `TypeError` from
  `unsupported_by` as `UsageError(str(exc))` with none, which made it the one malformed-declaration message
  that told the caller nothing about how to fix it — on the surface whose entire job is telling a client what
  to correct. The addition is kept deliberately, and `tests/test_client_gate.py` records the decision beside
  the assertion so the next reader finds the reasoning rather than the diff: `hint` is a *conditional* key of
  the error envelope, emitted by `errors.DevteamError.payload()` only when set, so its presence already
  varied between two errors of this same command, and `AppFacingKeySetContractTest` pins success payloads
  only. ADR-0014 § 2 now states the general rule rather than leaving it as a one-off — a conditional `hint`
  appearing on a path that did not set it is the *"adding a key"* case and is free.

### JSON contract

Written under this fixed heading because ADR-0014 § 2 step 3 requires it whenever an output shape or an
exit code moves, whether or not the contract number moves with it.

- **Contract version: `1` → `1` (unchanged).** No payload key was added, removed, renamed or retyped.
- **One exit code corrected.** `devteam compat --client-file <file that is not valid UTF-8 | input nested
  too deeply for the JSON parser>` moved from exit **3** to exit **2**. Read against § 2's *"changing which
  exit code an existing outcome uses"* clause this is a contract break, and it is recorded that way rather
  than left implicit. Two facts are why the number does not move, and both are now written into § 2 so the
  next occurrence is not re-argued: the old exit 3 was a **crash** reaching the caller through
  `cli.main`'s catch-all as *"unexpected `UnicodeDecodeError` / `RecursionError`"*, not a decided outcome —
  and a rule that protects a crash is not protecting a contract; and **the CLI has never been released** —
  `scripts/cli/devteam` does not exist at `v2.48.0`, the latest tag, so `json_contract: 1` has never
  reached a client and there is no prior value for a bump to distinguish it from.
- **Not exit-code changes.** `--client-schemas ""` at exit 2 and `devteam list` at exit 3 look like moved
  codes and are not: `--client-schemas` and everything reached through it are new in this same unreleased
  change set, so they replace no released behaviour.
- **Additive, per § 2's "does not oblige a bump" list.** The global `--client-schemas` flag and the
  `DEVTEAM_CLIENT_SCHEMAS` variable; the refusal's seven `details` keys; `machine_layout_pending` on the
  exit-3 refusal's `details`; a `hint` on `devteam compat --client '[]'`. Every error-message rewording in
  the section above.
- **Commands affected:** `compat` (error documents), and every command via the new global flag. No
  success payload changed, and the 16 key sets pinned by
  `tests/test_json_contract.py::AppFacingKeySetContractTest` are unchanged.
- **No deprecation window opens or closes.** Nothing emits a `deprecated` list; there is nothing to
  deprecate at `json_contract: 1`.

### Changed
- **37 markdown references now read the projection**, not the v2 source file. The five documents that
  describe the *source* layer — the canonical `user-preferences` skill, first-time setup, both
  health-check references and `CLAUDE-md/preferences.md` — keep naming `user-data/preferences.json`,
  because that is what they are about. `skills/shared/user-preferences/SKILL.md` now states the read
  path, the one-level fallback for an unbound project, and that writes go through `devteam prefs set`.

### Fixed — independent of the split

- **A clean local lint and a red CI on the same commit.** `01-lint.sh` runs the identical
  shellcheck command in both places, but nothing pins the version: CI uses whatever the runner
  image ships and a contributor uses whatever their machine has. Traced to shellcheck 0.11.0 no
  longer emitting an SC2317 "unreachable" false positive that the runner's older build still
  does — for a function invoked by an `EXIT` trap, which shellcheck cannot see is called. The
  three findings are fixed at the source rather than silenced: the trap-invoked function's
  directive now covers the check reported from the other side, and two `A && B || C` chains are
  grouped so the shell reads what they mean — `C` was reachable when `A` succeeded and `B`
  failed, which is not if-then-else. The gate now prints the shellcheck version, because the
  next divergence should cost one look at the log instead of a bisect.

  **Now pinned.** `.github/shellcheck.pin` is the single source of truth for the version and
  its per-architecture sha256; CI installs exactly that release and verifies the hash before
  running the binary, because this repository already refuses an unverified download in
  `scripts/lib/installer-fetch.sh` and a CI step executing whatever the network returned would
  contradict that for no reason. The install step then asserts the version now on `PATH` is the
  pinned one, since `install`ing to `/usr/local/bin` only wins if it precedes the image's copy.
  `01-lint.sh` reads the version from the same file and warns when a contributor's differs,
  naming the direction that actually bites: a **newer** shellcheck finds fewer things, so it
  hands you a green CI will not honour. That warning is advisory, not blocking — CI is pinned so
  it can only fire locally, and refusing to lint at all because someone is a minor version
  behind trades a real check for a version complaint.

  Pinned **forward** to 0.11.0 rather than back to the runner image's 0.9.0: pinning to the old
  default would enshrine the false positive that started this, and 0.11.0 is what a contributor
  on a current machine already has, so the pin moves CI to meet developers instead of the
  reverse.

- **The mandated duplicate-ADR check could never find an ADR.**
  `skills/shared/adr/SKILL.md` § Check Before Creating told the reader to list existing titles with
  `grep -h '^# ' docs/development/adrs/adr-*.md`. No file in that directory has ever matched that
  pattern — `new-adr.sh` emits `NNNN-slug.md` — so the check returned an empty list every time it ran,
  which is precisely the failure mode that produces a second ADR for a decision that already has one.
  The skill no longer carries a glob at all: `scripts/new-adr.sh --list` is a new mode that prints the
  titles and creates nothing, and the script is the one place that knows both naming schemes. The
  skill also claimed the script creates `adr-NNN-title.md`, which it stopped doing.
- **The ADR-gap safety net warned at the session that had just added an ADR.**
  `scripts/hooks/stop/03e-adr-gap-check.sh` recognised "an ADR was already added, nothing to warn" by
  matching `adrs/adr-[0-9]+.*\.md$` against the touched paths. Since no real filename carries the
  `adr-` prefix, that escape hatch could never fire, so the heuristic aimed a false positive at
  whoever had just done the right thing. The prefix is now optional in the pattern, and the comment
  points at `new-adr.sh`'s `adr_files` as the owner of the scheme list.
- **The two naming schemes were spelled out three times**, and the third copy was the stale one. They
  now have a single definition inside `new-adr.sh` (`adr_files`), used by the title listing, the
  number scan and `--list` alike.

- **The two telemetry hooks wrote into the shared, versioned core store.**
  `scripts/hooks/pre-tool-use/02b-telemetry.sh` and `scripts/hooks/stop/05-telemetry.sh` derived the
  project root by counting `..` hops from `SCRIPT_DIR`, which assumes the flat v2 vendored layout. The
  default v3 bind modes (`link` on macOS/Linux, `copy` on Windows) insert a `core/` segment, so the
  count landed one level short at `.dev-team-agents/core/user-data`. `cd`+`pwd` keeps that logical
  path, but an actual write follows the symlink — verified: it resolves to
  `<store>/core/versions/<version>/user-data/`. Every bound project on the machine would have written
  its `telemetry-queue.json` and `state.json` into one shared directory inside the tree `devteam
  update` replaces wholesale and `store gc` can remove. Only the opt-in `vendored` mode, which has no
  `core/` indirection, happened to work. Both hooks now resolve the root via `git rev-parse
  --git-common-dir` like every other hook. Root cause predates the ADR-0013 split and is unrelated to
  it; `pre-tool-use/02-graphify-hint.sh` was never affected because it already resolved via git.

### Fixed — M2.1 review round

A five-agent review of the split (backend, security, architecture, tests, docs) returned 28 findings.
Two were CRITICAL and both are closed.

- **`devteam import` extracted a hostile archive unchecked on the declared python floor.**
  `store.py` had its own member loop that validated `member.name` and stopped there, then relied on
  `extractall(..., filter="data")` with an `except TypeError` fallback. `filter=` does not exist on
  python 3.9 — the interpreter the CLI is *required* to support, and the system python on macOS — so
  the fallback extracted with `extractall`'s `fully_trusted` default and nothing ever inspected
  `member.linkname`. A symlink member with an absolute target, or a hardlink whose target climbed
  out, was a write outside the store and a read-any-file-then-exfiltrate chain. `update.py` already
  had the correct validator; the duplicate loop is how it went unchecked. Both paths now share
  `update.safe_members`, promoted from `_safe_members` because an underscore invites a third weaker
  copy.
- **The store relocation stranded every layout-2 project's state pointer.** Moving `state.json` into
  the machine subtree without rewriting `.dev-team-agents/state-dir` made `state_get` return an
  empty string for **every** key — installed version, session id, session head, health-check marker,
  update-check throttle — with no error anywhere. The relocation now rewrites both pointers for every
  bound project it can resolve, and `devteam doctor` repairs a missing or stale pointer in place
  rather than only reporting it. The ADR's claim that the relocation "moves nothing inside a project"
  was exactly why it was incomplete; it now says it moves no *content* there.
- **A portable export shipped plaintext credentials.** `devteam upgrade` retires the whole legacy
  `user-data/` directory to `data/quarantine/`, secrets included, and quarantine was portable and
  included in the default archive — a reviewer extracted a database password from one. Quarantine is
  now `paths.LOCAL_ONLY_STORE_ENTRIES`: portable by content, never in a default export. The export
  filter also classifies by **basename at every path depth**, so a nested or differently-cased
  secret (`env/Credentials.local.json`) cannot escape either.
- **`devteam export --all` packed the live lock directory.** The exclusion tested only the first path
  component, and locks moved to `machines/<id>/locks/` — whose first component is `machines`. A
  restored lock names a pid that does not exist on the receiving machine, and `_break_if_stale`'s
  300-second floor meant the next command polled and then failed with a confusing `ConflictError`.
  Components are now matched at every depth, and the filter and the file count are **one** predicate
  so they cannot drift.
- **The export landed in the repository, world-readable.** The default destination was `Path.cwd()`
  with mode `0644` and no gitignore entry — one `git add -A` from committing an archive of the data
  store. It now defaults to `cache_dir()/exports/`, is `chmod 0600`, and `devteam-data-*.tar.gz` is
  in the managed project gitignore block for the `--to .` case.
- **`machine-id` identified the store, not the machine.** ADR-0007 deliberately places `data/` in the
  Windows **roaming** profile and presents that as a backup feature — and a roaming profile is
  replicated between machines by policy, so the documented Windows layout guaranteed two machines
  answering with one id. Same for a restored disk image, a VM clone, and `$DEVTEAM_HOME` on a network
  mount. The record is now `{"id": …, "created_on": <host>}` and a host mismatch **re-issues** a new
  id and subtree rather than adopting records that describe another machine. A legacy bare-UUID
  record is adopted and annotated, never re-issued — re-issuing would have orphaned the records that
  id already named.
- **Consent travelled with a portable export.** `telemetry` and `auto_update` are `CONSENT_KEYS`
  precisely because consent belongs to one installation, and the existing backfill only adds keys
  that are *missing* — so an imported `preferences.json` already saying `true` silently enabled
  telemetry on a machine whose owner was never asked. `devteam import` now strips both keys, so the
  cascade resolves them as `consent-withheld`.
- **A portable import could take the receiving machine's registry out of the active store.** Promoting
  an archive that carries no machine subtree moved the live `machines/` aside with it, and every bound
  project read as unbound. The local records are carried across first, `machines/` before
  `machine-id` so a failure cannot orphan the identity from the records it names, with rollback and
  staging cleanup on error. A `data/machines` member that is not a directory — a dangling symlink made
  `exists()` false — is now refused instead of misread as a portable archive.
- **`devteam path` and `devteam doctor` wrote to disk.** Both minted `data/machine-id` as a side
  effect of being asked a question, so a second `doctor` diagnosed a world the first one created.
  Both now resolve the identity read-only. `doctor` also reports another machine's record set as
  `warn` rather than `ok` — inert is not the same as expected.
- **`graphify.json` was moved into a per-user store.** It is committed, shared by every developer
  through a deliberate gitignore exception, and `scripts/graphify-refresh.sh` reads it at the
  in-project path. `devteam upgrade` copied it into `data/projects/<id>/` and retired the exception
  that kept it tracked, so graph refresh would have stopped working for everyone else on the next
  pull. `paths.PROJECT_OWNED_RECORDS` is now a third class that stays in the project, and the
  exception survives the gitignore rewrite. If the file cannot be put back after the legacy directory
  is quarantined, the staged copy is kept and named rather than cleaned up.
- **The classifier was case-sensitive and one level deep.** `Credentials.local.json` classified as
  portable while macOS APFS and Windows hand the same file to anything opening the lowercase name,
  and `env/credentials.local.json` escaped the check entirely. `paths.is_machine_local_record()` now
  takes a case-folded basename and `paths.path_is_machine_local()` answers for a whole path.
- **Quarantine was the one part of the store that was not owner-only.** Its directories were `0755`
  holding `0644` files, so containment rested entirely on `data/` being `0700`. Quarantine now goes
  through `jsonio.ensure_dir` (`0700`) and files the upgrade copies are `chmod 0600`.
- **The export manifest disclosed the absolute store path**, and therefore the OS username and home
  layout, to whoever received the archive. Removed.
- **`devteam upgrade` never said to commit the layout change.** `layout` lives in the committed
  `project.json`, so an uncommitted upgrade is invisible to a fresh clone: it comes back on layout 1
  and asks to upgrade again. Observed in an end-to-end run, not reported by the review. The command's
  output now names the file to commit, and also reports both pointers and any project-owned file it
  kept in place.
- **Two defects the round's own fixes introduced, caught by the regression tests written for them.**
  `devteam doctor` still minted a machine identity on a store with no installation: `check_machine()`
  resolved read-only but `check_registry()` reached `registry_file()` through `machine_dir()`, which
  creates one — so `doctor` created the store it had just reported missing. Registry **reads** now
  thread an explicitly read-only id, and no identity means no bound projects. And the guard that
  refuses a non-directory `data/machines` member tested `exists() and not is_dir()`, but
  `Path.exists()` follows the link and is `False` for a **dangling** symlink, which is precisely the
  case the guard was written for; `is_symlink()` is now checked first.
- **The relocation was invisible to a `--json` client.** ADR-0011 makes the desktop app a client of
  this CLI, so a store mutation it could not observe in the document was a contract gap. The result
  now carries `store_relocation`.
- **Every bash hook was blind to layout 2.** They all hardcoded `.dev-team-agents/user-data/`, so an
  upgraded project lost the framework's own enforcement and the upgrade actively fought itself:
  `session-start.sh` recreated the retired directory on every session, which then re-tripped the
  "run `devteam upgrade`" nag permanently for an upgrade that had already run and would refuse to run
  again; `stop/01-session-summary.sh` instructed the agent to recreate the summary in the project,
  re-splitting the episodic layer; and `pre-compact.sh`'s `[ -d user-data ]` guard silently disabled
  the PreCompact summary gate. A shared resolver (`scripts/hooks/lib/data-dirs.sh`) now answers for
  both pointers with the in-project path as the layout-1 fallback, so one code path serves both
  layouts, and the nag fires only when the directory holds something other than a
  `paths.PROJECT_OWNED_RECORDS` entry.
- **The hooks read a preferences file that layout 2 does not have.** They read the v2 source layer
  directly instead of `.dev-team-agents/resolved/preferences.json`, the projection the M2 cascade
  writes and that agents already read — so on layout 2 the session banner reported defaults and the
  telemetry consent check failed closed against a missing file. The hooks now resolve the projection,
  and `session-start.sh`'s key backfill is gated to genuine layout 1 so it never writes into a
  generated file.
- **`skills/shared/project-context/SKILL.md` step 4 pointed at the wrong directory.** The canonical
  context-loading order every agent follows read the session summary through `state-dir`, which now
  names the machine subtree. The justification for not writing a second pointer — "nothing reads it
  yet" — counted only CLI and bash readers and missed the largest reader class: an agent following a
  skill. Both pointers are now written and the skill reads `memory-dir`.
- **Upgrade visibility**: `devteam doctor` reports a stale layout, a missing or wrong state pointer
  and a missing preference projection as `warn` findings; the session banner says the same thing with
  an observable test (a bound project whose `user-data/` still exists) and no JSON parsing.
- 75 new tests (202 total). Beyond the cascade and upgrade coverage, there is now one regression test
  per finding from the review round, each naming the defect it pins: the store import path refusing an
  absolute-target symlink, an escaping hardlink and a device member; a default export carrying no
  secret planted at the top of the legacy memory directory, nested one level down, or spelled with
  different case; `--all` excluding locks at any depth while still carrying the registry and the
  manifests; the machine identity re-issued on a host mismatch but **adopted** for a legacy
  bare-UUID record; consent keys resolving as `consent-withheld` after an import; `graphify.json`
  surviving an upgrade in the project with its gitignore exception intact; quarantine at `0700` with
  copied files at `0600`; and `devteam path` and `doctor` creating nothing on an empty store. The
  export file count and the archive filter are asserted against each other, because they are one
  predicate and a drift between them was previously invisible. `test_paths.py` now exercises every
  machine-local resolver under `darwin`, `win32` and `linux`.
- One behaviour is recorded as **uncovered** rather than tested with a contorted fixture:
  `upgrade.apply`'s keep-the-staged-copy path when a project-owned file cannot be restored needs a
  reliably unwritable directory, which is permission-bit dependent and flaky under CI.

### Fixed — M1 review findings

A five-role review (backend, security, architecture, devops, QA) of the milestone found 43
findings. Every one is resolved below or recorded as a deferred decision; each has a test named
after the failure it prevents.

- **Data loss: three code paths deleted content instead of quarantining it.** `unbind`, a re-`sync`
  and a re-bind in `copy` or `vendored` mode called `rmtree` on real artifact directories — which
  in those modes can hold files the user added. Reproduced with planted files: 0 of 5 survived, and
  the routine `sync --all` after an update was enough to trigger it. Only symlinks are unlinked
  now (they hold no content and `sync` recreates them); everything real goes to
  `data/quarantine/<date>/<project_id>/` via the new `scripts/lib/devteam/quarantine.py`.
- **Data loss: a manifest entry with no `path` deleted the whole project.** `Path(root) / ""` is
  the project root, and the removal helper then took its directory branch — destroying source code
  before crashing on the missing key. `_prune_stale` already guarded this; `unbind` and `doctor`
  did not.
- **Path containment was never checked.** `_is_inside` existed, was correct, and no write path
  called it. A repository that commits `.claude` or `.dev-team-agents` as a symlink relocated the
  whole bind outside the project, and a vendored bind deleted the link's target — reproduced
  against a synthetic `~/Documents/scripts`. `require_inside` is now called before every write and
  every removal, directories are created one component at a time, and the check resolves the
  artifact's **parent** rather than following the artifact into the store.
- **CRITICAL: tarball extraction could write outside the extraction directory.** The member filter
  validated `member.name` and never `member.linkname`, and `extractall` was called with no
  `filter=` — so on any interpreter below 3.14 a symlink or hardlink member redirected every later
  member. Now `filter="data"` where available, plus an explicit floor that rejects absolute and
  escaping link targets, device and FIFO members. Four attack classes are covered by tests.
- **No integrity check on the downloaded release**, while `scripts/lib/installer-fetch.sh` has
  verified the v2 installer against a published digest all along. `devteam update --sha256` pins
  out of band, `DEVTEAM_TARBALL_SHA256` does the same from the environment, and the absence of any
  digest is now reported in the output rather than passed over silently. The store also copies
  trees with `symlinks=False`, so an archive symlink can never land in a version that
  `providers` executes scripts from.
- **`--ref` was interpolated into the download URL unvalidated**, where `../` segments retargeted
  the fetch at another repository — and the semver check ran only after the archive had been
  extracted. Refs are validated against `vX.Y.Z` before the first request, quoted into the URL,
  and every request (including redirects) is restricted to GitHub over https with a response-size
  cap.
- **A bound project had no hook dispatchers at all.** `.claude/settings.json` was never written, so
  the session banner, the `Stop` dispatcher (session-summary enforcement, orphan-skill scan, agent
  lint, ADR-gap check), the `PreCompact` gate and the update check ran nowhere. `hooks.py` now
  merges the four entries into the project's own file, rewrites a stale v2 path in place instead of
  duplicating it, and removes only its own entries on `unbind`.
- **116 shipped path references did not resolve in a bound project** — 103 to
  `.dev-team-agents/scripts/…`, 13 to `.dev-team-agents/templates/…`, including `CLAUDE.md`'s own
  `bash .dev-team-agents/scripts/new-adr.sh`. The bind now creates a `.dev-team-agents/core`
  pointer to the resolved version, recorded in the manifest like any other artifact.
- **`devteam bind --provider opencode` could never succeed**: `install-opencode.sh` hard-requires
  `opencode/plugin/dev-team-agents.ts`, which `CORE_TREES` did not copy — and `providers.detect`
  selects opencode automatically for any project with an `.opencode/` directory. `opencode` and
  `CLAUDE-md` (whose absence left every companion link in the stored `CLAUDE.md` dangling) are now
  copied into each version.
- **`devteam bind --provider codex` vendored 2.3 MB of framework back into the project**, via
  `ensure_claude_framework`, untracked and not ignored — so the next `git add -A` committed it,
  and `migrate` then classified the bind's own output as a v2 install. The mirror pass is skipped
  when the `core` pointer exists, and both the Codex hook path and the opencode plugin resolve
  through the pointer with a v2 fallback.
- **Bash-installer output was invisible to the manifest**, so `unbind` reported "removed 0
  artifact(s)" while leaving 93 entries under `.codex/`. Delegated paths are recorded as
  `kind: "delegated"` in the same list every lifecycle operation walks. Files the installers
  *merge into* — `.claude/settings.json`, `.opencode/opencode.json`, `AGENTS.md` — are reported as
  project-owned instead, and are neither ignored nor removed.
- **A partial bind left artifacts nothing could clean up.** A missing `jq` surfaced from inside the
  opencode installer after 154 symlinks already existed and before the manifest, registry entry or
  exclude block recorded them. Tool checks and the identity-collision check now run before the
  first write.
- **A plain `devteam bind` silently released an existing pin** and moved the project to `current`.
  `pin=None` means "unchanged"; only `devteam pin --release` clears it.
- **`store gc` could delete a pinned version.** The keep-set was computed outside the lock, and
  `gc` took the `core` lock while `pin` took `registry`, so the two could not serialize. Both locks
  are taken, registry-then-core, with the computation inside them.
- **A stolen lock let two writers proceed, and the victim's `release()` freed the thief's lock.**
  `owner.json` now carries a nonce that `release` verifies, a holder whose pid is alive is never
  judged stale, and a caller that lost its lock is told.
- **`.gitignore` with CRLF was rewritten to LF across the whole file**, producing a whole-file diff
  in a committed file on every bind — in exactly the Windows repositories most likely to use `copy`
  mode. The managed block now reads and writes without newline translation and renders itself with
  the file's dominant terminator.
- **`store use` accepted an empty or partial version directory** as `current`, after which every
  bind failed with "core is missing …/agents". Activation applies the same tree validation as
  installation, a `<v>.incoming` staging directory is no longer listed as a version, and a failed
  `--force` install no longer removes the previous tree before its replacement is complete.
- **`migrate --apply` reversed a deliberate `--mode=vendored` bind**, which on disk is
  indistinguishable from a v2 install. It now checks the registry first and refuses with a pointer
  to `devteam bind --mode link`.
- **A linked worktree of a bound repository could not be bound.** It carries the same committed
  `project_id`, which read as a fork collision — and following that advice would have written a new
  identity into a tracked file on a feature branch, renaming the main checkout's identity on merge.
  Same-repository checkouts are now recognised, recorded on the entry, refreshed by `sync`, and
  unbinding one no longer clears the ignore block the others share. (Verified empirically: git
  reads only `$GIT_COMMON_DIR/info/exclude` for a linked worktree, so a per-worktree exclude file —
  the other candidate fix — does not work.)
- **The `--json` contract broke on every argparse-level error**: `devteam teleport --json`,
  `--mode bogus`, `--provider bogus` and a missing `--from` printed usage on stderr and nothing on
  stdout. The parser now routes its own errors through the emitter, an unexpected exception is
  rendered as one document instead of a traceback, and `OSError` in `sync --all` becomes a
  per-project problem rather than aborting the remaining projects with zero bytes on stdout.
- **Exit codes contradicted the documented contract.** `doctor` returned 0 for `warn`-level
  findings and emitted `ok: true` beside `status: warn`; `update` returned 0 while reporting
  projects it had failed to sync. Both now exit 1, `ok` is derived from the outcome, and `update`
  lists the failures in its human output.
- **`doctor` discarded every finding it had collected** when the store was broken — the case it
  exists for. It now reports that as a finding, detects drift in `copy` mode (where it previously
  detected none, on the platform that mode exists for), compares link targets by path components
  instead of substring, distinguishes a broken symlink from a stale one, and checks that the hook
  dispatchers are registered.
- **Store files and directories were world-readable** (0755 directories, and JSON at 0600 only by
  accident of `NamedTemporaryFile`). Modes are explicit now: 0700 for store directories, 0600 for
  store files, and 0644 for the committed `project.json` and `settings.json`, which were being
  written 0600.
- **`project_id` validation accepted a trailing newline** (`$` matches before one), which would
  have produced a directory name with an embedded newline under `data/projects/`.
- **Installer subprocesses inherited the whole environment**; they now get a minimal one with an
  explicitly resolved `bash`, an actionable message naming Git for Windows when it is missing, and
  a truncated stderr in the `--json` hint.
- **CI had no python gate for the floor it supports.** The `python` job is a matrix over 3.9 (the
  declared floor, now enforced in `scripts/cli/devteam`) and `3.x`; testing only the newest
  interpreter is what hid the tarfile defect, since `filter="data"` is the default from 3.14.
  `__pycache__` is ignored at every level and stripped from the package, and the test log is no
  longer truncated to 20 lines.

### Deferred, recorded rather than fixed
- ~~`registry.json` and the per-project manifests hold absolute paths, so the `data/` tree is not
  portable across machines even though the memory in it is.~~ **Resolved in M2.1** — the tree is
  split per machine and a portable export plus each project's committed `project.json` rebuilds a
  bind elsewhere. ADR-0013 amends ADR-0007.
- `state.json:installed_version` is still read by `/devteam:version`, the session banner and
  telemetry, and no v3 path writes it. Recorded in ADR-0007 as the open state-ownership question.
- ADR-0008's memory-survival claims are marked **pending**: identity ships in M1, relocation does
  not.
- Extending shellcheck to `.github/scripts` waits on the `SC2034` work on branch
  `ci/readme-sync-empty-baseline`, to keep the two changes from colliding in `01-lint.sh`.

### Changed
- **Every skill is now linked, at either supported depth.** The v2 installer's two-level loop (`install.sh:599`) iterated `skills/<category>/<name>/` only, so `skills/skill-creator/SKILL.md` — one level up — was never linked into `.claude/skills/`. The bind engine covers both layouts.
- **`CLAUDE.md` split further.** The command table and the per-key frontmatter rules moved to `CLAUDE-md/commands.md`, and the v3 store/CLI reference is in `CLAUDE-md/cli.md`. Content is unchanged — a move, not a rewrite. This is the extraction four consecutive audit passes reported as open (`token-claude-md-…-monolithic`).

### Fixed
- **`helpers/size-limits.sh` failed the build on its own warning.** The `CLAUDE.md` advisory threshold (600 lines, hard limit 700) pushed its finding into the same `VIOLATIONS` array as real violations, so the script exited 1 — and `01-lint.sh` wraps it as `blocking`, whose stated policy is "zero known violations in the tree today". CI was red on `main` for a file the script only warns about. Warnings are now tracked and printed separately, and do not fail the gate.
- **`scripts/new-adr.sh` restarted ADR numbering.** It scanned `adr-[0-9]*.md` while this repository's only ADR is `0006-mobile-pipeline-architecture.md`, so the next ADR would have been `adr-001-…` beside `0006` — two files claiming different numbers under two conventions. Both naming schemes are scanned now, and new files are emitted as `NNNN-slug.md` with four digits.

---

## [2.48.0] - 2026-09-23

### Added
- **Progress Reporting rule in `plan-mode`**: `skills/shared/plan-mode/SKILL.md` now mandates a per-step status update after each approved-plan step completes — a checklist of done/pending steps with elapsed time per step, plus a closing summary with total time when the plan finishes. Applies whether the plan's steps came from the agent or from a checklist the user handed over directly (still subject to the existing mandatory-plan trigger for multi-step tasks). Cross-referenced with `skills/shared/work-feedback/SKILL.md` so the two check-in mechanisms — periodic polling within a background step vs. one report between steps — don't appear to compete.

## [2.47.2] - 2026-08-21

### Added
- **Readability rule for main-window output**: `skills/shared/output-format/SKILL.md` now requires short paragraphs, lead-with-the-point answers, and bullets/tables over prose for anything an agent writes directly to the chat window (plans, explanations, reviews) — loaded by reviewers, `software-architect`, `qa-specialist`, `security-specialist`, `plan-mode`, and `/devteam:explain`. Reduces output tokens as a side effect.

## [2.47.1] - 2026-08-20

### Fixed
- **Comments policy had no length cap**: `skills/shared/comments-policy/SKILL.md` allowed WHY comments but didn't bound how long they could be, letting agents produce large documentation-style blocks in code and config files (observed in nginx config). Added a hard limit — max 3 lines per comment, max 3 comments per contiguous block — extended explicitly to config/infra files, not just source code.

## [2.47.0] - 2026-08-18

### Added
- **`/devteam:merge` command**: wraps `git merge` with target-branch detection (stops if already on the default branch), an isolated worktree/infra-aware quiz — commit + rebase + merge + teardown (recommended, delegated to `skills/shared/worktree/SKILL.md`'s existing finalize routine) vs. commit + merge only vs. merge only — and a nudge toward `/devteam:learn` when its `.learn-last-run` marker is stale relative to the current commit. `opt_out` plan gate, no agent spawn (thin wrapper), same pattern as `/devteam:push`.

## [2.46.1] - 2026-08-18

### Fixed
- **Autonomous Sprint Protocol resolved the worktree/branch decision silently, with no visible confirmation**: the manual Execution Strategy Gate has a step 5 ("Announce the chosen strategy, then proceed to execution"), but the autonomous-mode auto-resolve path (`skills/architecture/orchestration/SKILL.md`) had no equivalent — it read `worktree_active`, acted on it, and moved straight to spawning subagents, so the user had no way to confirm whether an isolated worktree was actually created before file writes started. The protocol now requires a one-line announcement of the resolved worktree/branch decision immediately after auto-resolving and before any subagent is spawned.

## [2.46.0] - 2026-08-18

### Added
- **Periodic work-feedback status table**: while background sub-agents work, the main agent now polls every N minutes (default 5) and prints a table-only status check-in — steps in planned order, ✅/⏳/🕐 status. New `skills/shared/work-feedback/SKILL.md` is the canonical home for the config gate, `ScheduleWakeup` loop mechanics, and table format; wired into `skills/architecture/orchestration/SKILL.md` § Spawn Integrity as check 5. Gated entirely by two new `credentials.local.json` keys, `work_feedback_active` (default `true`) and `work_feedback_interval_minutes` (default `5`) — `install.sh` writes them on fresh installs and additively backfills existing files, and `/devteam:health-check` Category 10 detects and fixes missing keys.
- **Unit-test isolation is now a hard rule**: `skills/testing/test-pyramid/SKILL.md` gained an explicit "no external agents" rule for unit tests (no DB, external API, filesystem, queue, or cache — even test/staging instances), mirrored into `backend-test-specialist`/`frontend-test-specialist`'s Test Quality Standards and enforced with a `[BLOCKING]` check in `backend-reviewer`/`frontend-reviewer`.

## [2.45.1] - 2026-08-17

### Fixed
- **`/devteam:commit` could silently skip documenting a commit**: Step 0 ("Auto knowledge capture") ran `/devteam:learn`'s evidence gathering *before* the commit was made, so its `git log`/`git diff` evidence never saw the commit about to happen, and the session-guard marker (`.dev-team-agents/.learn-last-run`) recorded the **pre-commit** HEAD. A later `/devteam:commit` call in the same session would then see "HEAD unchanged" and skip learn entirely, leaving that commit's work undocumented. The step now runs as Step 6, after commits (and any worktree rebase/merge) complete, so the marker reflects the post-commit HEAD.

## [2.45.0] - 2026-08-17

### Added
- **Commit Rule now ships to installed projects**: the Work Summary Table + skill-load + no-attribution rules previously only reached `/devteam:commit` (wired directly into `commands/commit.md`, which is shipped) — a direct-prompt commit in an installed project had no shipped file telling it to load `conventional-commits` or show the table, because the rule lived only in this source repo's own root `CLAUDE.md`, which `install.sh` never copies. `install.sh` Step 8b now injects the same rule into the target project's `CLAUDE.md`, mirroring the existing pre-compact-auto-summary injection exactly (marker-guarded append). Since `update.sh` re-runs `install.sh`, this backfills existing installs on update. `setup-health-check` Category 6 gained the matching detection + auto-fix for projects that update via health-check instead of re-running `install.sh`.

### Fixed
- **Unscoped full-suite test runs now blocked, not just nudged**: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` previously only injected an `additionalContext` reminder, which was easy to ignore in practice. It now hard-blocks (`exit 2`) the narrow case where a command looks like a full test suite run **and** nothing has been touched yet this session (clean working tree, no commits today) — there is no scope to derive from and no in-flight work the run could belong to. A `DEVTEAM_FULL_SUITE_CONFIRMED=1` command prefix lets an explicitly user-requested full run through. All other cases keep the existing nudge.
- **Graphify hint no longer spams every Glob/Grep**: `02-graphify-hint.sh` re-injected the same `additionalContext` block on every single Glob/Grep call for the whole session, compounding in the retained transcript — a confirmed contributor to "Prompt is too long" failures on long sessions. It now fires once per session via a `user-data/.graphify-hint-shown` marker, cleared by `session-start.sh` at the start of the next session.
- **Reviewer and PR flows no longer pull unscoped full diffs into context**: `skills/shared/reviewer-base/SKILL.md` and `commands/pr.md` pulled a full `git diff` into context regardless of size — another contributor to prompt-size overflow on sessions with large diffs. Both now check `git diff --stat` first and fall back to targeted per-file diffs above a size threshold.
- **Work Summary Table row/fallback fixes**: added a branch-name row and a `00`-seconds fallback when the seconds component of the work-start timestamp is unknown.

## [2.44.7] - 2026-08-16

### Added
- **Work Summary Table before commits**: `/devteam:commit` and any direct-prompt commit now show a standardized table (work start, commit request time, duration, worktree, isolated infra) before presenting the commit plan. Canonical definition lives in `skills/shared/conventional-commits/SKILL.md`, wired into `commands/commit.md` Step 5 and referenced from `CLAUDE.md`'s Commit Rule.

## [2.44.5] - 2026-08-15

### Fixed
- **`new-adr.sh` failed on a project's first ADR**: the `LAST=$(...)` pipeline that scans `docs/development/adrs/` for the highest existing ADR number ran `grep -oE 'adr-[0-9]+'` over an empty candidate list when no `adr-*.md` files exist yet. `grep` exits 1 on no match, and under `set -euo pipefail` that aborted the script before the template was ever written — so a fresh project could never create its first ADR. The pipeline is now wrapped with `|| true` so the empty case is tolerated and `LAST` falls back to `0` via the existing `${LAST:-0}` default.

## [2.44.4] - 2026-08-15

### Fixed
- **`update.sh` aborted the whole update on slim installs with opencode/Codex configured**: after a successful core update, it unconditionally re-ran `install-opencode.sh`/`install-codex.sh`, which abort with `exit 3` when the cross-CLI plumbing isn't bundled (slim installs strip it — see `scripts/lib/strip-tarball.sh`). Under `set -euo pipefail` that exit took down the entire update script, even though the Claude Code update itself had already succeeded. `update.sh` now checks for the plumbing first and, when it's missing, skips the provider re-render and prints the `install-provider.sh` bootstrap command instead of failing.
- **`installed_version` was never actually persisted through a normal install or update**: `install.sh` sources `scripts/lib/state.sh` for its `state_get`/`state_set` helpers only when that file happens to sit next to it on disk — true only when re-running the already-installed `.dev-team-agents/scripts/install.sh` copy directly. The far more common paths (a fresh `curl | bash` install, and every run through `update.sh`, which downloads `install.sh` alone to a `mktemp` file) don't have `lib/state.sh` alongside, so they fell back to no-op stubs: `state_set() { :; }`. Step 9's `state_set installed_version "$RESOLVED" ...` silently did nothing, so `state.json` kept reporting the old version forever — `/devteam:update` and the update-check hook would report an update available even right after a successful update completed. The fallback now embeds working `state_get`/`state_set` implementations (same JSON logic as `lib/state.sh`) instead of stubs.

## [2.43.0] - 2026-08-11

### Added
- **`agent_completed` telemetry event**: queues per-agent token usage and the actually resolved model (not the `tiers.json` config) at Stop time. `scripts/hooks/lib/agent-usage.sh` incrementally scans the session transcript for `Agent` tool_use/toolUseResult pairs (same byte-offset-cache technique as the disabled notifier hook) and sums usage from each agent's own output file. Dedup is by transcript offset rather than confirmed agent completion, since the parent transcript's `toolUseResult` was never observed transitioning out of `async_launched` — a still-writing agent is undercounted and not retried later, a documented tradeoff rather than unverified completion detection. `effort` is intentionally not collected: no empirical evidence it is exposed anywhere in the transcript.
- **`ingestion-api` skill**: new architecture skill wired into `backend-developer`, `database-specialist`, `devops-specialist`, and `software-architect`.
- **`sse-streaming` skill**: new skill with Server-Sent Events guidance, wired into `backend-developer`, `backend-reviewer`, `frontend-developer`, and `software-architect`.
- **HTTP client connection pooling guidance** added to the `resilience` skill, referenced from `backend-developer`.
- **Generic WebSocket best practices** documented in the `realtime` skill's implementation reference.
- **Provider embeddings/RAG comparison reference** added to the `llm-integration` skill.

### Changed
- **Re-enabled the `PreToolUse` telemetry queue and `Stop` telemetry flush hooks** (`02b-telemetry.sh`, `05-telemetry.sh`), disabled since 2026-08-06 pending review. `agent_spawned`, `command_invoked`, and `session_end` are collected again for any installation with `telemetry: true` — installations that already had it enabled do not need to re-consent, since `telemetry`/`auto_update` are never backfilled to `false` once explicitly set to `true`. `PRIVACY.md` and `CLAUDE-md/hooks.md` updated to match; both files now document the two hooks' coupling — re-enable together, never one alone, or events queue with nothing to flush them (or vice versa).

### Fixed
- **Telemetry queue was cleared even when delivery to PostHog failed**: `telemetry-send.sh`'s flush swallowed `curl`/`wget`'s exit status and unconditionally cleared the queue and bumped `last_flush` afterward, so a network failure during flush silently discarded events that were never actually sent. The real exit status is now captured, and the queue is only cleared on confirmed delivery.
- **Telemetry doc/behavior drift and a few robustness gaps**: `PRIVACY.md` documented three events (`agent_spawned`, `command_invoked`, `session_end`) that weren't being collected at the time because their hooks were disabled; `scripts/lib/telemetry-guard.sh` interpolated the preferences path directly into a Python source string instead of passing it as an argument; the anonymous install ID lived only in `telemetry-queue.json` and was regenerated if that file was ever lost. Guard now reads the path via `sys.argv`; the ID is persisted in `state.json` with the queue file kept as a fallback for existing installs.

## [2.42.0] - 2026-08-11

### Added
- **`/devteam:status` command**: runs `git status`/`git diff`/`git log` in a single bash call and prints branch, worktree, unstaged/staged changes, last 5 commits, and totals as formatted markdown tables. Accepts an optional `<branch-name>` argument to inspect a branch other than the current one — full unstaged/staged tables when that branch has a linked worktree checked out, commit history only otherwise. No agent spawn, minimum token cost.

## [2.41.2] - 2026-08-11

### Changed
- **`/devteam:install` prioritizes native Windows installs over WSL**: `skills/devops/tool-installers/SKILL.md` previously routed every Windows install through WSL unconditionally. It now checks for `winget`/`choco`/`scoop` first and uses native per-tool commands (e.g. `winget install BurntSushi.ripgrep.MSVC`) when available, falling back to WSL only when no native manager is present or the native install fails. Added a short manual fallback (get `winget`/Scoop, or activate WSL) for when neither path works.

## [2.41.1] - 2026-08-11

### Fixed
- **`graphify-refresh.sh` failed on every installed project**: it sourced `state.sh` via `$PROJECT_ROOT/scripts/lib/state.sh`, a path that only resolves when the script runs inside this repo itself. Once installed under `.dev-team-agents/`, that path doesn't exist and the script errored on every run (`No such file or directory`), silently disabling graphify change-detection. Now resolves `state.sh` relative to the script's own location (`BASH_SOURCE`), matching the pattern `scripts/new-adr.sh` already used.
- **Symlink repairs could silently recur on Windows**: `fix-symlinks.sh` could report "repaired" or "nothing to fix" while the underlying problem returned on the next `git checkout`/`pull`/`stash`/`reset --hard`, or on a teammate's fresh clone. Cause: when a `.claude/agents/dev-team`, `.claude/commands/devteam`, or `.claude/skills/<name>` symlink was first committed on a machine without native symlink support, its git blob stays mode `100644` (plain file) forever — `ln -s` fixes the working tree but never touches that committed blob. `fix-symlinks.sh` now detects this via `git ls-files -s` and prints `[DEVTEAM:SYMLINK_COMMIT_NEEDED]` with the exact `git add`/`git commit` needed to make the fix permanent; `/devteam:symlinks` and the health-check docs surface it distinctly from a plain repair.

## [2.41.0] - 2026-08-11

### Added
- **`/devteam:version` command**: prints the installed dev-team-agents version in the exact `[DEVTEAM:SESSION_BANNER]` layout `session-start.sh` shows at session start, on demand. Zero agent spawn, single bash call reading `installed_version` from `state.json` (same `CHANGELOG.md` fallback chain as the session banner) — built for minimum token cost, not routed through a subagent.

### Changed
- **Health-check No-Destruction Rule gained one narrow, canonical exception**: a `<name>.pre-migration.bak` file written by `state_migrate_legacy` may now be deleted, but only after Category 3 independently re-confirms its mapped key already holds a value in `state.json` (`BAK_CONFIRMED` vs `BAK_UNCONFIRMED`). Previously these accumulated forever in every project's `user-data/` root — the rule said "never deletes" with no path to clean up files that, by construction, had already had their sole piece of information durably copied elsewhere.

## [2.37.1] - 2026-08-09

### Fixed
- **Session identity banner was never visible to the user**: `scripts/hooks/session-start.sh`'s banner (added in 2.36.0) assumed `SessionStart` hook stdout prints to the terminal like a plain shell script. It doesn't — Claude Code delivers it as context for Claude, not as rendered terminal output, so the banner was silently invisible on every provider. The hook now tags the block with `[DEVTEAM:SESSION_BANNER]`, and a new rule in `CLAUDE-md/hooks.md` § Session Start Banner — Echo Rule instructs Claude to reproduce it verbatim as the first thing in its first reply of the session.
- **`Stop` hook payload temp file collided on macOS**: `scripts/hooks/stop.sh` used `mktemp /tmp/devteam-stop-payload.XXXXXX.json` — BSD/macOS `mktemp` only substitutes `XXXXXX` when it is the literal end of the template, so the trailing `.json` suffix made it create a file with the literal, unrandomized name instead. The first `Stop` on a machine silently created that literal file; every `Stop` after it failed with `mkstemp failed ...: File exists`. Dropped the `.json` suffix — no consumer of `DEVTEAM_HOOK_PAYLOAD` depends on the extension, they all read it as a plain file path.
- **`/devteam:install` listing table was hand-aligned columns, not a markdown table**: `commands/install.md` Step 2 now renders the tool status list as a proper `| Tool | Gain | Status |` table.

## [2.37.0] - 2026-08-09

### Changed
- **`worktree_path` default moved to the project root**: the default value of `worktree_path` changed from `.dev-team-agents/worktrees` to `.worktrees`, and the matching `.gitignore` entry follows. Applies only to a fresh `preferences.json` — an existing file is never rewritten. Updated across the canonical default (`scripts/lib/preferences-defaults.json`), the installer, every skill that reads or documents the key, and all docs/README mirrors.

## [2.36.0] - 2026-08-09

### Added
- **Session banner**: `scripts/hooks/session-start.sh` now prints a one-time identity banner at the start of every session — name, installed version (with a `CHANGELOG.md`-based fallback for this repo's own self-hosted install), repo link, conversation language, auto-update status, and worktree status. Replaces the old standalone "Conversation language" line.

## [2.35.1] - 2026-08-09

### Changed
- **`worktree` skill — unified naming rule made explicit**: worktree directory, branch, and (when Docker isolation applies) Docker Compose project/container names always derived from the same `<context>/<brief-title>` slug, but this was only implicit across `SKILL.md` and `docker-isolation.md`. Added an explicit "Unified naming" bullet to `SKILL.md` → Key Rules and a cross-reference in `docker-isolation.md`, so agents state the rule instead of inferring it.

## [2.35.0] - 2026-08-09

### Added
- **Full-suite test guard**: `skills/shared/scoped-test-execution/SKILL.md` (never run the full test suite without explicit user request) was only enforced inside `/devteam:*` agent routing, via `project-context`'s mandatory load — a plain main-loop session never triggered that load and could self-escalate to an unscoped full-suite run. `scripts/hooks/session-start.sh` now injects the rule unconditionally into every session, and a new `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` nudges (does not block, per this repo's PreToolUse convention) when a `Bash` command looks like an unscoped full-suite run (pytest/jest/phpunit/go test/gradle/flutter/cargo/rspec with no path/filter).

## [2.34.2] - 2026-08-08

### Fixed
- **`worktree` skill — teardown could destroy uncommitted work**: `git worktree remove` deletes uncommitted/untracked content silently, and the finalization flow (`references/branch-flow.md` Step 8) ran it right after merge with no check on working-tree state. A worktree with no commits — abandoned, or merged in a sibling worktree — lost all its edits on teardown with no warning. Finalization now runs `git status --porcelain` before removal; a dirty tree aborts teardown and asks the user (commit / discard / keep the worktree) instead of proceeding.

## [2.34.1] - 2026-08-08

### Fixed
- **`scripts/install.sh` — orphaned `.dev-team-agents.old.*` / `.new.*` swap directories**: the install/update swap (Step 2c) renamed the previous installation aside before removing it, but the final `rm -rf` was best-effort (`|| true`) and never retried, so a process killed mid-swap — or a failed removal on a locked/permission-denied file — left the backup on disk forever, with no warning. Install now self-heals any stray `.old.*`/`.new.*` directory from a previous interrupted run at startup, and `_cleanup()` retries the removal on exit and prints an explicit warning with the path if it still fails, instead of swallowing the error silently. `/devteam:health-check` Category 3 also now detects and removes any leftover swap directories as a safety net.

## [2.34.0] - 2026-08-08

### Added
- **`/devteam:sync-rules` — mode selection**: a new Step 2 asks via `AskUserQuestion` whether to apply every surviving candidate automatically ("Apply all automatically", recommended) or review each one individually, before scanning starts. `--all`/`--yes` still skips straight to all-mode without the quiz. Previously the command always confirmed one candidate at a time with no way to batch-apply.

## [2.33.0] - 2026-08-08

### Added
- **`/devteam:sync-rules` command** (`commands/sync-rules.md`) — scans `docs/` for conventions documented only in prose, dedupes against `docs/development/reuse-guidelines.md`, and runs `/devteam:rule`'s classify → propose → confirm → append routine per candidate. Fixes the gap where a documented convention (e.g. a response-envelope rule) never becomes a mechanically enforced registry row, so neither `reuse-lint.sh` nor the review gate can catch a violation.
- Wired into `install.sh` and `update.sh` (post-run suggestion to run the scan) and into `/devteam:health-check` Category 11, which now stays detection-only and points to the command instead of duplicating its classify/propose logic.

## [2.32.1] - 2026-08-08

### Fixed
- **`orchestration` skill — Spawn Integrity check 4 (Liveness)**: the orchestrator had no way to distinguish a subagent that was still executing from one that had silently stalled or died — its only signal was the final returned message, so a status question mid-run got answered from stale assumption. Now it notes spawn time, tries any available status/output check before answering, and states explicitly that completion can't be confirmed instead of asserting "still running".

### Added
- **`/devteam:commit` — Step 2.5 unrelated-changes quiz**: before staging, cross-references unstaged/untracked files against what was actually touched in today's session and asks via `AskUserQuestion` how to handle anything that doesn't match, instead of silently sweeping unrelated work into the commit plan.

## [2.31.0] - 2026-08-06

### Added
- **`data-fetching-integrity` skill** (`skills/architecture/data-fetching-integrity/SKILL.md`) — tool-agnostic gate for duplicate/redundant API calls in SPA/SSG frontends: symptom table (double-fire on mount, re-fetch on every render, siblings independently fetching the same resource, avoidable waterfalls, no de-dupe for concurrent identical requests, un-debounced fetch-on-input), root causes, and prevention rules.
- **New mandatory rule wired into `frontend-developer`, `frontend-reviewer`, and `qa-specialist`** — developer loads the skill before writing fetch logic, reviewer flags a match as `[BLOCKING]`, QA validates via the network panel as `[BLOCKER]`. Added as a pre-delivery item in `skills/shared/frontend-done-checklist/SKILL.md`.

## [2.30.2] - 2026-08-06

### Fixed
- **`/devteam:commit` no longer bundles `graphify-out/` regenerated output into the task's commit** — new "Graphify isolation" rule in `commands/commit.md` always splits any staged or unstaged `graphify-out/` changes into their own trailing `chore(graphify): ...` commit, after the task's other layered commits.

## [2.30.1] - 2026-08-06

### Fixed
- **PreCompact block now prompts instead of silently complying** — `CLAUDE-md/hooks.md` documents that `pre-compact.sh` can only emit plain text, so on its "SESSION SUMMARY REQUIRED" block Claude must use `AskUserQuestion` (generate automatically / write it myself / show a draft first) instead of writing the entry without asking.

## [2.30.0] - 2026-08-06

### Added
- **`/devteam:push` command** — thin wrapper around `skills/shared/github-actions/SKILL.md`; asks a CI/CD-aware quiz (watch CI + auto-fix vs. push-only vs. other) when GitHub Actions is configured, otherwise pushes normally. `plan_gate: opt_out`.
- **CI/CD-aware quiz before pushing** — `skills/shared/github-actions/SKILL.md` now asks the user (via `AskUserQuestion`) whether to watch CI or just push, instead of always watching. The same quiz gates the push triggered by `/devteam:pr`'s `gh pr create`.
- **`ci_cd_detected` preference** — caches the GitHub Actions detection result in `preferences.json` (`null` = unchecked, `true` trusted as-is, `false` always rechecked).
- **Push as a session-summary finalization signal** — `/devteam:push` and the push inside `/devteam:pr` now write today's `session-summary.md` entry right after a successful push if one is missing, instead of waiting for session end.

## [2.29.0] - 2026-08-03

### Added
- **Health check staleness notification** — `session-start.sh` now warns when `/devteam:health-check` hasn't run in over `docs_stale_after_days`, or has never been recorded on a project already in motion. `/devteam:health-check` (Step 4) and `setup-health-check/SKILL.md` (Flow step 5) now write today's date to `.dev-team-agents/user-data/.last-health-check` on every run.
- **Uncommitted-progress warning** — `stop/04-notifier.sh` fires a one-time-per-session `warning` when the turn count passes the new `session_no_commit_turns` preference (default `8`) with a dirty working tree and no commit since the session started (tracked via `.dev-team-agents/user-data/.session-head`, written by `session-start.sh`). Catches the case where a crash, `/clear`, or context compaction would lose the most.

## [2.28.1] - 2026-08-03

### Fixed
- **Context-window warnings (`context_window_percent_warning`/`_limit`) now fire in purely conversational sessions** — `stop/04-notifier.sh`'s `DEVTEAM_NO_CHANGES` fast-path used to skip the entire context estimation block whenever no file changed, so sessions with no edits never got warned no matter how full the context actually was. The fast-path now only skips the once-per-day tip lookup.
- **Context-window estimation is now exact instead of a compensated heuristic** — the transcript-based method used to sum `input_tokens + output_tokens` across every turn and apply `transcript_multiplier` (1.8) to correct for the resulting drift; because of prompt caching each turn's `input_tokens` already includes the full prior conversation, so the sum silently double-counted history and grew unboundedly. It now reads only the LAST usage entry's `cache_read_input_tokens + cache_creation_input_tokens + input_tokens` — the exact context size sent on the most recent API call. `transcript_multiplier` is deprecated (no-op, kept for backward-compat reads) and documented as such across `notifications.md`, `preferences.md`, `user-preferences/SKILL.md`, and both installation guides.
- **opencode sessions now get the same accurate context estimation as Claude Code** — `opencode/plugin/dev-team-agents.ts` used to invoke `stop.sh` with no stdin at all on `session.idle`, so the transcript-based method could never activate there and every opencode session silently used the coarse turn-count fallback. The plugin now fetches the last assistant message's token usage via `client.session.messages()` and passes a synthetic transcript payload shaped like Claude's, requiring no change to the shared bash parsing. Codex needed no change — its usage schema already parses correctly under the same keys.
- **`auto_update` no longer fails silently when `.installed-version` is missing or corrupted** — `pre-tool-use/01-check-updates.sh` used to `exit 0` with zero diagnostic; it now prints a message pointing at `/devteam:health-check`.
- **Auto-update no longer reports success when it actually failed** — the "updated to $latest" notification used to fire unconditionally even when `uc_perform_auto_update` failed (e.g. a partial install missing `installer-fetch.sh`); it now checks the return code and falls back to the "update available" notice on failure.

## [2.28.0] - 2026-08-03

### Added
- **Token economy in subagent delegation** — `skills/architecture/orchestration/SKILL.md` gains two mandatory rules: Subagent Report Economy (every spawn prompt must instruct the subagent to close with a concise report — no dumped file contents, command logs, or step-by-step narration — since a subagent's final message is the only thing that reaches the orchestrator's context) and Spawn Prompt Economy (pass condensed, already-synthesized project context instead of a re-read instruction, and reference an on-disk plan by file path + section instead of pasting the full plan into every parallel spawn)

### Changed
- **`project-context/SKILL.md` split for lighter per-agent loads** — First-Time Setup Guard, Session Summary Write Rules, and the Immutability Warning moved to `skills/shared/project-context/references/`, loaded only on their trigger condition instead of unconditionally on every load; the always-loaded body drops from 372 to 297 lines with no loss of coverage

## [2.27.3] - 2026-08-03

### Added
- **Python 3 is now documented as a prerequisite** and checked as a non-blocking warning — `install.sh` warns with OS-specific install instructions (macOS/Linux/Windows) when `python3` is missing instead of failing silently later; `/devteam:health-check` gained Category 12 (Python Prerequisite) with the same warn-only behavior; `README.md`/`README.pt-BR.md` document it in a new Prerequisites section

## [2.27.2] - 2026-08-03

### Fixed
- **`install.sh`'s directory swap now falls back to copy+delete when a rename fails even after retries** — v2.27.1's retry-only fix assumed transient locks, but on WSL a project under `/mnt/<drive>/...` (DrvFs) can fail a whole-directory `rename()` reliably, with nothing locked. `_mv_or_copy` tries the retried rename first and falls back to an explicit `cp -R` + `rm -rf` before giving up; the error message now also names DrvFs as a possible cause on `/mnt/` paths

## [2.27.1] - 2026-08-03

### Fixed
- **`install.sh` retries the directory renames used to swap `.dev-team-agents` into place** — on Windows a single locked file (open editor, terminal `cd`'d into the folder, antivirus real-time scan) could fail the whole-directory `mv` and abort the update; the swap now retries up to 5 times with a 1s backoff before failing, and the resulting error message names the exact directory and likely causes instead of a raw `mv` permission error
- **`graphify-refresh.sh`'s change-detection gate is no longer defeated by `SIGPIPE` under `pipefail`** — `grep -q` closing the pipe on `git log`/`git diff` made the gate silently skip rebuilds, and the output swap could abort silently on macOS's deny-delete ACL on `graphify-out/cache`, losing the freshly built graph; both failure modes exited 0, so the graph went stale with no visible signal. Health check Category 5 now validates `graphify.json` content and every `targetPaths`/`manifestPaths` entry, checks output integrity, and actually runs the refresh script to confirm it rebuilds instead of trusting that `graphify-out/` exists

## [2.27.0] - 2026-08-02

### Added — Consistency-loop fixes across coding and design agents
- **`reuse-guidelines` is now consulted before creating, not just at review time** — `frontend-developer`, `ui-ux-designer`, `backend-developer`, `database-specialist`, `devops-specialist`, `mobile-developer`, and `software-architect` all check `docs/development/reuse-guidelines.md` for a canonical implementation before proposing anything new
- **`ui-ux-designer` auto-switches to Consultive Mode** after `frontend-developer` reports UI changes in the same session, instead of waiting to be asked
- **`software-architect` gained a live Consultive Mode alongside `backend-developer`**, flagging `[ARCH-DEVIATION]` in-session instead of only at the post-hoc Quality Gate; `backend-developer`'s done-checklist now requires resolving it first
- **`design-system-audit`'s Design Mode template now fits the 80-line cap** enforced by `docs-sync` for `docs/design/design-system.md`, instead of a template that could never fit it
- **New non-blocking `design-token-lint` Stop hook** reports hardcoded CSS `px` values outside `var(--...)` tokens as a nudge, without blocking the session
- **ADR creation now checks for an existing ADR on the same topic first** — `skills/shared/adr/SKILL.md` gained a Check Before Creating step, `/devteam:adr` loads it before scaffolding, and `new-adr.sh` prints existing ADR titles as a mechanical reminder, closing a gap where `/devteam:adr`, `/devteam:learn`, and `software-architect` could each independently create a duplicate ADR for the same decision

## [2.26.0] - 2026-08-02

### Added — Spec layer between overview and sprints, with a living-spec amendment protocol
- **`product-analyst` now writes one testable spec per feature** (`docs/specs/<feature>.md`, `Given/When/Then` acceptance criteria, `touches`/`depends_on`) before generating sprints, using the new `templates/spec-template.md` and `skills/shared/spec-gate/SKILL.md`
- **A mechanical gate auto-spawns `software-architect`** to write `<feature>-contract.md` whenever a spec's `touches` field spans more than one layer or introduces a new API/schema — no user request needed
- **Execution agents and `qa-specialist` now treat the linked spec as the implementation and validation boundary**, asking rather than assuming when something isn't covered, instead of re-interpreting the sprint task text
- **A Living Spec amendment protocol keeps the spec current after implementation**: business-level divergence is amended in place by the executing agent, interface-level divergence goes through `software-architect`, and every amendment is logged in the spec's new `Amendment Log` section
- **A Spec Sync Gate at the end of work** has `qa-specialist` verify the spec still matches what was built and every amendment carries a reason, tagging drift `[SPEC-DRIFT]` and treating it as a `[BLOCKER]`
- **A hard gate blocks marking a feature done while an open assumption remains** — every assumption must resolve to an answered question, a spec amendment, or an explicit blocker before hand-off, enforced by `qa-specialist`'s Definition of Done check
- **A new `skills/shared/feature-learn/SKILL.md` fires automatically at the end of `backend`/`frontend`/`fullstack`/`mobile` sessions**, promoting spec amendments and non-obvious findings into docs, wiki, or an ADR (scoped mirror of `/devteam:learn`) so knowledge compounds feature-to-feature instead of aging unpromoted in `session-summary.md`

## [2.24.7] - 2026-08-02

### Fixed — Codex now routes guided choices through `request_user_input` and audits that generation
- **The Codex renderer now maps `AskUserQuestion` explicitly to `request_user_input` in Plan mode and rewrites quiz payload examples into the Codex shape.** Generated Codex command skills now preserve structured choice payloads in a form the runtime can actually consume instead of only describing an abstract quiz flow
- **Codex no longer silently degrades guided choices into inline prose when the session is outside Plan mode.** The rendered instructions now require a `/plan` retry when `request_user_input` is unavailable, so commands that depend on interactive branching stop pretending to offer a native chooser they cannot render
- **`/devteam:health-check` now verifies the new Codex quiz generation explicitly.** The Codex provider checks inspect rendered skills for `request_user_input`, `/plan` retry guidance, and absence of the old plain-text-degrade wording, then repair drift by re-running `install-codex.sh`

## [2.24.6] - 2026-08-02

### Fixed — Codex preserves structured quizzes and provider rewrites stay isolated
- **The Codex renderer no longer flattens `AskUserQuestion` flows into plain-text prompts or strips quiz JSON blocks.** Rendered Codex skills and agents now preserve the original structured choice flow so dynamic quizzes, confirmation gates, and guided branching survive the provider adaptation
- **Codex tool-convention notes now instruct the runtime to use structured user input whenever the current surface exposes it, with plain-text fallback only as a last resort.** This aligns the generated artifacts with the actual Codex app/runtime behavior instead of hard-coding a degraded interaction model
- **The opencode agent renderer no longer passes through Codex-only body rewrites.** This removes a real cross-provider leakage bug in the render pipeline and keeps provider-specific adaptations scoped to the intended target

## [2.24.5] - 2026-08-02

### Changed — Codex now standardizes on `$devteam-*` only
- **The Codex renderer and installer no longer treat `/prompts:` as a supported command surface.** Rendered Codex commands now exist only as project-local skills under `.codex/skills/devteam-*/SKILL.md`, and the surrounding command-map/docs text was updated to make `$devteam-*` the sole official invocation path
- **Legacy prompt aliases are now handled only as drift cleanup.** `install-codex.sh`, the health-check references, and the compatibility notes still detect and remove old `.codex/prompts/devteam-*.md` leftovers, but the harness no longer offers or documents prompt alias installation as part of normal Codex usage

### Fixed — `devteam:commit` no longer dead-ends on unstaged-only changes
- **When a project has modified files but nothing staged, `/devteam:commit` now routes through a structured decision instead of stopping on a plain-text blocker.** The command asks whether it should stage everything and commit, just show the commit plan, or abort
- **Re-running `install-codex.sh` from the project's own `.dev-team-agents` copy now works.** The materialized runtime now includes the minimal render plumbing required for `--source .dev-team-agents`, skips self-copy loops safely, and bootstraps the notifier state files expected by hooks and health-checks

## [2.24.4] - 2026-08-02

### Fixed — Codex CI fixtures no longer expect the removed project-local prompt directory
- **The slim-bootstrap contract test now validates the installed Codex project shape against command skills, not `.codex/prompts/`.** The skills-first migration intentionally stopped creating project-local `devteam-*.md` prompt files, but the bootstrap assertion still `find`ed that directory and failed even when the install was correct
- **The Codex installed-fixture validator now requires `.codex/skills/devteam-*` and rejects leftover `.codex/prompts/devteam-*.md` files.** This brings CI in line with the new installer behavior and catches regressions back to the legacy layout instead of enshrining it

## [2.24.3] - 2026-08-02

### Fixed — Codex installs now converge old projects to the new skills-first layout
- **`install-codex.sh` now removes legacy project-local prompt aliases under `.codex/prompts/`** when refreshing a project. Older Codex installs kept `/prompts:devteam-*` files inside the repo; re-running the installer now migrates them to the supported shape: project-local `$devteam-*` skills in `.codex/skills/`, with `/prompts:devteam-*` available only as optional user-local aliases in `~/.codex/prompts`
- **`update.sh` now re-runs the Codex installer when a project has `.codex/` config**, just as it already did for opencode. That means `/devteam:update` now repairs stale Codex layouts and refreshes generated agents, hooks, and command skills instead of leaving Codex installs partially outdated
- **The Codex health-check now treats project-local `.codex/prompts/devteam-*.md` files as legacy drift**, so it can point the user to the canonical repair path instead of accepting the old layout as healthy

## [2.24.2] - 2026-08-02

### Fixed — the Codex port now matches the runtime that actually executes the harness
- **Codex command prompts no longer pretend to pin runtime model/effort.** In Codex, those settings apply to `.codex/agents/*.toml`, not to `.codex/prompts/*.md`; the renderer now keeps prompt metadata informational and leaves the enforcement to the spawned agents
- **The Codex renderer no longer emits invalid quiz-tool instructions.** Claude-specific `AskUserQuestion` phrasing and embedded quiz JSON are rewritten into direct plain-text questioning so the rendered Codex artifacts stop referring to nonexistent tool calls
- **The Codex compatibility checker now validates the artifacts the port actually ships.** It scans prompts, agents, and generated skills, and fails on stale pseudo-tool residues and misleading prompt model metadata

### Added — a skills-first Codex entrypoint alongside the legacy prompt surface
- **Every Codex command now renders twice:** as the existing compatibility prompt `/prompts:devteam-<name>` and as an explicit skill `$devteam-<name>`
- **`install-codex.sh` now installs both entrypoints** and documents `$devteam-*` as the forward-compatible path while keeping `/prompts:devteam-*` available
- **The setup-health-check references now validate the full Codex install shape** — hooks, generated prompts, generated `$devteam-*` skills, and `.codex/agents/*.toml` `model` / `model_reasoning_effort` against `tiers.json` including `agent_effort` overrides

## [2.24.1] - 2026-08-02

### Fixed — the opencode installer silently produced an empty command block
- **`install-opencode.sh` handed the whole command snippet to `jq` as an exec argument** (`jq --argjson new "$CLEAN_JSON"`). Every command body is embedded in that JSON as a `template` string, so it grows with the roster — adding `/devteam:explain` pushed it past `ARG_MAX` and the merge died with `jq: Argument list too long`, leaving `.opencode/opencode.json` with `"command": {}`
- **The snippet now reaches `jq` through a temp file, read with `--slurpfile`**, which has no size ceiling
- **`v2.24.0` carries the defect**: an opencode install from that tag registers zero slash commands. Use `v2.24.1` instead. Claude Code and Codex installs are unaffected — neither path goes through this merge
- Caught by the two CI jobs that exist for exactly this, `slim-bootstrap` and the opencode installed-fixture validator; both now report 26 commands

## [2.24.0] - 2026-08-02

### Added — `/devteam:explain`, a glossary you can reach without leaving the session
- **`/devteam:explain SPA` or `/devteam:explain SPA, SSR, tenant, middleware`** — explains a term, acronym, or piece of jargon that came up in the conversation. Acronyms and initialisms are always expanded on the heading line; every term gets what it is, **the problem it solves**, and a concrete example — a code block in the project's own language when the concept is a code concept
- **Short by design.** Two sentences for the definition, one or two for the problem, the shortest example that shows the point, and an explicit list of things never to write — no opening line about the question, no restatement of what was asked, no closing summary, no "the topic goes deeper than this" caveat
- **It draws when the term is a shape.** A fenced `mermaid` block for a flow (middleware, CI pipeline), an exchange between parties (OAuth, webhook), containment (multi-tenancy, subnets), or a lifecycle (saga, order status) — capped at three to seven nodes, with edges labelled by what actually moves. It deliberately does **not** draw for a definition, a property, or a convention (`idempotent`, `DTO`, `camelCase`): a box with the word inside it teaches nothing and makes a short answer feel long, which is the failure the command exists to avoid
- **It answers in the main context and spawns no agent.** That is the point, not an omission: the terms come from the live session, and a subagent receives only the prompt text — it would lose the message where the term appeared, the file it was about, and the decision it belonged to. The command grounds each term in the session first, the repository second (citing `file:line`), and only then explains it generically
- **It always closes by offering an interactive quiz** — application questions rather than recall, one at a time, each wrong option a real misconception, and feedback that names the misconception instead of just pointing at the right letter
- Joins `update`, `symlinks` and `health-check` as a row whose `agent` is filler; it is `conditional` on the plan gate and, like `/devteam:review`, carries no plan-gate step because it writes nothing

### Added — commands can pin their model on Claude Code
- **`commands/<name>.md` may now open with a YAML frontmatter block, and `model:` in it pins that command's body.** Until now `commands.json` `tier` was inert on Claude Code, which symlinks command bodies and never passes them through the render engine — the tier only ever took effect on opencode and Codex
- **The seven `repetitive` commands** (`docs`, `pr`, `commit`, `learn`, `update`, `symlinks`, `health-check`) carry `model: haiku`. The other eighteen carry no key and keep inheriting the session
- **Restricted to `repetitive` on purpose, with the argument that already keeps `effort:` sparse:** the key *overrides* the session's model. Pinning `/devteam:plan` to `opus` would silently undo a user who lowered the session for cost; a `haiku` pin can only ever cost less than what they chose. `/devteam:explain` is `repetitive` and deliberately carries **no** pin — its output is a teaching explanation grounded in the user's own code, and the session model is the one they picked for that
- **`check_command_roster()` in `helpers/agent-lint.sh` now enforces it** — a pin outside `repetitive` fails, and a pin inside it must equal `tiers.json.repetitive.claude`. Presence is permitted, not required. All three branches were negative-tested
- The `commands.json` `_comment` had stated the opposite (*"do NOT add frontmatter to commands/*.md directly — Claude Code parses them as body-only"*). Claude Code does read command frontmatter; the note is replaced by `_claude_model_pin`, which records the rule and the reasoning

### Fixed
- **The renderer now strips command frontmatter before emitting the opencode template and the Codex prompt.** Command bodies were read with a raw `read_text()`, so the new YAML block would have been emitted as literal text at the head of every `template` string and every Codex prompt. `render_command_claude` still re-reads the source file, so Claude receives it byte-identical — verified against the CI contract checker on all three providers

## [2.23.2] - 2026-08-01

### Fixed — two `commands.json` rows ran an agent on a model that was not its own
- **`tester` was `tier: repetitive` while its lead `backend-test-specialist` is `backend-exec`** — which also contradicted the `CLAUDE.md` rule against putting a test agent on that tier. On opencode the command rendered `kimi-k2.5` for an agent whose own file declares `kimi-k2.7-code`
- **`health-check` was `tier: backend-exec` while naming `setup-assistant`, a `reasoning` agent.** The command spawns no agent at all — the field is filler the renderer requires — so it now names `technical-writer` at `repetitive`, matching `update` and `symlinks`, the two other `opt_out` runners
- **The fields are not independent knobs.** On opencode the snippet's `agent` makes the command run *as* that agent while `model` comes from the **command's** tier. 23 of the 25 rows already mirrored their lead agent's tier; the rule was simply never written down or checked

### Added
- **`check_command_roster()` in `helpers/agent-lint.sh`** — every command's `agent` must exist in `agents/`, and its `tier` must equal that agent's tier. The CI contract checker validates the *rendered* output and only catches a dangling ref, so the source-side rule lives in the lint, alongside the orchestration-roster check that exists for the same reason
- **`_tier_rule` and `_filler_agent_note` in `scripts/lib/commands.json`**, and the matching rule in `CLAUDE.md` next to the command table

### Fixed — commands ignored their lead agent's effort override
- **The same defect on the effort axis.** `resolve_effort()` was called with `agent=None` for commands, so a command took its tier's effort and skipped the `agent_effort` override of the agent it runs as. `devteam:tester`, `devteam:dba`, `devops` and `qa` rendered `default`/`medium` for agents that declare `low`
- **The renderer now passes the lead agent from `commands.json`.** All 25 commands render an effort that matches the agent they run as — verified across opencode and Codex
- `tester` had been masking this: its old (wrong) `repetitive` tier produced `low` by accident, so fixing the model exposed the effort mismatch that was underneath

## [2.23.1] - 2026-08-01

### Changed — the run banner says `session-default` instead of `inherit`
- **An agent that sets no `effort:` key showed `inherit` in its banner**, which names the mechanism rather than telling the reader what the agent is running at. The 11 agents in `reasoning`, `backend-exec` and `frontend` now show `session-default`; the 6 carrying `effort: low` are unchanged
- **Showing the resolved level was rejected, not overlooked.** The session's effort is not knowable at render time, and `skills/shared/model-identity/SKILL.md` forbids an agent from resolving its own identity at runtime — so the fix is a clearer label for the same semantics, not new information
- **The label is hyphenated on purpose.** `helpers/agent-lint.sh` strips spaces from the banner cell before comparing, so a two-word label would have to be matched as `sessiondefault` and would read like a typo to whoever touches that check next
- Propagated to `helpers/agent-lint.sh`, `skills/shared/model-identity/SKILL.md`, `CLAUDE.md`, `docs/providers.md`, and the `render_run_banner()` fallback in `scripts/lib/render_provider.py`. `inherit` stays in prose describing the **frontmatter** mechanism, where inheritance is still the accurate word

### Fixed
- **The `CLAUDE.md` run-banner example showed a third value**, an em dash, while every agent showed `inherit`. It is now aligned with the 11 agents it documents

### Added — why `qa-specialist` takes low effort and the reviewers do not
- **`agent_effort` carried a note for the agent it excludes (`security-specialist`) but none for the one that looks like it should have been excluded too.** `_why_qa_specialist` in `scripts/lib/tiers.json` records the dividing line: not whether the role inspects code, but whether the agent is **handed what to check**. QA validates observable behavior against acceptance criteria written before it ran; review and security audit exist to surface what nobody wrote down, and that exploration is exactly what `low` cuts
- The same test is summarized in `CLAUDE.md` next to the `agent_effort` description, so it is applied before adding an agent to the map rather than after

## [2.23.0] - 2026-08-01

### Changed — versioning policy now describes what the repo actually does
- **"Breaking changes (agent behavior changes, removed skills) → major" was never applied literally.** Read as written it makes nearly every release a major; in practice `v2.20.2` shipped a new mandatory emission for all 17 agents as a **patch** and `v2.21.0` changed how five specialists reason as a **minor**
- `CLAUDE-md/versioning.md` now spells out the three tiers with the real tags as examples, and states the test that decides a major: **does an existing installation behave differently after an update without its user asking?** Changed values in `preferences-defaults.json` do not qualify on their own, because an existing `preferences.json` is never rewritten

### Changed — default `preferences.json` values (fresh installs only)
- **`language` `en` → `pt-BR`, `auto_update` `false` → `true`, `worktree_active` `false` → `true`, `telemetry` `false` → `true`** in `scripts/lib/preferences-defaults.json`. These apply **only to a `preferences.json` that does not exist yet** — an existing file is still never rewritten, and neither is `credentials.local.json`
- **The installer still asks.** The language prompt now defaults to `[pt-BR]`, and the telemetry consent gate is unchanged: no terminal, `DEVTEAM_NONINTERACTIVE=1`, `n`, or 60s of silence all still write `telemetry: false`. Silence is still not consent

### Fixed — the default schema had drifted across five copies
- **`qa_browser` was missing** from the no-python3 fallback heredoc in `install.sh`, which also hardcoded `worktree_active: false` independently of the schema
- **`telemetry` was inverted** between `skills/shared/user-preferences/SKILL.md` (`true`) and the canonical file (`false`)
- **The health check validated a stale 9-field list**, silently passing files missing eight fields. It now reads the required set from `preferences-defaults.json` instead of hardcoding it
- **`skills/shared/project-context/SKILL.md` hand-wrote a 12-field copy** in its first-run path. It now copies the canonical file rather than retyping the JSON
- **`CLAUDE.md` now names the canonical file and lists every mirror** that cannot read it, so the next key change touches all of them

### Fixed — a backfill could switch telemetry and auto-update on without consent
- **`telemetry` and `auto_update` are now `CONSENT_KEYS`.** When either is absent from an **existing** `preferences.json`, both `install.sh` and `scripts/hooks/session-start.sh` write `false` rather than the schema's `true`. That file's owner never saw a prompt for a field added after they installed, so an absent key means "no"
- **This resolves a disagreement `CLAUDE-md/preferences.md` had recorded as an open question.** The fail-closed read path in `telemetry-guard.sh` treats a missing key as disabled, while the backfill would write the schema default and flip it to enabled at the next session start. The fix was the backfill, not the schema value — a fresh install should still default to enabled, subject to the prompt
- **The legacy `.auto-update` flag file still wins.** An install carrying it opted in explicitly, so the consent guard does not read its missing `auto_update` key as a revocation

### Fixed — an orchestrator could report spawns that never happened
- **Observed in the wild:** a `software-architect` run reported spawning `test-author` and `frontend-test-specialist` and said it was "waiting on the consolidated summary", while the UI showed no running task — no side panel, no animated logo, no pulsing bullet. `test-author` **does not exist** in this repo. Nothing had been spawned; the narration was invented
- **`skills/architecture/orchestration/SKILL.md` gained a `## Spawn Integrity` section** with three ordered checks: (1) **preflight** — if the Task tool is not in your tool list, stop and say so; never describe what the subagents would have done, which matters most for a nested orchestrator that may not have the tool at all; (2) **name validation** — `subagent_type` must appear verbatim in the Agent Roster, never inferred from the role; (3) **evidence** — a subagent's run banner arrives only in its final message, so no banner returned means it did not run
- **The consolidated-summary template was inviting the failure.** `### Agents spawned` / `[list of agents and what they did]` asks for a list from memory and accepts one written by an orchestrator that spawned nobody. It is now a table whose Model column is filled from the **returned** banner, with `NOT RUN` for any agent that returned none — and an all-`NOT RUN` result must be stated as the headline, not buried
- **`helpers/agent-lint.sh` now validates the roster against `agents/`** in both directions: a row naming a nonexistent agent, a row whose tier contradicts the agent's frontmatter, or an agent missing from the roster entirely (with `software-architect` and `setup-assistant` exempt — the orchestrator itself and the user-invoked onboarding agent). Verified against all three failure modes rather than assumed
- **Fixed the drift this check immediately caught:** the roster listed `backend-test-specialist` as tier `repetitive`, contradicting both its frontmatter and the explicit rule in `CLAUDE.md` that test authoring is not low-judgment work

### Fixed — subagents ran the full test suite despite `scoped-test-execution`
- **The rule was opt-in and reached 5 of 17 agents.** Nothing instructed a full-suite run; the leak was by omission. `frontend-developer`, `database-specialist`, the three reviewers and `software-architect` never loaded the skill
- **It is now part of the Foundational Rule.** `skills/shared/project-context/SKILL.md` carries a `## Test Execution — Scoped by Default` section, so every agent reaches it through the skill it already loads first. Fixing this centrally, rather than in twelve agent bodies, also kept `devops-specialist` (at the 211-line ceiling) from needing to grow
- **Orchestrators were propagating the problem.** `skills/architecture/orchestration/SKILL.md` now forbids passing "run the tests" unqualified into a spawn prompt, or instructing a full-suite run unless the user asked for one this session
- **Where the rule already existed, it was a checkbox on line ~157** of a 200-line body — passive, and read last. The two agents phrasing it that way (`backend-developer`, `mobile-developer`) now use the imperative "load before invoking any test runner" form that the compliant agents already used
- **The CI carve-out is explicit.** This governs local runs only; a pipeline still executes 100% of the suite and must never be narrowed to satisfy the rule

## [2.22.2] - 2026-07-31

### Fixed — the v2.22.1 compliance measurement was wrong, and so was the diagnosis it rested on
- **The real opening-banner rate is 14 of 16, not 13 of 13.** v2.22.1 classified every no-banner subagent transcript as a generic inline spawn by reading its prompt text (`You are implementing **Wave 1** of…`) instead of the `subagent_type` that produced it. Correlating each transcript with its spawning `Agent` tool call shows two of those were **dev-team agents that failed to emit**: `frontend-developer` and `database-specialist`
- **Both misses share a shape:** they were spawned *by another agent* with a long, directive task prompt, and their first action was to start the work (`Now let's write the core modules.`). The same pressure that loses the closing banner after a long task also loses the opening one when a strong task prompt arrives up front. `skills/shared/model-identity/SKILL.md` now says so explicitly
- **The v2.22.1 fix is unaffected** — it targets the closing banner, which was and remains 0 of 6. It does not address these two opening misses, which fail for a different reason
- **Corrected in `CHANGELOG.md`, `CLAUDE.md` and the model-identity skill.** The v2.22.1 entry keeps a pointer to this one rather than being silently rewritten
- **Method note worth keeping:** a subagent's prompt text says nothing about which agent definition ran it. Attribute transcripts through the `subagent_type` on the spawning `Agent` call, or the numbers are guesses

## [2.22.1] - 2026-07-31

### Fixed — the closing run banner from v2.20.2 was never actually emitted
- **Measured against live sessions, not assumed.** Across `navicms` and `site-prefeituras` on v2.22.0: the opening banner appeared in **14 of 16** dev-team agent runs, and the closing one in **0 of 6** runs that produced more than one message. Runs of 2, 3, 4, 6, 13 and 22 messages all opened with the banner and none closed with it; `Ran on:` appeared nowhere. (This line originally read "13 of 13" — see v2.22.2 for why that was wrong)
- **The v2.20.2 wording was not the problem — its position was.** Stating the requirement in `## Model Identity` at the top of the body means it has to survive the entire task; after a 22-message run it is long gone. Agents now carry a **`## Before You Finish`** section as the last thing in the body, so the requirement is the last instruction read before the summary is composed
- **`agent-lint.sh` enforces both presence and position**, because a section that works by recency stops working the moment someone appends another one below it. Adding a section to an agent now means adding it *above* that one
- **Earlier "success" readings were false positives.** Three runs looked compliant because the banner appeared in both the first and last message — they were single-message runs where those are the same text. Only runs with a genuinely separate summary test this
- **`helpers/size-limits.sh`: agent ceiling 205 → 211**, the exact size of the now-11-line mandatory model-identity boilerplate. The comment states the rule that survives this: raise it only for a new block required of every agent, by exactly that block's size, and never to make one long agent fit

## [2.22.0] - 2026-07-31

### Changed — the five specialists now run at low effort on opencode and Codex too
- **`agent_effort` entries gained `codex` and `opencode` keys.** v2.21.0 scoped the override to `claude`, leaving the same five agents on their tier defaults elsewhere; they now drop to `low` on all three providers. `qa-specialist` renders `variant: low` on opencode and `model_reasoning_effort = "low"` on Codex, against tier defaults of `default` and `medium`
- **A provider omitted from an entry still falls back to its tier level**, so the map can be rolled out one provider at a time — that is what made this a two-step change rather than a rewrite
- **`security-specialist` remains excluded** and keeps its `reasoning` tier level: `high` on both opencode and Codex
- Both values were checked against the contract's allowed sets before landing — `low` is in `CODEX_EFFORTS` and in the opencode effort set, and `check_tiers_completeness` validates column presence per tier rather than the rendered effort, so a per-agent override does not conflict with it

## [2.21.0] - 2026-07-31

### Added — per-agent effort overrides, and `low` on five specialists
- **New `agent_effort` map in `scripts/lib/tiers.json`**, keyed by agent name then provider, resolved ahead of the tier-level `effort`. Effort tracks how much a role needs to *reason*, which does not always follow the tier that picks its model — so it could not be expressed in a tier→effort map alone
- **`effort: low` on `backend-test-specialist`, `frontend-test-specialist`, `database-specialist`, `devops-specialist` and `qa-specialist`.** These roles carry detailed instructions and work largely to spec, so the extra exploration higher effort buys does not pay for itself
- **`security-specialist` is deliberately excluded, and the reason is recorded in `tiers.json` next to the map.** Low effort means fewer, more consolidated tool calls and less exploration before answering; in a security audit that exploration *is* the product, and cutting it is how a finding goes unreported. The exclusion is a decision, not an oversight — the note is there so the next person to notice the gap does not "fix" it
- **Scoped to the `claude` column.** opencode and Codex keep their tier-level effort — `qa-specialist` still renders `variant: default` on opencode
- **`agent-lint.sh` resolves the same precedence** and fails both on a mismatched effort and on an effort set where neither the agent nor its tier defines one. The lookup keys on the filename stem, which is the name the renderer uses, so the two cannot disagree

## [2.20.2] - 2026-07-31

### Fixed — the run banner never reached the main conversation from a background subagent
- **A subagent returns only its summary; everything before that stays in its own context.** The banner was emitted once, opening the agent's first response, so it reached the user only while the agent ran in the *foreground*. Claude Code runs subagents in the **background by default from v2.1.198**, which turned the banner into something visible only by opening the agent's transcript via `/tasks` — defeating the point of having one
- **Agents now emit the banner twice**: opening the first response, and closing the summary they hand back, under a `**Ran on:**` heading. The second emission is the load-bearing one — it is the only one that lands where the user is actually reading
- **Still exactly twice.** Not after every tool call and not between phases: those intermediate messages never leave the agent's context, so a banner there is pure noise
- This was a design gap in v2.20.0, not a regression. On Claude Code 2.1.140 and earlier the foreground default masked it; the failure would have appeared silently on upgrade

## [2.20.1] - 2026-07-31

### Fixed — Claude Code does support per-subagent effort; v2.20.0 said it did not
- **The claim was checked against the docs and was wrong.** `tiers.json`, `CLAUDE.md`, `docs/providers.md` and the model-identity skill all stated that Claude Code has no effort concept, and the run banner printed `—` in the Effort column. Claude Code accepts an `effort:` frontmatter key on subagents (`low` … `max`)
- **`repetitive` now sets `effort: low`** — bounded, low-judgment work where the saving is unambiguous, on top of the Haiku move. **No other tier sets it**, deliberately: the key *overrides* the session's effort level, so setting it everywhere would silently undo a user who lowered effort for cost or latency. Omitted means the agent inherits the session, which is the right default
- **The banner's Effort column now reads `inherit`** on tiers that set none, instead of `—`, which is what the agent actually runs at
- **`agent-lint.sh` guards the new key in both directions:** an agent whose tier defines an effort must carry it and match, and an agent whose tier does not must not carry one at all

### Fixed — a `set -o pipefail` interaction that made the linter exit silently
- **`grep` returning 1 inside a command substitution killed the whole script.** `effort:` is absent on 16 of 17 agents, so `effort_fm=$(… | grep -E "^effort:" | …)` failed the pipeline, `set -e` fired, and the linter exited 1 having printed nothing — no findings, no error, no clue
- **The same latent bug sat in the banner lookup.** An agent with no `<!-- run-banner -->` block would have crashed the linter instead of reporting the missing block — the exact condition that check exists to catch. Both now end in `|| true`

### Verified — model aliases are accepted by Claude Code
- Confirmed on two independent sources: the subagent frontmatter reference (`sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit`), and the installed 2.1.140 binary, which carries the `opus` / `sonnet` / `haiku` / `inherit` literals. `fable` is **absent** from that build, which reinforces the earlier decision to keep it out of the tier map
- **Documented two ways the banner can be out of step with reality.** The frontmatter `model:` is only the third source Claude Code consults, after `CLAUDE_CODE_SUBAGENT_MODEL` and any per-invocation `model` parameter; and an org `availableModels` allowlist makes it silently fall back to the inherited model. The banner reports configured intent, not the runtime's final choice

## [2.20.0] - 2026-07-31

> **Action required if you maintain a custom agent.** The authoring rule was "**No `model:` key**"; `model:` is now required and must equal `tiers.json[<tier>].claude`. Any agent authored against the old rule fails `helpers/agent-lint.sh` on the next run — including from the `Stop` hook. Add the key (`reasoning` → `opus`, `backend-exec` / `frontend` → `sonnet`, `repetitive` → `haiku`) plus the `<!-- run-banner -->` block; the lint message names the expected value. Released as a minor rather than a major despite the agent-behavior change, so this note is the migration signal.

### Added — subagents now actually switch models on Claude Code (behavior change)
- **The tier system was inert on Claude Code.** `render_agent_claude()` is the identity case and `install.sh` symlinks `agents/` into `.claude/agents/dev-team/` without ever invoking the renderer, so the resolved model was computed and then discarded. Every subagent ran on the session's model — `software-architect` (`reasoning`) and `technical-writer` (`repetitive`) were indistinguishable. Only opencode and Codex had per-tier model selection
- **Agents now carry a `model:` frontmatter key** alongside `tier:`. It is a *checked mirror* of `tiers.json[<tier>].claude`, not an independent value — Claude Code reads it directly from the symlinked source, which is the only channel available when nothing is rendered at install time
- **The `claude` column holds aliases now** (`opus` / `sonnet` / `haiku`) instead of pinned ids. The pinned ids had already drifted a generation behind (`claude-opus-4-7`, `claude-sonnet-4-6`); aliases track the current model of each family and do not go stale on a model launch
- **New mapping, chosen for cost/quality/latency:** `reasoning` → `opus`, `backend-exec` / `frontend` → `sonnet`, `repetitive` → `haiku`. The material change is `repetitive`, which was paying Sonnet rates for doc generation and now runs on Haiku at roughly a third of the cost
- **`backend-test-specialist` moved from `repetitive` to `backend-exec`**, matching `frontend-test-specialist` in `frontend`. The two had been asymmetric; the asymmetry only became expensive once `repetitive` meant Haiku, since authoring backend tests is not low-judgment work. `repetitive` now holds `technical-writer` alone
- **Three copies of the mapping, one guard.** `helpers/agent-lint.sh` re-derives the map from `tiers.json` on every run and fails if `model:` or the run-banner row disagrees with it, in either direction. `model` is now in `REQUIRED_FIELDS`
- **Rejected alternative:** having `render_agent_claude()` inject the model and `install.sh` copy instead of symlink. That breaks the byte-identity assertion in `check_claude` (`.github/scripts/ci/provider/_contract.py`), requires `update.sh` to re-render, and changes what `fix-symlinks.sh` and the health-check's symlink category test. The mirrored key achieves the same result with none of that blast radius

### Added — every agent opens with a run banner, on all three providers
- **`skills/shared/model-identity/SKILL.md` now emits a table** (agent, tier, model, effort) rather than a one-line blockquote, and each agent body carries its own values in a `<!-- run-banner -->` block inside `## Model Identity`
- **The banner is resolved at render time, not runtime.** `render_run_banner()` rewrites the Model and Effort cells for opencode and Codex; the source copy holds Claude's values because Claude is the identity case. Agent and Tier cells are provider-agnostic and pass through
- **This replaces a runtime resolution procedure that was wrong by construction.** The skill used to tell each agent to detect the provider by directory presence — checking `.opencode/` *before* `.claude/` — and then read `tiers.json` itself. A Claude project that later ran `install-opencode.sh` (a flow the framework explicitly supports) would report opencode's model on every Claude agent. It also cost a file read on every single agent invocation
- **`helpers/size-limits.sh`: agent ceiling 200 → 205.** The banner adds a fixed 5 lines to all 17 agents; six were pushed over. The content budget is unchanged at 200 — the comment in the script says so, and says not to raise it again to fit a long agent
- **Note for whoever extends `agent-lint.sh` next:** the first draft of the `tiers.json` lookup used `f"{tier}\t{entry[\"claude\"]}"` — a backslash inside an f-string expression, which is a `SyntaxError` — behind a trailing `|| true`. The map came back empty and the check silently passed everything. It was caught only by introducing drift on purpose and noticing that two of the three expected errors fired. Never let a `|| true` cover a snippet whose failure mode is "the check does nothing"; the guard now reports an unreadable `tiers.json` as an error instead of skipping

### Fixed — the shellcheck gate now passes on the tree it was promoted against
- **`helpers/orphan-skill-scan.sh` had `2>/dev/null` in the middle of a `find` expression**, before `-exec … -print`. It worked — the shell strips the redirect and applies it to `find` — but it read as a per-action redirect and was one edit away from becoming one. Moved to the end
- **Three `# shellcheck source=` directives used script-relative paths**, which resolve to nothing when CI runs `shellcheck -x` from the repo root. The unresolved source hid the guard's use of `PREFS_FILE`, so each `SC1091` also produced a bogus `SC2034` — nine findings from one cause. The paths are now repo-root-relative, the form `scripts/update.sh` already used, and in two of the three the directive moved below the `[ -f … ] || exit 0` guard, since a directive separated from its `.` line is not attached to it
- **`_telemetry_enabled` is now called with `"$PREFS_FILE"` at all four call sites.** Behaviourally identical (`${1:-${PREFS_FILE:-}}`), but it turns an implicit dependency on a global into an argument, which is what keeps the `SC2034` class from returning if a source path ever breaks again
- **`SC2317` and `SC2329` are both disabled on `uc_setup_http`** — the unreachable-function check was renumbered between shellcheck releases, and CI runs an older build than a current local install
- **Note for whoever promotes the next advisory check:** this gate was flipped to blocking in `c7535b7` with the note "the tree is clean". It was not, and `main` stayed red until this fix. Run `bash .github/scripts/ci/01-lint.sh` — not the individual helpers — before promoting

## [2.19.0] - 2026-07-31

### Changed — agents run scoped tests, never the full suite (behavior change)
- **New canonical skill `skills/shared/scoped-test-execution/SKILL.md`.** When finishing a task, an agent now runs only the tests covering the code it touched plus that code's direct dependents. The project's full suite is left to CI, or to the user running it manually
- **One exception, and only one:** an explicit user request in the session ("run the whole suite"). Suite speed, refactor width, changes to shared code, a failing scoped test, a release or a merge do **not** authorize a full run. An ambiguous request ("make sure nothing broke") resolves to the scoped run plus an offer, never to escalation
- **The `< 60 s` fast-suite criterion in `/devteam:commit` is gone.** Step 4.5c used to run `npm test` / `pytest` / `go test ./...` / `make test` whenever the suite was believed to be fast; it now delegates to the skill and runs only what covers the staged files
- **`/devteam:refactor` no longer tells `qa-specialist` to run the full suite** during the quality gate
- **Definition-of-Done lines updated** in `backend-developer`, `mobile-developer` and `skills/shared/frontend-done-checklist` — "Test suite passes" became "Tests covering the change pass". `backend-test-specialist`, `frontend-test-specialist` and `qa-specialist` load the skill before executing any test command
- **No gate was weakened:** a failing scoped test still blocks the task, CI pipelines still execute 100% of the suite, and what agents *write* is still governed by `skills/testing/test-strategy/SKILL.md`

### Changed — telemetry now requires explicit consent (behavior change, action may be required)
- **Anonymous telemetry defaults to DISABLED.** It is enabled only when the installer could reach a terminal *and* the user actively accepted the prompt. Previously the value was pre-set to `"telemetry": true` and the consent prompt was gated behind `[ -t 0 ]` — which is false under the documented `curl … | bash` install, because stdin is a pipe. The prompt therefore never appeared on the primary install path while telemetry was already on, contradicting the opt-out consent both READMEs advertised
- **The interactivity test is now "can we open `/dev/tty`"**, not `[ -t 0 ]`, so the prompt is actually shown on the `curl … | bash` path. Pressing Enter still accepts — the opt-out model survives wherever the prompt is genuinely reachable
- **A 60-second timeout or an EOF counts as declining.** Silence is not consent
- **`DEVTEAM_NONINTERACTIVE=1` forces the silent path** (CI, container image builds, automated provisioning) — no prompt, telemetry left off
- **The read path fails closed to match.** `_telemetry_enabled` was defined three times across `scripts/helpers/telemetry-send.sh`, `stop/05-telemetry.sh` and `pre-tool-use/02b-telemetry.sh`, and a missing or unreadable `preferences.json` used to resolve to *on*. It is now a single definition in the new **`scripts/lib/telemetry-guard.sh`**, and a missing file, an unreadable file, a missing `telemetry` key, or no `python3` all resolve to *off*. A consumer that cannot source the guard must also skip sending
- **Existing `preferences.json` values are untouched** by an update. A **legacy file missing the `telemetry` key now resolves to off** on the read path. Note the remaining seam: `scripts/lib/preferences-defaults.json` still carries `"telemetry": true`, so the session-start backfill will write `true` into such a legacy file on the next session — documented in `CLAUDE-md/preferences.md` until the default is flipped
- **`PRIVACY.md` corrected on two counts** — it described a pure opt-out model (now a consent table matching the installer), and it named the PostHog **EU** region while the code has always posted to `us.i.posthog.com`. The document now states the US region, and mentions `DEVTEAM_POSTHOG_ENDPOINT` for self-hosted instances
- **PostHog key comment disambiguated.** Two adjacent comments claimed the embedded key was both intentionally public and a placeholder to replace before release. It is a full-length `phc_` project *capture* key — write-only ingestion, cannot read, query or export. The stale TODO referred to a literal placeholder that no longer exists

### Fixed — install, update and rollback lifecycle
- **Fresh installs were broken.** A genuinely clean install died at Step 2b: `user-data/` does not exist in the tarball, so the credentials heredoc failed and `set -e` exited 1. Reproduced against the unmodified original; fixed with `mkdir -p`
- **The install swap could destroy an existing installation with nothing to restore from.** `rm -rf` preceded each `mv`: if the first move failed the existing install was already gone, and if the second failed, `user-data/` — preferences and session summary — survived only in an unadvertised `mktemp` directory. Replaced with a **stage-aside-swap**: build the new tree as a sibling, rename the current one aside, rename the new one in, delete the aside copy last. Both critical steps are same-filesystem renames, and an `EXIT` trap restores the aside copy if the script dies between them. Also corrects a comment claiming the rename kept the running script alive — `update.sh` executes from inside the tree being replaced
- **Download failures reported a single generic message.** stderr from all three fetches went to `/dev/null`, so TLS errors, a 404 on a bad tag, proxy failures and rate limits were indistinguishable on the sole install entry point. The cause is now printed, on the failure path only
- **`chmod` had drifted past three shipped subtrees** (`hooks/lib`, `scripts/helpers`, `scripts/lib`) because it enumerated four directories by hand. Replaced with a recursive `find`, so it cannot drift again
- **Update integrity.** `update.sh` piped an unverified download into `bash`. There is no release workflow and no published checksum, so authenticity is not achievable here and is **not** claimed. What is now true: the installer is fetched from the **same pinned ref** as the payload rather than a moving `main`; the payload is verified before `bash` sees it (non-empty, size floor, shebang, project markers, `bash -n` parse — which catches truncation); and a SHA-256 is checked when `DEVTEAM_INSTALLER_SHA256` or a published digest exists, with a mismatch aborting. The file header states plainly that this does not defend against a repo-write attacker, who controls both files
- **New `scripts/lib/installer-fetch.sh`** — `rollback.sh` duplicated `update.sh`'s HTTP detection, GitHub coordinates and fetch sequence byte for byte. Extracted into one shipped library, now also used by the unattended auto-update hook path

### Fixed — repository tooling that silently did nothing, or the wrong thing
- **`orphan-skill-scan.sh` no longer deletes.** Its auto-fix ran `sed "/$ref/d"`, removing the *entire line* containing a broken skill reference — on a routing-table row that took the detection signals with it, silently, unattended, on every Stop. Observed live: moving the `jquery` skill destroyed its row in `frontend-developer.md`. It now **repairs** the path when the skill can be located unambiguously by basename, and **reports** anything it cannot resolve instead of removing it
- **`orphan-skill-scan.sh` no longer counts a narrative mention as a load**, which was producing an unresolvable standing finding on `software-architect`. The genuine finding (`migration-v1-to-v2` had no agent reference) still reported, and is now resolved
- **`archive-index.sh` was a guaranteed no-op**, not merely unwired: its parser matched `### YYYY-MM-DD` while the index uses `## YYYY-MM-DD`, so it found zero sections and would have reported "nothing to archive" forever — the documented 90-day rotation could never have run even once triggered. Both `awk` passes also mishandled nested category headings; removal would have truncated the file to EOF. Rewritten and verified against a sandboxed copy of the real index: correct quarter routing, entry count conserved, idempotent, with a trustworthy `--dry-run`
- **`check-fingerprint-uniqueness.sh` now scans the archive files too.** Scoped to a single file, this blocking gate would have silently degraded from a global to a per-file guarantee the moment rotation ran
- **`orphan-template-scan.sh` now checks resolvability, not mention.** It surfaced 6 references using bare `templates/…` paths that resolve only inside this repository, not from an installed project root; `runbook-template.md` had zero resolvable references and was previously reported healthy. All template references now use the installed `.dev-team-agents/templates/…` form that `new-adr.sh` already proved
- **`check-codex-compat.sh` aborted with an unbound variable** when run with no arguments, contradicting its own usage line

### Fixed — skills
- **`discovery-mode` shipped two real bugs in a snippet models transcribe verbatim.** The acquire block returned before the staleness check could ever run, so a stale lock blocked discovery permanently; and the check used GNU-only `date -d` with `|| echo 0`, which on macOS made every lock look stale and **deleted it unconditionally** — the exact opposite of the intent, on a large share of installs. Both fixed with `find -mmin`, verified across GNU, BSD and dash
- **`architecture-awareness` contradicted the stack-agnostic core rule** at the one place every coding agent reads on every spawn: it enumerated frameworks and bundlers with no section gate, so `backend-developer` received SPA advice and `mobile-developer` received two browser sections that do not apply. Rewritten as structural signal-to-model tables with a routing gate and a mobile section that voids the DOM rules
- **`mobile/ios` and `mobile/android` stacked instead of replacing.** Each opened by loading the very reference the agent's routing table already loads — 507 lines for a cross-platform task. Each now declares itself the engineering half and defers the design half
- **`reviewer-base` restated a strict subset of the SonarQube detection signals**, silently missing two detection paths. It now delegates to that skill's own table
- **`security-checklist` asserted the security/QA overlap** rather than partitioning it. It now carries an explicit ownership boundary with a cross-boundary reporting protocol
- **Integration skills audited before the inlined agent copies were deleted.** Kong's `strip_path` rule lived only in `references/consumers.md`, so removing the agent copy would have reference-gated a critical rule; none of SonarQube's four developer rules existed in the skill at all. Supabase and `async-jobs` each gained one rule. Nothing was lost in the extraction

### Added
- **`/devteam:setup`** — `commands/setup.md` gives `setup-assistant` the slash-command entry point every other agent already had. Detects `FIRST_RUN` vs `REFRESH` from the presence of `docs/project.md`, reports the mode, and delegates the full flow. Registered in `scripts/lib/commands.json` with `plan_gate: required`
- **`skills/architecture/llm-integration`** — embeddings, retrieval, prompt versioning, evaluation, and an 11-row failure-mode table covering prompt injection and PII. The repo had no such skill; its only pointer, in `db-comparison`, routed pgvector questions to a multitenancy skill
- **`skills/testing/load-testing`** — load profiles, SLO-derived thresholds and percentile interpretation, with an explicit boundary against `performance-budgets`. Loaded by `backend-test-specialist`
- **`skills/testing/frontend-hook-tests`** and **`skills/testing/decoupled-frontend`** — React `renderHook` / Vue `withSetup` recipes, and MSW handlers, state coverage and selector priority, extracted from `frontend-test-specialist`
- **`skills/devops/infrastructure-sizing`** and **`skills/security/dependency-audit`** — both were stack-prescriptive at source and were rewritten to preserve the judgment while dropping the prescription: sizing is capability tiers T0–T3, scanner selection is a lockfile-signal table where exactly one row applies. Product names survive only as labelled examples
- **`skills/architecture/orchestration`** and **`skills/architecture/architecture-docs`** — extracted from `software-architect` to bring it under the line cap
- **`skills/legacy/`** — new skill category for legacy-codebase survival material. `jquery` moves here from `ui-libraries`; its content is survival guidance, not component-library reference
- **New Stop sub-scripts** — `03b-fingerprint-uniqueness.sh` (static validation; exits 2 so the finding reaches the session instead of arriving later as a red build) and `99b-archive-index.sh` (cleanup tier, must run after every check that reads the fingerprint bank, gated by a daily stamp since rotation is time-based). Both degrade silently where `helpers/` is absent, as it is in every installed project
- **`DEVTEAM_HOOK_DEBUG`** — set it to trace which hook sub-scripts ran, which were skipped, and with what exit code

### Changed — hooks
- **Both dispatchers now require the documented `NN-name.sh` / `NNx-name.sh` filename pattern** and skip anything that does not match. They previously globbed every `.sh` in their directory, so a draft or a renamed `.bak` executed on every Stop or every tool call. Chosen over an allowlist (no second registry to drift) and over an opt-out marker (fails open). All current sub-scripts match
- **`pre-tool-use/02-telemetry.sh` renamed to `02b-telemetry.sh`.** Two sub-scripts shared the `02-` prefix with order decided only by an alphabetical tiebreak; `02-graphify-hint.sh` keeps its number as the externally referenced one
- **Change gates.** `02b-orphan-template-scan` was the only Stop sub-script with no gate, running a full recursive scan across four trees on every Stop including purely conversational ones. `05-telemetry` ignored the dispatcher's no-changes flag, queueing a `session_end` for every empty turn. Both now honour it; `05` keeps the flush (it is TTL-gated and the only delivery path for events queued by PreToolUse) and suppresses only the event
- **Hot path.** `01-check-updates` forked `python3` to read the update interval *before* its own TTL early-return, so the 24h cache could never prevent the fork — on a hook that runs on every tool call. The interval now comes from a sidecar cache invalidated with `[ prefs -nt cache ]`, a bash builtin. Measured: cold run 1 fork, hot run 0 subprocesses
- **`01-check-updates` decomposed** from a 209-line monolith into a 79-line orchestrator over the new **`scripts/hooks/lib/update-check.sh`**, which also fixes a pre-existing trap leak where the auto-update `EXIT` trap replaced the temp-file trap
- **Auto-update integrity.** `uc_perform_auto_update` piped an unverified download from a moving ref straight into `bash` — on the *unattended* path. It now delegates to `scripts/lib/installer-fetch.sh` for ref pinning and payload verification, and **skips the upgrade entirely** if that library is absent rather than falling back to an unverified fetch
- **Git state deduplicated.** `stop.sh` computes the touched-path set once and exports it via the new **`scripts/hooks/lib/touched-paths.sh`**; sub-scripts `02`, `02b`, `03` and `03b` no longer each re-run identical `git status` / `git log` invocations. Four forks removed, and the sub-scripts still work standalone
- **Notifier tips moved out of the script.** The 45 inline tip strings now live in `scripts/hooks/stop/tips/tips.{en,pt-BR,es}.txt`, so the notifier reads **one** locale after the daily gate instead of parsing all three on every Stop. Adding a locale is one file plus one `case` arm

### Changed — agent and command authoring standards
- **Agent frontmatter is `name` + `description` + `tier`.** `CLAUDE.md` still mandated the `model:` and `tools:` keys that the multi-provider port removed — following the canonical doc produced an agent that failed CI. The standards block now documents the four valid tiers, points at `scripts/lib/tiers.json` as the canonical tier → model id map, and drops both the Haiku note (no tier resolves to Haiku on any provider) and the obsolete tools-order rule
- **All 17 agents are within the 200-line cap for the first time** — from 11 violations to 0, and `agents/` from ~3,900 to 3,100 lines. `software-architect` 372 → 185, `frontend-test-specialist` 266 → 180, `backend-developer` 265 → 167, `setup-assistant` 244 → 195, `devops-specialist` 243 → 198, `security-specialist` 240 → 198, `frontend-developer` 236 → 196, `code-reviewer` 233 → 185, `qa-specialist` 227 → 196, `backend-reviewer` 209 → 194, `mobile-developer` 203 → 173
- **`helpers/size-limits.sh` now passes strict with no flag** — 17/17 agents, 25/25 commands and every `SKILL.md` within their caps. `commands/learn.md` (229 → 194) was the last file over any declared limit
- **The Foundational Rule is delegated, not inlined.** 15 agents carried the same 12-item context list — 384 duplicated lines fleet-wide. All 17 now delegate to `skills/shared/project-context/SKILL.md` in one line and keep only genuinely role-specific additions
- **Directives with a canonical home were deleted rather than paraphrased**: the project-rules-override sentence (14 copies) lives in `project-context`; the docs-sync closing paragraph (13 copies, already drifted into two variants) is now a **Task Closure Rule** in `skills/shared/docs-sync/SKILL.md`; the comments-policy routing parenthetical (8 copies) is in that skill's Conditional Section Loading table; the SonarQube detection triple (11 copies) is in `project-context`; the token-efficiency load line, drifted into nine wordings, is now one. The TODO/FIXME reviewer bullet, triplicated in two diverging variants, is gone entirely — `comments-policy` already owns the rule and all three reviewers load it
- **`## Worktree Isolation` now delegates.** The decision cascade was restated in all 8 coding agents (~15 lines each) and drifted between them. Agents point at the canonical cascade in `CLAUDE.md` and at `skills/shared/worktree/SKILL.md`; the cascade itself is documented exactly once
- **`code-reviewer` matches its documented contract.** It shipped 10 structural review categories while `CLAUDE.md` says the router coordinates rather than duplicates specialist checks. Nine were covered by the specialists and were removed; the three that existed only here — running the linters, cross-cutting silent bugs, static-state-vs-injection — survive as Router Responsibilities. Its 15-item Foundational Rule, which mixed five conditional loads into the mandatory list, is now split
- **Stack-prescriptive agent bodies moved to skills** — `security-specialist`'s nine-scanner command block, `backend-developer`'s eight blocks of inlined integration rules, `devops-specialist`'s Kubernetes/Nginx/Datadog decision framework, `frontend-test-specialist`'s hook recipes and decoupled-frontend material, `backend-test-specialist`'s five-language coverage matrix, `setup-assistant`'s Docker Compose probe (now in `stack-detection`, whose consumer is every agent rather than devops alone). `frontend-developer`'s data-fetching and security rules and `frontend-reviewer`'s type-safety criteria were rewritten framework-neutrally, with identifiers demoted to examples
- **`setup-assistant`** merges its duplicate Immutability Warning headings, delegates its bundled Health Check and Update Manager roles to the procedures that already exist for `/devteam:health-check` and `/devteam:update`, and gains a trigger for the `migration-v1-to-v2` skill, which had no consumer despite defining what v2 is
- **`product-analyst`** loads the 237-line `backlog-template` only when producing backlog output, and its tracker section gained an explicit fallback instead of silently handling two of the five trackers the installer advertises
- **Quiz-first Rule enforced across `commands/` too.** Seven live violations were found, not the two previously reported — the linter only ever scanned `agents/`, so `commands/` had never been checked, and its regex only matched yes/no forms. Fixed in `refactor`, `audit`, `commit` and `pr`; `refactor` and `audit` now load `interaction-patterns`
- **Command preambles collapsed to one line.** The `current-context` and `interaction-patterns` directives were two copy-pasted paragraphs across 20 files, now a single identical line (~35% shorter). The `.claude/agents/dev-team/` prefix, repeated 72 times, is declared once per file in the 15 files with two or more spawn references; the six single-reference files keep it inline
- **All six implementation commands now share an identical Session close step** — session-summary append with per-agent sub-headings, then commit and PR. Five of the six previously ended at the resolution message, leaving the working tree dirty with no terminus, while two others in the same family defined one. Only `learn.md` had mentioned session-summary at all
- **`commit.md` no longer restates the layered-commit table** it already loads from `conventional-commits`. Rows 8 (Config/CI) and 9 (Docs), which existed only in the command, were appended to the skill so nothing was lost
- **`plan-mode` no longer carries a second copy of the plan format** in box-drawing characters, which the repo's own `output-format` skill forbids. It loads `templates/plan-template.md`

### Changed — CI, validators and governance
- **CI push trigger narrowed to `main` + tags.** Concurrency alone cannot dedupe push-vs-PR because the two events carry different refs, so both runs survived. **Trade-off: a branch with no open PR no longer gets CI on push.** A concurrency group was added alongside
- **New `tag-name` job rejects tags outside `vX.Y.Z`.** Scoped to the tag-push event and reads only the ref just created, so the two existing malformed tags are never evaluated and are left in place
- **`agent-lint.sh` gained skill validators** — skill frontmatter `name` must equal its directory basename (the renderer resolves opencode skills by name while installers symlink by directory, so a divergence is load-bearing across providers; the single violator, `shadcn-ui` vs `shadcn/`, is fixed), skill names must be unique across categories, and the quiz-first check now catches multiple-choice prompts, not only yes/no variants. A skill-description length check (95-char budget) is included as an advisory warning; 21 descriptions currently exceed it
- **`size-limits.sh` now covers `commands/`** (limit 200, matching agents) — previously the only shipped content category with no size discipline
- **README-sync is now structural.** It compared heading counts and total lines, so a faithful translation of wrong data passed green. It now compares the **ordered heading skeleton** plus per-section fence, table-row, link and line counts, and discovers pairs instead of using a hardcoded list. This immediately caught real pre-existing drift: `docs/installation.pt-BR.md` was missing the entire "Windows: symlinks in a committed installation" subsection, now translated and inserted. The gate ships with **no known-drift exemptions**
- **Enforcement is now exactly two wrappers**, blocking and advisory, with the policy stated in-file and a `PROMOTE WHEN` note on each advisory — promotion is a one-word change once the subjects are clean
- **`CODEOWNERS` gains a default catch-all** so no future path lands unowned, plus explicit rules for the five missing skill domains, `helpers/`, `.github/` and the sync-governed doc pairs. The dead `workflows/` rule is removed

### Removed
- **`templates/backlog-template.md`** — no consumer ever referenced the file, and the same-named skill emits a different document shape, so wiring them together would have forced the skill to document a format it never produces

### Documentation
- **`docs/agents.md` / `docs/agents.pt-BR.md`** — the hand-maintained `Model` column was wrong for `technical-writer` (listed Haiku, resolves to sonnet) and `setup-assistant` (listed Sonnet, resolves to opus), and the pt-BR mirror had faithfully propagated both errors. The column is replaced by the agent's actual `tier`, with the provider mapping stated once below the table; the duplicate of `tiers.json` was the drift's root cause
- **`CLAUDE.md` File Structure** — previously omitted `helpers/`, `opencode/`, `user-data/`, `.github/`, `PRIVACY.md` and `CLAUDE-md/` (cross-referenced four times by `CLAUDE.md` itself), documented 5 of 15 scripts and 8 of 11 skill domains. Now complete and verified against the tree, including `skills/legacy/`, `scripts/lib/{installer-fetch,telemetry-guard}.sh`, `scripts/hooks/lib/{touched-paths,update-check}.sh` and `scripts/hooks/stop/tips/`. It also documents the two directories named `helpers` and their opposite packaging fates: root `helpers/` is stripped at install, `scripts/helpers/` ships and runs
- **`CLAUDE.md` hook maps** — Stop and PreToolUse convention sections now list `03b-`, `99b-` and `02b-telemetry.sh`, document the mandatory filename pattern both dispatchers enforce, and record the `DEVTEAM_NO_CHANGES` / `DEVTEAM_TOUCHED_PATHS` contract. The Hook Files Map gains all three shared libraries under `scripts/hooks/lib/`
- **`CLAUDE.md` — new "Canonical Rule Homes" section** listing each cross-cutting rule, the single skill that owns it, and what agents must do instead of restating it
- **`CLAUDE.md` Code Reviewer roles** — said `code-reviewer` delegates to the test specialists; it routes to `backend-reviewer` / `frontend-reviewer` via `skills/shared/review-router/SKILL.md`
- **`CLAUDE.md` Orphan Skill Self-Check Rule** — the `AUTO-FIXED` line no longer describes deletion, and the two distinct `ACTION REQUIRED` classes are documented separately
- **README command tables** — `/devteam:health-check`, `/devteam:adr`, `/devteam:update`, `/devteam:symlinks` and `/devteam:setup` were missing; both READMEs now document all 25. The `/devteam:plan` row was corrected to reflect `product-analyst` as protagonist. The `current-context` exception list was corrected against `grep -L`: it wrongly listed `symlinks` and omitted `health-check`
- **`CLAUDE-md/user-data.md`** — added the `opencode/` strip rule and the four update-check / archive state files under `user-data/`
- **`CLAUDE-md/notifications.md`** — sub-script table reconciled with the real `scripts/hooks/stop/` contents; the tip section now describes the locale data files rather than inline strings
- **`docs/providers.md`** — documents the skill `name` == directory invariant as a cross-provider requirement, corrects the CI job name (`provider-contracts`, not `provider-matrix`), and corrects the packaging note: `strip-tarball.sh` keeps the render engine and provider installers in a Claude install so providers can be added offline, and removes only `opencode/`, `helpers/`, `.claude/`, `.github/`, `.gitignore` and `scripts/install.sh`

### Changed — slim Claude install + on-demand provider bootstrapping
- **Slim Claude installer** — `scripts/install.sh` no longer bundles the cross-CLI plumbing into the client's `.dev-team-agents/`. The following files are stripped from the extracted tarball before install: `scripts/install-opencode.sh`, `scripts/install-codex.sh`, `scripts/render-provider.sh`, `scripts/lib/render_provider.py`, `scripts/lib/{tiers,tool-map,command-map,commands}.json`, and the `opencode/` directory. The default Claude-only client footprint drops by the size of those ~7 files. Users who want opencode or Codex CLI support bootstrap it on demand (see below)
  > **Superseded before release.** `scripts/lib/strip-tarball.sh` now removes only `opencode/` from that list — the render engine, `scripts/lib/*.json` and both provider installers are kept in a Claude install so providers can be added offline. `install-provider.sh` remains the curl-pipe entry point for users starting from scratch.
- **New `scripts/lib/strip-tarball.sh`** — single source of truth for the slim strip rules. Sourced by `install.sh` (during tarball install) and by `.github/scripts/ci/slim-bootstrap.sh` (CI contract test), eliminating duplication. Add or remove a strip entry in one place; CI catches the regression automatically

### Added — multi-provider CI contract net
- **Per-provider contract tests** — new job `provider-contracts` in `.github/workflows/ci.yml` runs across `claude | opencode | codex` with five sequential checks per provider: render → attendance (counts derived from canonical source, never hardcoded) → schema/cross-ref contract → fixture install → fixture validation. The contract checker (`.github/scripts/ci/provider/_contract.py`) enforces: every tier has a column for every provider; every command in `commands.json` has a valid `agent` ref pointing at an existing source agent; opencode agents have frontmatter matching the schema (`mode ∈ {subagent, primary, all}`, `model` carries a provider prefix, `permission` keys are from the allowed set); opencode command snippet entries have all four required keys (`description`, `agent`, `model`, `template`); codex agent TOML parses and carries `name/description/model/developer_instructions` without provider prefix on model and valid `model_reasoning_effort` if present; codex prompts carry a `<!-- description: ... -->` header and follow the `devteam-<name>.md` naming. Violations exit non-zero with a one-line diagnostic
- **`slim-bootstrap` CI job** — new dedicated job verifies (1) a `git archive HEAD | tar -x` extraction + `apply_strip` produces the slim Claude shape (cross-CLI plumbing absent, Claude runtime essentials present — both lists asserted), (2) `install-provider.sh opencode --source` bootstraps `.opencode/` correctly into a slim-claude fixture (22 commands merged into `opencode.json`, plugin copied, skills symlinked, 17 agents), (3) `install-provider.sh codex --source` does the same for `.codex/` (17 agents + 22 prompts + 4 managed hooks + skills)
- **CI scripts externalized** — `.github/workflows/ci.yml` now invokes helper scripts under `.github/scripts/ci/` instead of inlining logic. New layout: `.github/scripts/ci/01-lint.sh`, `02-readme-sync.sh`, `slim-bootstrap.sh`, and `provider/{10-render,20-attendance,30-contract,40-install-fixture,50-validate-installed}.sh` + `_contract.py`. Pipeline is 3 jobs (`lint`, `provider-contracts` ×3, `slim-bootstrap`) with each step a single `bash .github/scripts/ci/...` invocation
- **Negative-test rehearsal** — the contract checker has been locally verified to catch: missing tier column for a provider, dangling `agent` ref in `commands.json`, malformed rendered opencode frontmatter (unknown `permission` key, missing `mode`, etc.). Each prints one diagnostic line and fails the build
- **New `scripts/install-provider.sh`** — curl-pipeable bootstrap that downloads a tarball of the requested version (`main` by default, or `--version vX.Y.Z`) and runs `install-opencode.sh` / `install-codex.sh` from a temp source dir with `--source`. It accepts `--source <path>` for working from a local clone without network. Usage: `bash <(curl -sSL .../install-provider.sh) opencode` or `... codex`
- **install-opencode.sh / install-codex.sh** — added a defensive check that exits with a clear error and bootstrap guidance when invoked from a source dir that lacks the render engine (`scripts/render-provider.sh` or `lib/{render_provider.py,tiers.json,…}` not present). This case happens when a slim Claude install is mistakenly used as the source; the message points the user at the `install-provider.sh` curl-pipe
- **README.md and README.pt-BR.md** — new "How It Works — Single Source, Multi-CLI" section right after "What This Is" with a textual architecture diagram showing the canonical source → render engine → per-provider output flow, and the slim Claude install alongside it. The "Other providers" section is rewritten to use the new `install-provider.sh` curl-pipe as the entry point (instead of pointing at `install-opencode.sh` / `install-codex.sh` inside the framework install, which no longer ships by default)
- **docs/providers.md** — added a note at the end of the "Adding a new provider" section explaining why the install scripts are stripped from slim installs and how `install-provider.sh` bootstraps them on demand

### Removed
- **`workflows/` directory and concept** — the 5 scope-specific workflow files (`design.md`, `fullstack.md`, `mobile.md`, `refactor.md`, `review.md`) and the 5 `/devteam:workflow-*` loader commands are gone. Each scope is now reached directly through its `/devteam:<scope>` command (`/devteam:design`, `/devteam:fullstack`, `/devteam:mobile`, `/devteam:refactor`, `/devteam:review`), which already delegated to the right agent. The `skills/shared/workflow-detection/SKILL.md` skill was removed. `agents/software-architect.md` and `commands/architect.md` no longer reference a separate workflow file. `helpers/orphan-skill-scan.sh` and `helpers/orphan-template-scan.sh` no longer scan a `workflows/` directory. `scripts/install.sh` `KEEP_ROOT` no longer distributes a `workflows/` directory. The 5 `workflow-*` entries were removed from `scripts/lib/commands.json`. CLAUDE.md, both READMEs, `docs/providers.md`, `CONTRIBUTING.md`, and `.github` templates were updated to drop framework-workflow references (`.github/workflows/` and `skills/shared/git-workflow/` are unrelated and kept)

### Added — multi-provider port (single source of truth)
- **Provider-agnostic render engine** — `scripts/render-provider.sh` (+ python engine `scripts/lib/render_provider.py`) renders the canonical `agents/` + `commands/` into the frontmatter shape expected by Claude Code, opencode, or Codex CLI. Agent bodies stay unchanged; a short "Tool conventions" preamble per provider explains how Claude Code tool names map to that provider's native tools. Fails fast on any unknown tier or missing `tier:` key
- **Per-agent `tier:` frontmatter key** — every `agents/*.md` now declares one of `reasoning | backend-exec | frontend | repetitive`. `helpers/agent-lint.sh` validates this key
- **Canonical tier → provider model id map** — `scripts/lib/tiers.json` carries the full model id per tier per provider (`claude`, `opencode`, `codex`). Adding a new provider is one new column, no edits to any agent or skill
- **Per-provider metadata** — `scripts/lib/tool-map.json` (Claude tool names → provider equivalents, used to generate the body's "Tool conventions" preamble) and `scripts/lib/command-map.json` (per-provider output form for slash commands)
- **Per-command metadata** — `scripts/lib/commands.json` declares each `commands/<name>.md`'s tier + lead agent + description, removing any need to add frontmatter to source command bodies
- **`scripts/install-opencode.sh`** — installs dev-team-agents into a project's `.opencode/` (renders 17 agents with opencode-shaped frontmatter, symlinks `skills/`, copies the plugin at `opencode/plugin/dev-team-agents.ts`, deep-merges 27 `devteam:<name>` command keys into `.opencode/opencode.json`)
- **`scripts/install-codex.sh`** — installs dev-team-agents into a project's `.codex/` (renders 17 agents as `.codex/agents/<name>.toml`, renders 27 prompts as `.codex/prompts/devteam-<name>.md` → `/prompts:devteam-<name>`, symlinks `skills/`, writes 4 managed hooks to `.codex/hooks.json` wiring `SessionStart | PreToolUse | PreCompact | Stop` to the existing bash dispatchers)
- **opencode plugin** — `opencode/plugin/dev-team-agents.ts` binds opencode's `event`, `tool.execute.before`, and `experimental.session.compacting` hooks to the same `scripts/hooks/*.sh` that Claude Code uses. Hook behavior stays single-source; only the binding event adapts
- **CI matrix job** — `.github/workflows/ci.yml` runs `provider-matrix` across `claude | opencode | codex`, asserting each emits 17 agents + 27 commands and installs cleanly into a fixture project
- **`docs/providers.md`** — canonical reference for the provider port: tier map, install commands per provider, the `/devteam:plan` UX across providers, how to add a new provider (single column in `tiers.json` + a row in `tool-map.json` + a row in `command-map.json` + one install-$provider.sh shell)
- **README updates** — new "Other providers (opencode, Codex)" section in both `README.md` and `README.pt-BR.md`; CLAUDE.md gains a "Multi-provider port" reference section

### Changed
- **Per-agent model id is now derived from `tier:` + `tiers.json`** — `model:` in `agents/*.md` is kept as the Claude fallback; non-Claude installations ignore it and resolve model via `tiers.json[tier][provider]`
- **Codex slash-command divergence** — Codex CLI's custom-prompt namespace is hardcoded as `/prompts:<name>`, so dev-team-agents commands are exposed as `/prompts:devteam-<name>` in Codex (e.g., `/prompts:devteam-plan`). Claude Code and opencode both preserve the canonical `/devteam:<name>` UX. The divergence is documented in `docs/providers.md`

### Fixed — silent bugs detected by post-SHIP audit
- **codex hooks.json shape (CRITICAL).** The `.codex/hooks.json` file previously emitted an array under `"hooks"` (e.g. `{"hooks": [{"event": "Stop", ...}]}`) but the Codex spec requires an object keyed by event name (`{"hooks": {"Stop": [...]}}`). Each hook `command` field was emitted as an array (`["bash", "../a.sh"]`) but the spec requires a string (`"bash ../a.sh"`). Both bugs caused all 4 lifecycle dispatchers to be silently ignored by Codex. Fixed.
- **`ensure-claude-framework.sh` — hook scripts not materialised in opencode/codex-only setups (CRITICAL).** Both `install-opencode.sh` and `install-codex.sh` now source `scripts/lib/ensure-claude-framework.sh` which copies the Claude-runtime subset (`scripts/hooks/`, `scripts/lib/`, `scripts/helpers/`, `agents/`, `commands/`, `skills/`, `templates/`) to `.dev-team-agents/` in the target project. This is done IDEMPOTentently (only if the hooks dir is absent). Without this, the opencode plugin's `${directory}/.dev-team-agents/scripts/hooks/...` paths and codex hooks.json's `.dev-team-agents/scripts/hooks/...` commands would reference non-existent files, making all lifecycle hooks silently non-functional. Previous codex installer created a dangling symlink to the bootstrap temp dir (deleted after curl-pipe cleanup). Fixed.
- **opencode agent `task` permission always set.** Every opencode agent now gets `permission: { task: "allow" }` unconditionally, regardless of whether the source agent's Claude `tools:` line listed `Task`. Per the framework's design, any agent may delegate via subagent. Without this, reviewers and other read-only agents would be prompted before each `task` call.
- **opencode `options.effort` removed (no-op).** The `options.effort: high|default|low` field previously emitted in every opencode agent's frontmatter is removed. Opencode's schema has no `effort` field — unknown frontmatter is silently routed into an untyped `options` object with zero effect. Documented in `docs/providers.md` Known Limitations.
- **Renderer preamble extended (skill-loading + subagent-spawn idioms).** The per-provider "Tool conventions" block that opens every rendered agent body now covers two new idiom classes: (a) how to interpret `Load skills/<category>/<name>/SKILL.md` (opencode → `skill({ name: '<name>' })`, codex → `Read .dev-team-agents/skills/<category>/<name>/SKILL.md`), and (b) how to interpret `spawn the agent at .claude/agents/dev-team/<X>.md` (opencode → `task({ name: '<X>' })`, codex → `spawn_agent({ agent_type: '<X>' })`). Source in `scripts/lib/tool-map.json`.
- **Contract tests tightened.** New shared contract validators: `check_tool_map_idiom_notes` (each non-claude provider's tool-map entry must carry `idiom_notes` — catches forgotten preamble additions when adding a provider column), `check_slug_uniqueness_in_tool_map` (no duplicate `from` keys), `check_installer_references` (`install-opencode.sh` / `install-codex.sh` must source `ensure-claude-framework.sh`). The codex `check_codex_hooks_json_shape` validator now enforces event-keyed object structure, `command` is string, and each command path resolves on disk. `50-validate-installed.sh` now asserts `.dev-team-agents/scripts/hooks/stop.sh`, `pre-tool-use.sh`, `session-start.sh`, `pre-compact.sh` exist on disk after both opencode and codex installs. `slim-bootstrap.sh` asserts hooks are materialised after both bootstrap steps.
- **`ensure-claude-framework.sh`** — new helper `scripts/lib/ensure-claude-framework.sh` containing the `ensure_claude_framework()` bash function. Sourced by both `install-opencode.sh` and `install-codex.sh`. Copies the runtime subset to `.dev-team-agents/` idempotentently, so that hook scripts are always project-local and survive bootstrap temp-dir cleanup.
- **Per-provider install docs.** New `docs/install-claude.md`, `docs/install-opencode.md`, `docs/install-codex.md` — each a focused step-by-step reference with troubleshooting. README "How to Install" collapsed to a table of one-line curl commands pointing at each doc.
- **`docs/providers.md` Known Limitations section.** Covers opencode effort no-op, per-provider skill-loading idiom differences, and codex UX divergence.

## [1.11.0] - 2026-07-24

### Added
- **Push & GitHub Actions monitoring** — new `skills/shared/github-actions/SKILL.md`. When the user explicitly asks to push and `gh` is configured, agents watch the triggered Actions run and, on failure, run a capped diagnose→fix→re-push loop (max 3 attempts) with a one-line summary each cycle. Wired into `/devteam:pr` and a new **Push & CI Monitoring Rule** in `CLAUDE.md`
- **README agent list** — both READMEs (EN/pt-BR) now list all 17 agents grouped by role with a one-line summary each
- **Mandatory post-implementation handoff** — `/devteam:backend`, `/devteam:frontend`, `/devteam:mobile`, and `/devteam:fullstack` now always hand off to `code-reviewer` + `qa-specialist` after implementation, presenting a single consolidated block of critical findings
- **`qa_browser` preference** — `qa-specialist` prefers the in-app Claude browser for browser testing; in the CLI it asks which browser to use (quiz) and can save the choice as the `qa_browser` default in `preferences.json`

### Changed
- **`/devteam:plan` reworked** — `product-analyst` is now the protagonist and produces a **business-only** requirements document ready to become sprints; `software-architect` joins only on explicit technical request. The `product-analyst` agent gained a fixed interrogation methodology (7 lenses), an anti-overengineering rule, and a 3-category finding model
- **Sprints reorganized** — sprint files now live under `docs/backlog/sprints/` as `sprint-<n>.md`, with a `sprints.md` status index (Planned → In progress → Done) kept current as sprints finalize
- **Test creation is now gated** — `/devteam:backend|frontend|mobile|fullstack|fix|refactor` create tests only when the project sets `TESTS_REQUIRED=yes` (absent key defaults to running tests); when `TESTS_REQUIRED=no` the test phase is skipped entirely
- **`/devteam:review` with no arguments** now asks a dynamic quiz — current local branch / another local branch / a PR link (GitHub, GitLab, Bitbucket, …) / other — and acts on the chosen target
- **Sprints designed for parallel execution** — `product-analyst` now decomposes scope for maximum parallelism and fills a **Parallel Execution Plan** (waves of mutually independent tasks). The `backlog-template` sprint file gained per-task `Wave` + `Worktree branch` fields and a waves table. Isolation model is explicit: worktree-per-task always; isolated Docker stack per worktree **only when the project uses Docker** — otherwise parallelism is by worktree alone

### Removed
- **Lifecycle workflow commands** — `/devteam:workflow-new`, `/devteam:workflow-maintenance`, `/devteam:workflow-bugfix`, `/devteam:workflow-inherited`, and `/devteam:workflow-security-patch`, plus their `workflows/*.md` files. These lifecycle concerns are now encapsulated in the agents (`software-architect` built-in behavior + the direct commands). Scope-specific workflows (design, fullstack, mobile, refactor, review) are retained

---

## [1.10.0] — 2026-07-21

### Added
- Worktree preferences in `preferences.json` — four keys (`worktree_active`, `worktree_base_branch`, `worktree_path`, `worktree_docker_isolate`) let coding agents default to a git worktree per task without asking. `scripts/lib/preferences-defaults.json` is the new canonical default schema, read by both `install.sh` and the session-start health check
- Health-check backfill — `session-start.sh` fills any missing `preferences.json` key from the canonical schema on every session (idempotent, preserves existing user values), self-healing installs that predate a newly added key
- Docker isolation per worktree — `skills/shared/worktree/references/docker-isolation.md` describes spinning up an isolated `docker compose -p <project>-wt-<ctx>-<title>` stack (namespaced containers/volumes/networks, host ports not published, teardown scoped to the isolated project only)
- `/devteam:learn` now declares a commit manifest in its plan (Step 3) and auto-commits the knowledge-base updates after execution (conventional commits, local only, no push). New `--no-commit` argument opts out

### Changed
- Worktree decision is now a three-level cascade — `.dev-team-agents/.worktree-session` (per-session override) → `worktree_active` in `preferences.json` (default) → ask once (legacy installs). Propagated to the 8 coding agents, `software-architect` worktree detection, and `CLAUDE.md`
- Worktree base branch is auto-detected (`origin/HEAD` → current branch) instead of assuming `beta` or `master`; `worktree_path` makes the worktree location configurable (default `.dev-team-agents/worktrees`)
- Worktree finalization enforces rebase-onto-base → resolve → merge → teardown of the worktree and its isolated Docker stack only, never the main infrastructure
- The coding agents' worktree prompt now uses `AskUserQuestion` (quiz-first) instead of a plain `(yes / no)` text prompt
- Synced the preferences schema across the `user-preferences` skill, `setup-assistant`, installation guides (EN/pt-BR), and both READMEs

---

## [1.9.3] — 2026-07-19

### Fixed
- `/devteam:update` now repairs a broken installation instead of falsely reporting "Up to date". When `.dev-team-agents/user-data/.installed-version` is missing or empty (`Installed: unknown`), the version check exited silently and the command reported the install as current; it now force-reinstalls the latest release to rewrite the metadata and clears the cached ETag so a stale `304` cannot mask the mismatch
- `01-check-updates.sh` no longer treats an install that is behind the still-latest release as up to date. A `304 Not Modified` short-circuited before comparing the local version against the latest release, silencing the "update available" notification after its first fire. The resolved version is now cached alongside the ETag (`.last-releases-version`) and reused on `304` to complete the comparison

---

## [1.9.2] — 2026-07-17

### Added
- `/devteam:symlinks` command — detects the OS, runs `fix-symlinks.sh` to repair materialized `.claude/` links, and walks the user through the OS fix (quiz-first) when native symlinks are blocked

---

## [1.9.1] — 2026-07-17

### Fixed
- `scripts/fix-symlinks.sh` now removes the legacy `stop/02-graphify-refresh.sh` sub-script during an in-place repair. On stale Windows installs the old sub-script called a `graphify-refresh.sh` that exited non-zero when graphify was absent, looping the Stop hook; a full update already drops it via the install-dir replace, but a symlink-only repair did not

---

## [1.9.0] — 2026-07-16

### Added
- `scripts/fix-symlinks.sh` — repairs `.claude/` links materialized as plain files instead of symlinks (Windows without Developer Mode / `core.symlinks`); auto-fixes when the OS allows and otherwise prints three remediation options. Detected automatically at session start (`[DEVTEAM:SYMLINK_BROKEN]`) and verified at install time; health-check Category 1 now distinguishes OK / MATERIALIZED / MISSING

### Changed
- Documented the Windows materialized-symlink repair flow across README (EN/pt-BR) and the installation guide

---

## [1.8.2] — 2026-06-29

### Fixed
- `graphify-refresh.sh` exits `0` on skip instead of non-zero, preventing a Stop-hook loop when graphify is not installed

---

## [1.8.1] — 2026-06-28

### Fixed
- Removed an unused `_notify` function in `session-start.sh`

---

## [1.8.0] — 2026-06-28

### Added
- `/devteam:learn` command for consolidating session decisions, patterns, and discoveries into docs, wiki, and ADRs
- Post-execution review step in `software-architect` and auto-learn hand-off in `/devteam:commit`

---

## [1.7.4] — 2026-06-28

### Fixed
- Suppress WSL `BASH_ENV` bashrc noise on hook invocation (follow-up to 1.7.3)

---

## [1.7.3] — 2026-06-24

### Fixed
- Suppress WSL `BASH_ENV` bashrc noise on hook invocation

---

## [1.7.2] — 2026-06-24

### Fixed
- Enforce LF line endings in the target project `.gitattributes` on install

---

## [1.7.1] — 2026-06-24

### Added
- First-time setup guard with quiz in `project-context`
- `SessionStart` emits a structured signal when `preferences.json` is missing
- Installer injects a pre-compact auto-summary rule into the project `CLAUDE.md`; health-check detects and auto-fixes it when missing

### Changed
- Added `.gitattributes` to enforce LF line endings in the repository

---

## [1.7.0] — 2026-05-18

### Added
- Anonymous usage telemetry via PostHog, wired into `install.sh` and `update.sh`; `PRIVACY.md` documents what is collected and how to opt out

---

## [1.6.7] — 2026-05-18

### Fixed
- Prune stale skill symlinks during update
- Resolve shellcheck warnings in hook and lint scripts

---

## [1.6.6] — 2026-05-18

### Fixed
- Anchor the fingerprint uniqueness check to registration lines only

---

## [1.6.5] — 2026-05-18

Large refactor/performance release focused on reducing per-session and per-spawn context-budget usage.

### Added
- `stack-detection` skill wired to agents; iOS and Android platform skills
- `interaction-patterns` skill (quiz-first rule) and `push-notifications` skill
- `validate-commit-msg.sh` gate in `/devteam:commit`; `workflow-mobile` and `workflow-design` shortcut commands
- Fingerprint uniqueness check, orphan-template scanner, and additional CI scans

### Changed
- Fragmented `CLAUDE.md` into `CLAUDE-md/` sub-files; extracted large inline sections across agents and skills (project-context, mobile, integrations, frontend, ui-ux) to `references/` subdirectories
- Moved dev-only tools to `helpers/`; moved the context-cache path to `user-data/`; canonicalized tools order; added the Hook Files Map
- Made agents stack-agnostic — removed Docker-first and stack-prescriptive language

### Fixed
- Restored the worktree session-file gate across coding agents; hardened `rollback.sh` and `pre-compact.sh` guards; corrected the CI fast-path comparison and fingerprint regex

---

## [1.6.4] — 2026-05-13

### Fixed
- README sync check compares section counts instead of header text

---

## [1.6.3] — 2026-05-13

### Added
- `release-prep` skill; ADR, backlog-item, and runbook templates
- Context cache, discovery lockfile, and graphify skip conditions; PreCompact hook and rollback script
- `conventional-commits` `validate.sh`; size-limits check; mobile and design workflows

### Changed
- Reduced file sizes across architect, database, setup, and reviewer agents; extracted large devops and docs skills to `references/`
- Extended orphan-skill-scan to cover `commands/` and `workflows/`; added Portuguese translations for agents and installation guides

### Fixed
- Implemented the worktree session-file gate in all coding agents; removed non-canonical frontmatter keys from design skills

---

## [1.6.2] — 2026-05-12

### Changed
- Restructured README for first-time readability; extracted the agent reference and installation guide to `docs/`

---

## [1.6.1] — 2026-05-12

### Added
- `/devteam:mobile` and `/devteam:adr` commands
- Plan-gate enforcement across all implementation commands; context estimation via transcript tokens with a preferences fallback

### Changed
- Reduced the git-log window from `-20` to `-10` across 10 agents; expanded the preferences schema (`transcript_multiplier`, `model_max_tokens`)

### Fixed
- Disabled Claude co-authoring in git artifacts and added a Jira REST API fallback; reclassified plans as conversation items using the user's preferred language; added a daily gate to the notifier tip-of-session; fixed the graphify-setup skill path in `setup-assistant`

---

## [1.6.0] — 2026-05-11

### Added
- `mobile-developer` agent with React Native, Expo, and Flutter skills
- Material Design 3 and iOS HIG mobile design skills

---

## [1.5.5] — 2026-05-11

### Fixed
- `check-updates.sh` no longer exits with code 1 when the GitHub API returns an empty response

---

## [1.5.4] — 2026-05-11

### Fixed
- Exclude repo-only files from the distributed package
- Remove the rollback feature and `.previous` directory from the installer

---

## [1.5.3] — 2026-05-11

### Changed
- Trimmed all skill descriptions to reduce context-budget usage

---

## [1.5.2] — 2026-05-11

### Fixed
- Jira MCP setup checks deferred tools via ToolSearch before showing setup instructions

---

## [1.5.1] — 2026-05-11

### Fixed
- Skip the Graphify prompt when already configured; strip `agent-lint.sh` from the distributed package

---

## [1.5.0] — 2026-05-11

### Added
- User preferences system (`preferences.json`) with a language prompt on install; notification system and the `04-notifier.sh` stop sub-script
- `user-preferences` and `notifier` shared skills; per-engine database skills for all 7 engines
- Architecture skills (event-driven, rate-limiting, api-versioning); `diataxis-framework`; fullstack workflow; recovery paths in all workflows
- Community health files and GitHub templates; rollback support in the installer/update script; session-start staleness hook

### Changed
- Migrated command context detection to the `current-context` skill and `spawn-classifier`; rewrote `/devteam:refactor` with test-first coverage and dependency mapping; expanded database-specialist engine detection
- Untracked `session-summary.md` and added it to `.gitignore`

### Fixed
- Removed the manual shellcheck `apt-get install` step in CI

---

## [1.4.0] — 2026-05-10

### Added
- MIT `LICENSE` file
- `.github/workflows/ci.yml` — frontmatter validation, orphan scan, shellcheck, README sync check
- `scripts/agent-lint.sh` — validates frontmatter on all `agents/*.md`
- Stop hook sub-scripts: `02-orphan-skill-scan.sh`, `03-agent-lint.sh`
- Orphan skill scan Phase 3: duplicate skill detection

### Changed
- `.claude/settings.json` uses the stop dispatcher (`scripts/hooks/stop.sh`) instead of direct orphan scan
- Fixed 23 real duplicate skill references across 6 agents

---

## [1.3.16] — 2026-05

### Added
- `/devteam:update` command for checking and applying updates
- 13 new skills across security, testing, database, devops, and integrations
- 7 new architecture skills; updated `api-design`
- 7 new shared skills; refactored `comments-policy` (417 → 76 lines)
- `workflows/refactor.md` and `workflows/review.md`
- Jira integration section in 7 agents; `skills/integrations/jira/SKILL.md`

### Changed
- Refactored 4 agents by extracting skills: `db-comparison`, `setup-health-check`, `frontend-patterns`, `ssh-remote-access`
- `/devteam:*` commands namespaced (were `/devteam-*`)
- `session-summary.md` moved to `user-data/` directory

---

## [1.3.0] — 2026-05

### Added
- Comprehensive `/devteam:*` slash commands (plan, backend, frontend, fullstack, fix, refactor, architect, review, qa, security, dba, devops, tester, docs, pr, design, commit, update)
- Graphify integration for visual codebase navigation
- Wiki knowledge base system (`docs/wiki/`)
- Contradiction Guard in `project-context` skill

### Changed
- Agents enforce human-only authorship in git artifacts (no Claude attribution)
- `setup-assistant` adds audit step, devops/tests doc dirs

---

## [1.2.0] — 2026-04

### Added
- `skills/shared/` modular skill system
- `agent-creator` and `skill-creator` skills
- Release preparation skill (`release-prep`)
- `session-summary.md` per-session notes (multi-agent append pattern)

### Changed
- Skills extracted from agents to reduce inline duplication
- Auto-routing skill for agent delegation

---

## [1.1.0] — 2026-04

### Added
- Core agent roster: `backend-developer`, `frontend-developer`, `database-specialist`, `devops-specialist`, `qa-specialist`, `security-specialist`, `software-architect`, `product-analyst`, `technical-writer`, `code-reviewer`, `setup-assistant`
- Worktree isolation pattern for coding agents
- `skills/shared/project-context/SKILL.md` — foundational context loader
- `skills/shared/conventional-commits/SKILL.md`
- Pre-tool-use update check hook (`01-check-updates.sh`)
- Stop hook for session summary (`01-session-summary.sh`)
- Orphan skill scan (`scripts/orphan-skill-scan.sh`)

---

## [1.0.0] — 2026-03

### Added
- Initial release: installer (`scripts/install.sh`), updater (`scripts/update.sh`)
- 5 core workflows: `new-project`, `bug-fix`, `maintenance`, `inherited-project`, `security-patch`
- `templates/plan-template.md`
- `CLAUDE.md` authoring standards

[Unreleased]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.3...HEAD
[1.9.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.2...v1.9.3
[1.9.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.1...v1.9.2
[1.9.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.0...v1.9.1
[1.9.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.2...v1.9.0
[1.8.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.4...v1.8.0
[1.7.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.3...v1.7.4
[1.7.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.2...v1.7.3
[1.7.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.7...v1.7.0
[1.6.7]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.6...v1.6.7
[1.6.6]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.5...v1.6.6
[1.6.5]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.4...v1.6.5
[1.6.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.3...v1.6.4
[1.6.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.5...v1.6.0
[1.5.5]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.4...v1.5.5
[1.5.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.3...v1.5.4
[1.5.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.16...v1.4.0
[1.3.16]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.0...v1.3.16
[1.3.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Dev-Toolbelt/dev-team-agents/releases/tag/v1.0.0
