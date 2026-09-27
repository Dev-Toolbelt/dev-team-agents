"""Per-provider bind artifacts.

Claude Code is materialised natively here, because its layout is a handful of
directory links. opencode and Codex are produced by the installers that already
exist (``install-opencode.sh``, ``install-codex.sh``), invoked with the store's
version directory as ``--source``: the render engine is not reimplemented, it is
pointed somewhere new.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .errors import EnvError

ALL_PROVIDERS = ("claude", "opencode", "codex")


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
_ENV_PASSTHROUGH = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "DEVTEAM_HOME", "TERM")
#: Installer stderr is surfaced as a hint; cap it so a chatty script cannot flood
#: the `--json` document the desktop app consumes.
_HINT_MAX = 2000


def _installer_env():
    env = {key: os.environ[key] for key in _ENV_PASSTHROUGH if key in os.environ}
    env.setdefault("PATH", os.defpath)
    return env


def _run_installer(script, version_dir, project_root, extra_args=None):
    if not script.is_file():
        raise EnvError("installer not found in the core version: {}".format(script))
    bash = shutil.which("bash")
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
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        if len(detail) > _HINT_MAX:
            detail = detail[:_HINT_MAX] + " […truncated]"
        raise EnvError(
            "{} failed (exit {})".format(script.name, result.returncode),
            hint=detail or None,
        )
    return result.stdout.decode("utf-8", "replace")


def require_tools(provider):
    """Fail early with a readable message instead of deep inside a bash script."""
    needed = {"opencode": ("bash", "python3", "jq"), "codex": ("bash", "python3")}.get(
        provider, ()
    )
    missing = [tool for tool in needed if shutil.which(tool) is None]
    if missing:
        raise EnvError(
            "provider {} needs {} on PATH".format(provider, ", ".join(missing)),
            hint=(
                "Install the missing tool(s) and retry, or bind without this provider. "
                "On Windows, bash comes from Git for Windows."
            ),
        )


def install_opencode(version_dir, project_root):
    require_tools("opencode")
    script = Path(version_dir) / "scripts" / "install-opencode.sh"
    return _run_installer(script, version_dir, project_root)


def install_codex(version_dir, project_root):
    require_tools("codex")
    script = Path(version_dir) / "scripts" / "install-codex.sh"
    return _run_installer(script, version_dir, project_root)


#: Project-relative paths each delegated installer writes. The list is the
#: contract between the bash installers and the manifest: anything not listed
#: here is invisible to ``unbind``, ``sync`` and ``doctor``.
DELEGATED_ARTIFACTS = {
    "opencode": (
        ".opencode/agents",
        ".opencode/skills",
        ".opencode/plugins",
    ),
    "codex": (
        ".codex/agents",
        ".codex/skills",
        ".codex/hooks.json",
    ),
}

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


def delegated_artifacts(provider, project_root):
    """Manifest records for what a delegated installer actually wrote.

    Recorded as ``kind: "delegated"`` in the same ``artifacts`` list as everything
    else, because a separate ``delegated`` key was written to the manifest and then
    read by nothing: ``unbind`` left 93 entries under ``.codex/`` behind while
    reporting "removed 0 artifact(s)", and ``doctor`` could not see a stale
    provider tree at all.

    Only paths that exist after the run are recorded, so a list entry the
    installer did not produce never becomes a phantom artifact.
    """
    root = Path(project_root)
    records = []
    for rel in DELEGATED_ARTIFACTS.get(provider, ()):  # declared order
        candidate = root / rel
        if candidate.exists() or candidate.is_symlink():
            records.append({"path": rel, "kind": "delegated", "provider": provider})
    return records
