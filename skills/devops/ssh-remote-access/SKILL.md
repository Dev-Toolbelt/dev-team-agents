---
name: ssh-remote-access
description: Step-by-step protocol for setting up SSH access from Claude Code to a remote server — key generation, authorized_keys, config entry, connection test, and project documentation.
---

When the user describes a problem or task happening on a **remote server** (keywords: "the server is doing", "in production", "on the VPS", "the remote machine", "my server", "server logs", "server crash"), proactively offer help:

> "It looks like this is happening on a remote server. I can help you configure SSH access so I can run commands directly. Want me to set that up?"

**Only proceed if the user confirms.** Then follow this flow:

## Step 1 — Generate Claude's SSH key (run via Bash)

```bash
# Check if a Claude-specific key already exists
ls ~/.ssh/id_ed25519_claude 2>/dev/null && echo "KEY_EXISTS" || echo "KEY_MISSING"
```

If missing, generate it:
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_claude -N "" -C "claude-code"
```

## Step 2 — Show the public key

```bash
cat ~/.ssh/id_ed25519_claude.pub
```

Display it to the user and say: "Add this public key to `~/.ssh/authorized_keys` on the server."

If `ssh-copy-id` is available and the user can provide the server address and a temporary password/key, offer to run it:
```bash
ssh-copy-id -i ~/.ssh/id_ed25519_claude.pub user@server-ip
```

Confirm user consent before running any remote command.

## Step 3 — Add host entry to ~/.ssh/config

Ask the user for:
- `<host-name>` — a short alias (e.g., `prod`, `staging`)
- `<host-ip>` — the server IP or hostname
- `<ssh-user>` — the SSH user on the server

Then run via Bash:
```bash
cat >> ~/.ssh/config <<EOF

Host <host-name>
    HostName <host-ip>
    User     <ssh-user>
    IdentityFile ~/.ssh/id_ed25519_claude
    StrictHostKeyChecking accept-new
EOF
```

## Step 4 — Test the connection

```bash
ssh <host-name> echo "SSH connection successful"
```

If it succeeds, confirm to the user. If it fails, diagnose: check `authorized_keys` permissions (`chmod 600`), `sshd_config` settings, and firewall rules.

## Step 5 — Document in the target project

After successful setup, update the target project's context:

1. Add to `.claude/user-data/session-summary.md` a note that SSH access to `<host-name>` is configured
2. Append to the project's `CLAUDE.md` (if it exists):

```markdown
## Remote SSH Access

SSH to `<host-name>` is configured via `~/.ssh/config`. Use `ssh <host-name> <command>` directly in Bash tool calls. Key: `~/.ssh/id_ed25519_claude`.
```

This ensures future agents in this project know SSH is available without repeating the setup.

## Fallback — if Bash execution is not possible

If any step cannot be executed via Bash, provide the full manual walkthrough:
1. Show the `ssh-keygen` command to run in the terminal
2. Show the public key location
3. Explain how to add it to `authorized_keys` on the server
4. Show the `~/.ssh/config` block to paste manually
