"""Make the ``orchestrator`` persona the Claude Code session default (ADR-0062).

``orchestrator_default`` is personal, so the key goes to the **uncommitted**
``.claude/settings.local.json`` (git-ignored by the bind-managed ``.gitignore`` block), never
to the committed ``.claude/settings.json``.

| Provider | Where | Key |
|---|---|---|
| claude | ``.claude/settings.local.json`` | ``agent`` |
| opencode | none: its default agent would land in a committed config | |
| codex | none: devteam does not write Codex ``config.toml``; ``/devteam:orchestrate`` covers it | |

With the preference on, the key is written only when ``agent`` is absent from
``settings.local.json``; with it off, the key is removed only while it holds ``"orchestrator"``.
That value is treated as ours on removal: a user who sets ``"orchestrator"`` by hand there
loses it when the preference is off or the project is unbound. Any other value is never
overwritten or removed. ``devteam bind``/``sync``/``unbind`` and ``install.sh`` reach
:func:`apply_project` (the installer through ``scripts/lib/default_agent.py``).
"""

from __future__ import annotations

from pathlib import Path

from . import jsonio
from .errors import EnvError

PERSONA = "orchestrator"

#: The provider-native key per provider. opencode and Codex have none and are deliberately absent.
KEYS = {"claude": "agent"}

CLAUDE_FILE = ".claude/settings.local.json"
_PREFS_FILES = (".dev-team-agents/resolved/preferences.json", ".dev-team-agents/user-data/preferences.json")


def apply(data, provider, enabled):
    """Apply the rule to a parsed config object. Returns True when it changed."""
    key = KEYS[provider]
    if enabled:
        if key in data:
            return False
        data[key] = PERSONA
        return True
    if data.get(key) == PERSONA:
        data.pop(key)
        return True
    return False


def read_enabled(project_root):
    """The ``orchestrator_default`` preference of a project; ``False`` when unreadable or unset."""
    for rel in _PREFS_FILES:
        try:
            data = jsonio.read_json(Path(project_root) / rel, default=None)
        except EnvError:
            return False
        if isinstance(data, dict):
            return data.get("orchestrator_default") is True
    return False


def apply_project(project_root, provider, enabled):
    """Apply the rule to the project's local settings file. Returns True when it changed.

    Raises ``EnvError`` for a file that is not a strict JSON object and ``ConflictError`` for
    a path that resolves outside the project; either way the file is left untouched.
    """
    # Lazy: `bind` imports this module.
    from .bind import require_inside

    root = Path(project_root)
    path = require_inside(root / CLAUDE_FILE, root, what=CLAUDE_FILE)
    data = jsonio.read_json(path, default=None)
    if data is None:
        if not enabled:
            return False
        data = {}
    if not isinstance(data, dict):
        raise EnvError("{} is not a JSON object".format(path), hint="Fix the file by hand; it was not changed.")
    if not apply(data, provider, enabled):
        return False
    jsonio.write_json_atomic(path, data, mode=0o644, dir_mode=None)
    return True
