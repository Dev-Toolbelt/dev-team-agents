"""Which commands a new user is shown, and which ones their own use reveals (ADR-0030 section 5).

Three facts live here and nowhere else:

* the featured set, read from ``scripts/lib/commands.json`` (``featured: true``);
* the usage record ``command-usage.json`` (a machine-local record, see
  ``paths.MACHINE_LOCAL_RECORDS``): ``{"<command>": {"count": n, "last_used": iso8601}}``;
* the reveal rule: the ``related`` commands of the commands already used, minus the featured
  ones, minus the ones already used, ordered by the usage count of their source, then by their place in the source's own list.

Nothing here hides or removes a command: every command stays installed on every provider.
The session-start banner (``scripts/hooks/session-start.sh``) and the usage hook
(``scripts/hooks/user-prompt-submit/03-command-usage.sh``) are thin shells around this module.

A hook never disturbs the provider, so every function that a hook calls swallows its own
failures (:func:`record`, :func:`hook_main`, :func:`banner`) and returns a harmless value.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import jsonio, lock

USAGE_FILE = "command-usage.json"

#: The most "Also try:" commands the banner ever shows.
ALSO_TRY_LIMIT = 3

_LIB_DIR = Path(__file__).resolve().parent.parent

#: A command invocation at the start of a prompt: `/devteam:<name>` (Claude Code, opencode)
#: or `$devteam-<name>` (Codex). Whether `<name>` is a real command is decided against
#: commands.json, not by this pattern.
_INVOCATION_RE = re.compile(r"^\s*(?:/devteam:|\$devteam-)([a-z][a-z-]*)(?=\s|$)")

#: Env markers a provider's own process sets, strongest first. `DEVTEAM_PROVIDER` is the
#: explicit override (the opencode plugin sets it); Claude Code exports `CLAUDECODE`.
_ENV_PROVIDER = (("DEVTEAM_PROVIDER", None), ("CLAUDECODE", "claude"), ("CLAUDE_PROJECT_DIR", "claude"))

#: What a project carries for each provider, relative to its root. One entry per provider in
#: `providers.ALL_PROVIDERS` (tests/test_command_usage.py fails when one is missing).
_INSTALLED_MARKERS = {
    "claude": (".claude/commands/devteam",),
    "opencode": (".opencode/plugins/dev-team-agents.ts",),
    "codex": (".codex/hooks.json",),
}


def _load_json(name, lib_dir=None):
    path = Path(lib_dir or _LIB_DIR) / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_commands(lib_dir=None):
    """``{name: metadata}`` from commands.json, in file order; ``{}`` when unreadable."""
    data = _load_json("commands.json", lib_dir)
    commands = data.get("commands") if isinstance(data, dict) else None
    return commands if isinstance(commands, dict) else {}


def featured(commands):
    """The featured command names, in the file's order."""
    return [name for name, meta in commands.items() if isinstance(meta, dict) and meta.get("featured") is True]


def related(commands, name):
    meta = commands.get(name)
    rel = meta.get("related") if isinstance(meta, dict) else None
    return [item for item in rel if isinstance(item, str)] if isinstance(rel, list) else []


def exposed_name(provider, name, lib_dir=None):
    """How a provider spells the command: ``/devteam:plan`` or ``$devteam-plan``."""
    template = (
        ((_load_json("command-map.json", lib_dir).get("providers") or {}).get(provider) or {}).get(
            "exposed_name_template"
        )
        or "/devteam:{name}"
    )
    return template.format(name=name)


# ── the usage record ─────────────────────────────────────────────────────────


def usage_path(state_dir):
    return Path(state_dir) / USAGE_FILE


def read_usage(state_dir):
    """The record as a dict; ``{}`` for an absent, malformed or wrongly shaped file."""
    try:
        data = jsonio.read_json(usage_path(state_dir), default={})
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        name: entry
        for name, entry in data.items()
        if isinstance(entry, dict) and isinstance(entry.get("count"), int) and entry["count"] > 0
    }


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record(state_dir, name, now=None):
    """Count one use of ``name``. Locked, atomic; ``True`` when written, never raises.

    A record that is not valid JSON is left alone (the store rule: never overwrite what cannot
    be read), so a corrupt file stops recording instead of being destroyed.
    """
    path = usage_path(state_dir)
    try:
        with lock.Lock(str(path)[: -len(".json")] + ".lock", timeout=5.0, stale_after=30.0):
            data = jsonio.read_json(path, default={})
            if not isinstance(data, dict):
                return False
            entry = data.get(name) if isinstance(data.get(name), dict) else {}
            count = entry.get("count") if isinstance(entry.get("count"), int) else 0
            data[name] = {"count": count + 1, "last_used": now or _now()}
            jsonio.write_json_atomic(path, data)
        return True
    except Exception:
        return False


def command_in_prompt(prompt, commands):
    """The command a prompt opens with, when it is one of ``commands``; else ``None``."""
    if not isinstance(prompt, str):
        return None
    match = _INVOCATION_RE.match(prompt)
    if match and match.group(1) in commands:
        return match.group(1)
    return None


def revealed(commands, usage, limit=ALSO_TRY_LIMIT):
    """Related commands of the used ones, minus featured, minus used, by their source's count."""
    skip = set(featured(commands)) | set(usage)
    # Per target: the source's usage count (higher first), then its place in that source's own
    # `related` list (the curated priority), then the command name so the order is total.
    best = {}
    for source, entry in usage.items():
        if source not in commands:
            continue
        for position, target in enumerate(related(commands, source)):
            if target in commands and target not in skip:
                rank = (-entry["count"], position, source)
                if target not in best or rank < best[target]:
                    best[target] = rank
    return sorted(best, key=lambda target: (best[target], target))[:limit]


# ── provider detection and the banner ────────────────────────────────────────


def detect_provider(project_root, environ=None):
    """The provider whose syntax the banner should use.

    The invoking provider's own env marker wins. Failing that, the providers the project carries:
    a lone one is the answer; with several, Claude Code's marker being absent rules it out when
    another is installed, and anything still ambiguous falls back to the first in
    ``ALL_PROVIDERS`` order (Claude Code).
    """
    env = os.environ if environ is None else environ
    for key, provider in _ENV_PROVIDER:
        value = env.get(key)
        if value:
            chosen = provider or value.strip().lower()
            if chosen in _INSTALLED_MARKERS:
                return chosen
    root = Path(project_root)
    present = [p for p, marks in _INSTALLED_MARKERS.items() if any((root / m).exists() for m in marks)]
    others = [p for p in present if p != "claude"]
    if others:
        return others[0]
    return "claude"


def banner_lines(project_root, state_dir, environ=None, lib_dir=None):
    """The compact "Start with:" (and, once earned, "Also try:") lines."""
    commands = load_commands(lib_dir)
    names = featured(commands)
    if not names:
        return []
    provider = detect_provider(project_root, environ)
    lines = ["Start with: " + " ".join(exposed_name(provider, n, lib_dir) for n in names)]
    more = revealed(commands, read_usage(state_dir))
    if more:
        lines.append("Also try: " + " ".join(exposed_name(provider, n, lib_dir) for n in more))
    return lines


def banner(project_root, state_dir):
    """Print the banner lines; print nothing on any failure."""
    try:
        for line in banner_lines(project_root, state_dir):
            print(line)
    except Exception:
        return


def hook_main(state_dir, stream):
    """UserPromptSubmit entry: record the command the payload's prompt opens with. Never raises."""
    try:
        payload = json.load(stream)
        prompt = payload.get("prompt") if isinstance(payload, dict) else None
        name = command_in_prompt(prompt, load_commands())
        if name:
            record(state_dir, name)
    except Exception:
        return
