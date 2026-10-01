"""Register the hook dispatchers a bound project needs.

v2's ``install.sh`` (Steps around :675-807) wrote four entries into
``.claude/settings.json``. The first cut of the v3 bind produced agents, commands
and skills and stopped there — so a bound project silently lost the session
banner, the ``Stop`` dispatcher (session-summary enforcement, orphan-skill scan,
agent-lint, ADR-gap check), the ``PreCompact`` summary gate and the update check.
``CLAUDE.md`` § Agent Memory System calls that dispatcher the reason three of its
rules are "enforced automatically after installation"; without it they are
enforced nowhere.

``settings.json`` is the project's own file and may be committed, so this module
merges into it and **never** rewrites it wholesale: it adds the entries it owns,
replaces a stale v2 path with the current one, and leaves every other key alone.
``unwire`` removes only the entries it recognises.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from . import jsonio, project
from .errors import EnvError

SETTINGS_FILE = Path(".claude") / "settings.json"

#: `env -u BASH_ENV -u ENV` keeps a WSL login shell from injecting
#: /etc/bash.bashrc noise into hook output — carried over from install.sh:676.
ENV_PREFIX = "env -u BASH_ENV -u ENV"

#: Paths resolve through the in-project `scripts` link, so they keep working after
#: an update re-points it and they stay relative, which a committed
#: settings.json requires. The same path a v2 install wrote, so the file does not
#: differ between the two layouts.
HOOK_DIR = "{}/scripts/hooks".format(project.PROJECT_DIR)
#: What binds wrote while the project carried one `core` pointer to the whole
#: version. Still recognised as ours, so a sync rewrites such an entry in place
#: instead of appending a second one beside it.
CORE_POINTER_HOOK_DIR = "{}/core/scripts/hooks".format(project.PROJECT_DIR)
#: What a pre-v2.1.0 install wrote. Recognised so a migration rewrites it in place:
#: left alone, each event would run a dispatcher from a tree the migration just
#: moved into quarantine, beside the new one.
PRE_ROOT_HOOK_DIR = "{}/scripts/hooks".format(project.PRE_ROOT_DIR)
OWNED_HOOK_DIRS = (HOOK_DIR, CORE_POINTER_HOOK_DIR, PRE_ROOT_HOOK_DIR)

EVENTS = (
    ("PreToolUse", "pre-tool-use.sh"),
    ("Stop", "stop.sh"),
    ("SessionStart", "session-start.sh"),
    ("PreCompact", "pre-compact.sh"),
    ("PostToolUse", "post-tool-use.sh"),
    ("SessionEnd", "session-end.sh"),
    ("UserPromptSubmit", "user-prompt-submit.sh"),
    # A subagent launch that failed never reaches PostToolUse; the same dispatcher retires it.
    ("PostToolUseFailure", "post-tool-use.sh"),
)

#: Matchers for the events that filter by tool name. `PreToolUse` sees every tool
#: (its sub-scripts filter cheaply themselves); `PostToolUse` is narrowed to the todo
#: tools and the subagent tool (`Agent`, `Task` in older builds — where a review agent's
#: report comes back) so no other tool call forks the dispatcher at all; `PostToolUseFailure` is
#: narrowed to the subagent tool for the same reason.
MATCHERS = {
    "PreToolUse": ".*",
    "PostToolUse": "TodoWrite|TaskCreate|TaskUpdate|Agent|Task",
    "PostToolUseFailure": "Agent|Task",
}


#: Matchers a previous release of ours wrote, per event. Only these are rewritten to the current
#: one; any other matcher on our entry is the user's own choice and is left alone.
PREVIOUS_MATCHERS = {
    "PostToolUse": ("TodoWrite|TaskCreate|TaskUpdate",),
}


#: The provider runs a hook in the session's CURRENT directory, and a Claude Code session keeps
#: the directory a Bash call `cd`-ed into — a relative path then names nothing, and every hook
#: (credential guard included) fails as a "non-blocking error" nobody reads. So the command first
#: walks up from there to the nearest directory holding the hooks — the project root, or a
#: worktree's own root when it has one, or a sub-project's own install even when Claude Code was
#: opened above it — and falls back to the root Claude Code was opened at. The logical path is
#: walked first, then the physical one, for a directory entered through a symlink; a step that
#: does not shorten the path (no `/` left) ends the walk instead of spinning.
#: Every hook already assumes it runs there. `bash -c` rather than bare shell syntax because the
#: hook shell is not ours to choose, and `env -u` comes before it so bash does not source
#: `BASH_ENV` either. `exec bash <script>`, like Codex's command, so a copy that lost its mode
#: bits still runs. Still relative: settings.json is committed. The walk is the same text as
#: `install-codex.sh` `cmd()`; `scripts/install.sh` `_hook_cmd` writes this exact command.
ROOT_WALK = (
    'for d in "$PWD" "$(pwd -P)"; do '
    'while [ -n "$d" ] && [ ! -d "$d/{hooks}" ]; do p=${{d%/*}}; [ "$p" = "$d" ] && p=; d=$p; done; '
    '[ -n "$d" ] && break; done; '
    'cd "${{d:-{fallback}}}" && exec bash {hooks}/{script}'
)


def command_for(script):
    body = ROOT_WALK.format(hooks=HOOK_DIR, fallback="${CLAUDE_PROJECT_DIR:-.}", script=script)
    return "{} bash -c '{}'".format(ENV_PREFIX, body)


def _is_our_command(command, script):
    """True when a hook command runs our dispatcher for ``script``, in any layout we have shipped."""
    return script in command and any(owned in command for owned in OWNED_HOOK_DIRS)


def _is_devteam_entry(entry, script):
    """True when this settings entry is one we own, in any layout we have shipped."""
    if not isinstance(entry, dict):
        return False
    return any(
        isinstance(hook, dict) and _is_our_command(hook.get("command") or "", script)
        for hook in entry.get("hooks", []) or []
    )


def _warn(emitter, message):
    if emitter is not None:
        emitter.warn(message)
    else:
        print("-> NOTE: " + message, file=sys.stderr)


def wire(project_root, emitter=None):
    """Ensure every dispatcher in :data:`EVENTS` are registered. Returns manifest records.

    The returned records carry ``kind: "settings"``; ``unbind`` routes them to
    :func:`unwire` instead of removing a file the project owns.
    """
    settings_path = Path(project_root) / SETTINGS_FILE
    data = jsonio.read_json(settings_path, default=None)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise EnvError(
            "{} is not a JSON object".format(settings_path),
            hint="Fix the file by hand; dev-team-agents will not overwrite it.",
        )

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise EnvError("{}: 'hooks' must be an object".format(settings_path))

    changed = False
    wired = []
    for event, script in EVENTS:
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            raise EnvError("{}: hooks.{} must be a list".format(settings_path, event))
        desired = {"hooks": [{"type": "command", "command": command_for(script)}]}
        if event in MATCHERS:
            desired["matcher"] = MATCHERS[event]

        existing_index = next(
            (i for i, entry in enumerate(entries) if _is_devteam_entry(entry, script)), None
        )
        if existing_index is None:
            entries.append(desired)
            changed = True
        else:
            # A v2 entry pointing at the pre-pointer path, or a stale variant: rewrite it in
            # place rather than adding a second one. Only OUR hook's command changes — a sibling
            # hook the user put in the same entry, and any key on ours (`timeout`), are kept,
            # and so is a matcher we never shipped.
            current = entries[existing_index]
            merged = copy.deepcopy(current)
            for hook in merged.get("hooks") or []:
                if isinstance(hook, dict) and _is_our_command(hook.get("command") or "", script):
                    hook["command"] = command_for(script)
                    hook.setdefault("type", "command")
            has, wanted = current.get("matcher"), desired.get("matcher")
            if has != wanted:
                if has in PREVIOUS_MATCHERS.get(event, ()):
                    merged["matcher"] = wanted
                else:
                    _warn(
                        emitter,
                        "{} matcher {!r} left as is; dev-team-agents needs {!r}".format(event, has, wanted),
                    )
            if current != merged:
                entries[existing_index] = merged
                changed = True
        wired.append(event)

    # v2 set this so Claude Code does not add a Co-Authored-By trailer. Only fill
    # it when absent — a project that deliberately set `true` keeps its choice.
    if "includeCoAuthoredBy" not in data:
        data["includeCoAuthoredBy"] = False
        changed = True

    if changed:
        jsonio.write_json_atomic(settings_path, data, mode=0o644)
    elif emitter is not None:
        emitter.warn("hooks already registered in {}".format(SETTINGS_FILE))

    # `.as_posix()`: see `project._write_pointer` — the manifest's "path" values
    # are forward-slash everywhere else.
    return [{"path": SETTINGS_FILE.as_posix(), "kind": "settings", "events": wired}]


def unwire(project_root):
    """Remove only the entries :func:`wire` owns, keeping the rest of the file."""
    settings_path = Path(project_root) / SETTINGS_FILE
    data = jsonio.read_json(settings_path, default=None)
    if not isinstance(data, dict):
        return []
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []

    removed = []
    for event, script in EVENTS:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        kept = [entry for entry in entries if not _is_devteam_entry(entry, script)]
        if len(kept) != len(entries):
            removed.append(event)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop("hooks", None)

    if removed:
        jsonio.write_json_atomic(settings_path, data, mode=0o644)
    return removed


def registered_events(project_root):
    """Events whose dispatcher is currently registered, for ``doctor``."""
    settings_path = Path(project_root) / SETTINGS_FILE
    data = jsonio.read_json(settings_path, default=None)
    if not isinstance(data, dict):
        return []
    hooks_section = data.get("hooks")
    if not isinstance(hooks_section, dict):
        return []
    found = []
    for event, script in EVENTS:
        entries = hooks_section.get(event)
        if not isinstance(entries, list):
            continue
        if any(_is_devteam_entry(entry, script) for entry in entries):
            found.append(event)
    return found
