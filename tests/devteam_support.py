"""Shared fixtures for the devteam CLI tests.

Every test points ``$DEVTEAM_HOME`` at a throwaway directory, so no test can
read or write a real user's store. The source tree fixture is deliberately tiny:
the real one carries 152 skills, and copying it per test would trade minutes of
CI time for no extra coverage.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))

CLI = REPO_ROOT / "scripts" / "cli" / "devteam"


def make_source_tree(root, version="3.0.0", skills=("shared/project-context", "testing/unit")):
    """A minimal but structurally faithful dev-team-agents tree."""
    root = Path(root)
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "backend-developer.md").write_text("# agent\n", encoding="utf-8")
    (root / "commands").mkdir(parents=True, exist_ok=True)
    (root / "commands" / "plan.md").write_text("# command\n", encoding="utf-8")
    (root / "templates").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "plan-template.md").write_text("# template\n", encoding="utf-8")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "noop.sh").write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
    (root / "scripts" / "new-adr.sh").write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
    # The hook dispatchers a bind registers in settings.json must exist in the
    # version, or a test cannot tell a wired path from a dangling one.
    # The canonical preference schema: every bind resolves the cascade against it.
    (root / "scripts" / "lib").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "lib" / "preferences-defaults.json").write_text(
        json.dumps(
            {
                "language": "pt-BR",
                "auto_update": True,
                "telemetry": True,
                "worktree_active": True,
                "worktree_base_branch": None,
                "session_summary_max_days": 30,
                "qa_browser": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
    for script in ("pre-tool-use.sh", "stop.sh", "session-start.sh", "pre-compact.sh"):
        (root / "scripts" / "hooks" / script).write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
        )
    for rel in skills:
        skill_dir = root / "skills" / rel
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: {}\ndescription: test\n---\n".format(Path(rel).name), encoding="utf-8"
        )
    # A depth-1 skill: the layout the v2 installer's two-level loop skipped.
    top = root / "skills" / "skill-creator"
    top.mkdir(parents=True, exist_ok=True)
    (top / "SKILL.md").write_text("---\nname: skill-creator\n---\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [{}] - 2026-09-27\n\n- test\n".format(version), encoding="utf-8"
    )
    return root


def make_git_project(root, name="app"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "README.md").write_text("# {}\n".format(name), encoding="utf-8")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
    for command in (["git", "init", "-q", "."], ["git", "add", "-A"], ["git", "commit", "-qm", "init"]):
        subprocess.run(command, cwd=str(root), check=True, env=env, stdout=subprocess.DEVNULL)
    return root


class StoreTestCase(unittest.TestCase):
    """Base class giving each test an isolated store and source tree."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="devteam-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.home = self.tmp / "store"
        self._saved_env = {
            key: os.environ.get(key)
            for key in (
                "DEVTEAM_HOME",
                "DEVTEAM_PLATFORM",
                "DEVTEAM_MACHINE_ID",
                "DEVTEAM_HOSTNAME",
            )
        }
        os.environ["DEVTEAM_HOME"] = str(self.home)
        os.environ.pop("DEVTEAM_PLATFORM", None)
        # A machine-id override leaking out of one test would silently give the next
        # one a store whose registry it cannot see.
        os.environ.pop("DEVTEAM_MACHINE_ID", None)
        # Likewise a spoofed hostname: it decides whether a recorded machine-id is
        # adopted or re-issued, so it must not survive past the test that set it.
        os.environ.pop("DEVTEAM_HOSTNAME", None)
        self.addCleanup(self._restore_env)
        self.source = make_source_tree(self.tmp / "source")

    def _restore_env(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def install_version(self, version, activate=None):
        from devteam import versions

        make_source_tree(self.tmp / "source", version=version)
        return versions.install_from_tree(
            self.tmp / "source", version=version, force=True, make_current=activate
        )

    def new_project(self, name="app"):
        return make_git_project(self.tmp / name, name=name)

    def run_cli(self, *args):
        """Invoke the real entry point; returns ``(code, stdout, stderr)``."""
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
            check=False,
        )
        return (
            result.returncode,
            result.stdout.decode("utf-8", "replace"),
            result.stderr.decode("utf-8", "replace"),
        )
