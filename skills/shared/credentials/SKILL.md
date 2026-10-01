---
name: credentials
description: Remote environment credentials (staging, production) — access and read-only enforcement.
---

# Credentials — Remote Environment Access

Use this skill whenever a task requires accessing a remote environment (staging, production, QA, etc.).

## File Location

`.dev-team-agents/credentials.local.json` in the **main checkout** — every linked git worktree shares that one file (see § 1 for resolving it).

This file is **gitignored** and **never committed**. It is created only via an explicit action: `devteam cred local init` or the app's Credentials tab. If the file does not exist, tell the user to create it via one of those methods — never create it yourself.

## Structure

`devteam cred local init` writes the canonical template. The file follows a category → environment → credential pattern: `devops` (per environment: `ssh`, `database[]`, `docker`) and `app` (per environment: `appUrl`, `username`, `password`); users may add more. It also carries two flat top-level settings unrelated to credentials — `work_feedback_active` and `work_feedback_interval_minutes`, consumed by `skills/shared/work-feedback/SKILL.md`.

### Key `agents`

Each category has an `agents` array listing which agents typically need that category's credentials. This is a suggestion — any agent may use any category if the task requires it.

### Extensibility

Users may add:
- **New environments** (e.g. `"qa"`, `"review"`, `"sandbox"`) under any category
- **New categories** at the top level (e.g. `"monitoring"`, `"ci"`, `"cloud"`)
- **New credential fields** within any environment

Treat any unknown key as valid. Never reject or remove user-added structure.

## How to Use

### 1. Locate the File

Ask the CLI for the path — it resolves the main checkout (worktrees, monorepo subprojects) and prints no secret value:

```bash
CRED_FILE=$(devteam cred local show --json 2>/dev/null \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["path"])' 2>/dev/null)
[ -n "$CRED_FILE" ] || CRED_FILE=".dev-team-agents/credentials.local.json"
[ -f "$CRED_FILE" ] || echo "MISSING"
```

If the file does not exist, tell the user to create it via `devteam cred local init` or the app's Credentials tab.

### 2. Read the JSON

```python
import json
with open(CRED_FILE) as f:  # the path resolved in step 1
    creds = json.load(f)
```

### 3. Find the Relevant Credentials

- Identify the **category** that matches your role or the task scope (e.g., `"devops"` for infrastructure, `"app"` for application access)
- Identify the **environment** (e.g., `"staging"`, `"production"`)
- Check if the required fields are filled in

### 4. Handle Empty Fields

If a required field is empty (`""`, `{}`, `null`, or missing):

> Ask the user: "The field `<field>` under `<category>` → `<environment>` is empty. How should I access this environment?"

Use `AskUserQuestion` with relevant options (SSH key path, password, token, etc.) or let the user type free-form input.

### 5. Read-Only Enforcement

**By default, you may only READ from remote environments.** This includes:
- Browsing HTTP endpoints (GET requests via browser or curl)
- Running read-only CLI commands (`ssh user@host ls`, `docker ps`, `kubectl get pods`, database `SELECT`)
- Inspecting logs, configs, or state

**You MUST ask for explicit user permission before:**
- Writing or modifying any file on the remote environment
- Executing commands that change state (`rm`, `mv`, `sed -i`, `kubectl apply`, database `INSERT/UPDATE/DELETE`)
- Restarting services or deploying code
- Running destructive operations

When you need write/execute access, pause and ask:

> "I need to `<action>` on `<environment>`. This is not read-only. Do you authorize this operation?"

Proceed only after the user explicitly confirms.

### 6. Protocol-Specific Access

| Protocol | Read-only patterns |
|----------|--------------------|
| HTTP/HTTPS | `curl -s <url>`, browser GET, API calls without side effects |
| SSH | `ssh <user>@<host> <command>` with read-only commands |
| Docker | `docker exec <container> <read-command>`, `docker logs`, `docker ps` |
| Database | `SELECT` queries only (via `psql`, `mysql`, `sqlite3`, etc.) |
| Kubernetes | `kubectl get`, `kubectl describe`, `kubectl logs` |

### 7. No Matching Environment

If the target environment is not in the file, ask the user for connection details and suggest they add it to `credentials.local.json` for future use.
