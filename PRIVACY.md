# Privacy Policy — dev-team-agents

dev-team-agents can collect **anonymous, aggregate usage data** to help us understand
which agents and commands are most valuable and guide product decisions.

**Telemetry is off unless you turn it on.** Nothing is collected until
`.dev-team-agents/user-data/preferences.json` contains `"telemetry": true`, and the
installer writes that value only after you were actually shown the prompt and
accepted it. See "Consent" below for the exact rules.

---

## Consent

On **first install only**, `install.sh` asks whether to enable anonymous telemetry.
It asks by opening the controlling terminal (`/dev/tty`) rather than testing stdin,
so the prompt appears even on the documented `curl … | bash` path, where stdin is a
pipe.

| Situation at install time | Result |
|---|---|
| Terminal reachable, you press Enter or answer `y` | Enabled |
| Terminal reachable, you answer `n` | Disabled |
| Terminal reachable, no answer within 60 seconds, or stdin hits EOF | **Disabled** — silence is not consent |
| `DEVTEAM_NONINTERACTIVE=1` set (CI, container images, provisioning) | **Disabled**, no prompt shown |
| No terminal reachable at all | **Disabled**, with a printed note on how to enable it later |

Re-installs and updates never re-ask and never change an existing value.

The read path fails closed to match: a missing `preferences.json`, an unreadable one,
a file with no `telemetry` key, or a machine without `python3` all mean "consent was
never recorded", and nothing is queued or sent.

---

## What we collect

Only when telemetry is enabled:

| Event | When | Data sent |
|-------|------|-----------|
| `first_install` | First-time installation | Installed version, OS (`darwin`/`linux`) |
| `install` | Re-install or update via installer | Installed version, OS |
| `update` | Manual update via `update.sh` | Previous version, new version, mode (`manual`) |
| `agent_spawned` | Any time an agent is started via the `Task` tool | OS, installed version |
| `command_invoked` | Any `/devteam:*` slash command executed | Command name (e.g. `plan`, `backend`), OS, version |
| `session_end` | End of each CLI session (any supported provider) | Whether the stop hook was active, OS, version |
| `agent_completed` | An agent invocation finishes | Agent name, the actual resolved model it ran on, token counts (input/output/cache), provider |

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
(gitignored) and sent in batches to **PostHog** (US region, `us.i.posthog.com`) over
HTTPS. The queue is flushed at most once every 24 hours or when it reaches 100 events.
The endpoint can be repointed at a self-hosted PostHog instance with the
`DEVTEAM_POSTHOG_ENDPOINT` environment variable.

PostHog data retention: aggregate metrics are kept indefinitely; raw event logs
are retained for 90 days and then deleted automatically.

---

## Turning it off (or on)

The value lives in `.dev-team-agents/user-data/preferences.json`:

```json
{
  "telemetry": false
}
```

Set it to `false` to stop collection, or `true` to opt in if you declined (or were
never asked) at install time. After saving, you can verify the current state with:

```bash
.dev-team-agents/scripts/helpers/telemetry-send.sh --dry-run
```

---

## Questions

Open an issue at <https://github.com/Dev-Toolbelt/dev-team-agents/issues>.
