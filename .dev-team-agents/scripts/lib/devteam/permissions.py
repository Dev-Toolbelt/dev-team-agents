"""The provider-native "ask" rules that put a write through `integration call` before the user.

ADR-0031 left one gap: `--allow-write` is passed by the agent it guards. ADR-0032 closes it
with each provider's own permission mechanism, a prompt the agent cannot answer itself:

| Provider | Where | Matches |
|---|---|---|
| claude | ``.claude/settings.json`` → ``permissions.ask`` | wildcard anywhere |
| opencode | ``.opencode/opencode.json`` → ``permission.bash`` = ``"ask"`` | wildcard, last match wins |
| codex | ``.codex/rules/devteam.rules`` → ``prefix_rule(decision="prompt")`` | prefix only |

Codex matches only a prefix, so every rule keys on the method as the fourth word. The CLI
refuses a write in any other form (``integrations.is_canonical_call``), which is what makes
that prefix reliable. Claude and opencode also match ``--allow-write`` anywhere, as a second
net.

This module is the one source of the rule text. ``hooks.py`` merges the Claude rules during
bind; the delegated installers reach the others through ``scripts/lib/permission_rules.py``.
Each merge adds or removes only entries whose text is one of ours, and never rewrites a
file it cannot parse. These rules are a prompt in the agent's own tool, not a sandbox: a
command spelled another way (``bash -c``, the script by path) walks past them, which the
providers' own documentation says of every such rule.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .errors import EnvError

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
CALL_PREFIX = "devteam integration call"
ALLOW_WRITE_FLAG = "--allow-write"


def command_patterns():
    """The glob patterns Claude and opencode share, in a stable order."""
    patterns = ["{} * {} *".format(CALL_PREFIX, method) for method in WRITE_METHODS]
    patterns.append("{} * {}".format(CALL_PREFIX, ALLOW_WRITE_FLAG))
    patterns.append("{} * {} *".format(CALL_PREFIX, ALLOW_WRITE_FLAG))
    return patterns


# ── claude ────────────────────────────────────────────────────────────────────

#: Every ask rule we write into `.claude/settings.json`. Recognised by exact text.
CLAUDE_ASK_RULES = tuple("Bash({})".format(pattern) for pattern in command_patterns())
#: Rules a previous release wrote; removed and replaced, never left beside the new ones.
PREVIOUS_CLAUDE_ASK_RULES = ()


def merge_claude(data):
    """Add our ask rules to a parsed `settings.json` object. Returns True when it changed.

    Raises ``EnvError`` when ``permissions`` or ``permissions.ask`` has a shape we cannot
    merge into; the caller leaves the file untouched.
    """
    permissions = data.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise EnvError("'permissions' must be an object", hint="Fix the file by hand; it was not changed.")
    ask = permissions.setdefault("ask", [])
    if not isinstance(ask, list):
        raise EnvError("'permissions.ask' must be a list", hint="Fix the file by hand; it was not changed.")
    kept = [rule for rule in ask if rule not in PREVIOUS_CLAUDE_ASK_RULES]
    changed = len(kept) != len(ask)
    for rule in CLAUDE_ASK_RULES:
        if rule not in kept:
            kept.append(rule)
            changed = True
    permissions["ask"] = kept
    return changed


def unmerge_claude(data):
    """Remove our ask rules from a parsed `settings.json` object. Returns how many went."""
    permissions = data.get("permissions") if isinstance(data, dict) else None
    if not isinstance(permissions, dict) or not isinstance(permissions.get("ask"), list):
        return 0
    ours = set(CLAUDE_ASK_RULES) | set(PREVIOUS_CLAUDE_ASK_RULES)
    ask = permissions["ask"]
    kept = [rule for rule in ask if rule not in ours]
    removed = len(ask) - len(kept)
    if kept:
        permissions["ask"] = kept
    else:
        permissions.pop("ask")
    if not permissions:
        data.pop("permissions")
    return removed


def claude_rules_present(data):
    """Our ask rules missing from a parsed `settings.json` object (empty when all are there)."""
    permissions = data.get("permissions") if isinstance(data, dict) else None
    ask = permissions.get("ask") if isinstance(permissions, dict) else None
    ask = ask if isinstance(ask, list) else []
    return [rule for rule in CLAUDE_ASK_RULES if rule not in ask]


# ── opencode ──────────────────────────────────────────────────────────────────

OPENCODE_ASK_RULES = tuple(command_patterns())
PREVIOUS_OPENCODE_ASK_RULES = ()


def merge_opencode(data):
    """Add our rules to a parsed opencode config, as the LAST ``permission.bash`` keys.

    opencode evaluates bash patterns with the last match winning, so a broader rule the
    user listed (``"devteam *": "allow"``) must come before ours. Our keys are removed and
    re-appended on every run, which keeps them last. A ``permission.bash`` given as one
    action string is turned into its object form (``{"*": <action>}``), which means the
    same thing. Returns True when the object changed.
    """
    permission = data.setdefault("permission", {})
    if not isinstance(permission, dict):
        raise EnvError("'permission' must be an object", hint="Fix the file by hand; it was not changed.")
    original = permission.get("bash", {})
    bash = {"*": original} if isinstance(original, str) else original
    if not isinstance(bash, dict):
        raise EnvError("'permission.bash' must be an object or a string", hint="Fix the file by hand; it was not changed.")
    ours = set(OPENCODE_ASK_RULES) | set(PREVIOUS_OPENCODE_ASK_RULES)
    rebuilt = {key: value for key, value in bash.items() if key not in ours}
    for rule in OPENCODE_ASK_RULES:
        rebuilt[rule] = "ask"
    unchanged = isinstance(original, dict) and list(original.items()) == list(rebuilt.items())
    permission["bash"] = rebuilt
    return not unchanged


def unmerge_opencode(data):
    """Remove our ``permission.bash`` keys. Returns how many went."""
    permission = data.get("permission") if isinstance(data, dict) else None
    bash = permission.get("bash") if isinstance(permission, dict) else None
    if not isinstance(bash, dict):
        return 0
    ours = set(OPENCODE_ASK_RULES) | set(PREVIOUS_OPENCODE_ASK_RULES)
    removed = [key for key in bash if key in ours]
    for key in removed:
        bash.pop(key)
    if not bash:
        permission.pop("bash")
    if not permission:
        data.pop("permission")
    return len(removed)


def opencode_findings(data):
    """Why our opencode rules would not prompt, as short sentences (empty when they would)."""
    problems = []
    permission = data.get("permission") if isinstance(data, dict) else None
    bash = permission.get("bash") if isinstance(permission, dict) else None
    keys = list(bash) if isinstance(bash, dict) else []
    missing = [rule for rule in OPENCODE_ASK_RULES if bash is None or not isinstance(bash, dict) or bash.get(rule) != "ask"]
    if missing:
        problems.append("{} of the ask rules are missing".format(len(missing)))
    elif keys[-len(OPENCODE_ASK_RULES):] != list(OPENCODE_ASK_RULES):
        problems.append("a permission.bash rule listed after ours can override them (the last match wins)")
    agents = data.get("agent") if isinstance(data, dict) else None
    if isinstance(agents, dict):
        for name, agent in agents.items():
            agent_permission = agent.get("permission") if isinstance(agent, dict) else None
            if isinstance(agent_permission, dict) and "bash" in agent_permission:
                problems.append("agent {!r} sets its own permission.bash, which takes precedence".format(name))
    return problems


# ── codex ─────────────────────────────────────────────────────────────────────

CODEX_RULES_FILE = ".codex/rules/devteam.rules"
CODEX_RULES_MARKER = "# Managed by dev-team-agents (ADR-0032)."


def _starlark(value):
    return json.dumps(value)


def codex_rules(callable_names):
    """The whole `devteam.rules` file for the given integration names."""
    names = sorted(callable_names)
    lines = [
        CODEX_RULES_MARKER + " Rewritten on every install and sync: edits here are lost.",
        "# A write through `devteam integration call` asks the user first. Reads are not matched.",
        "",
    ]
    for name in names:
        lines += [
            "prefix_rule(",
            "    pattern = {},".format(
                _starlark(["devteam", "integration", "call", name, list(WRITE_METHODS)])
            ),
            '    decision = "prompt",',
            '    justification = "A write to the {} API through dev-team-agents needs your approval.",'.format(name),
            "    match = [{}],".format(
                ", ".join(
                    _starlark("devteam integration call {} {} /example --allow-write".format(name, method))
                    for method in WRITE_METHODS
                )
            ),
            "    not_match = [{}],".format(_starlark("devteam integration call {} GET /example".format(name))),
            ")",
            "",
        ]
    return "\n".join(lines)


def codex_rules_current(project_root, callable_names):
    """True when the project's rules file holds exactly what :func:`codex_rules` renders."""
    path = Path(project_root) / CODEX_RULES_FILE
    try:
        return path.read_text(encoding="utf-8") == codex_rules(callable_names)
    except OSError:
        return False


def codex_config_dir(home=None):
    """Codex's user config directory: ``<home>/.codex`` for an explicit ``home``, else ``$CODEX_HOME``,
    else ``~/.codex``. The one resolver every read of the user's Codex config goes through."""
    if home:
        return Path(home) / ".codex"
    return Path(os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex"))


def codex_project_trusted(project_root, home=None):
    """True / False when the user's Codex ``config.toml`` says, ``None`` when it cannot tell.

    Codex loads project rules only for a trusted project. Read with a regex rather than a
    TOML parser: ``tomllib`` is not in the Python 3.9 this CLI supports.
    """
    config = codex_config_dir(home) / "config.toml"
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return None
    return _trusted_in(text, project_root)


def _trusted_in(text, project_root):
    """Whether one Codex config's text marks ``project_root`` as trusted."""
    root = str(Path(project_root).resolve())
    header = re.compile(r'^\[projects\.(?:"([^"]+)"|\'([^\']+)\')\]\s*$', re.M)
    for match in header.finditer(text):
        path = match.group(1) or match.group(2)
        if path.rstrip("/") != root.rstrip("/"):
            continue
        body = text[match.end():]
        nxt = re.search(r"^\[", body, re.M)
        body = body[: nxt.start()] if nxt else body
        trust = re.search(r'^\s*trust_level\s*=\s*"([^"]*)"', body, re.M)
        return bool(trust) and trust.group(1) == "trusted"
    return False


_TOML_NOISE = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'|#.*')


def _toml_sections(text):
    """``[(table, body)]`` of a TOML text: ``""`` for the lines before the first header.

    An array of tables or a quoted header is listed as ``None``: no key looked up here lives there.
    A line that opens with ``[`` while a multi-line array value is still open (``  [1, 2],``) is a
    value, never a header.
    """
    simple = re.compile(r"^[ \t]*\[[ \t]*([A-Za-z0-9_-]+(?:[ \t]*\.[ \t]*[A-Za-z0-9_-]+)*)[ \t]*\][ \t]*(?:#.*)?$")
    sections, table, body, depth, fence = [], "", [], 0, None
    for line in text.splitlines(True):
        if fence:
            # Inside a multi-line string nothing is a header or a bracket, until its closing quotes.
            body.append(line)
            if fence in line:
                fence = None
            continue
        if depth == 0 and line.lstrip(" \t").startswith("["):
            sections.append((table, "".join(body)))
            name = simple.match(line.rstrip("\r\n"))
            table = re.sub(r"[ \t]", "", name.group(1)) if name else None
            body = []
            continue
        body.append(line)
        opened = next((d for d in ('"""', "'''") if line.count(d) % 2), None)
        if opened:
            line, fence = line[:line.index(opened)], opened
        bare = _TOML_NOISE.sub("", line)
        depth = max(0, depth + bare.count("[") - bare.count("]"))
    sections.append((table, "".join(body)))
    return sections


def _toml_bool(text, dotted):
    """True when the TOML ``text`` sets the boolean at ``dotted`` to true, else False (see :func:`_toml_value`)."""
    return _toml_value(text, dotted) is True


def _toml_value(text, dotted):
    """The boolean the TOML ``text`` sets at ``dotted`` (``a.b.c``): True, False, or ``None`` when it sets none.

    Finds it in a ``[a.b]`` table, as a dotted key (``b.c = true`` under ``[a]``, ``a.b.c`` at the
    top), or in an inline table (``b = { c = true }``). Regex-based: ``tomllib`` is not in the
    Python 3.9 this CLI supports.
    """
    parts = dotted.split(".")
    for table, body in _toml_sections(text):
        if table is None:
            continue
        prefix = table.split(".") if table else []
        rest = parts[len(prefix):]
        if parts[:len(prefix)] != prefix or not rest:
            continue
        key = r"\s*\.\s*".join(re.escape(p) for p in rest)
        found = re.search(r"^\s*{}\s*=\s*(true|false)\b".format(key), body, re.M)
        if found:
            return found.group(1) == "true"
        if len(rest) > 1:
            owner = r"\s*\.\s*".join(re.escape(p) for p in rest[:-1])
            inline = re.search(r"^\s*{}\s*=\s*\{{([^}}]*)\}}".format(owner), body, re.M)
            value = inline and re.search(r"(?:^|[\s,]){}\s*=\s*(true|false)\b".format(re.escape(rest[-1])), inline.group(1))
            if value:
                return value.group(1) == "true"
    return None


def codex_default_mode_questions_enabled(home=None):
    """Whether ``[features] default_mode_request_user_input = true`` is set in the user's Codex ``config.toml``.

    True when enabled, False when the file is readable but the key is absent or false,
    ``None`` when the file cannot be read. devteam only reads this file; it never writes it.
    """
    config = codex_config_dir(home) / "config.toml"
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return None
    return _toml_bool(text, "features.default_mode_request_user_input")


def codex_update_plan_enabled(project_root=None, home=None):
    """Whether Codex's ``update_plan`` tool is switched on (``[tools.update_plan] enabled = true``).

    Looks in the user config (:func:`codex_config_dir`) and in ``<project_root>/.codex/config.toml``
    when Codex trusts the project (it ignores the file otherwise). The project's own setting overrides
    the user's, so a project ``enabled = false`` wins over a user ``true``; a file that sets nothing
    defers to the other. True when the effective value is on, False when a config is readable and
    the effective value is off or unset, ``None`` when no config can be read. Codex 0.160 ships with
    the tool off, and without it an approved plan cannot reach the task board. devteam only reads these files.
    """
    try:
        user_text = (codex_config_dir(home) / "config.toml").read_text(encoding="utf-8")
    except OSError:
        user_text = None
    project_text = None
    if project_root and user_text is not None and _trusted_in(user_text, project_root):
        try:
            project_text = (Path(project_root) / ".codex" / "config.toml").read_text(encoding="utf-8")
        except OSError:
            pass
    if user_text is None and project_text is None:
        return None
    for text in (project_text, user_text):
        value = _toml_value(text, "tools.update_plan.enabled") if text is not None else None
        if value is not None:
            return value
    return False
