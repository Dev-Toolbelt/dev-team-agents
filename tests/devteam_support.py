"""Shared fixtures for the devteam CLI tests.

Every test points ``$DEVTEAM_HOME`` at a throwaway directory, so no test can
read or write a real user's store. ``StoreTestCase.setUp`` also clears **every other
environment seam the package reads**, and restores each one afterwards: a variable left
inherited from the developer's shell does not fail loudly, it quietly changes what the
suite exercises. A new seam added to ``devteam/`` belongs in that list on the same day.
The source tree fixture is deliberately tiny:
the real one carries 152 skills, and copying it per test would trade minutes of
CI time for no extra coverage.

**A throwaway directory is not enough on its own.** ``secrets.py`` stores credential
values in the *OS* secret store — on macOS the login keychain, through the ``security``
CLI — which lives outside ``$DEVTEAM_HOME`` entirely, so no temp directory and no
content-digest snapshot can see it and ``shutil.rmtree`` cannot undo it. Left
un-neutralised it was not theoretical: a full run wrote three items into the developer's
real keychain, one per random project id, from ``test_client_gate.py`` and
``test_json_contract.py`` — accumulating silently, one set per run. ``setUp`` therefore
pins ``TEST_PLATFORM`` and verifies the consequence; see the comment on that pin.
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

# Imported for the *names* of the environment seams `StoreTestCase` neutralises below,
# not for behaviour. A seam renamed in the package then breaks this import loudly instead
# of leaving the fixture clearing a variable nothing reads any more — which is the failure
# mode that matters, because a seam that stops being neutralised does not announce itself:
# it changes what the whole suite exercises. `DEVTEAM_HOSTNAME` is still a literal because
# `paths.machine_host()` reads it from an inline tuple and exports no constant for it.
from devteam import compat, paths, update  # noqa: E402  (needs the sys.path bootstrap above)
# Aliased, not imported bare: `secrets` is also a stdlib module name, and the shadowing
# trap `creds.py` documents at its own import of this module applies here identically.
from devteam import secrets as secrets_module  # noqa: E402  (same bootstrap as above)

#: The platform key every test runs under. Non-darwin and non-win32 on purpose — it is the
#: one seam the package exposes that reaches secret-backend selection. See the pin in
#: `StoreTestCase.setUp`.
TEST_PLATFORM = "linux"


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


def assert_local_secret_backend():
    """Fail the fixture if a test could still reach a real OS secret store.

    The platform pin in ``setUp`` is indirect: it selects a platform and *infers* a
    backend from what that platform can probe. That inference stops holding the day
    ``secrets.py`` gains a backend available on ``TEST_PLATFORM`` — a Secret Service /
    libsecret adapter is the obvious candidate — and it would stop holding silently,
    because an item written to an OS store is invisible to every check this suite makes:
    outside ``$DEVTEAM_HOME``, untouched by ``shutil.rmtree``, and not removable by the
    suite even in principle. So assert the consequence, not the cause.

    Probing is pure and cheap here: with a non-darwin, non-win32 platform key every probe
    short-circuits on the platform check alone, spawning no ``security`` process and
    touching no file. It deliberately does **not** call ``paths.secrets_dir()`` — that
    resolves a machine id and would create store state before a test has asked for any.
    """
    chosen = secrets_module.default_backend()
    if chosen != "insecure":
        raise AssertionError(
            "test fixture would write credential values to the {!r} backend, which is an "
            "OS secret store outside $DEVTEAM_HOME: a test writing to it leaves an item in "
            "the developer's real keychain that the suite cannot clean up. The "
            "DEVTEAM_PLATFORM pin in StoreTestCase.setUp no longer implies the local "
            "'insecure' backend — give secrets.py an explicit backend-selection seam "
            "rather than widening this one.".format(chosen)
        )


class StoreTestCase(unittest.TestCase):
    """Base class giving each test an isolated store and source tree."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="devteam-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.home = self.tmp / "store"
        self._saved_env = {
            key: os.environ.get(key)
            for key in (
                paths.HOME_ENV,
                paths.PLATFORM_ENV,
                paths.MACHINE_ID_ENV,
                "DEVTEAM_HOSTNAME",
                compat.CLIENT_SCHEMAS_ENV,
                update.SHA256_ENV,
            )
        }
        os.environ[paths.HOME_ENV] = str(self.home)
        # Pinned, not popped — and pinned for the secret backend, not for the layout.
        # `$DEVTEAM_HOME` redirects every path the package derives, but the OS secret
        # store is not a path: `secrets.py` shells out to `security` and writes into the
        # real login keychain, which no temp directory contains. `platform_key()` is the
        # only environment seam in the package that reaches backend selection, so a
        # non-darwin value makes `_probe_keychain()` short-circuit to "requires macOS";
        # `default_backend()` then resolves to `insecure`, whose file sits in
        # `paths.secrets_dir()` under `$DEVTEAM_HOME` and dies with the temp tree.
        #
        # It has to be an environment variable rather than a patch: the writes that
        # escaped came from `devteam cred set` in a **subprocess** (`run_cli`), which
        # inherits this environment and would not see any in-process monkeypatch.
        #
        # This is the mechanism `test_credentials.py` already applied per-class; it moved
        # here because the leak was never confined to that file. Safe for the rest of the
        # suite: with `$DEVTEAM_HOME` set, `core_dir()`/`data_dir()`/`cache_dir()` take the
        # override branch and never consult the platform key at all, so the only other
        # things it reaches are two informational `"platform"` strings. A test that wants a
        # specific platform still sets it after `super().setUp()`, as several already do.
        os.environ[paths.PLATFORM_ENV] = TEST_PLATFORM
        # A machine-id override leaking out of one test would silently give the next
        # one a store whose registry it cannot see.
        os.environ.pop(paths.MACHINE_ID_ENV, None)
        # Likewise a spoofed hostname: it decides whether a recorded machine-id is
        # adopted or re-issued, so it must not survive past the test that set it.
        os.environ.pop("DEVTEAM_HOSTNAME", None)
        # The client write gate: a declaration inherited from the developer's own shell
        # is checked against every mutating command the suite runs, so an exported
        # variable either refuses them with exit 4 or — the worse case — passes while
        # the tests exercise the *declared* path instead of the anonymous one they are
        # written for. Tests that want a declaration pass it explicitly.
        os.environ.pop(compat.CLIENT_SCHEMAS_ENV, None)
        # An out-of-band tarball digest pin belongs to a real download, never to a
        # fixture: exported, it turns `update.verify_digest`'s "no digest was published"
        # answer into a mismatch error on a payload it was never meant to describe.
        os.environ.pop(update.SHA256_ENV, None)
        self.addCleanup(self._restore_env)
        assert_local_secret_backend()
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

    def run_cli(self, *args, input_text=None):
        """Invoke the real entry point; returns ``(code, stdout, stderr)``.

        ``input_text``, when given, is written to the subprocess's stdin and
        closed — this is how a caller exercises a command that reads a value
        from stdin (`devteam cred set`) without ever putting it on the argv
        this call builds, which is the whole point of that design.
        """
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            input=input_text.encode("utf-8") if input_text is not None else None,
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
