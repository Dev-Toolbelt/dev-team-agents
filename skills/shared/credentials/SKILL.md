---
name: credentials
description: Every secret an agent needs — references, exec, sign-in, read-only remote access.
---

# Credentials — Remote Environment Access

Use this skill whenever a task requires accessing a remote environment (staging, production, QA, etc.) or needs any secret — a password, token, passphrase, TOTP seed or signed-in session.

## File Location

`.dev-team-agents/credentials.local.json` in the **main checkout** — every linked git worktree shares that one file (see § 1 for resolving it).

This file is **gitignored** and **never committed**. It is created only via an explicit action: `devteam cred local init` or the app's Credentials tab. If the file does not exist, tell the user to create it via one of those methods — never create it yourself.

## Structure

The file is **free-form**: the user names, nests and removes groups and fields as they like. Nothing in it is a fixed category, environment or agent mapping — find what you need by key name and context. `devteam cred local init` writes a small example the user is expected to edit or delete.

Two reserved keys may appear in any object; every other key is the user's own:

| Key | Value | Meaning |
|-----|-------|---------|
| `$production` | `true` | This object and everything nested below it is **production** — see § 5 |
| `$secrets` | list of sibling key names | Those keys hold secrets. The app keeps them write-only; never echo, log or paste them |

A secret value may be stored by reference instead of in the file (ADR-0053): the leaf is `{"$ref": "<ref>"}`, sometimes with a `"$backend"` beside it. The value lives in the machine's secret store or in a password manager (`op://…`, `bw://…`), never in the file.

Two flat top-level keys are settings, not credentials: `work_feedback_active` and `work_feedback_interval_minutes`, consumed by `skills/shared/work-feedback/SKILL.md`.

Strip the `$`-prefixed keys before using an object as connection data. Treat any other key as valid; never reject, rename or remove user structure.

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

- Find the group that matches the task by its key names and nesting (e.g. a `staging` group under `api`, a `jira` group with a `token`)
- Work out whether it is production: `$production: true` on it **or on any ancestor**. A group merely *named* `production` without the flag is not marked, so ask when the name and the flag disagree
- Check if the required fields are filled in

### 3a. Secret Values

- A `{"$ref": …}` leaf is never resolved by reading files, the keychain or a vault yourself. When a command needs the value, run it through the CLI, which injects the group's values as `DEVTEAM_<KEY>` environment variables into that one process and audits the read:
  ```bash
  devteam cred local exec /staging/ssh -- sh -c 'SSHPASS="$DEVTEAM_PASSWORD" sshpass -e ssh "$DEVTEAM_USER@$DEVTEAM_HOST" uptime'
  ```
- Never print, echo or log a `DEVTEAM_*` variable, and never pass one as a visible argument when the tool reads it from the environment.
- A group under `$production` also needs `--production`. Ask the user before adding it, naming the command; the approval covers that one command.
- `details.reason: "tracked-file"` means `credentials.local.json` is committed to git, so no reference is resolved. Tell the user; never work around it.
- A plaintext secret you meet (a marked or secret-looking key holding a string) still works outside production, through `exec`; mention once that `devteam cred local secure --apply` or the app's *Secure now* moves it out of the file. Under `$production`, do not use it: ask the user to secure it first.
### 3b. Any Access That Needs a Secret

Every task that needs a password, token, key passphrase, TOTP seed or a signed-in session — in any environment, for any request, not only release QA — reaches it through one of these paths, and only these:

| Need | Path |
|------|------|
| A command using a credentials-file secret (SSH, database client, API call, deploy tool) | `devteam cred local exec <group-pointer> -- <cmd>` — only the scalar fields of that one group are injected; nested objects need their own group |
| A web page behind a login | `devteam qa auth <group-pointer>`, then open the page with the storageState file at the returned `path`. The group needs `username`, `password` (optional `totp_secret`) and a `login` object — `url`, `username_selector`, `password_selector`, `submit_selector`, optional `totp_selector` and `success_url_contains`; without one, `--interactive` lets the user sign in once |
| A connected integration (GitHub, Jira, Cloudflare) | Its own skill: `devteam integration call` where the integration supports it, its MCP tools otherwise. Connecting is the user's action, in their own terminal or the app |
| A token already configured in an MCP server | Use that server's tools; never read its config for the token |
| Local development | The project's own `.env` or environment, read by the program that needs it; never printed |
| A secret not stored anywhere | Ask with `AskUserQuestion` (**I stored it** / **Cancel**) for the user to store it: the app's Credentials tab, or by hand in the file followed by `devteam cred local secure --apply`. Then check `devteam cred local show`: the field must be `set` with a `stored` value other than `invalid`; ask again if not |

Never ask the user to type or paste a secret in the chat, never type one into a page or a prompt, and never read one from the credentials file, the keychain, a vault or an MCP config yourself. `devteam cred get`, `devteam cred local copy-value`, `op read` and `bw get` are the user's commands, not an agent's.

A secret no path can use — an SSH key passphrase (`ssh` does not read it from the environment), a TOTP code outside `qa auth` — means stop and ask the user to unlock it in their own terminal (for SSH, `ssh-add` into their agent). Never fall back to handling the value.

`--production` on `exec` is not write authorization: § 5 still asks before each state-changing action.

### 4. Handle Empty Fields

If a required field is empty (`""`, `{}`, `null`, or missing):

- **Non-secret field** (host, port, username, URL, SSH key path): ask with `AskUserQuestion`, offering the likely values plus Other, and suggest adding the answer to the file.
- **Secret field** (password, token, passphrase, TOTP seed): never ask for the value in the chat; follow the last row of § 3b.

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

**Release QA is the one exception**, in staging and production alike: its single authorization covers exactly the state-changing scenarios it lists (`skills/shared/release-qa/SKILL.md` § Step 3), and nothing outside that list.

**Under `$production`**, the same rule tightens: ask before **every** state-changing action, one action per question, and name it as production in the question. An earlier approval — for another action, for staging, or "for this session" — never carries over.

### 6. Protocol-Specific Access

| Protocol | Read-only patterns |
|----------|--------------------|
| HTTP/HTTPS | `curl -s <url>`, browser GET, API calls without side effects |
| SSH | `ssh <user>@<host> <command>` with read-only commands |
| Docker | `docker exec <container> <read-command>`, `docker logs`, `docker ps` |
| Database | `SELECT` queries only (via `psql`, `mysql`, `sqlite3`, etc.) |
| Kubernetes | `kubectl get`, `kubectl describe`, `kubectl logs` |

### 7. No Matching Environment

If the target environment is not in the file, ask the user for its non-secret connection details and suggest they add it to `credentials.local.json`; its secrets are stored per § 3b, never sent in the chat.
