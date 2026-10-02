"""scripts/lib/python.sh — `python3` resolves to a working interpreter on Windows Git Bash.

Windows is simulated with ``DEVTEAM_PLATFORM=win32`` and a PATH whose first directory
holds stubs: a broken ``python3`` (the Microsoft Store alias exits 9009), and, per case,
a working ``python`` or ``py`` that forwards to the interpreter running these tests.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT, requires_bash

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
from devteam import providers  # noqa: E402
from devteam.errors import EnvError  # noqa: E402

LAUNCHER = REPO_ROOT / "scripts" / "lib" / "python.sh"
STATE_LIB = REPO_ROOT / "scripts" / "lib" / "state.sh"

BROKEN = '#!/bin/sh\necho "Python was not found; run without arguments to install from the Microsoft Store" >&2\nexit 9009\n'


def _forward(log, drop_flag=False):
    shift = '[ "$1" = "-3" ] && shift\n' if drop_flag else ""
    return '#!/bin/sh\necho "$0 $*" >> "{}"\n{}exec "{}" "$@"\n'.format(log, shift, sys.executable)


@requires_bash()
class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="py-launcher-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.stubs = self.tmp / "bin"
        self.stubs.mkdir()
        self.log = self.tmp / "calls.log"

    def _stub(self, name, body):
        path = self.stubs / name
        path.write_text(body)
        path.chmod(0o755)

    def _run(self, script, platform="win32", extra_env=None):
        env = {
            "PATH": os.pathsep.join([str(self.stubs), os.path.dirname(shutil.which("bash")), "/usr/bin", "/bin"]),
            "HOME": str(self.tmp),
            "DEVTEAM_PLATFORM": platform,
        }
        env.update(extra_env or {})
        return subprocess.run(
            ["bash", "-c", '. "{}"\n{}'.format(LAUNCHER, script)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60, check=False,
        )

    def test_a_broken_python3_falls_back_to_python(self):
        self._stub("python3", BROKEN)
        self._stub("python", _forward(self.log))
        result = self._run('python3 -c "print(6 * 7)"; echo "picked=$DTA_PYTHON"')
        self.assertEqual(result.stdout.split(), ["42", "picked=python"], result.stderr)

    def test_only_py_is_reached_with_its_version_flag(self):
        self._stub("python3", BROKEN)
        self._stub("python", BROKEN)
        self._stub("py", _forward(self.log, drop_flag=True))
        result = self._run('python3 -c "print(1)"; echo "picked=$DTA_PYTHON $DTA_PYTHON_FLAG"')
        self.assertEqual(result.stdout.split(), ["1", "picked=py", "-3"], result.stderr)

    def test_a_working_python3_on_windows_needs_no_shim(self):
        self._stub("python3", _forward(self.log))
        result = self._run('echo "$(type -t python3) $DTA_PYTHON"')
        self.assertEqual(result.stdout.split(), ["file", "python3"])

    def test_bash_children_inherit_the_shim_without_sourcing_anything(self):
        self._stub("python3", BROKEN)
        self._stub("python", _forward(self.log))
        result = self._run("bash -c 'command -v python3 >/dev/null && python3 -c \"print(7)\"'")
        self.assertEqual(result.stdout.strip(), "7", result.stderr)

    def test_nothing_working_leaves_python3_alone(self):
        self._stub("python3", BROKEN)
        self._stub("python", BROKEN)
        result = self._run('echo "$(type -t python3) [${DTA_PYTHON:-}]"')
        self.assertEqual(result.stdout.split(), ["file", "[]"])

    def test_posix_with_python3_probes_nothing(self):
        self._stub("python3", _forward(self.log))
        result = self._run('echo "$(type -t python3) [${DTA_PYTHON:-}]"', platform="linux")
        self.assertEqual(result.stdout.split(), ["file", "[]"])
        self.assertFalse(self.log.exists(), "a POSIX python3 on PATH must not even be probed")

    def test_an_explicit_interpreter_wins(self):
        self._stub("python3", BROKEN)
        result = self._run('python3 -c "print(3)"; echo "picked=$DTA_PYTHON"', platform="linux",
                           extra_env={"DEVTEAM_PYTHON": sys.executable})
        self.assertEqual(result.stdout.split(), ["3", "picked=" + sys.executable], result.stderr)

    def test_windows_runs_python_in_utf8_mode_and_posix_is_left_alone(self):
        self._stub("python3", _forward(self.log))
        self.assertEqual(self._run('echo "[${PYTHONUTF8:-}]"').stdout.strip(), "[1]")
        self.assertEqual(self._run('echo "[${PYTHONUTF8:-}]"', platform="linux").stdout.strip(), "[]")
        self.assertEqual(self._run('echo "[$PYTHONUTF8]"', extra_env={"PYTHONUTF8": "0"}).stdout.strip(), "[0]")

    def test_a_shipped_library_reaches_the_resolved_interpreter(self):
        self._stub("python3", BROKEN)
        self._stub("python", _forward(self.log))
        state = self.tmp / "state.json"
        result = self._run('. "{}"; state_set greeting "a \\"quoted\\" value" "{}"; state_get greeting "{}"'.format(
            STATE_LIB, state, state))
        self.assertEqual(result.stdout.strip(), 'a "quoted" value', result.stderr)
        self.assertTrue(self.log.read_text().strip(), "state.sh never ran the resolved python")


class RequireToolsTest(unittest.TestCase):
    #: What each provider's installer needs besides python. A provider added to
    #: ALL_PROVIDERS without a row here fails the test.
    NEEDS = {"claude": (), "opencode": ("bash", "jq"), "codex": ("bash",)}

    def test_every_provider_accepts_a_machine_without_python3_on_path(self):
        self.assertEqual(set(self.NEEDS), set(providers.ALL_PROVIDERS))
        no_python = lambda tool: None if tool in ("python3", "python", "py") else "/usr/bin/" + tool  # noqa: E731
        for provider in providers.ALL_PROVIDERS:
            with self.subTest(provider=provider), mock.patch.object(providers.shutil, "which", no_python):
                providers.require_tools(provider)

    def test_a_missing_non_python_tool_is_still_refused(self):
        for provider, needs in self.NEEDS.items():
            for tool in needs:
                which = lambda name, _t=tool: None if name == _t else "/usr/bin/" + name  # noqa: E731
                # bash is resolved through devteam.shells, which also probes Git for Windows' folders.
                found_bash = None if tool == "bash" else "/usr/bin/bash"
                with self.subTest(provider=provider, tool=tool), mock.patch.object(providers.shutil, "which", which), \
                        mock.patch.object(providers.shells, "bash_path", return_value=found_bash):
                    with self.assertRaises(EnvError):
                        providers.require_tools(provider)

    def test_installers_are_told_which_interpreter_runs_the_cli(self):
        self.assertEqual(providers._installer_env()["DEVTEAM_PYTHON"], sys.executable)


if __name__ == "__main__":
    unittest.main()
