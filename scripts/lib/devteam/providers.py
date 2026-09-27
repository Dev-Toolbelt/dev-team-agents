"""Per-provider bind artifacts.

Claude Code is materialised natively here, because its layout is a handful of
directory links. opencode and Codex are produced by the installers that already
exist (``install-opencode.sh``, ``install-codex.sh``), invoked with the store's
version directory as ``--source``: the render engine is not reimplemented, it is
pointed somewhere new.
"""

from __future__ import annotations

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


def _run_installer(script, version_dir, project_root, extra_args=None):
    if not script.is_file():
        raise EnvError("installer not found in the core version: {}".format(script))
    command = ["bash", str(script), "--source", str(version_dir)]
    if extra_args:
        command.extend(extra_args)
    result = subprocess.run(
        command,
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise EnvError(
            "{} failed (exit {})".format(script.name, result.returncode),
            hint=result.stderr.decode("utf-8", "replace").strip() or None,
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
            hint="Install the missing tool(s), or bind without this provider.",
        )


def install_opencode(version_dir, project_root):
    require_tools("opencode")
    script = Path(version_dir) / "scripts" / "install-opencode.sh"
    return _run_installer(script, version_dir, project_root)


def install_codex(version_dir, project_root):
    require_tools("codex")
    script = Path(version_dir) / "scripts" / "install-codex.sh"
    return _run_installer(script, version_dir, project_root)


#: Project-relative paths each delegated installer owns, used for the local
#: exclude block and for teardown. Directories end with a slash.
DELEGATED_ARTIFACTS = {
    "opencode": [".opencode/agents/", ".opencode/skills/", ".opencode/plugins/"],
    "codex": [".codex/agents/", ".codex/skills/", ".codex/hooks.json"],
}
