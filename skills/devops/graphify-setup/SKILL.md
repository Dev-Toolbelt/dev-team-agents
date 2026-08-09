---
name: graphify-setup
description: Graphify — autonomous setup: graphify.json, Stop hook, CLAUDE.md.
---

## Skip Conditions

Do not run this setup if any of the following are true:

- The project contains **no JavaScript, TypeScript, or Python source files** (check: `find . -name "*.js" -o -name "*.ts" -o -name "*.py" | grep -v node_modules | head -1`)
- A valid `graphify.json` already exists and the project structure hasn't changed
- The user explicitly says graphify is not relevant to their stack (pure mobile, database-only, embedded, etc.)

If the project type is ambiguous, ask once: `"Does your project use JavaScript, TypeScript, or Python as its primary language?"` before running Step 1.

---

## Purpose

Set up Graphify for the project autonomously. Claude handles everything — dependency installation, project structure inference, configuration — and only asks the user when it cannot proceed without their input (permission errors, genuinely ambiguous structure).

---

## Step 1 — OS Detection

Run:
```bash
uname -s
```

| Output | OS |
|--------|-----|
| `Darwin` | macOS — follow macOS instructions |
| `Linux` | Linux or WSL — follow Linux instructions |
| `MINGW*` / `MSYS*` / other | Windows — see below |

**Windows handling:**

First, check if WSL is available and active:
```bash
wsl --status 2>/dev/null || echo "WSL_NOT_FOUND"
```

- **WSL active** → run all subsequent steps inside the WSL shell (`wsl bash -c "<command>"`). Follow Linux instructions for all installs.
- **WSL not found or not configured** → stop and inform the user:

  > Windows without WSL is not supported. Please activate WSL first:
  > 👉 https://learn.microsoft.com/en-us/windows/wsl/install
  >
  > Once WSL is set up, re-run this setup and everything will work via Linux instructions.

Do not continue on Windows until WSL is confirmed active.

---

## Step 2 — Check and Install graphify + jq

```bash
command -v graphify && graphify --version || echo "NOT_FOUND"
command -v jq && jq --version || echo "NOT_FOUND"
```

If either is missing, run `/devteam:install graphify jq` and wait for it to finish — that command owns the cross-OS install/verify logic for both (`skills/devops/tool-installers/SKILL.md`). Do not install them directly here; this avoids duplicating install commands in two places. Do not continue past this step until both are confirmed working.

---

## Step 4 — Infer Project Structure

Do not ask the user. Explore the project autonomously to determine `targetPaths` and `manifestPaths`.

**4a — Detect stack via manifest files**

Check which of these exist at the project root:

| File | Stack |
|------|-------|
| `package.json` | Node.js / JavaScript / TypeScript |
| `composer.json` | PHP |
| `requirements.txt` / `pyproject.toml` / `setup.py` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `Gemfile` | Ruby |
| `pom.xml` / `build.gradle` | Java / Kotlin |

**4b — List top-level directories**

```bash
find . -maxdepth 2 -type d ! -path './.git*' ! -path './node_modules*' \
  ! -path './vendor*' ! -path './dist*' ! -path './build*' \
  ! -path './.graphify*' ! -path './.claude*' ! -path './coverage*' \
  ! -path './__pycache__*' ! -path './target*' | sort
```

**4c — Select targetPaths using these heuristics**

| Stack | Likely targetPaths (keep only those that exist) |
|-------|------------------------------------------------|
| Node.js | `src`, `lib`, `app`, `routes`, `components`, `pages`, `services`, `api` |
| PHP (Laravel) | `app`, `routes`, `config`, `database/migrations`, `tests` |
| PHP (other) | `src`, `lib`, `app` |
| Python | `src`, `app`, any directory containing `__init__.py` |
| Go | `cmd`, `internal`, `pkg`, `api` |
| Rust | `src` |
| Ruby | `app`, `lib`, `config` |
| Java/Kotlin | `src/main`, `src/test` |
| Unknown | any directory with source-like names; skip build/output dirs |

Filter to only include paths that actually exist. If after applying heuristics you still cannot determine targetPaths with reasonable confidence (e.g., flat or unconventional layout), ask the user once listing your best guesses for confirmation.

**4d — Select manifestPaths**

Include all manifest files found in Step 4a that exist at the root. Also include lock files if present (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `composer.lock`, `Gemfile.lock`, `poetry.lock`).

---

## Step 5 — Generate .dev-team-agents/user-data/graphify.json

Create the config file at `.dev-team-agents/user-data/graphify.json` — this is where `graphify-refresh.sh` reads it from:

```json
{
  "targetPaths": ["<inferred-dir1>", "<inferred-dir2>"],
  "manifestPaths": ["<inferred-manifest1>"]
}
```

Omit `manifestPaths` if no manifest files were found. Do not ask the user to confirm — proceed directly to Step 6.

---

## Step 6 — Graphify Hook Sub-scripts

The `02-graphify-hint.sh` (PreToolUse) sub-script is **built-in** to the dev-team-agents tarball. No manual creation is needed.

Graph rebuilds are **on-demand, not automatic** — the Stop hook that used to rebuild on every session (`99-graphify-refresh.sh`) is disabled (see `CLAUDE-md/hooks.md` § Disabled Hooks). Refresh the graph manually when needed:

```bash
bash .dev-team-agents/scripts/graphify-refresh.sh
```

Remove any legacy file if present:

```bash
rm -f .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh
```

The Stop dispatcher and PreToolUse dispatcher pick these up automatically — no changes to `settings.json` are needed.

---

## Step 7 — Update .gitignore

Add the following entries to the project's `.gitignore`. Group them under a `# Dev Team Agents` comment so they are easy to identify:

```bash
GITIGNORE_ENTRIES=(
  "# Dev Team Agents"
  ".dev-team-agents/user-data/.graphify-last-run"
  "graphify-out/cache"
  ".dev-team-agents/worktrees"
)

for ENTRY in "${GITIGNORE_ENTRIES[@]}"; do
  grep -qxF "$ENTRY" .gitignore 2>/dev/null || echo "$ENTRY" >> .gitignore
done
```

- `.dev-team-agents/user-data/.graphify-last-run` — build marker, project-specific, not shared
- `graphify-out/cache` — Graphify internal cache, rebuilt automatically
- `.dev-team-agents/worktrees` — worktree isolation directories, local only

---

## Step 8 — Run First Build

```bash
bash .dev-team-agents/scripts/graphify-refresh.sh
```

If the build succeeds, `graphify-out/` will be created at the project root.

If it fails, diagnose the error:

| Symptom | Fix |
|---------|-----|
| `graphify not found` | Complete Step 2 |
| `jq not found` | Complete Step 2 |
| `graphify.json not found` | Complete Step 5 — file must be at `.dev-team-agents/user-data/graphify.json` |
| Source dir not found | Verify path with user and update `.dev-team-agents/user-data/graphify.json` |

---

## Step 9 — Inject CLAUDE.md Section

Check if the project `CLAUDE.md` already contains a `## Context Navigation (Graphify)` section. If not, **append** (never replace) the following:

```markdown
## Context Navigation (Graphify)

**3-Layer Query Rule:**
1. Query `graphify-out/graph.json` or `GRAPH_REPORT.md` for structure and relationships
2. Check `docs/` for decisions and context
3. Read raw source files only when editing or when layers 1–2 lack the answer

**Rebuild:** always use `.dev-team-agents/scripts/graphify-refresh.sh` — never `graphify update .` directly.
Rebuild runs automatically after each Claude session via the Stop hook.
Manual rebuild needed after: new modules/services, structural reorganization, or domain flow changes.
```

---

## Step 10 — Confirm Setup

Report to the user:

```
✅ Graphify is set up for this project.

  Knowledge graph : graphify-out/  (versioned)
  Last-run marker : .dev-team-agents/user-data/.graphify-last-run  (gitignored)
  Config          : .dev-team-agents/user-data/graphify.json
  Auto-rebuild    : Stop hook → .dev-team-agents/scripts/graphify-refresh.sh

Rebuilds happen automatically after each Claude session when new files are
added, deleted, or moved inside the tracked directories.
```
