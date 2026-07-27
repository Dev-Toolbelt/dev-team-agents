---
name: migration-v1-to-v2
description: Detects and migrates projects from dev-team-agents v1 (Claude-only, materialized copies) to v2 (multi-provider, symlinks).
---

# Migration v1 → v2

Load this skill when a project shows signs of v1 installation. Detect, then execute the steps below.

## Detection — Is this v1 or v2?

| Signal | v1 (old) | v2 (current) |
|--------|----------|--------------|
| Agent location | Files in `.claude/agents/` (no subdirectory) | Symlinks at `.claude/agents/dev-team/` → `.dev-team-agents/agents/` |
| Command location | Files directly in `.claude/commands/` | Symlinks at `.claude/commands/devteam/` → `.dev-team-agents/commands/` |
| Skill location | Copied dirs in `.claude/skills/` | Symlinks to `.dev-team-agents/skills/<cat>/<name>/` |
| Project docs | Inside `.claude/docs/` | Inside `docs/` |
| Source root | `.claude/dev-team-agents/` or none | `.dev-team-agents/` |
| Auto-routing | Keyword matching in `CLAUDE.md` | Explicit `/devteam:<name>` commands |
| Provider support | Claude Code only | Claude Code + OpenCode + Codex CLI |
| Symlink materialization | N/A (copied files) | Real symlinks on macOS/Linux; may be plain copies on Windows (Git Bash) |
| Updates | Manual re-copy | `git pull` or `/devteam:update` — symlinks pick up changes automatically |

## Migration Steps

### 0. Ensure `.dev-team-agents/` exists at project root

```bash
# Install if missing (curl | bash)
if [ ! -d .dev-team-agents ]; then
  curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
fi

# Or migrate from legacy location (v1 stored source in .claude/)
if [ -d .claude/dev-team-agents ] && [ ! -d .dev-team-agents ]; then
  mv .claude/dev-team-agents .dev-team-agents
fi

# Ensure VERSION file exists (used by update checks)
if [ ! -f .dev-team-agents/VERSION ]; then
  echo "v2.0.0" > .dev-team-agents/VERSION
fi
```

### 1. Move project docs to root

```bash
# Move docs from inside .claude/ to project root
[ -d .claude/docs ] && mv .claude/docs docs
```

### 2. Remove materialized v1 copies

```bash
# Backup project-specific commands first
cp .claude/commands/create-site.md /tmp/ 2>/dev/null || true

# Remove old materialized directories
rm -rf .claude/agents .claude/skills .claude/scripts .claude/templates

# Recreate commands and restore project-specific ones
mkdir -p .claude/commands
mv /tmp/create-site.md .claude/commands/ 2>/dev/null || true
```

### 3. Create symlinks to `.dev-team-agents/`

**macOS / Linux** — use symlinks:

```bash
# Agents (namespaced under dev-team/)
ln -s ../../.dev-team-agents/agents .claude/agents/dev-team

# Commands (namespaced under devteam/)
ln -s ../../.dev-team-agents/commands .claude/commands/devteam

# Skills (link each individual skill directory)
for cat in .dev-team-agents/skills/*/; do
  for dir in "$cat"*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    ln -s "../../.dev-team-agents/${dir#.dev-team-agents/}" ".claude/skills/${name}"
  done
done

# Templates
ln -s ../../.dev-team-agents/templates .claude/templates

# Scripts (must be copied — hooks need real executables)
cp -R .dev-team-agents/scripts .claude/scripts
```

**Windows (Git Bash)** — `ln -s` may copy content instead of creating symlinks. Detect and fall back:

```bash
# Try symlink first
ln -s ../../.dev-team-agents/agents .claude/agents/dev-team 2>/dev/null || true

# Verify it's a real symlink; if not, copy instead
if [ "$(uname)" = "MINGW"* ] || [ "$(uname)" = "MSYS"* ] || ! file ".claude/agents/dev-team" 2>/dev/null | grep -q "symbolic link"; then
  rm -rf .claude/agents/dev-team .claude/commands/devteam 2>/dev/null || true
  cp -r .dev-team-agents/agents .claude/agents/dev-team
  cp -r .dev-team-agents/commands .claude/commands/devteam
  for cat in .dev-team-agents/skills/*/; do
    for dir in "$cat"*/; do
      [ -d "$dir" ] || continue
      name=$(basename "$dir")
      rm -rf ".claude/skills/$name" 2>/dev/null || true
      cp -r "$dir" ".claude/skills/$name"
    done
  done
  rm -rf .claude/templates 2>/dev/null || true
  cp -r .dev-team-agents/templates .claude/templates
fi

# Fix permissions (Windows Git Bash often strips +x)
git update-index --chmod=+x .dev-team-agents/scripts/hooks/*.sh 2>/dev/null || true
```

### 4. Create `.claude/settings.json`

**macOS / Linux:**

```json
{
  "includeCoAuthoredBy": false,
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-tool-use.sh" }]
    }],
    "Stop": [{
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/stop.sh" }]
    }],
    "SessionStart": [{
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/session-start.sh" }]
    }],
    "PreCompact": [{
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-compact.sh" }]
    }]
  }
}
```

**Windows (Git Bash)** — `env -u` may fail. Remove the `-u BASH_ENV -u ENV` wrapper:

```json
{
  "includeCoAuthoredBy": false,
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{ "type": "command", "command": ".dev-team-agents/scripts/hooks/pre-tool-use.sh" }]
    }],
    "Stop": [{
      "hooks": [{ "type": "command", "command": ".dev-team-agents/scripts/hooks/stop.sh" }]
    }],
    "SessionStart": [{
      "hooks": [{ "type": "command", "command": ".dev-team-agents/scripts/hooks/session-start.sh" }]
    }],
    "PreCompact": [{
      "hooks": [{ "type": "command", "command": ".dev-team-agents/scripts/hooks/pre-compact.sh" }]
    }]
  }
}
```

### 5. Create `user-data/` directory

```bash
mkdir -p .dev-team-agents/user-data
```

| File | Purpose |
|------|---------|
| `preferences.json` | Language, worktree, project config |
| `session-summary.md` | Session continuity |
| `.installed-version` | Version tracking |

### 6. Configure OpenCode provider (if applicable)

#### 6a. Render agents and commands

```bash
python3 .dev-team-agents/scripts/lib/render_provider.py \
  --provider opencode \
  --source-dir .dev-team-agents \
  --target-dir .
```

Merge the generated `commands.snippet.jsonc` into `.opencode/opencode.json` → `command` key.

#### 6b. Create thin wrapper agents

OpenCode needs agent files in `.opencode/agents/`. Each is a thin wrapper — prompt body stays in `.dev-team-agents/agents/`.

```bash
mkdir -p .opencode/agents
for agent in backend-developer backend-reviewer backend-test-specialist code-reviewer \
             database-specialist devops-specialist frontend-developer frontend-reviewer \
             frontend-test-specialist mobile-developer product-analyst qa-specialist \
             security-specialist setup-assistant software-architect technical-writer \
             ui-ux-designer; do
  cat > ".opencode/agents/${agent}.md" <<EOF
---
description: $(grep "^description: " ".dev-team-agents/agents/${agent}.md" 2>/dev/null | sed 's/description: //')
mode: subagent
permission:
  task: allow
  bash: deny
---
EOF
done
```

#### 6c. Create OpenCode plugin (hooks bridge)

```bash
mkdir -p .opencode/plugins
cat > .opencode/plugins/dev-team-agents.ts <<'PLUGINEOF'
import type { Plugin } from "@opencode-ai/plugin"
import { exec } from "node:child_process"
import { promisify } from "node:util"

const execAsync = promisify(exec)
const HOOK_TIMEOUT_MS = 5000

export const DevTeamAgents: Plugin = async ({ client, directory }) => {
  const HOOKS = `${directory}/.dev-team-agents/scripts/hooks`

  const runHook = async (script: string, stdin?: string): Promise<string> => {
    try {
      const { stdout } = await execAsync(`bash ${script}`, {
        input: stdin, maxBuffer: 1024 * 1024, timeout: HOOK_TIMEOUT_MS,
      })
      return stdout
    } catch (err) {
      await client.app.log({ body: { service: "dev-team-agents", level: "warn", message: `hook error: ${script} - ${String(err)}` }})
      return ""
    }
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") await runHook(`${HOOKS}/session-start.sh`)
      if (event.type === "session.idle") await runHook(`${HOOKS}/stop.sh`)
    },
    "tool.execute.before": async (input, output) => {
      await runHook(`${HOOKS}/pre-tool-use.sh`, JSON.stringify({ tool: input.tool, args: output.args }))
    },
    "experimental.session.compacting": async (_input, output) => {
      const r = await runHook(`${HOOKS}/pre-compact.sh`)
      if (r?.trim()) output.context.push(`## dev-team-agents session summary\n${r.trim()}`)
    },
  }
}
PLUGINEOF
```

#### 6d. Create `.opencode/.gitignore`

```bash
cat > .opencode/.gitignore <<'EOF'
node_modules
package.json
package-lock.json
bun.lock
.gitignore
EOF
```

#### 6e. Configure AGENTS.md

OpenCode reads `AGENTS.md` (takes precedence over `CLAUDE.md`). Create or update it with the dev-team-agents section:

```markdown
## dev-team-agents

PROJECT_TYPE: [new | existing | migration | monorepo]
TESTS_REQUIRED: yes
CICD_PLATFORM: [github-actions | gitlab-ci | none]
GRAPHIFY: [enabled | disabled]
BACKLOG_LOCATION: local
CLOUD_PROVIDER: [none | aws | gcp | azure]
ISSUE_TRACKER: [none | jira | github]
ISSUE_TRACKER_ACCESS: [read-only | read-write]

### Agent Activation
- product-analyst: active
- software-architect: active
- backend-test-specialist: active
- frontend-test-specialist: active
- ui-ux-designer: active
- devops-specialist: active
```

### 7. Update `CLAUDE.md`

| v1 path | v2 path |
|---------|---------|
| `.claude/docs/` | `docs/` |
| `.claude/dev-team-agents/` | `.dev-team-agents/` |

Replace keyword-based auto-routing sections with the v2 command table.

## Post-Migration Verification

```bash
# Confirm agents and commands are accessible
ls .dev-team-agents/agents/          # 17+ agent files
ls .dev-team-agents/commands/        # 21+ command files

# Confirm symlinks or copies are in place
ls .claude/agents/dev-team/          # should list agents
ls .claude/commands/devteam/         # should list commands
ls .claude/skills/ | wc -l          # 130+ skills

# On macOS/Linux — verify real symlinks
file .claude/agents/dev-team | grep -q "symbolic link" && echo "OK: symlink"

# On Windows — verify content was copied
[ "$(uname)" = "MINGW"* ] && ls .claude/agents/dev-team/*.md > /dev/null && echo "OK: copied"

# Confirm hooks are wired
grep "dev-team-agents/scripts/hooks" .claude/settings.json

# OpenCode-specific
file .opencode/opencode.json 2>/dev/null && echo "OK: opencode config"
file .opencode/plugins/dev-team-agents.ts 2>/dev/null && echo "OK: opencode plugin"
ls .opencode/agents/ | wc -l 2>/dev/null
```

## Known Windows Issues

| Problem | Symptom | Fix |
|---------|---------|-----|
| `ln -s` copies instead of symlinking | `file <dir>` shows `directory` not `symbolic link` | Use `cp -r` fallback or enable Developer Mode (Settings → For Developers → Developer Mode) |
| `env -u BASH_ENV` fails in Git Bash | Hook returns error | Omit `-u BASH_ENV -u ENV` from `settings.json` hook commands |
| Shell scripts `\r\n` line endings | `$'\r': command not found` error | Set `git config core.autocrlf false` or run `dos2unix` on `.sh` files |
| Permission denied on hooks | `Permission denied` in hook output | `git update-index --chmod=+x .dev-team-agents/scripts/hooks/*.sh` |
| Spaces in project path | Commands break on spaces | Ensure project path has no spaces, or quote all paths |

## Rollback

```bash
# macOS / Linux
find .claude -type l -delete
cp -R .dev-team-agents/scripts .claude/scripts

# Windows (content was copied, not symlinked)
rm -rf .claude/agents/dev-team .claude/commands/devteam
# Reinstall v1 from backup or git history
```
