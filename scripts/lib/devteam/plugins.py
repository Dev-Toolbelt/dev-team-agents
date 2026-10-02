"""Plugins: manifest-declared, per-project integrations (ADR-0019).

A plugin is a directory in the versioned core (``plugins/<name>/plugin.json``). This
module is everything the CLI knows about them: discovering and validating manifests,
reading and writing the per-project settings file, probing requirements, coercing
config values, and running the actions and status script a manifest declares.

Nothing here names a plugin. The one exception is ``LEGACY_FILES``, which maps the
pre-plugin ``graphify.json`` onto the plugin that replaced it.

Settings live in ``<project>/.dev-team-agents/plugin-settings/<name>.json`` -- a
project-owned, committed record (``paths.PROJECT_OWNED_RECORDS``). They are written
with the ``indent=2, sort_keys=True`` layout the PreToolUse dispatcher matches first with
a pure-bash ``"enabled": true`` test (a whitespace-tolerant fallback covers other layouts),
so the canonical format stays part of the contract.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import jsonio, project, registry, shells, versions
from .errors import ConflictError, EnvError, UsageError
from .lock import store_lock

SCHEMA = 1
PLUGINS_DIR = "plugins"
SETTINGS_DIR = "plugin-settings"
MANIFEST = "plugin.json"

#: A plugin that replaced a hand-wired integration reads (and migrates) the old file.
LEGACY_FILES = {"graphify": "graphify.json"}

TAIL_BYTES = 8 * 1024
DEFAULT_ACTION_TIMEOUT = 300
DEFAULT_STATUS_TIMEOUT = 10
TIMEOUT_EXIT_CODE = 124
#: How long to wait for pipes to close after killing a script's process group.
KILL_GRACE_SECONDS = 2.0
TERM_GRACE_SECONDS = 3.0
#: Longest value `config set` accepts, and the largest config passed inline in the env.
MAX_VALUE_BYTES = 64 * 1024
MAX_ENV_CONFIG_BYTES = 64 * 1024

_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_BINARY_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_SCRIPT_RE = re.compile(r"^(?!/)(?!.*(^|/)\.\.(/|$))[A-Za-z0-9._/-]+$")
_INT_RE = re.compile(r"^[+-]?[0-9]+$")

CONFIG_TYPES = ("boolean", "string", "integer", "string_list", "enum")
PICKERS = ("directory", "file")
FACT_TONES = ("positive", "warning", "neutral")
RUNTIMES = ("bash", "python3")
OUTPUTS = ("config", "json", "log")
HOOK_EVENTS = ("pre_tool_use", "stop")

_TOP_KEYS = {"schema", "name", "title", "description", "homepage", "requires", "config",
             "actions", "status", "hooks"}


# ── manifest validation ───────────────────────────────────────────────────────


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_keys(obj, where, required, allowed, problems):
    if not isinstance(obj, dict):
        problems.append("{} must be an object".format(where))
        return False
    for key in required:
        if key not in obj:
            problems.append("{}: missing required key '{}'".format(where, key))
    for key in obj:
        if key not in allowed:
            problems.append("{}: unknown key '{}'".format(where, key))
    return True


def _check_script(value, where, problems):
    if not isinstance(value, str) or not _SCRIPT_RE.fullmatch(value):
        problems.append(
            "{} must be a relative path inside the plugin directory (no '..', no leading '/')".format(
                where
            )
        )


def _type_matches(kind, value):
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return _is_int(value)
    if kind == "string":
        return isinstance(value, str)
    if kind == "string_list":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    return isinstance(value, str)  # enum


def validate_manifest(data, dirname=None):
    """Problems with a parsed manifest, as a list of strings (empty when valid).

    A stdlib re-statement of ``plugins/_schema/plugin.schema.json`` plus the rules a
    schema cannot say (name equals directory, unique ids and keys, defaults that match
    their declared type). ``helpers/plugin-lint.sh`` validates against the schema file
    itself; keep the two in step.
    """
    problems = []
    if not _check_keys(data, "manifest", ("schema", "name", "title", "description"), _TOP_KEYS, problems):
        return problems

    if data.get("schema") != 1 or isinstance(data.get("schema"), bool):
        problems.append("schema must be 1")
    name = data.get("name")
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        problems.append("name must match ^[a-z][a-z0-9-]{1,31}$")
    elif dirname is not None and name != dirname:
        problems.append("name '{}' must equal the directory name '{}'".format(name, dirname))
    title = data.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 40:
        problems.append("title must be a string of 1-40 characters")
    description = data.get("description")
    if not isinstance(description, str) or not 1 <= len(description) <= 200:
        problems.append("description must be a string of 1-200 characters")
    if "homepage" in data and (
        not isinstance(data["homepage"], str) or not data["homepage"].startswith("https://")
    ):
        problems.append("homepage must be an https:// URL")

    if "requires" in data:
        if not isinstance(data["requires"], list):
            problems.append("requires must be an array")
        else:
            for index, item in enumerate(data["requires"]):
                where = "requires[{}]".format(index)
                if not _check_keys(item, where, ("binary", "install_hint"), ("binary", "install_hint"), problems):
                    continue
                if "binary" in item and (
                    not isinstance(item["binary"], str) or not _BINARY_RE.fullmatch(item["binary"])
                ):
                    problems.append("{}.binary must match ^[A-Za-z0-9._-]+$".format(where))
                if "install_hint" in item and (
                    not isinstance(item["install_hint"], str) or not item["install_hint"]
                ):
                    problems.append("{}.install_hint must be a non-empty string".format(where))

    if "config" in data:
        _validate_config(data["config"], problems)
    if "actions" in data:
        _validate_actions(data["actions"], problems)

    if "status" in data:
        status = data["status"]
        if _check_keys(status, "status", ("runtime", "script"), ("runtime", "script", "timeout_seconds"), problems):
            if status.get("runtime") not in RUNTIMES:
                problems.append("status.runtime must be one of {}".format(", ".join(RUNTIMES)))
            if "script" in status:
                _check_script(status["script"], "status.script", problems)
            if "timeout_seconds" in status and not (
                _is_int(status["timeout_seconds"]) and 1 <= status["timeout_seconds"] <= 30
            ):
                problems.append("status.timeout_seconds must be an integer 1-30")

    if "hooks" in data:
        hooks = data["hooks"]
        if _check_keys(hooks, "hooks", (), HOOK_EVENTS, problems):
            for event, script in hooks.items():
                if event in HOOK_EVENTS:
                    _check_script(script, "hooks.{}".format(event), problems)
    return problems


def _validate_config(config, problems):
    if not isinstance(config, list):
        problems.append("config must be an array")
        return
    seen = set()
    allowed = ("key", "type", "label", "help", "required", "default", "placeholder", "min", "max", "options", "picker")
    for index, field in enumerate(config):
        where = "config[{}]".format(index)
        if not _check_keys(field, where, ("key", "type", "label", "help", "default"), allowed, problems):
            continue
        key = field.get("key")
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            problems.append("{}.key must match ^[A-Za-z][A-Za-z0-9_]{{0,63}}$".format(where))
        elif key in seen:
            problems.append("{}: duplicate key '{}'".format(where, key))
        else:
            seen.add(key)
        kind = field.get("type")
        if kind not in CONFIG_TYPES:
            problems.append("{}.type must be one of {}".format(where, ", ".join(CONFIG_TYPES)))
        for text in ("label", "help"):
            if text in field and (not isinstance(field[text], str) or not field[text]):
                problems.append("{}.{} must be a non-empty string".format(where, text))
        if "required" in field and not isinstance(field["required"], bool):
            problems.append("{}.required must be a boolean".format(where))
        if "placeholder" in field and not isinstance(field["placeholder"], str):
            problems.append("{}.placeholder must be a string".format(where))
        if "picker" in field:
            if field["picker"] not in PICKERS:
                problems.append("{}.picker must be one of {}".format(where, ", ".join(PICKERS)))
            elif kind not in ("string", "string_list"):
                problems.append("{}.picker is only allowed on string or string_list fields".format(where))
        for bound in ("min", "max"):
            if bound in field and not _is_int(field[bound]):
                problems.append("{}.{} must be an integer".format(where, bound))
        options = field.get("options")
        if "options" in field:
            if not isinstance(options, list) or not options:
                problems.append("{}.options must be a non-empty array".format(where))
            else:
                for o_index, option in enumerate(options):
                    o_where = "{}.options[{}]".format(where, o_index)
                    if _check_keys(option, o_where, ("value", "label"), ("value", "label"), problems):
                        for part in ("value", "label"):
                            if part in option and not isinstance(option[part], str):
                                problems.append("{}.{} must be a string".format(o_where, part))
        if kind == "enum" and "options" not in field:
            problems.append("{}: an enum field needs options".format(where))
        if kind in CONFIG_TYPES and "default" in field and not _type_matches(kind, field["default"]):
            problems.append("{}.default does not match type {}".format(where, kind))
        if (
            kind == "enum"
            and isinstance(options, list)
            and isinstance(field.get("default"), str)
            and field["default"] not in [o.get("value") for o in options if isinstance(o, dict)]
        ):
            problems.append("{}.default is not one of the options".format(where))


def _validate_actions(actions, problems):
    if not isinstance(actions, list):
        problems.append("actions must be an array")
        return
    seen = set()
    allowed = ("id", "label", "help", "runtime", "script", "output", "requires_enabled", "timeout_seconds")
    for index, action in enumerate(actions):
        where = "actions[{}]".format(index)
        if not _check_keys(action, where, ("id", "label", "help", "runtime", "script", "output"), allowed, problems):
            continue
        action_id = action.get("id")
        if not isinstance(action_id, str) or not _ID_RE.fullmatch(action_id):
            problems.append("{}.id must match ^[a-z][a-z0-9-]{{0,31}}$".format(where))
        elif action_id in seen:
            problems.append("{}: duplicate id '{}'".format(where, action_id))
        else:
            seen.add(action_id)
        for text in ("label", "help"):
            if text in action and (not isinstance(action[text], str) or not action[text]):
                problems.append("{}.{} must be a non-empty string".format(where, text))
        if action.get("runtime") not in RUNTIMES:
            problems.append("{}.runtime must be one of {}".format(where, ", ".join(RUNTIMES)))
        if action.get("output") not in OUTPUTS:
            problems.append("{}.output must be one of {}".format(where, ", ".join(OUTPUTS)))
        if "script" in action:
            _check_script(action["script"], "{}.script".format(where), problems)
        if "requires_enabled" in action and not isinstance(action["requires_enabled"], bool):
            problems.append("{}.requires_enabled must be a boolean".format(where))
        if "timeout_seconds" in action and not (
            _is_int(action["timeout_seconds"]) and 1 <= action["timeout_seconds"] <= 3600
        ):
            problems.append("{}.timeout_seconds must be an integer 1-3600".format(where))


# ── discovery ─────────────────────────────────────────────────────────────────


class Plugin:
    """A validated manifest and the directory it came from."""

    def __init__(self, directory, manifest):
        self.dir = Path(directory)
        self.manifest = manifest
        self.name = manifest["name"]

    @property
    def config_fields(self):
        return self.manifest.get("config", [])

    def field(self, key):
        for field in self.config_fields:
            if field["key"] == key:
                return field
        return None

    def defaults(self):
        return {f["key"]: _copy(f["default"]) for f in self.config_fields}

    def action(self, action_id):
        for action in self.manifest.get("actions", []):
            if action["id"] == action_id:
                return action
        return None


def _copy(value):
    return json.loads(json.dumps(value))


def discover(version_dir):
    """``({name: Plugin}, invalid)`` for the plugins shipped in a core version.

    ``invalid`` lists ``{"name", "problems"}`` for directories whose manifest is
    unreadable or fails validation; they are never returned as plugins. ``_``-prefixed
    directories (the schema) are not plugins.
    """
    root = Path(version_dir) / PLUGINS_DIR
    found = {}
    invalid = []
    if not root.is_dir():
        return found, invalid
    for entry in sorted(root.iterdir()):
        if entry.name.startswith((".", "_")) or not entry.is_dir():
            continue
        manifest_path = entry / MANIFEST
        if not manifest_path.is_file():
            invalid.append({"name": entry.name, "problems": ["{} is missing".format(MANIFEST)]})
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            invalid.append({"name": entry.name, "problems": ["cannot read manifest: {}".format(exc)]})
            continue
        problems = validate_manifest(data, dirname=entry.name)
        if problems:
            invalid.append({"name": entry.name, "problems": problems})
            continue
        found[data["name"]] = Plugin(entry, data)
    return found, invalid


class Context:
    """Everything one command needs: the project, its state dir and the core plugins."""

    def __init__(self, project_root, project_id):
        self.root = Path(project_root)
        self.project_id = project_id
        pin = (registry.get(project_id) or {}).get("pin") if project_id else None
        self.version = versions.resolve(pin)
        self.version_dir = versions.require(self.version)
        self.plugins, self.invalid = discover(self.version_dir)

    def plugin(self, name):
        found = self.plugins.get(name)
        if found is None:
            raise UsageError(
                "unknown plugin '{}'".format(name),
                hint="Available: {}".format(", ".join(sorted(self.plugins)) or "none"),
            )
        return found

    def state_dir(self):
        return project.state_dir(self.root, self.project_id)


# ── settings ──────────────────────────────────────────────────────────────────


def settings_rel(name):
    return "{}/{}/{}.json".format(project.PROJECT_DIR, SETTINGS_DIR, name)


def settings_path(project_root, name):
    return Path(project_root) / project.PROJECT_DIR / SETTINGS_DIR / "{}.json".format(name)


def legacy_path(project_root, name):
    filename = LEGACY_FILES.get(name)
    if filename is None:
        return None
    return project.legacy_memory_dir(project_root) / filename


def read_settings(project_root, name):
    """The stored state: ``{enabled, config, source, exists}``.

    ``source`` is ``settings`` for the plugin-settings file, ``legacy`` for a plugin
    whose pre-plugin file is still the only record, ``none`` otherwise. Unknown config
    keys are kept as stored; :func:`build_view` reports them.
    """
    path = settings_path(project_root, name)
    data = jsonio.read_json(path)
    if data is not None:
        if not isinstance(data, dict):
            raise EnvError("{} must hold a JSON object".format(path), hint="Fix the file by hand.")
        config = data.get("config", {})
        if not isinstance(config, dict):
            raise EnvError("{}: 'config' must be an object".format(path), hint="Fix the file by hand.")
        return {"enabled": data.get("enabled") is True, "config": config, "source": "settings", "exists": True}
    legacy = legacy_path(project_root, name)
    if legacy is not None:
        try:
            content = jsonio.read_json(legacy)
        except EnvError:
            content = None
        if isinstance(content, dict):
            return {"enabled": True, "config": content, "source": "legacy", "exists": False}
    return {"enabled": False, "config": {}, "source": "none", "exists": False}


def _trim(plugin, config):
    """Drop declared keys equal to their default; keep everything else."""
    out = {}
    for key, value in config.items():
        field = plugin.field(key)
        if field is not None and value == field["default"]:
            continue
        out[key] = value
    return out


def _write_body(project_root, plugin, enabled, config):
    """Write the settings file; the caller holds the ``plugin-settings`` lock."""
    body = {"schema": SCHEMA, "enabled": bool(enabled), "config": _trim(plugin, config)}
    path = settings_path(project_root, plugin.name)
    # mode 0644 (committed, shared), directories left to the umask.
    jsonio.write_json_atomic(path, body, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None)
    return body


def write_settings(project_root, plugin, enabled, config):
    with store_lock("plugin-settings"):
        return _write_body(project_root, plugin, enabled, config)


def update_settings(project_root, plugin, change):
    """Read-modify-write of one plugin's settings under a single lock.

    ``change(state)`` receives the freshly read state and returns ``(enabled, config)``
    to write, or ``None`` to leave the file alone. When the state came from the legacy
    file, the write completes the move: the new file is written first and the legacy
    one is unlinked afterwards, exactly like :func:`migrate_legacy`. Returns
    ``(state_read, body_written_or_None)``.
    """
    with store_lock("plugin-settings"):
        state = read_settings(project_root, plugin.name)
        result = change(state)
        if result is None:
            return state, None
        enabled, config = result
        body = _write_body(project_root, plugin, enabled, config)
        if state["source"] == "legacy":
            legacy = legacy_path(project_root, plugin.name)
            try:
                os.unlink(str(legacy))
            except OSError:
                pass
        return state, body


def effective_config(plugin, stored):
    merged = plugin.defaults()
    for key, value in stored.items():
        if plugin.field(key) is not None:
            merged[key] = value
    return merged


def _non_empty(value):
    if value is None:
        return False
    if isinstance(value, (str, list)):
        return len(value) > 0
    return True


def coerce(plugin, key, raw):
    """Parse the CLI string ``raw`` into the type ``key`` declares, or raise ``UsageError``."""
    field = plugin.field(key)
    if field is None:
        raise UsageError(
            "plugin '{}' has no config key '{}'".format(plugin.name, key),
            hint="Declared keys: {}".format(", ".join(f["key"] for f in plugin.config_fields) or "none"),
        )
    kind = field["type"]
    text = raw if isinstance(raw, str) else json.dumps(raw)
    if len(text.encode("utf-8", "replace")) > MAX_VALUE_BYTES:
        raise UsageError("value for '{}' is larger than {} KiB".format(key, MAX_VALUE_BYTES // 1024))
    if kind == "boolean":
        lowered = text.strip().lower()
        if lowered not in ("true", "false"):
            raise UsageError("'{}' expects true or false, got '{}'".format(key, text))
        return lowered == "true"
    if kind == "integer":
        if not _INT_RE.fullmatch(text.strip()):
            raise UsageError("'{}' expects a base-10 integer, got '{}'".format(key, text))
        try:
            value = int(text.strip(), 10)
        except ValueError:
            raise UsageError("'{}' expects a base-10 integer, got a number that is too long".format(key)) from None
        _check_range(field, key, value)
        return value
    if kind == "string":
        return text
    if kind == "string_list":
        try:
            value = json.loads(text)
        except (ValueError, RecursionError):
            raise UsageError(
                "'{}' expects a JSON array of strings".format(key), hint="Example: '[\"src\",\"lib\"]'"
            ) from None
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise UsageError("'{}' expects a JSON array of strings".format(key), hint="Example: '[\"src\",\"lib\"]'")
        return value
    options = [o["value"] for o in field.get("options", [])]
    if text not in options:
        raise UsageError("'{}' must be one of: {}".format(key, ", ".join(options)))
    return text


def _check_range(field, key, value):
    if "min" in field and value < field["min"]:
        raise UsageError("'{}' must be >= {}".format(key, field["min"]))
    if "max" in field and value > field["max"]:
        raise UsageError("'{}' must be <= {}".format(key, field["max"]))


def sanitize_proposed(plugin, proposed):
    """Keep only the values of a ``config``-output answer that fit their declared type."""
    accepted = {}
    if not isinstance(proposed, dict):
        return accepted
    for key, value in proposed.items():
        field = plugin.field(key)
        if field is None or not _type_matches(field["type"], value):
            continue
        if field["type"] == "enum" and value not in [o["value"] for o in field.get("options", [])]:
            continue
        if field["type"] == "integer":
            try:
                _check_range(field, key, value)
            except UsageError:
                continue
        accepted[key] = value
    return accepted


# ── requirements, running scripts ─────────────────────────────────────────────


def requirements(plugin):
    return [
        {
            "binary": req["binary"],
            "found": shutil.which(req["binary"]) is not None,
            "install_hint": req["install_hint"],
        }
        for req in plugin.manifest.get("requires", [])
    ]


def _interpreter(runtime):
    if runtime == "python3":
        return sys.executable or shutil.which("python3") or "python3"
    # Never a bare `bash` on Windows: that is WSL's launcher, whose children a kill does not reach.
    return shells.bash_path() or "bash"


def _script_path(plugin, rel):
    """The absolute script, refused when it resolves outside the plugin directory."""
    base = plugin.dir.resolve()
    target = (plugin.dir / rel).resolve()
    if target != base and base not in target.parents:
        raise EnvError("script '{}' escapes the plugin directory".format(rel))
    if not target.is_file():
        raise EnvError("script '{}' of plugin '{}' does not exist".format(rel, plugin.name))
    return target


def _env(ctx, plugin, config):
    env = dict(os.environ)
    env.pop("DEVTEAM_PLUGIN_CONFIG", None)
    env.pop("DEVTEAM_PLUGIN_CONFIG_TRUNCATED", None)
    env.update(
        {
            "DEVTEAM_PROJECT_ROOT": str(ctx.root),
            "DEVTEAM_PLUGIN_DIR": str(plugin.dir),
            "DEVTEAM_PLUGIN_SETTINGS": str(settings_path(ctx.root, plugin.name)),
            "DEVTEAM_STATE_DIR": str(ctx.state_dir()),
        }
    )
    serialized = json.dumps(config, sort_keys=True)
    if len(serialized.encode("utf-8")) <= MAX_ENV_CONFIG_BYTES:
        env["DEVTEAM_PLUGIN_CONFIG"] = serialized
    else:
        # An environment block has a hard size limit (E2BIG on exec); a script that sees
        # this flag reads DEVTEAM_PLUGIN_SETTINGS instead.
        env["DEVTEAM_PLUGIN_CONFIG_TRUNCATED"] = "1"
    return env


def _tail(text):
    data = text.encode("utf-8", "replace")
    if len(data) <= TAIL_BYTES:
        return text
    return data[-TAIL_BYTES:].decode("utf-8", "replace")


def _signal_group(proc, signum):
    """Send ``signum`` to the script's process group; falls back to the script itself."""
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signum)
            return
        except OSError:
            pass
    try:
        proc.send_signal(signum)
    except (OSError, ValueError):
        pass


def _windows_job(proc):
    """A Job Object holding the script and everything it starts, or None.

    Under Git Bash a script's children are not in the script's Windows process tree (the
    MSYS2 runtime starts them), so neither TerminateProcess nor ``taskkill /T`` reaches a
    ``sleep`` or a build it launched, and that child keeps the output pipes open. Processes
    created by a job member join the job, so terminating the job ends all of them.
    """
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        if not kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(proc._handle))):
            kernel32.CloseHandle(wintypes.HANDLE(job))
            return None
        return job
    except (OSError, AttributeError, ValueError, TypeError):
        return None


def _close_job(job):
    if job is None:
        return
    try:
        import ctypes
        from ctypes import wintypes

        ctypes.WinDLL("kernel32").CloseHandle(wintypes.HANDLE(job))
    except (OSError, AttributeError):
        pass


def _kill_group(proc, job=None):
    if os.name == "nt":
        if job is not None:
            try:
                import ctypes
                from ctypes import wintypes

                if ctypes.WinDLL("kernel32").TerminateJobObject(wintypes.HANDLE(job), 1):
                    return
            except (OSError, AttributeError):
                pass
        # No job: end the tree Windows knows about. taskkill is resolved from SystemRoot, never PATH.
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
        try:
            subprocess.run(
                [taskkill, "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=KILL_GRACE_SECONDS, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    _signal_group(proc, signal.SIGKILL if os.name == "posix" else signal.SIGTERM)


def _group_alive(pid):
    if os.name != "posix":
        return False
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _abandon(proc, exc):
    """Partial output of a script whose pipes never closed; the pipes are closed here."""
    out = getattr(exc, "stdout", None) or getattr(exc, "output", None)
    err = getattr(exc, "stderr", None)
    for pipe in (proc.stdout, proc.stderr):
        try:
            if pipe is not None:
                pipe.close()
        except (OSError, ValueError):
            pass
    try:
        proc.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    return out, err


def _spawn(argv, cwd, env, timeout, merge_stderr):
    """``(exit_code, stdout, stderr, timed_out)``.

    The script runs in its own session. On a timeout, or when this process is sent
    SIGTERM/SIGINT, the whole process group is killed, so nothing outlives the CLI. A
    descendant that ``setsid``-ed away can keep a pipe open; reading is bounded so that
    never hangs the CLI.
    """
    kwargs = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True
    received = {"sig": None, "pid": None, "term_at": None}
    previous = {}
    job = None

    def send_term():
        if received["pid"] is not None and received["term_at"] is None:
            received["term_at"] = time.monotonic()
            if os.name == "posix":
                try:
                    os.killpg(received["pid"], signal.SIGTERM)
                except OSError:
                    pass

    def on_signal(signum, _frame):
        received["sig"] = signum
        send_term()

    if os.name == "posix" and threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, on_signal)
    try:
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
                **kwargs
            )
        except OSError as exc:
            return 127, "", "cannot start {}: {}".format(argv[0], exc), False
        received["pid"] = proc.pid
        if os.name == "nt":
            job = _windows_job(proc)
        if received["sig"] is not None:
            send_term()

        deadline = time.monotonic() + timeout
        killed_at = None
        give_up = None
        timed_out = False
        while True:
            try:
                out, err = proc.communicate(timeout=0.25)
                break
            except subprocess.TimeoutExpired as exc:
                now = time.monotonic()
                if received["sig"] is not None:
                    send_term()
                elif now >= deadline and not timed_out:
                    timed_out = True
                    send_term()
                term_at = received["term_at"]
                # TERM first so the script's own cleanup runs; KILL what outlives the grace.
                if term_at is not None and killed_at is None:
                    group_gone = proc.poll() is not None and not _group_alive(proc.pid)
                    if group_gone or now >= term_at + TERM_GRACE_SECONDS:
                        # Nothing left to wait for in the group (only a setsid-ed straggler
                        # can still hold the pipe), or the grace ran out.
                        _kill_group(proc, job)
                        killed_at = now
                        give_up = now + KILL_GRACE_SECONDS
                if give_up is not None and now >= give_up:
                    out, err = _abandon(proc, exc)
                    break
        # The script may have exited on TERM while a descendant is still cleaning up.
        term_at = received["term_at"]
        if term_at is not None and killed_at is None:
            while _group_alive(proc.pid) and time.monotonic() < term_at + TERM_GRACE_SECONDS:
                time.sleep(0.05)
            if _group_alive(proc.pid):
                _kill_group(proc, job)
    finally:
        _close_job(job)
        for signum, handler in previous.items():
            try:
                signal.signal(signum, handler if handler is not None else signal.SIG_DFL)
            except (OSError, ValueError, TypeError):
                pass
    if received["sig"] is not None:
        # Hand the signal back to whatever was handling it before, now that the group is gone.
        os.kill(os.getpid(), received["sig"])
    decode = lambda b: (b or b"").decode("utf-8", "replace")  # noqa: E731
    code = TIMEOUT_EXIT_CODE if timed_out or proc.returncode is None else proc.returncode
    return code, decode(out), decode(err), timed_out


def _execute(ctx, plugin, action, config):
    """Run one action; builds the ``RunResult`` without any gating."""
    script = _script_path(plugin, action["script"])
    timeout = action.get("timeout_seconds", DEFAULT_ACTION_TIMEOUT)
    output_kind = action["output"]
    started = time.monotonic()
    code, out, err, timed_out = _spawn(
        [_interpreter(action["runtime"]), str(script)],
        ctx.root,
        _env(ctx, plugin, config),
        timeout,
        merge_stderr=output_kind == "log",
    )
    duration = int((time.monotonic() - started) * 1000)
    ok = code == 0
    parsed = None
    parse_problem = None
    if ok and output_kind in ("config", "json"):
        try:
            parsed = json.loads(out)
        except ValueError:
            parsed = None
        if not isinstance(parsed, dict):
            parsed = None
            ok = False
            parse_problem = "action printed no JSON object on stdout"
    if timed_out:
        log = "timed out after {}s\n".format(timeout) + out + err
    elif parse_problem:
        log = parse_problem + "\n" + out + err
    elif output_kind == "log" or not ok:
        log = out + err
    else:
        log = ""
    return {
        "plugin": plugin.name,
        "action": action["id"],
        "ok": ok,
        "exit_code": code,
        "duration_ms": duration,
        "output": parsed if ok else None,
        "log_tail": _tail(log),
    }


def _read_status(ctx, plugin, config):
    status = plugin.manifest.get("status")
    if status is None:
        return None
    try:
        script = _script_path(plugin, status["script"])
    except EnvError:
        return None
    code, out, _err, timed_out = _spawn(
        [_interpreter(status["runtime"]), str(script)],
        ctx.root,
        _env(ctx, plugin, config),
        status.get("timeout_seconds", DEFAULT_STATUS_TIMEOUT),
        merge_stderr=False,
    )
    if timed_out or code != 0:
        return None
    try:
        parsed = json.loads(out)
    except ValueError:
        return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("summary"), str):
        return None
    facts = []
    for fact in parsed.get("facts") or []:
        if isinstance(fact, dict) and "label" in fact and "value" in fact:
            item = {"label": str(fact["label"]), "value": str(fact["value"])}
            if isinstance(fact.get("tone"), str) and fact["tone"] in FACT_TONES:
                item["tone"] = fact["tone"]
            facts.append(item)
    return {"summary": parsed["summary"], "facts": facts}


# ── views ─────────────────────────────────────────────────────────────────────


def build_view(ctx, plugin, with_status=True):
    """The ``PluginView`` of ADR-0019 § 3."""
    state = read_settings(ctx.root, plugin.name)
    config = effective_config(plugin, state["config"])
    reqs = requirements(plugin)
    required_keys = [f["key"] for f in plugin.config_fields if f.get("required")]
    manifest = plugin.manifest
    status = None
    if with_status and state["enabled"] and manifest.get("status"):
        status = _read_status(ctx, plugin, config)
    return {
        "name": plugin.name,
        "title": manifest["title"],
        "description": manifest["description"],
        "homepage": manifest.get("homepage"),
        "enabled": state["enabled"],
        "source": state["source"],
        "settings_file": settings_rel(plugin.name),
        "requirements": reqs,
        "ready": all(r["found"] for r in reqs),
        "configured": all(_non_empty(config.get(k)) for k in required_keys),
        "config_fields": manifest.get("config", []),
        "config": config,
        "unknown_config": sorted(k for k in state["config"] if plugin.field(k) is None),
        "actions": [
            {
                "id": a["id"],
                "label": a["label"],
                "help": a["help"],
                "output": a["output"],
                "requires_enabled": a.get("requires_enabled", True),
                "writes": a["output"] != "config",
                "timeout_seconds": a.get("timeout_seconds", DEFAULT_ACTION_TIMEOUT),
            }
            for a in manifest.get("actions", [])
        ],
        "hooks": [event for event in HOOK_EVENTS if event in manifest.get("hooks", {})],
        "status": status,
    }


def list_views(ctx):
    return [build_view(ctx, ctx.plugins[name]) for name in sorted(ctx.plugins)]


# ── mutations ─────────────────────────────────────────────────────────────────


def _missing_requirements_error(plugin, reqs, verb):
    missing = [r for r in reqs if not r["found"]]
    return EnvError(
        "cannot {} '{}': missing {}".format(verb, plugin.name, ", ".join(r["binary"] for r in missing)),
        hint="; ".join("{}: {}".format(r["binary"], r["install_hint"]) for r in missing),
        details={"missing": [r["binary"] for r in missing]},
    )


def enable(ctx, name, force=False):
    plugin = ctx.plugin(name)
    reqs = requirements(plugin)
    if not force and not all(r["found"] for r in reqs):
        raise _missing_requirements_error(plugin, reqs, "enable")
    state = read_settings(ctx.root, name)
    if state["enabled"]:
        return {"plugin": build_view(ctx, plugin), "changed": False, "seeded": False}

    # The seeder can run for a while, so it runs outside the lock; the write below
    # re-reads the state under the lock and only applies the proposal to a plugin that
    # still has no record.
    proposed = {}
    if state["source"] == "none":
        seeder = next((a for a in plugin.manifest.get("actions", []) if a["output"] == "config"), None)
        if seeder is not None and all(r["found"] for r in reqs):
            try:
                result = _execute(ctx, plugin, seeder, effective_config(plugin, {}))
            except EnvError:
                result = None
            if result and result["ok"]:
                proposed = sanitize_proposed(plugin, result["output"])

    outcome = {"seeded": False}

    def change(fresh):
        if fresh["enabled"]:
            return None
        config = dict(fresh["config"])
        if fresh["source"] == "none" and proposed:
            config.update(proposed)
            outcome["seeded"] = True
        return True, config

    _, body = update_settings(ctx.root, plugin, change)
    return {"plugin": build_view(ctx, plugin), "changed": body is not None, "seeded": outcome["seeded"]}


def disable(ctx, name):
    plugin = ctx.plugin(name)
    _, body = update_settings(
        ctx.root, plugin, lambda fresh: (False, fresh["config"]) if fresh["enabled"] else None
    )
    return {"plugin": build_view(ctx, plugin), "changed": body is not None}


def config_get(ctx, name, key=None):
    plugin = ctx.plugin(name)
    config = effective_config(plugin, read_settings(ctx.root, name)["config"])
    if key is None:
        return {"plugin": name, "config": config}
    if plugin.field(key) is None:
        raise UsageError("plugin '{}' has no config key '{}'".format(name, key))
    return {"plugin": name, "key": key, "value": config[key]}


def config_set(ctx, name, key, raw):
    plugin = ctx.plugin(name)
    value = coerce(plugin, key, raw)
    update_settings(
        ctx.root, plugin, lambda fresh: (fresh["enabled"], dict(fresh["config"], **{key: value}))
    )
    return {"plugin": build_view(ctx, plugin), "key": key, "value": value}


def config_unset(ctx, name, key):
    plugin = ctx.plugin(name)
    if plugin.field(key) is None and key not in read_settings(ctx.root, name)["config"]:
        raise UsageError("plugin '{}' has no config key '{}'".format(name, key))

    def change(fresh):
        if key not in fresh["config"]:
            return None
        config = dict(fresh["config"])
        del config[key]
        return fresh["enabled"], config

    _, body = update_settings(ctx.root, plugin, change)
    return {"plugin": build_view(ctx, plugin), "key": key, "removed": body is not None}


def run(ctx, name, action_id):
    plugin = ctx.plugin(name)
    action = plugin.action(action_id)
    if action is None:
        raise UsageError(
            "plugin '{}' declares no action '{}'".format(name, action_id),
            hint="Declared: {}".format(", ".join(a["id"] for a in plugin.manifest.get("actions", [])) or "none"),
        )
    reqs = requirements(plugin)
    if not all(r["found"] for r in reqs):
        raise _missing_requirements_error(plugin, reqs, "run an action of")
    state = read_settings(ctx.root, name)
    if action.get("requires_enabled", True) and not state["enabled"]:
        raise ConflictError(
            "plugin '{}' is disabled; action '{}' needs it enabled".format(name, action_id),
            hint="Run `devteam plugin enable {}` first.".format(name),
        )
    return _execute(ctx, plugin, action, effective_config(plugin, state["config"]))


# ── legacy migration ──────────────────────────────────────────────────────────


def _already_migrated(legacy, target):
    """True when the legacy file only repeats the settings file: a finished move.

    The legacy path is unlinked here, silently -- its bytes live in the new file, so
    nothing is lost, and warning about it would report a conflict that does not exist.
    """
    try:
        old = jsonio.read_json(legacy)
        new = jsonio.read_json(target)
    except EnvError:
        return False
    if not (isinstance(old, dict) and isinstance(new, dict)):
        return False
    if new.get("enabled") is not True or new.get("config", {}) != old:
        return False
    try:
        os.unlink(str(legacy))
    except OSError:
        return False
    return True


def migrate_legacy(project_root):
    """Move each pre-plugin settings file into ``plugin-settings/``.

    Idempotent and never destructive: the content is written into the new shape first
    and only then is the old path removed, so the bytes are never held in one place
    only. No ``.migrated`` leftover is kept: a stray file in ``user-data/`` would read
    as un-upgraded memory. When the new file already exists nothing is touched and the
    leftover is reported. Returns
    ``{"moved": [...], "skipped": [{"plugin", "reason"}]}``.
    """
    moved = []
    skipped = []
    root = Path(project_root)
    for name in sorted(LEGACY_FILES):
        legacy = legacy_path(root, name)
        if legacy is None or not legacy.is_file():
            continue
        target = settings_path(root, name)
        if target.exists():
            if _already_migrated(legacy, target):
                continue
            skipped.append({"plugin": name, "reason": "plugin-settings/{}.json already exists".format(name)})
            continue
        try:
            content = jsonio.read_json(legacy)
        except EnvError as exc:
            skipped.append({"plugin": name, "reason": exc.message})
            continue
        if not isinstance(content, dict):
            skipped.append({"plugin": name, "reason": "{} is not a JSON object".format(legacy.name)})
            continue
        body = {"schema": SCHEMA, "enabled": True, "config": content}
        with store_lock("plugin-settings"):
            if target.exists():
                if not _already_migrated(legacy, target):
                    skipped.append(
                        {"plugin": name, "reason": "plugin-settings/{}.json already exists".format(name)}
                    )
                continue
            jsonio.write_json_atomic(target, body, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None)
            os.unlink(str(legacy))
        moved.append(name)
    return {"moved": moved, "skipped": skipped}
