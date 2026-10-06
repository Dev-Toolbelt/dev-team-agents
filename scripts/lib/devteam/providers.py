"""Per-provider bind artifacts.

Claude Code is materialised natively here, because its layout is a handful of
directory links. opencode and Codex are produced by the installers that already
exist (``install-opencode.sh``, ``install-codex.sh``), invoked with the store's
version directory as ``--source``: the render engine is not reimplemented, it is
pointed somewhere new.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import shells
from .errors import ConflictError, EnvError

ALL_PROVIDERS = ("claude", "opencode", "codex")

#: A link written as a file is tiny. Anything larger is not one.
LINK_STUB_MAX = 4096

#: Where a v2 Codex / opencode install linked the framework skills. As a link
#: stub (a checkout without symlink support) it points into the v2 install.
V2_SKILL_LINKS = (".codex/skills/dev-team-agents", ".opencode/skills/dev-team-agents")


def _decode_utf16(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        raw = raw[2:]
    return raw.decode("utf-16-le")


def read_link_stub(path):
    """The target of a symlink that a checkout wrote as a regular file, or ``None``.

    Three shapes exist: Cygwin/MSYS ``IntxLNK\\x01`` plus a UTF-16LE target, Cygwin's
    ``!<symlink>`` plus a target (UTF-16LE after a BOM, UTF-8 otherwise), and git's
    own with ``core.symlinks=false`` — the link text, as plain UTF-8. Never raises.
    """
    try:
        info = os.lstat(str(path))
        if not os.path.isfile(str(path)) or os.path.islink(str(path)) or info.st_size > LINK_STUB_MAX:
            return None
        with open(str(path), "rb") as stream:
            raw = stream.read(LINK_STUB_MAX + 1)
        if len(raw) > LINK_STUB_MAX:
            return None
        if raw.startswith(b"IntxLNK\x01"):
            text = _decode_utf16(raw[8:])
        elif raw.startswith(b"!<symlink>"):
            body = raw[10:]
            text = _decode_utf16(body) if body[:2] == b"\xff\xfe" else body.decode("utf-8")
        else:
            if b"\0" in raw:
                return None
            text = raw.decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        return None
    text = text.strip("\0").strip()
    if not text or "\n" in text or "\r" in text or "\0" in text:
        return None
    return text


def detect(project_root):
    """Providers a project already uses; ``claude`` when nothing indicates one."""
    root = Path(project_root)
    found = []
    if (root / ".claude").is_dir():
        found.append("claude")
    if (
        (root / ".opencode").is_dir()
        or (root / "opencode.json").is_file()
        or (root / "opencode.jsonc").is_file()
    ):
        found.append("opencode")
    if (root / ".codex").is_dir():
        found.append("codex")
    return found or ["claude"]


def skill_dirs(version_dir):
    """Every skill directory in a version, at either supported depth.

    ``skills/<category>/<name>/SKILL.md`` is the common layout;
    ``skills/<name>/SKILL.md`` also exists (``skill-creator``) and the v2
    installer's two-level loop silently skipped it.
    """
    skills_root = Path(version_dir) / "skills"
    if not skills_root.is_dir():
        return []
    found = {}
    for candidate in sorted(skills_root.glob("*/SKILL.md")):
        found.setdefault(candidate.parent.name, candidate.parent)
    for candidate in sorted(skills_root.glob("*/*/SKILL.md")):
        found.setdefault(candidate.parent.name, candidate.parent)
    return [(name, path) for name, path in sorted(found.items())]


def claude_artifacts(version_dir):
    """``(relative path in project, absolute source)`` pairs for Claude Code."""
    vdir = Path(version_dir)
    artifacts = [
        (Path(".claude") / "agents" / "dev-team", vdir / "agents"),
        (Path(".claude") / "commands" / "devteam", vdir / "commands"),
    ]
    for name, path in skill_dirs(vdir):
        artifacts.append((Path(".claude") / "skills" / name, path))
    return artifacts


#: Variables the installers documentably need. The child used to inherit the whole
#: environment; a minimal one keeps an unrelated variable from changing what a
#: shell script does, and makes the PATH the installer resolves explicit.
_ENV_PASSTHROUGH = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "DEVTEAM_HOME",
    "TERM",
    # Windows (Git Bash, python, mktemp) cannot start or find a temp dir without
    # these; all are absent on POSIX, so passing them through changes nothing there.
    "SYSTEMROOT",
    "SystemDrive",
    "WINDIR",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "PATHEXT",
    "COMSPEC",
    "MSYSTEM",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
)
#: Installer stderr is surfaced as a hint; cap it so a chatty script cannot flood
#: the `--json` document the desktop app consumes.
_HINT_MAX = 2000


def _installer_env():
    env = {key: os.environ[key] for key in _ENV_PASSTHROUGH if key in os.environ}
    env.setdefault("PATH", os.defpath)
    # The installers' `python3` resolves through scripts/lib/python.sh, which tries this
    # interpreter first: the one running the CLI is known to work.
    if sys.executable:
        env["DEVTEAM_PYTHON"] = sys.executable
    return env


def _run_installer(script, version_dir, project_root, extra_args=None):
    if not script.is_file():
        raise EnvError("installer not found in the core version: {}".format(script))
    bash = shells.bash_path()
    if bash is None:
        raise EnvError(
            "bash is required to run {} but was not found on PATH".format(script.name),
            hint="On Windows, install Git for Windows (which provides bash) and retry.",
        )
    command = [bash, str(script), "--source", str(version_dir)]
    if extra_args:
        command.extend(extra_args)
    try:
        result = subprocess.run(
            command,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_installer_env(),
            check=False,
        )
    except OSError as exc:
        raise EnvError("cannot run {}: {}".format(script.name, exc)) from exc
    if result.returncode == INSTALLER_CONFLICT_EXIT:
        # The installer found a path the project owns at one of its targets and
        # wrote nothing. `bind` runs the same check in its preflight, so reaching
        # this means the tree changed between the two — still a conflict, not a
        # failure of the environment.
        lines = result.stderr.decode("utf-8", "replace").splitlines()
        conflicts = [
            line.strip()
            for line in lines
            if line.startswith("  ") and line.strip() and " " not in line.strip()
        ]
        raise ConflictError(
            "{} refused: {} already exist(s) and were not created by dev-team-agents".format(
                script.name, ", ".join(conflicts) or "a target path"
            ),
            hint="Move or remove them, then run `devteam bind` again.",
            details={"paths": conflicts},
        )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        if len(detail) > _HINT_MAX:
            detail = detail[:_HINT_MAX] + " […truncated]"
        raise EnvError(
            "{} failed (exit {})".format(script.name, result.returncode),
            hint=detail or None,
        )
    return result.stdout.decode("utf-8", "replace")


#: `python3` is satisfied by any of these: scripts/lib/python.sh resolves the
#: installers' `python3` to whichever works (Windows often has only `python`/`py`).
_PYTHON_NAMES = ("python3", "python", "py")


def _tool_available(tool):
    if tool == "python3":
        return bool(sys.executable) or any(shutil.which(name) for name in _PYTHON_NAMES)
    if tool == "bash":
        return shells.bash_path() is not None
    return shutil.which(tool) is not None


def require_tools(provider):
    """Fail early with a readable message instead of deep inside a bash script."""
    needed = {"opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}.get(
        provider, ()
    )
    missing = [tool for tool in needed if not _tool_available(tool)]
    if missing:
        raise EnvError(
            "provider {} needs {} on PATH".format(provider, ", ".join(missing)),
            hint=(
                "Install the missing tool(s) and retry, or bind without this provider. "
                "On Windows, bash comes from Git for Windows."
            ),
        )


#: Exit status `scripts/lib/provider-ownership.sh` uses for "a target path belongs
#: to the project". Mirrors ``PO_CONFLICT_EXIT`` there.
INSTALLER_CONFLICT_EXIT = 4

#: The installer script for each delegated provider.
DELEGATED_INSTALLERS = {
    "opencode": "install-opencode.sh",
    "codex": "install-codex.sh",
}


def delegated_targets(provider, version_dir, project_root):
    """Project-relative paths the provider's installer would write, in its order.

    Asked of the installer itself (``--list-targets``) rather than re-derived here:
    the installer is what writes them, so it is the only list that cannot drift.
    Writes nothing to the project.
    """
    script = Path(version_dir) / "scripts" / DELEGATED_INSTALLERS[provider]
    output = _run_installer(script, version_dir, project_root, ["--list-targets"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def _install_delegated(provider, version_dir, project_root, owned):
    """Run a delegated installer, vouching for ``owned`` as framework-owned paths.

    ``--owned`` is always passed, even empty: it also tells the installer that
    ``devteam`` keeps the bookkeeping, so it writes no ledger of its own into the
    project.
    """
    require_tools(provider)
    script = Path(version_dir) / "scripts" / DELEGATED_INSTALLERS[provider]
    handle, owned_file = tempfile.mkstemp(prefix="devteam-owned-", suffix=".txt")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            for rel in sorted(set(owned or ())):
                stream.write(rel + "\n")
        return _run_installer(script, version_dir, project_root, ["--owned", owned_file])
    finally:
        try:
            os.unlink(owned_file)
        except OSError:
            pass


def install_opencode(version_dir, project_root, owned=None):
    return _install_delegated("opencode", version_dir, project_root, owned)


def install_codex(version_dir, project_root, owned=None):
    return _install_delegated("codex", version_dir, project_root, owned)


#: What the delegated installers recorded before they recorded files: whole
#: directories, one entry each. A directory entry claimed everything in it — the
#: project's own agents and skills included — so `unbind` quarantined them, and the
#: exclude block hid new ones from git. Kept only to recognise and migrate an old
#: manifest; never written.
LEGACY_DELEGATED_PATHS = {
    "opencode": (".opencode/agents", ".opencode/skills", ".opencode/plugins"),
    "codex": (".codex/agents", ".codex/skills", ".codex/hooks.json"),
}

#: The Codex hooks file. The project may carry its own hooks in it, so it is a
#: merged file like `.claude/settings.json`: `unbind` removes only the entries the
#: installer marked, never the file.
CODEX_HOOKS_FILE = ".codex/hooks.json"
#: Mirrors ``MANAGED_MARKER`` in `install-codex.sh`.
CODEX_HOOKS_MARKER = "_dev_team_agents_managed"


def is_legacy_delegated(item):
    """True for a manifest record in the pre-file-level, whole-directory shape."""
    provider = item.get("provider")
    return item.get("kind") == "delegated" and item.get("path") in LEGACY_DELEGATED_PATHS.get(
        provider, ()
    )


def legacy_owned(previous_artifacts, targets):
    """Targets an old, directory-level manifest implicitly claimed.

    A file under a directory the old manifest recorded, whose name is one the
    installer writes, is the file that installer overwrote on every previous run —
    whatever it held, the framework's copy replaced it. Anything else in that
    directory was never the framework's.
    """
    legacy_dirs = [
        item["path"] for item in previous_artifacts if is_legacy_delegated(item) and item.get("path")
    ]
    owned = []
    for rel in targets:
        if any(rel == d or rel.startswith(d + "/") for d in legacy_dirs):
            owned.append(rel)
    return owned


#: Files the installers **merge into** rather than own: the project's own config,
#: which carries the user's fields too. They are neither excluded from git nor
#: removed by ``unbind`` — the project commits them, exactly as it commits
#: ``.claude/settings.json``.
MERGED_PROJECT_FILES = {
    "opencode": (".opencode/opencode.json", ".opencode/opencode.jsonc", "opencode.json"),
    "codex": ("AGENTS.md",),
}


def merged_project_files(provider, project_root):
    """Project-owned files a delegated installer touched, for reporting only."""
    root = Path(project_root)
    return [
        rel for rel in MERGED_PROJECT_FILES.get(provider, ()) if (root / rel).exists()
    ]


def delegated_artifacts(provider, project_root, targets):
    """Manifest records for what a delegated installer actually wrote.

    One record per file or link the installer owns, never the directory holding
    it: `.codex/agents/` is shared with the project's own agents, and a directory
    record made `unbind`, the prune and the exclude block act on those too.

    Only paths that exist after the run are recorded, so a target the installer
    did not produce never becomes a phantom artifact. The Codex hooks file is
    recorded as ``codex-hooks``: merged into, not owned.
    """
    root = Path(project_root)
    records = []
    for rel in targets:
        candidate = root / rel
        if candidate.exists() or candidate.is_symlink():
            records.append({"path": rel, "kind": "delegated", "provider": provider})
    if provider == "codex" and (root / CODEX_HOOKS_FILE).is_file():
        records.append({"path": CODEX_HOOKS_FILE, "kind": "codex-hooks", "provider": provider})
    return records


def unwire_codex_hooks(project_root):
    """Remove only the hook groups `install-codex.sh` marked; keep the rest of the file.

    Returns the events that lost an entry. The file is left in place even when it
    ends up with no hooks: the project may commit it.
    """
    path = Path(project_root) / CODEX_HOOKS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    removed = []
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept = [
            group
            for group in groups
            if not (
                isinstance(group, dict)
                and any(
                    isinstance(hook, dict)
                    and CODEX_HOOKS_MARKER in (hook.get("statusMessage") or "")
                    for hook in group.get("hooks", [])
                )
            )
        ]
        if len(kept) != len(groups):
            removed.append(event)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event)
    if removed:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
    return sorted(removed)


#: Mirrors ``MANAGED_EVENTS`` in `install-codex.sh`.
CODEX_MANAGED_EVENTS = (
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "PreCompact",
    "Stop",
    "SessionEnd",
)
#: Where `install-opencode.sh` copies the plugin that wires opencode's hooks.
OPENCODE_PLUGIN_FILE = ".opencode/plugins/dev-team-agents.ts"
#: The slash commands `install-opencode.sh` registers are keyed ``devteam:<name>``.
OPENCODE_COMMAND_PREFIX = "devteam:"


def codex_hook_events(project_root):
    """Managed Codex events currently present in `.codex/hooks.json`."""
    path = Path(project_root) / CODEX_HOOKS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    found = []
    for event in CODEX_MANAGED_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        for group in groups:
            inner = group.get("hooks", []) if isinstance(group, dict) else []
            if any(
                isinstance(hook, dict) and CODEX_HOOKS_MARKER in (hook.get("statusMessage") or "")
                for hook in inner
            ):
                found.append(event)
                break
    return found


def unwire_opencode_commands(project_root):
    """Remove only the ``devteam:*`` command keys from the project's opencode config.

    Returns ``(removed, untouched)``: the number of keys removed and the project
    files left alone because they are not plain JSON (JSONC with comments or
    trailing commas) — those are reported, never rewritten.
    """
    root = Path(project_root)
    removed = 0
    untouched = []
    for rel in MERGED_PROJECT_FILES["opencode"]:
        path = root / rel
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError:
            untouched.append(rel)
            continue
        except ValueError:
            # A JSONC file the installer never wrote is no problem of ours.
            if OPENCODE_COMMAND_PREFIX in raw:
                untouched.append(rel)
            continue
        commands = data.get("command") if isinstance(data, dict) else None
        if not isinstance(commands, dict):
            continue
        ours = [key for key in commands if str(key).startswith(OPENCODE_COMMAND_PREFIX)]
        if not ours:
            continue
        for key in ours:
            commands.pop(key)
        if not commands:
            data.pop("command")
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        os.replace(str(tmp), str(path))
        removed += len(ours)
    return removed, untouched
