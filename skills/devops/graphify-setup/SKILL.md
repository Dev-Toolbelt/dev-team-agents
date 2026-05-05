---
name: graphify-setup
description: OS-aware Graphify installation and project configuration. Installs graphify and jq autonomously, infers project structure from the codebase to generate .claude/user-data/graphify.json, configures the Stop hook in the project .claude/settings.json, adds graphify-out/.last-run to .gitignore, runs the first build, and injects the Context Navigation section into the project CLAUDE.md. Only prompts the user when a step fails due to permissions or when the configuration cannot be inferred confidently.
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

## Step 2 — Check and Install graphify

```bash
command -v graphify && graphify --version || echo "NOT_FOUND"
```

**If not found**, attempt installation based on the detected OS without asking:

| OS | Try in order |
|----|-------------|
| macOS | `brew install graphify` |
| Linux/WSL | `npm install -g graphify` → fallback `pip install graphify` |

Run the install command directly. If it fails due to a permission error or requires `sudo`, inform the user of the exact command to run and wait for them to confirm it's done before continuing. After install, re-run `command -v graphify` to verify. Do not continue until graphify is confirmed working.

---

## Step 3 — Check and Install jq

```bash
command -v jq && jq --version || echo "NOT_FOUND"
```

**If not found**, attempt installation without asking:

| OS | Command |
|----|---------|
| macOS | `brew install jq` |
| Ubuntu/Debian / WSL | `sudo apt-get install -y jq` |
| Fedora/RHEL | `sudo dnf install -y jq` |

If the install requires elevated privileges and fails, report the command to the user and wait for confirmation before continuing.

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

## Step 5 — Generate .claude/user-data/graphify.json

Create the config file at `.claude/user-data/graphify.json` — this is where `graphify-refresh.sh` reads it from:

```json
{
  "targetPaths": ["<inferred-dir1>", "<inferred-dir2>"],
  "manifestPaths": ["<inferred-manifest1>"]
}
```

Omit `manifestPaths` if no manifest files were found. Do not ask the user to confirm — proceed directly to Step 6.

---

## Step 6 — Configure Stop Hook

Add the graphify-refresh script as a Stop hook so Claude triggers a rebuild automatically after completing each session.

**Target the project-level settings file** — never the global `~/.claude/settings.json`. Read `<project-root>/.claude/settings.json`. If it doesn't exist, create it.

Merge the following under the `hooks.Stop` array — preserve all existing hooks and keys:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/dev-team-agents/scripts/graphify-refresh.sh"
          }
        ]
      }
    ]
  }
}
```

Use the `update-config` skill if available to safely merge settings. Otherwise merge the JSON manually, preserving all existing keys.

---

## Step 7 — Update .gitignore

Add `graphify-out/.last-run` to the project's `.gitignore` (the rest of `graphify-out/` is versioned):

```bash
grep -qxF 'graphify-out/.last-run' .gitignore 2>/dev/null || echo 'graphify-out/.last-run' >> .gitignore
```

---

## Step 8 — Run First Build

```bash
bash .claude/dev-team-agents/scripts/graphify-refresh.sh
```

If the build succeeds, `graphify-out/` will be created at the project root.

If it fails, diagnose the error:

| Symptom | Fix |
|---------|-----|
| `graphify not found` | Complete Step 2 |
| `jq not found` | Complete Step 3 |
| `graphify.json not found` | Complete Step 5 — file must be at `.claude/user-data/graphify.json` |
| Source dir not found | Verify path with user and update `.claude/user-data/graphify.json` |

---

## Step 9 — Inject CLAUDE.md Section

Check if the project `CLAUDE.md` already contains a `## Context Navigation (Graphify)` section. If not, **append** (never replace) the following:

```markdown
## Context Navigation (Graphify)

**3-Layer Query Rule:**
1. Query `graphify-out/graph.json` or `GRAPH_REPORT.md` for structure and relationships
2. Check `.claude/docs/` for decisions and context
3. Read raw source files only when editing or when layers 1–2 lack the answer

**Rebuild:** always use `.claude/dev-team-agents/scripts/graphify-refresh.sh` — never `graphify update .` directly.
Rebuild runs automatically after each Claude session via the Stop hook.
Manual rebuild needed after: new modules/services, structural reorganization, or domain flow changes.
```

---

## Step 10 — Confirm Setup

Report to the user:

```
✅ Graphify is set up for this project.

  Knowledge graph : graphify-out/  (versioned)
  Last-run marker : graphify-out/.last-run  (gitignored)
  Config          : .claude/user-data/graphify.json
  Auto-rebuild    : Stop hook → .claude/dev-team-agents/scripts/graphify-refresh.sh

Rebuilds happen automatically after each Claude session when new files are
added, deleted, or moved inside the tracked directories.
```
