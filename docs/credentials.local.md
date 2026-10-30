# Credentials Reference

Reference for `.dev-team-agents/credentials.local.json`: how to create and edit it, the two reserved keys, and how to fill it safely.

---

## Index

- [Summary](#summary)
- [File Location](#file-location)
- [Creating and Editing](#creating-and-editing)
- [Structure](#structure)
- [Secret Values](#secret-values)
- [Release QA Sign-In](#release-qa-sign-in)
- [Usage Notes](#usage-notes)
- [Security Guidance](#security-guidance)

---

## Summary

`credentials.local.json` is the local, gitignored credential and environment reference file. It gives selected agents enough structured information to access staging or production systems when a task requires operational validation or deployment support.

It is a local file whose shape you choose. Secret values do not have to live in it: a secret can be stored by reference, with the value kept in your machine's secret store or in a password manager (see [Secret Values](#secret-values)).

---

## File Location

```text
.dev-team-agents/credentials.local.json
```

The file is machine-local (never exported or committed) and ignored by the bind-managed `.gitignore` block. It lives in the main checkout's `.dev-team-agents/`; every linked git worktree shares it, and a monorepo subproject keeps its own.

---

## Creating and Editing

The file does not exist by default. Create it in one of three ways:

### Via the Desktop App

Open the **Credentials** tab in the project view. Click **Create file** to create `credentials.local.json` from the starter example. The tab is a tree editor: add, rename, nest, move between groups and remove groups and fields, mark a field secret or a group production, and search keys and visible values.

Secrets are write-only: a value marked in `$secrets`, or one that looks secret, appears only as set / not set, with Replace. A secret that is set also has a copy button. It puts the raw value on the clipboard without showing it, and the clipboard is cleared after 30 seconds, or when the app quits, unless you copied something else meanwhile. Save or discard your edits before copying.

### Via the CLI

```bash
devteam cred local init
```

Creates the file with the canonical template. Exits with error (code 4) if the file already exists.

### By Hand

Run `devteam cred local init` and edit the result, or write the file yourself following the structure below, then run:

```bash
chmod 600 .dev-team-agents/credentials.local.json
```

---

## Structure

The file is free-form. Name, nest and remove groups and fields however suits the project: there is no fixed category, environment or agent list. `devteam cred local init` writes a small `example` group to start from; edit it or delete it.

Two reserved keys may appear in **any** object. Every other key is yours:

| Key | Value | Meaning |
|-----|-------|---------|
| `$production` | `true` | The object and everything nested below it is production. Agents ask before every state-changing action there, one action at a time |
| `$secrets` | list of sibling key names | Those keys hold secrets. The app keeps them write-only, and `devteam cred local show` never prints them |

Two top-level keys are settings, not credentials: `work_feedback_active` (default `true`) and `work_feedback_interval_minutes` (default `5`), read by the agents' periodic progress check-ins.

Example:

```json
{
  "work_feedback_active": true,
  "work_feedback_interval_minutes": 5,
  "api": {
    "staging": {
      "url": "https://staging.example.com",
      "username": "qa@example.com",
      "password": "...",
      "$secrets": ["password"]
    },
    "production": {
      "$production": true,
      "url": "https://example.com",
      "db": { "host": "db.internal", "dsn": "...", "$secrets": ["dsn"] }
    }
  },
  "jira": { "site": "acme.atlassian.net", "token": "...", "$secrets": ["token"] }
}
```

A value stays hidden even without a `$secrets` entry when its key looks secret (`password`, `token`, `secret`, `apiKey`…) or the value does (a URL with `user:password@`, a URL with a query string, pasted key material). That is a safety net, not a substitute: mark your secrets so a value under an innocent name (`conn`, `dsn2`) is protected too.

---

## Secret Values

A secret entered through the app's Credentials tab, or with a `set-secret` patch, is stored in the machine's secret store (Keychain on macOS, DPAPI on Windows) and the file keeps only a reference:

```json
"password": { "$ref": "devteam/<project_id>/local/<id>", "$backend": "keychain" }
```

You can also point at a password manager by hand: `{ "$ref": "op://QA/staging/password" }` (1Password CLI) or `{ "$ref": "bw://<item-id>/password" }` (Bitwarden CLI). The vendor CLI must be installed and unlocked.

| Command | What it does |
|---------|--------------|
| `devteam cred local secure` | Lists secrets still stored as plaintext in the file; changes nothing |
| `devteam cred local secure --apply` | Moves them into the secret store and writes their references |
| `devteam cred local exec <pointer> -- <cmd>` | Runs `<cmd>` with the group's values as `DEVTEAM_<KEY>` environment variables; this is how agents use a secret without seeing it |

Under `$production`, a plaintext secret is refused on write and reported by `devteam doctor`. On a machine with no secret store, values fall back to an `insecure` file outside the project; that fallback is refused under `$production`.

Every read of a secret value is recorded in the machine-local audit log, without the value.

---

## Release QA Sign-In

`/devteam:release-qa` signs in with `devteam qa auth <pointer>` instead of typing a password. Give the group a test identity and a `login` recipe:

```json
"staging": {
  "url": "https://staging.example.com",
  "qa": {
    "username": "qa@example.com",
    "password": { "$ref": "devteam/<project_id>/local/<id>", "$backend": "keychain" },
    "totp_secret": { "$ref": "devteam/<project_id>/local/<id>", "$backend": "keychain" },
    "$secrets": ["password", "totp_secret"],
    "login": {
      "url": "https://staging.example.com/login",
      "username_selector": "#email",
      "password_selector": "#password",
      "submit_selector": "button[type=submit]",
      "totp_selector": "#otp",
      "success_url_contains": "/dashboard"
    }
  }
}
```

Without a recipe or a stored password, `devteam qa auth <pointer> --interactive` opens a browser, you sign in once, and the session is kept on this machine until it expires (at most 8 hours). Sign-in uses the project's own Playwright install. Use a dedicated test account, never a person's account, in production as everywhere else.

---

## Usage Notes

- Keep only what the agents actually need.
- Mark every production group with `$production`. A group named `production` without the flag is not marked.
- Prefer staging credentials whenever the task does not explicitly require production.
- Renaming a secret, or moving it to another group, keeps its value and its secret mark: the change happens in the file, and the value never reaches the app.

---

## Security Guidance

- Do not commit this file.
- Keep file permissions restrictive.
- Prefer SSH keys over passwords for server access.
- Prefer least-privilege database users.
- Use dedicated non-personal app accounts where possible.
- Treat production credentials as exceptional, not default.
