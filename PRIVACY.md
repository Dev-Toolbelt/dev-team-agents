# Privacy Policy — dev-team-agents

dev-team-agents collects **anonymous, aggregate usage data** to help us understand
which agents and commands are most valuable and guide product decisions.

---

## What we collect

| Event | When | Data sent |
|-------|------|-----------|
| `first_install` | First-time installation | Installed version, OS (`darwin`/`linux`) |
| `install` | Re-install or update via installer | Installed version, OS |
| `update` | Manual update via `update.sh` | Previous version, new version, mode (`manual`) |
| `agent_spawned` | Any time an agent is started via the `Task` tool | OS, installed version |
| `command_invoked` | Any `/devteam:*` slash command executed | Command name (e.g. `plan`, `backend`), OS, version |
| `session_end` | End of each Claude Code session | Whether the stop hook was active, OS, version |

All events also include:
- **`$lib`**: always `"dev-team-agents"` (identifies the source)
- **`version`**: the installed version tag (e.g. `v1.2.0`)
- **`os`**: operating system family (`darwin` or `linux`)

---

## What we do NOT collect

- File names, file paths, or directory structures
- Code content or text from your codebase
- Agent conversation content or prompts
- Project names, repository names, or branch names
- Your username, email address, or any personal identifier
- IP addresses (stripped at the PostHog ingestion layer)

---

## Anonymous identifier

Each installation generates a one-way **SHA-256 hash** derived from your machine
hostname and home directory path. This hash:

- Is stored locally in `.dev-team-agents/user-data/telemetry-queue.json`
- Cannot be reversed to recover your hostname or home directory
- Is used only to deduplicate install events (not to track individuals)
- Is never transmitted along with any personal data

---

## Data storage

Events are buffered locally in `.dev-team-agents/user-data/telemetry-queue.json`
(gitignored) and sent in batches to **PostHog** (EU region) over HTTPS.
The queue is flushed at most once every 24 hours or when it reaches 100 events.

PostHog data retention: aggregate metrics are kept indefinitely; raw event logs
are retained for 90 days and then deleted automatically.

---

## Opt out

Set `"telemetry": false` in `.dev-team-agents/user-data/preferences.json`:

```json
{
  "telemetry": false
}
```

After saving, no events will be queued or sent. You can verify by running:

```bash
.dev-team-agents/scripts/helpers/telemetry-send.sh --dry-run
```

---

## Questions

Open an issue at <https://github.com/Dev-Toolbelt/dev-team-agents/issues>.
