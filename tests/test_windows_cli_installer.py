"""packaging/windows-cli — the Windows CLI installer (ADR-0028), as far as a non-Windows host can prove it.

What runs here: the PATH edit logic, the launcher's payload (Python executes a zip that
follows arbitrary prefix bytes on every platform, so the CLI really is started through
it), the staged layout the NSIS script copies, and the pins. What does not: the NSIS
wizard, the registry write and the distlib stub itself — the release workflow installs
silently on a Windows runner for those.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from devteam_support import REPO_ROOT

HERE = REPO_ROOT / "packaging" / "windows-cli"


def _load(name):
    spec = importlib.util.spec_from_file_location("windows_cli_" + name, str(HERE / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


postinstall = _load("postinstall")
build = _load("build")


class UserPathTest(unittest.TestCase):
    BIN = r"C:\Users\Ana\AppData\Local\Programs\devteam\bin"

    def test_appends_to_an_existing_path_and_keeps_it_as_written(self):
        current = r"%USERPROFILE%\bin;C:\tools;"
        self.assertEqual(postinstall.path_with(current, self.BIN), r"%USERPROFILE%\bin;C:\tools;" + self.BIN)

    def test_an_empty_path_becomes_the_entry(self):
        self.assertEqual(postinstall.path_with("", self.BIN), self.BIN)

    def test_an_entry_already_present_in_another_case_or_with_a_slash_is_not_added_twice(self):
        current = r"C:\tools;" + self.BIN.upper() + "\\"
        self.assertEqual(postinstall.path_with(current, self.BIN), current)

    def test_removal_takes_every_copy_and_nothing_else(self):
        current = r"C:\tools;{0};C:\other;{0}\\".format(self.BIN)
        self.assertEqual(postinstall.path_without(current, self.BIN), r"C:\tools;C:\other")

    def test_removal_from_a_path_without_the_entry_changes_nothing(self):
        self.assertEqual(postinstall.path_without(r"C:\tools", self.BIN), r"C:\tools")


class LauncherPayloadTest(unittest.TestCase):
    def test_the_payload_after_the_stub_runs_the_cli(self):
        tmp = Path(tempfile.mkdtemp(prefix="win-launcher-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        cli = REPO_ROOT / "scripts" / "cli" / "devteam"
        exe = tmp / "devteam.exe"
        exe.write_bytes(postinstall.launcher_bytes(b"MZ-not-a-real-stub" * 64, sys.executable, str(cli)))

        # What distlib's stub does: run the interpreter on its own file.
        result = subprocess.run(
            [sys.executable, str(exe), "path", "--json"],
            env=dict(os.environ, DEVTEAM_HOME=str(tmp / "home")),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", json.loads(result.stdout))

    def test_the_payload_runs_under_an_isolated_interpreter_like_the_embeddable_one(self):
        # The embeddable distribution's `._pth` gives an isolated sys.path with no `site`
        # and no script directory. `-I -S` is the closest a non-Windows host gets to it.
        tmp = Path(tempfile.mkdtemp(prefix="win-launcher-isolated-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        exe = tmp / "devteam.exe"
        cli = REPO_ROOT / "scripts" / "cli" / "devteam"
        exe.write_bytes(postinstall.launcher_bytes(b"MZ", sys.executable, str(cli)))
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(exe), "version", "--json"],
            env=dict(os.environ, DEVTEAM_HOME=str(tmp / "home")),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("compat", json.loads(result.stdout))

    def test_the_shebang_quotes_an_interpreter_path_with_spaces(self):
        data = postinstall.launcher_bytes(b"STUB", r"C:\Users\Ana Maria\python\python.exe", "cli")
        self.assertTrue(data.startswith(b'STUB#!"C:\\Users\\Ana Maria\\python\\python.exe"\r\n'))


class FakeWinreg:
    """The slice of `winreg` postinstall uses, over one in-memory value."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_READ, KEY_WRITE = 1, 2
    REG_SZ, REG_EXPAND_SZ, REG_DWORD = 1, 2, 4

    def __init__(self, value=None, kind=2):
        self.value, self.kind, self.writes = value, kind, []

    def OpenKey(self, root, path, reserved, access):
        return contextlib.nullcontext(self)

    def QueryValueEx(self, key, name):
        if self.value is None:
            raise FileNotFoundError(name)
        return self.value, self.kind

    def SetValueEx(self, key, name, reserved, kind, value):
        self.writes.append((kind, value))
        self.value, self.kind = value, kind


class EditUserPathTest(unittest.TestCase):
    BIN = r"C:\Users\Ana\AppData\Local\Programs\devteam\bin"

    def _edit(self, fake, transform):
        with mock.patch.dict(sys.modules, {"winreg": fake}), \
                mock.patch.object(postinstall, "_broadcast_environment_change") as broadcast:
            changed = postinstall._edit_user_path(transform)
        return changed, broadcast

    def test_appends_and_keeps_the_value_type(self):
        fake = FakeWinreg(r"%USERPROFILE%\bin", kind=FakeWinreg.REG_EXPAND_SZ)
        changed, broadcast = self._edit(fake, lambda cur: postinstall.path_with(cur, self.BIN))
        self.assertTrue(changed)
        self.assertEqual(fake.writes, [(FakeWinreg.REG_EXPAND_SZ, r"%USERPROFILE%\bin;" + self.BIN)])
        broadcast.assert_called_once()

    def test_creates_the_value_when_the_user_has_no_path(self):
        fake = FakeWinreg(None)
        self._edit(fake, lambda cur: postinstall.path_with(cur, self.BIN))
        self.assertEqual(fake.writes, [(FakeWinreg.REG_EXPAND_SZ, self.BIN)])

    def test_writes_nothing_and_broadcasts_nothing_when_unchanged(self):
        fake = FakeWinreg(self.BIN, kind=FakeWinreg.REG_SZ)
        changed, broadcast = self._edit(fake, lambda cur: postinstall.path_with(cur, self.BIN))
        self.assertFalse(changed)
        self.assertEqual(fake.writes, [])
        broadcast.assert_not_called()

    def test_an_unexpected_value_type_is_rewritten_as_expandable(self):
        fake = FakeWinreg(r"C:\tools", kind=FakeWinreg.REG_DWORD)
        self._edit(fake, lambda cur: postinstall.path_with(cur, self.BIN))
        self.assertEqual(fake.writes[0][0], FakeWinreg.REG_EXPAND_SZ)


class WriteLauncherTest(unittest.TestCase):
    def test_an_existing_launcher_is_moved_aside_then_replaced(self):
        tmp = Path(tempfile.mkdtemp(prefix="win-write-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        exe = tmp / "devteam.exe"
        exe.write_bytes(b"old")
        postinstall.write_launcher(str(exe), b"new")
        postinstall.write_launcher(str(exe), b"newer")
        self.assertEqual(exe.read_bytes(), b"newer")
        self.assertEqual((tmp / "devteam.exe.old").read_bytes(), b"new")


class StoreInstallTest(unittest.TestCase):
    def _run(self, returncode, output=""):
        completed = subprocess.CompletedProcess([], returncode, stdout=output)
        with mock.patch.object(postinstall.subprocess, "run", return_value=completed):
            return postinstall.store_install(postinstall.paths(r"C:\devteam"))

    def test_success_and_already_installed_both_pass(self):
        self.assertEqual(self._run(0, "installed 3.0.0"), 0)
        self.assertEqual(self._run(postinstall.EXIT_CONFLICT), 0)

    def test_any_other_exit_is_returned(self):
        self.assertEqual(self._run(3, "no store"), 3)


def _zip(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class StageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="win-stage-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _stage(self):
        embedded = _zip({"python.exe": b"py", "python314._pth": b"python314.zip\n."})
        wheel = _zip({"distlib/t64.exe": b"stub-x64"})
        pins = {
            "python": {"x64": {"url": "https://example.invalid/py.zip", "sha256": hashlib.sha256(embedded).hexdigest()}},
            "launcher": {
                "wheel_url": "https://example.invalid/distlib.whl",
                "wheel_sha256": hashlib.sha256(wheel).hexdigest(),
                "x64": {"member": "distlib/t64.exe", "sha256": hashlib.sha256(b"stub-x64").hexdigest()},
            },
        }
        downloads = {pins["python"]["x64"]["url"]: embedded, pins["launcher"]["wheel_url"]: wheel}
        root = self.tmp / "stage"
        with mock.patch.object(build, "fetch", lambda url, digest: downloads[url]):
            build.stage("x64", REPO_ROOT, pins, root)
        return root

    def test_the_stage_holds_what_the_nsis_script_copies(self):
        root = self._stage()
        nsi = (HERE / "devteam-cli.nsi").read_text(encoding="utf-8")
        copied = re.findall(r'File (?:/r )?"\$\{STAGE\}\\([^"]+)"', nsi)
        self.assertEqual(sorted(copied), sorted(path.name for path in root.iterdir()))

    def test_the_cli_is_laid_out_as_the_homebrew_formula_installs_it(self):
        root = self._stage()
        self.assertTrue((root / "cli" / "scripts" / "cli" / "devteam").is_file())
        self.assertTrue((root / "cli" / "scripts" / "lib" / "devteam" / "cli.py").is_file())
        self.assertTrue((root / "cli" / "scripts" / "lib" / "devteam" / "integrations").is_dir())
        self.assertEqual(list(root.rglob("__pycache__")), [])
        self.assertEqual((root / "launcher" / "launcher.exe").read_bytes(), b"stub-x64")
        self.assertTrue((root / "python" / "python.exe").is_file())

    def test_the_payload_is_a_tree_store_install_accepts(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
        from devteam import versions

        payload = self._stage() / "payload"
        for name in versions.CORE_TREES:
            self.assertTrue((payload / name).is_dir(), name)
        self.assertEqual(versions.version_from_tree(payload), versions.version_from_tree(REPO_ROOT))

    def test_a_launcher_stub_that_does_not_match_its_pin_is_refused(self):
        wheel = _zip({"distlib/t64.exe": b"tampered"})
        embedded = _zip({"python.exe": b"py"})
        pins = {
            "python": {"x64": {"url": "u1", "sha256": "x"}},
            "launcher": {"wheel_url": "u2", "wheel_sha256": "y",
                         "x64": {"member": "distlib/t64.exe", "sha256": hashlib.sha256(b"stub").hexdigest()}},
        }
        with mock.patch.object(build, "fetch", lambda url, digest: {"u1": embedded, "u2": wheel}[url]):
            with self.assertRaises(SystemExit):
                build.stage("x64", REPO_ROOT, pins, self.tmp / "stage")


class PinsTest(unittest.TestCase):
    def test_every_architecture_has_a_pinned_python_and_launcher(self):
        pins = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))
        digest = re.compile(r"^[0-9a-f]{64}$")
        self.assertRegex(pins["launcher"]["wheel_sha256"], digest)
        for arch in build.ARCHES:
            self.assertTrue(pins["python"][arch]["url"].startswith("https://www.python.org/ftp/python/"), arch)
            self.assertRegex(pins["python"][arch]["sha256"], digest)
            self.assertIn(pins["python"]["version"], pins["python"][arch]["url"])
            self.assertRegex(pins["launcher"][arch]["sha256"], digest)


if __name__ == "__main__":
    unittest.main()
