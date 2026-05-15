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

```bash
# agents symlink
ln -s ../dev-team-agents/agents .claude/agents/dev-team

# commands symlink
ln -s ../dev-team-agents/commands .claude/commands/devteam
```

## Auto-fix for non-executable scripts

```bash
chmod +x .claude/dev-team-agents/scripts/hooks/pre-tool-use.sh
chmod +x .claude/dev-team-agents/scripts/hooks/stop.sh
chmod +x .claude/dev-team-agents/scripts/hooks/session-start.sh
chmod +x .claude/dev-team-agents/scripts/hooks/stop/01-session-summary.sh
chmod +x .claude/dev-team-agents/scripts/hooks/stop/04-notifier.sh
chmod +x .claude/dev-team-agents/scripts/update.sh
```

## Auto-fix for .gitignore migration (legacy per-file → directory pattern)

When legacy individual entries are detected, offer migration:

> Your `.gitignore` uses the old per-file pattern for `user-data/`. The current version uses a directory-level ignore (`.claude/user-data/`) with a `graphify.json` exception. Migrate automatically?

On confirmation: remove the 4 legacy lines, add the 3 new entries.

Legacy entries to remove:
```
.claude/user-data/session-summary.md
.claude/user-data/.last-update-check
.claude/user-data/.installed-version
.claude/user-data/.auto-update
```

New entries to add:
```
.claude/user-data/
!.claude/user-data/graphify.json
.claude/.worktree-session
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

path = ".claude/user-data/preferences.json"
with open(path) as f:
    data = json.load(f)

for key, val in defaults.items():
    if key not in data:
        data[key] = val

with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
```

## Auto-fix for legacy .auto-update flag

```bash
# Set auto_update: true in preferences.json, then remove flag file
python3 - .claude/user-data/preferences.json <<'PYEOF'
import sys, json
f = sys.argv[1]
with open(f) as fh: data = json.load(fh)
data['auto_update'] = True
with open(f, 'w') as fh: json.dump(data, fh, indent=2); fh.write('\n')
PYEOF
rm .claude/user-data/.auto-update
```
