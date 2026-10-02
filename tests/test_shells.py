"""devteam.shells — the bash a shell script runs with, never WSL's launcher on Windows."""

import unittest

import devteam_support  # noqa: F401  (puts scripts/lib on sys.path)
from devteam import shells

GIT = "C:\\Program Files\\Git\\bin\\bash.exe"
WSL = "C:\\Windows\\System32\\bash.exe"
STORE = "C:\\Users\\u\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe"


def which(found):
    return lambda name: found if name == "bash" else None


class BashPathTest(unittest.TestCase):
    def test_posix_takes_bash_from_path_unchanged(self):
        self.assertEqual(shells.bash_path(windows=False, which=which("/usr/bin/bash")), "/usr/bin/bash")
        self.assertIsNone(shells.bash_path(windows=False, which=which(None)))

    def test_windows_takes_a_git_bash_found_on_path(self):
        self.assertEqual(shells.bash_path(windows=True, which=which(GIT), environ={}), GIT)

    def test_windows_never_takes_the_wsl_launcher_or_the_store_alias(self):
        env = {"ProgramFiles": "C:\\Program Files"}
        for stub in (WSL, STORE, WSL.lower(), WSL.replace("\\", "/")):
            with self.subTest(stub=stub):
                found = shells.bash_path(windows=True, which=which(stub), environ=env, isfile=lambda p: p == GIT)
                self.assertEqual(found, GIT)

    def test_windows_without_git_bash_finds_nothing_rather_than_wsl(self):
        self.assertIsNone(shells.bash_path(windows=True, which=which(WSL), environ={}, isfile=lambda p: False))


if __name__ == "__main__":
    unittest.main()
