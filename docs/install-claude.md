# Installing dev-team-agents for Claude Code

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
```

Run from your **project root**. The installer:

1. Detects or asks for your conversation language (BCP 47 tag, default `en`)
2. Downloads the latest release tarball
3. Extracts to `.dev-team-agents/` (slim bundle — only Claude-runtime files)
4. Symlinks agents → `.claude/agents/dev-team/`, skills → `.claude/skills/`, commands → `.claude/commands/devteam/`
5. Wires lifecycle hooks in `.claude/settings.json`

## After install

Start the setup flow by typing:

```
Help me set up this project with dev-team-agents
```

The `setup-assistant` agent scans your project, collects configuration (tests, CI, cloud provider), and generates living context docs in `.claude/docs/`.

## Options

| Flag | Effect |
|------|--------|
| `v1.2.0` (any tag) | Install a specific version |
| `latest` | Re-download the latest release (update) |

## Update

```bash
bash .dev-team-agents/scripts/update.sh
```

## Advanced

See [docs/installation.md](../docs/installation.md) for version pinning, auto-update, and notification tuning.