# Dry-running an untrusted project's commands is not safe

**Origin:** Local environment up/down commands and the Visual Check Gate | 2026-10-19
**Tags:** make -n, dry run, Makefile, npm scripts, pre/post hooks, compose project name, working_dir label, docker inspect, launch.json, preview_start

> Never use `make -n` or `npm run --dry-run` to show what a checkout will execute: both can run code, and the script line alone hides hooks and recipe prefixes.

---

## What it is

Commands a repository ships (Makefile targets, npm scripts, Compose services, `.claude/launch.json`) run with the user's privileges. Before the user confirms a run, the agent must show what will actually execute. The canonical rule lives in `skills/devops/local-environment/SKILL.md` (§ Discovery Order, § Compose Project Identity, § Pre-flight); this entry records only the non-obvious traps.

## Gotchas

- **`make -n` is not a dry run on an untrusted Makefile.** GNU make still expands `$(shell …)` while parsing, and it still runs recipe lines prefixed with `+` or that invoke `$(MAKE)`. Safe alternative: read the target's recipe and its prerequisite targets from the file itself, including any `include` files.
- **npm hooks run without being named.** `npm run <name>` also runs `pre<name>` and `post<name>` scripts. Show all three script entries from `package.json`, not only the one the user asked for.
- **Two checkouts with the same folder name share a Compose project.** The default project name is the folder basename, so `~/a/app` and `~/b/app` both become project `app`. `up` in one recreates the other's containers and reuses its named volumes; `down` stops the other's stack. Safe alternative: check ownership with `docker inspect --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' <container>`, and pass `-p <project>` and every `-f <file>` explicitly on each command.
- **Never run a bare `docker inspect` for ownership.** It dumps `Config.Env`, which holds secrets. Always use `--format` with a single label.
- **A repo-shipped `.claude/launch.json` runs as written.** `preview_start` by name executes its `runtimeExecutable`, `runtimeArgs` and `env` (for example `NODE_OPTIONS=--require`), which can differ from the command the user confirmed. Safe alternative: show the exact entry and get confirmation before starting it.

## References

- `skills/devops/local-environment/SKILL.md` — canonical rule for `/devteam:up` and `/devteam:down`
- `commands/up.md`, `commands/down.md`
