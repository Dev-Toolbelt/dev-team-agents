# Fix Patterns

## Auto-fix for `includeCoAuthoredBy`

```bash
python3 - .claude/settings.json <<'PYEOF'
import sys, json
f = sys.argv[1]
with open(f) as fh: data = json.load(fh)
data['includeCoAuthoredBy'] = False
with open(f, 'w') as fh: json.dump(data, fh, indent=2); fh.write('\n')
PYEOF
```

## Auto-fix for missing symlinks

Only when the path does **not** exist (MISSING). If the path exists as a plain
file (MATERIALIZED), `ln -s` fails — use the materialized-link fix below.

```bash
# agents symlink
ln -s ../../.dev-team-agents/agents .claude/agents/dev-team

# commands symlink
ln -s ../../.dev-team-agents/commands .claude/commands/devteam
```

## Fix for materialized symlinks (Windows)

When a link exists as a plain text file instead of a symlink (the Windows
"no native symlink support" condition), run the repair helper — never a raw
`ln -s`, which fails because the path already exists:

```bash
bash .dev-team-agents/scripts/fix-symlinks.sh
```

Behavior:
- **Auto-repairs** when the OS allows native symlinks (Developer Mode on, or an
  elevated process): enables `core.symlinks`, re-materializes each broken link
  (scoped `git checkout` if tracked, else `ln -s`), and re-validates. Exit 0.
- **Cannot repair** (native symlinks blocked): exits 3 and prints the 3
  remediation options. Present them to the user with `AskUserQuestion`
  (quiz-first), then auto-run the safe git steps once the blocker clears:

  1. **Developer Mode** (recommended, no admin) — user enables it in
     Settings → System → For developers; agent then runs
     `git config core.symlinks true && git checkout -- .claude` and re-validates.
  2. **Elevated terminal once** — user runs the two git commands above in an
     Administrator PowerShell, then restarts the CLI.
  3. **Run the CLI as administrator** — fully close the app (incl. tray and
     lingering processes), right-click → Run as administrator, re-run the helper.

After any successful repair, tell the user to restart their CLI so it
re-indexes commands, agents, and skills.

> `fix-symlinks.sh` inspects the `.claude/` tree only. On opencode and Codex
> installs the `skills/` symlink under `.opencode/` or `.codex/` breaks the same
> way — check it with `test -L <config-dir>/skills/dev-team-agents` and repair by
> re-running that provider's installer.

## Auto-fix for Codex provider drift

When any of the following Codex checks fail:
- missing or invalid `.codex/hooks.json`
- missing managed hook entries
- missing generated `$devteam-*` skill dirs
- generated `$devteam-*` skill frontmatter names do not match their folder basenames
- legacy project-local `.codex/prompts/devteam-*.md` aliases still exist
- rendered Codex command skills still use the pre-`request_user_input` quiz generation (missing `request_user_input`, missing `/plan` retry guidance, or still instructing degraded plain-text choice rendering)
- mismatched `.codex/agents/*.toml` `model` / `model_reasoning_effort`

re-render and reinstall the Codex provider:

```bash
bash .dev-team-agents/scripts/install-codex.sh
```

This is the canonical repair because the Codex install is rendered output. Fixing
individual prompt, skill, TOML, or hook files by hand invites drift from the
canonical source in `agents/`, `commands/`, `skills/`, and `scripts/lib/*.json`.

## Auto-fix for non-executable scripts

```bash
chmod +x .dev-team-agents/scripts/hooks/pre-tool-use.sh
chmod +x .dev-team-agents/scripts/hooks/stop.sh
chmod +x .dev-team-agents/scripts/hooks/session-start.sh
chmod +x .dev-team-agents/scripts/hooks/stop/01-session-summary.sh
chmod +x .dev-team-agents/scripts/update.sh
# 04-notifier.sh, 05-telemetry.sh, 02b-telemetry.sh, 01-check-updates.sh, and
# 99-graphify-refresh.sh are disabled by design — do not chmod their _disabled- variants
# back into the dispatch convention. See CLAUDE-md/hooks.md § Disabled Hooks.
```

## Auto-fix for .gitignore migration (legacy per-file → directory pattern)

When legacy individual entries are detected, offer migration:

> Your `.gitignore` uses the old per-file pattern for `user-data/`. The current version uses a directory-level ignore (`.dev-team-agents/user-data/`) with a `graphify.json` exception. Migrate automatically?

On confirmation: **replace** the 4 legacy lines with the 3 new entries — a single rewrite of the block, not a delete followed by an append. The 4 legacy paths are all covered by the directory pattern that replaces them, so nothing stops being ignored at any point; a two-step edit leaves a window where `user-data/` is tracked. This is a config rewrite, not a removal — see the No-Destruction Rule in `../SKILL.md`.

Legacy entries superseded by the rewrite:
```
.dev-team-agents/user-data/session-summary.md
.dev-team-agents/user-data/.last-update-check
.dev-team-agents/user-data/.installed-version
.dev-team-agents/user-data/.auto-update
```

New entries to add:
```
.dev-team-agents/user-data/
!.dev-team-agents/user-data/graphify.json
.dev-team-agents/.worktree-session
```

### Malformed single-line entry fix

If a legacy entry like `.claude/user-data/*!.claude/user-data/graphify.json` exists (no newline between the two patterns), separate them:

```bash
sed -i '' 's|\.claude/user-data/\*!\.claude/user-data/graphify\.json|.claude/user-data/\n!.claude/user-data/graphify.json|' .gitignore
```

Then update to the new paths:

```bash
sed -i '' 's|\.claude/user-data|.dev-team-agents/user-data|g' .gitignore
```

## Legacy directory migration

If legacy `.claude/` directories still exist (user-data, docs, context, tasks, dev-team-agents):

| Legacy path | New path | Action |
|---|---|---|
| `.claude/user-data/` | `.dev-team-agents/user-data/` | `mv .claude/user-data .dev-team-agents/user-data` |
| `.claude/docs/` | `docs/` | `mv .claude/docs docs` (merge if `docs/` exists) |
| `.claude/context/` | `docs/context/` | `mkdir -p docs/context && mv .claude/context/* docs/context/` |
| `.claude/tasks/` | `docs/tasks/` | `mkdir -p docs/tasks && mv .claude/tasks/* docs/tasks/` |
| `.claude/dev-team-agents/` | `.dev-team-agents/` | Run `bash .dev-team-agents/scripts/migrate-to-root.sh` |
| `.claude/.worktree-session` | `.dev-team-agents/.worktree-session` | `mv .claude/.worktree-session .dev-team-agents/` |

After moving, clean up under the **No-Destruction Rule** (`../SKILL.md`):

```bash
# Empty leftovers only — rmdir without -r fails on anything still holding content
rmdir .claude/user-data .claude/docs .claude/context .claude/tasks 2>/dev/null

# .claude/dev-team-agents/ — quarantine whatever migrate-to-root.sh left behind
if [ -d .claude/dev-team-agents ] && [ -n "$(ls -A .claude/dev-team-agents 2>/dev/null)" ]; then
  QUARANTINE=".dev-team-agents/user-data/legacy/$(date +%Y-%m-%d)"
  mkdir -p "$QUARANTINE"
  mv .claude/dev-team-agents "$QUARANTINE/"
  echo "→ Quarantined leftover .claude/dev-team-agents → $QUARANTINE/"
else
  rmdir .claude/dev-team-agents 2>/dev/null
fi
```

This path previously ran `rm -rf .claude/dev-team-agents`, unconditionally, on the line following `migrate-to-root.sh`. A migration that failed halfway therefore destroyed `user-data/` — session summaries, preferences, credentials — with no record that it had. Residue after a migration is evidence the migration is incomplete; it is never cleanup.

## State.json marker migration

If any `LEGACY_MARKER` was reported by Category 3 (a project still on the pre-consolidation dotfiles — `.installed-version`, `.installed-version.prev`, `.last-health-check`, `.last-update-check`, `.update-check-interval`, `.graphify-last-run`, `.session-id`, `.session-head`):

```bash
source .dev-team-agents/scripts/lib/state.sh
state_migrate_legacy .dev-team-agents/user-data
```

`state_migrate_legacy` is idempotent and additive under the **No-Destruction Rule**: it reads each present dotfile's value into the matching key in `state.json`, then renames the original to `<name>.pre-migration.bak` — it never deletes. Re-running it on a project that already migrated is a no-op (the dotfiles are gone, only the `.bak` files remain). Report which markers were migrated; leave the `.bak` files in place — they are not further cleanup for this check to perform.

## Auto-fix for missing pre-compact auto-summary rule in CLAUDE.md

Append the rule block to `CLAUDE.md` (idempotent — marker prevents duplicates):

```bash
_DTA_MARKER="<!-- dev-team-agents: pre-compact-auto-summary -->"
if ! grep -qF "$_DTA_MARKER" CLAUDE.md 2>/dev/null; then
    cat >> CLAUDE.md <<'CLAUDEEOF'

<!-- dev-team-agents: pre-compact-auto-summary -->
# Pre-compact Hook — Auto Session Summary
When `/compact` is blocked by the `pre-compact.sh` hook with the message "SESSION SUMMARY REQUIRED (pre-compact)", do the following **automatically, without asking the user**:

1. Write the session summary entry at the top of `.dev-team-agents/user-data/session-summary.md` using the format:
   ```
   ## YYYY-MM-DD HH:MM:SS | [brief task title]
   **Done**: what was implemented or changed

   **Decisions**: key choices made and why

   **Next**: what remains or is recommended next

   ---
   ```
   - Use today's date and current time
   - Base the content on the current conversation context
   - Always write in English
2. After writing, tell the user: "Session summary written. Run `/compact` again to proceed."

Do not ask for confirmation. Do not wait for user input. Write and notify immediately.
CLAUDEEOF
fi
```

## Auto-fix for missing Codex session-banner rule in AGENTS.md

Append the managed rule block to `AGENTS.md` (idempotent — marker prevents duplicates):

```bash
_DTA_CODEX_BANNER_MARKER="<!-- dev-team-agents: codex-session-banner -->"
if ! grep -qF "$_DTA_CODEX_BANNER_MARKER" AGENTS.md 2>/dev/null; then
    cat >> AGENTS.md <<'AGENTSEOF'

<!-- dev-team-agents: codex-session-banner -->
## Codex Session Banner

When the `SessionStart` hook context contains a line exactly equal to `[DEVTEAM:SESSION_BANNER]`, reproduce the next three lines **verbatim, unmodified**, as the first thing in your **first reply of the session**.

Rules:
- Do not add any text before the banner.
- Do not translate, summarize, or reformat it.
- Do not fabricate the banner when the marker is absent.
- This rule applies to normal conversation too, not only `$devteam-*` skills.
AGENTSEOF
fi
```

## Auto-fix for missing preferences.json fields

Inject missing fields without overwriting existing values:

```python
import json

defaults = {
    "language": "en",
    "context_window_percent_warning": 55,
    "context_window_percent_limit": 60,
    "suppress_notifications": False,
    "session_summary_max_days": 30,
    "session_summary_max_entries": 30,
    "docs_stale_after_days": 30,
    "auto_update": False,
    "update_check_interval_hours": 24,
}

path = ".dev-team-agents/user-data/preferences.json"
with open(path) as f:
    data = json.load(f)

for key, val in defaults.items():
    if key not in data:
        data[key] = val

with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
```

## Auto-fix for missing credentials.local.json

When the file does not exist, create it with the default template (fields empty):

```bash
CRED_FILE=".dev-team-agents/user-data/credentials.local.json"
cat > "$CRED_FILE" << 'JSONEOF'
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
JSONEOF
chmod 600 "$CRED_FILE"
```

## Auto-fix for missing top-level keys in credentials.local.json

Inject missing keys (`devops`, `app`) with defaults without overwriting existing data:

```python
import json

path = ".dev-team-agents/user-data/credentials.local.json"
template = {
    "devops": {
        "agents": ["software-architect", "devops-specialist", "security-specialist"],
        "staging": {"ssh": {"user": "", "host": "", "privateKeyPath": "", "path": ""}, "database": []},
        "production": {"ssh": {"user": "", "host": "", "privateKeyPath": "", "path": ""}, "docker": {}, "database": []}
    },
    "app": {
        "agents": ["software-architect", "backend-developer", "frontend-developer", "code-reviewer", "backend-reviewer", "frontend-reviewer", "qa-specialist", "security-specialist", "backend-test-specialist", "frontend-test-specialist"],
        "staging": {"appUrl": "", "username": "", "password": ""},
        "production": {"appUrl": "", "username": "", "password": ""}
    }
}

with open(path) as f:
    data = json.load(f)

changed = False
for key, val in template.items():
    if key not in data:
        data[key] = val
        changed = True

if changed:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
```

## Auto-fix for root-level credentials.local.json

When `credentials.local.json` exists at the project root instead of the correct location:

```bash
if [ -f "$PROJECT_ROOT/credentials.local.json" ] && [ ! -f ".dev-team-agents/user-data/credentials.local.json" ]; then
    mv "$PROJECT_ROOT/credentials.local.json" ".dev-team-agents/user-data/credentials.local.json"
    chmod 600 ".dev-team-agents/user-data/credentials.local.json"
    echo "→ Migrated credentials.local.json from project root to .dev-team-agents/user-data/"
elif [ -f "$PROJECT_ROOT/credentials.local.json" ] && [ -f ".dev-team-agents/user-data/credentials.local.json" ]; then
    QUARANTINE=".dev-team-agents/user-data/legacy/$(date +%Y-%m-%d)"
    mkdir -p "$QUARANTINE"
    mv "$PROJECT_ROOT/credentials.local.json" "$QUARANTINE/credentials.local.json"
    chmod 600 "$QUARANTINE/credentials.local.json"
    echo "→ credentials.local.json existed at both locations. The root-level copy was moved to $QUARANTINE/ — the one in user-data/ is authoritative. Compare them before discarding: the two may hold different keys."
fi
```

Never instruct the user to `rm` the duplicate. Two credential files at different paths are not presumed identical — the root-level one may carry a key the other lacks, and that is unrecoverable once deleted.

## Auto-fix for missing gitignore entry

```bash
_ENTRY=".dev-team-agents/user-data/credentials.local.json"
grep -qF "$_ENTRY" .gitignore 2>/dev/null || {
    echo "# NEVER commit credentials — contains remote access secrets" >> .gitignore
    echo "$_ENTRY" >> .gitignore
}
```

## Auto-fix for opencode agent model/variant config

When opencode agent files are missing `model:` or `variant:` in frontmatter, or the command snippets lack these fields, re-run the opencode installer:

```bash
bash .dev-team-agents/scripts/install-opencode.sh
```

This re-renders all agent files, command snippets, and plugin from the canonical source (`scripts/lib/tiers.json`), ensuring every agent has the correct model and variant per its tier.

After re-rendering, verify the fix:

```bash
missing=0
for f in .opencode/agents/*.md; do
  [ -f "$f" ] || continue
  has_model=$(grep -c '^model: ' "$f" || true)
  has_variant=$(grep -c '^variant: ' "$f" || true)
  if [ "$has_model" -eq 0 ] || [ "$has_variant" -eq 0 ]; then
    echo "STILL_MISSING: $(basename "$f" .md)"
    missing=$((missing + 1))
  fi
done
[ "$missing" -eq 0 ] && echo "OK: all agents have model+variant"
```

## Auto-fix for legacy .auto-update flag

```bash
# Set auto_update: true in preferences.json, then retire the flag file
python3 - .dev-team-agents/user-data/preferences.json <<'PYEOF'
import sys, json
f = sys.argv[1]
with open(f) as fh: data = json.load(fh)
data['auto_update'] = True
with open(f, 'w') as fh: json.dump(data, fh, indent=2); fh.write('\n')
PYEOF
QUARANTINE=".dev-team-agents/user-data/legacy/$(date +%Y-%m-%d)"
mkdir -p "$QUARANTINE"
mv .dev-team-agents/user-data/.auto-update "$QUARANTINE/"
```

The flag carries no content — its existence *was* the value, and that value is now in `preferences.json`. It is still moved rather than deleted, because the No-Destruction Rule has no "this one is safe" exception: a rule with a judgment call in it gets the judgment wrong eventually, and quarantining a zero-byte marker costs nothing.

## Backfill for `docs/development/reuse-guidelines.md`

Triggered by the Reuse Guidelines Backfill check (Category 11). After the user confirms a proposed row for a sentence found in `code-standards.md`, `design-system.md`, or a wiki entry:

```bash
REGISTRY="docs/development/reuse-guidelines.md"

# Create the registry from the template's header if this is the first row ever backfilled
if [ ! -f "$REGISTRY" ]; then
  head -n 3 .dev-team-agents/templates/reuse-guidelines-template.md | tail -n 2 > "$REGISTRY"
  # (the two header lines: "| name | type | ... |" and the "|---|---|...|" separator —
  #  never copy the template's example row)
fi

# Append the confirmed row (built in the check step, not here)
echo "$CONFIRMED_ROW" >> "$REGISTRY"
```

Then, in the **source document** (`code-standards.md`, `design-system.md`, or the wiki entry), replace the located sentence/paragraph with a one-line pointer, using Edit — never Write the whole file:

```
See `docs/development/reuse-guidelines.md` § <name> for the canonical rule.
```

Keep the original heading in place even if the paragraph under it is now just the pointer — removing the heading changes anchors other docs or commits may reference. This is a content *move*, not a deletion: the rule still exists, now in one place instead of two.
