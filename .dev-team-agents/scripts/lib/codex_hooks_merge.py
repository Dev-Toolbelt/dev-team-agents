#!/usr/bin/env python3
"""Merge the dev-team-agents hook entries into a project's Codex ``hooks.json``.

Run by ``scripts/install-codex.sh``:

    codex_hooks_merge.py <hooks.json> <hooks-dir> [--check]

``--check`` only validates the existing file. Exit codes: 0 ok, 4 the file is not a shape
this installer can merge into (it is left untouched and named on stderr — the same code the
ownership guard uses for a conflict), 1 anything else.
"""

import json
import os
import sys
import tempfile

# The Git Bash rules (never WSL's System32 launcher) live in the CLI package beside this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devteam.shells import find_git_bash, is_windows  # noqa: E402,F401  (find_git_bash is part of this module's API)

CONFLICT_EXIT = 4

# Per Codex spec (developers.openai.com/codex/hooks), the shape is:
#   { "hooks": { "<Event>": [ { "matcher": "...", "hooks": [ { type, command, ... } ] } ] } }
# — an OBJECT keyed by event name, each value an array of matcher groups.
# Each hook `command` is a STRING, not an array.
MANAGED_EVENTS = (
    "SessionStart", "PreToolUse", "PostToolUse", "UserPromptSubmit", "PreCompact", "Stop", "SessionEnd",
)
MANAGED_MARKER = "_dev_team_agents_managed"

SCRIPTS = {
    "SessionStart": "session-start.sh",
    "PreToolUse": "pre-tool-use.sh",
    "PostToolUse": "post-tool-use.sh",
    "UserPromptSubmit": "user-prompt-submit.sh",
    "PreCompact": "pre-compact.sh",
    "Stop": "stop.sh",
    "SessionEnd": "session-end.sh",
}

# PostToolUse is narrowed to `spawn_agent` (its response names the agent id a later wait settles),
# `wait_agent` (the agents' final states, and a review agent's report) and `close_agent` (an agent
# closed before it reported), `Bash` (an `exec_command` that finished: a PR/MR creation or merge is
# confirmed from its output) and the pull-request MCP tools — the only Codex tools
# whose result the task board reads. Codex feeds the todo list from PreToolUse (`update_plan`).
MATCHERS = {"PostToolUse": ".*(wait_agent|spawn_agent|close_agent|Bash|mcp__.*(create_pull_request|merge_pull_request))"}

# Codex runs a hook through the user's own shell (`$SHELL -lc`) in the session's working
# directory, which is not the project root when Codex was started in a subdirectory: a relative
# path then names nothing and every hook fails unseen. So the command walks up from there to the
# nearest directory holding the hooks — the same walk as `scripts/lib/devteam/hooks.py`
# (ROOT_WALK), with the working directory as its fallback. `bash -c '…'` because that shell may
# be zsh or fish; single quotes are literal in all of them, and `env -u BASH_ENV -u ENV` (the
# prefix hooks.py puts on the Claude command) stops a WSL login shell sourcing bashrc into the
# hook's output.
ROOT_WALK = (
    'for d in "$PWD" "$(pwd -P)"; do '
    'while [ -n "$d" ] && [ ! -d "$d/{hooks}" ] && [ ! -f "$d/{pointer}" ]; do p=${{d%/*}}; [ "$p" = "$d" ] && p=; d=$p; done; '
    '[ -n "$d" ] && break; done; '
    'cd "${{d:-.}}" && {{ [ -d {hooks} ] || [ ! -f {pointer} ] || {{ c=$(cat {pointer}) && exec bash "$c/versions/$(cat "$c/current")/scripts/hooks/lib/self-heal.sh" {script}; }}; exec bash {hooks}/{script}; }}'
)
ENV_PREFIX = "env -u BASH_ENV -u ENV"

# Windows: Codex runs the command through `cmd.exe /C`, where single quotes do not quote and a
# bare `bash` resolves to WSL's System32\bash.exe (or nothing). So the same walk is wrapped as
# `"<absolute Git Bash>" -c "<walk>"`, with the walk's own double quotes backslash-escaped.
# The whole command gets one more pair of quotes: `cmd /C` strips the first and last quote of a
# command line that holds more than two, which would otherwise eat the quotes around the path.


def core_pointer(hooks_dir):
    """The `core-dir` pointer beside the hooks: `.dev-team-agents/scripts/hooks` → `.dev-team-agents/core-dir`."""
    base = hooks_dir[: -len("/scripts/hooks")] if hooks_dir.endswith("/scripts/hooks") else ".dev-team-agents"
    return base + "/core-dir"


def unix_command(hooks_dir, script):
    walk = ROOT_WALK.format(hooks=hooks_dir, pointer=core_pointer(hooks_dir), script=script)
    return "{} bash -c '{}'".format(ENV_PREFIX, walk)


def windows_command(hooks_dir, script, bash_path):
    walk = ROOT_WALK.format(hooks=hooks_dir, pointer=core_pointer(hooks_dir), script=script)
    return '""{}" -c "{}""'.format(bash_path, walk.replace('"', '\\"'))


def command_for(hooks_dir, script, windows=None, bash_path=None):
    windows = is_windows() if windows is None else windows
    if not windows:
        return unix_command(hooks_dir, script)
    return windows_command(hooks_dir, script, bash_path or "bash")


def managed_groups(hooks_dir, windows=None, bash_path=None):
    # Each managed hook carries a statusMessage with the MANAGED_MARKER so we can
    # idempotently strip our own entries on re-install without touching user hooks.
    # (Codex spec does NOT define a per-hook id field — statusMessage is the
    # documented human-readable surface; we encode our marker there.)
    return {
        event: [
            {
                "matcher": MATCHERS.get(event, "*"),
                "hooks": [
                    {
                        "type": "command",
                        "command": command_for(hooks_dir, SCRIPTS[event], windows, bash_path),
                        "statusMessage": "dev-team-agents {} hook {}".format(event.lower(), MANAGED_MARKER),
                    }
                ],
            }
        ]
        for event in MANAGED_EVENTS
    }


class Conflict(Exception):
    pass


def load_existing(hooks_file):
    """The parsed file, ``{"hooks": {}}`` when absent. Raises ``Conflict`` for anything unmergeable."""
    if not os.path.exists(hooks_file):
        return {"hooks": {}}
    try:
        with open(hooks_file, encoding="utf-8-sig") as handle:
            existing = json.load(handle)
    except (OSError, ValueError) as exc:
        raise Conflict("cannot read it as JSON ({})".format(exc))
    if not isinstance(existing, dict):
        raise Conflict("the top level is not a JSON object")
    hooks_obj = existing.setdefault("hooks", {})
    if not isinstance(hooks_obj, dict):
        raise Conflict('"hooks" is not an object keyed by event name')
    for event in MANAGED_EVENTS:
        if event in hooks_obj and not isinstance(hooks_obj[event], list):
            raise Conflict('"hooks.{}" is not an array'.format(event))
    return existing


def merge(existing, groups):
    hooks_obj = existing["hooks"]
    # Strip any previously-managed entries (idempotent refresh) — detect ours by
    # the encoded marker in statusMessage.
    for event in list(hooks_obj.keys()):
        entries = hooks_obj[event]
        if not isinstance(entries, list):
            continue
        kept = []
        for grp in entries:
            hook_list = grp.get("hooks", []) if isinstance(grp, dict) else []
            is_managed = any(
                isinstance(h, dict) and MANAGED_MARKER in (h.get("statusMessage", "") or "")
                for h in hook_list
            )
            if not is_managed:
                kept.append(grp)
        if kept:
            hooks_obj[event] = kept
        else:
            hooks_obj.pop(event, None)
    # Merge managed groups into existing (append into each event's array).
    for event, event_groups in groups.items():
        hooks_obj.setdefault(event, []).extend(event_groups)
    return existing


def write_atomic(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".hooks.json.", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv):
    args = [a for a in argv[1:] if a != "--check"]
    check_only = "--check" in argv[1:]
    if len(args) != 2:
        sys.stderr.write("usage: codex_hooks_merge.py <hooks.json> <hooks-dir> [--check]\n")
        return 1
    hooks_file, hooks_dir = args
    try:
        existing = load_existing(hooks_file)
    except Conflict as exc:
        sys.stderr.write(
            "install-codex: ERROR: {} {}; it was left untouched.\n"
            "  Fix or move it and re-run — dev-team-agents never rewrites a hooks file it cannot merge into.\n".format(
                hooks_file, exc
            )
        )
        return CONFLICT_EXIT
    if check_only:
        return 0
    windows = is_windows()
    bash_path = None
    if windows:
        bash_path = find_git_bash()
        if bash_path is None:
            sys.stderr.write(
                "install-codex: WARNING: no Git Bash found (looked on PATH, skipping System32/WindowsApps, "
                "and in the Git for Windows default folders); hooks will call a bare `bash`.\n"
            )
    merged = merge(existing, managed_groups(hooks_dir, windows, bash_path))
    write_atomic(hooks_file, merged)
    try:
        shown = os.path.relpath(hooks_file)
    except ValueError:  # Windows: the file and the working directory are on different drives
        shown = hooks_file
    print("  + wrote {} managed hook events to {}".format(len(MANAGED_EVENTS), shown))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
