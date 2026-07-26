---
name: credentials
description: Remote environment credentials — read, use, enforce read-only access to staging/production environments.
---

# Credentials — Remote Environment Access

Use this skill whenever a task requires accessing a remote environment (staging, production, QA, etc.).

## File Location

`.dev-team-agents/user-data/credentials.local.json`

This file is **gitignored** and **never committed**. It is created automatically by `install.sh` and the health check.

## Structure

The file follows a category → environment → credential pattern. Two top-level categories are provided by default; users may add more:

```json
{
  "devops": {
    "agents": ["software-architect", "devops-specialist", "security-specialist"],
    "staging": {
      "ssh": { "user": "", "host": "", "privateKeyPath": "", "path": "" },
      "database": [
        { "type": "", "host": "", "port": "", "database": "", "username": "", "password": "" }
      ]
    },
    "production": {
      "ssh": { "user": "", "host": "", "privateKeyPath": "", "path": "" },
      "docker": {},
      "database": [
        { "type": "", "host": "", "port": "", "database": "", "username": "", "password": "" }
      ]
    }
  },
  "app": {
    "agents": ["software-architect", "backend-developer", "frontend-developer", "code-reviewer", "backend-reviewer", "frontend-reviewer", "qa-specialist", "security-specialist", "backend-test-specialist", "frontend-test-specialist"],
    "staging": { "appUrl": "", "username": "", "password": "" },
    "production": { "appUrl": "", "username": "", "password": "" }
  }
}
```

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

```bash
CRED_FILE=".dev-team-agents/user-data/credentials.local.json"
if [ ! -f "$CRED_FILE" ]; then
  echo "MISSING"
fi
```

If the file does not exist, notify the user and ask them to create it or run a health check.

### 2. Read the JSON

```python
import json
with open(".dev-team-agents/user-data/credentials.local.json") as f:
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
