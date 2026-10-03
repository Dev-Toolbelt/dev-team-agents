"""scripts/install-cli.sh — the macOS/Linux CLI bootstrap (ADR-0028), run for real from this tree.

`--from` the repository, so nothing is downloaded; DEVTEAM_HOME, DEVTEAM_CLI_HOME and
DEVTEAM_BIN_DIR keep every write inside a temporary directory.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
from devteam.providers import ALL_PROVIDERS  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "install-cli.sh"

#: What a bind through the installed CLI must leave in a project, per provider. One entry per
#: provider in `ALL_PROVIDERS`: the parity guard below fails the moment a provider is added
#: without its own case.
BIND_ARTIFACT = {
    "claude": ".claude",
    "opencode": ".opencode",
    "codex": ".codex",
}


@requires_bash()
@unittest.skipIf(sys.platform.startswith("win"), "install-cli.sh is the macOS/Linux channel; Windows has the NSIS installer")
class InstallCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="install-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = dict(
            os.environ,
            DEVTEAM_HOME=str(self.tmp / "home"),
            DEVTEAM_CLI_HOME=str(self.tmp / "cli"),
            DEVTEAM_BIN_DIR=str(self.tmp / "bin"),
        )
        self.bin = self.tmp / "bin" / "devteam"

    def _install(self, source=REPO_ROOT):
        return subprocess.run(
            ["bash", str(SCRIPT), "--from", str(source)],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=300,
        )

    def _devteam(self, *args):
        return subprocess.run(
            [str(self.bin), *args], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=60,
        )

    def test_installs_the_cli_and_the_framework_into_the_store(self):
        result = self._install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.access(str(self.bin), os.X_OK))
        listed = self._devteam("store", "list", "--json")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn('"current"', listed.stdout)

    def test_the_account_identity_ships_beside_the_package(self):
        self.assertEqual(self._install().returncode, 0)
        self.assertTrue((self.tmp / "cli" / "scripts" / "lib" / "auth-config.json").is_file())

    def test_the_launcher_names_the_verified_interpreter_by_absolute_path(self):
        self.assertEqual(self._install().returncode, 0)
        launcher = self.bin.read_text(encoding="utf-8")
        self.assertTrue(launcher.startswith("#!/bin/sh\n"), launcher)
        self.assertNotIn("env python3", launcher)

    def test_a_space_in_the_install_paths_does_not_break_the_launcher(self):
        spaced = self.tmp / "Ana Maria"
        self.env.update(DEVTEAM_CLI_HOME=str(spaced / "cli"), DEVTEAM_BIN_DIR=str(spaced / "bin"))
        self.bin = spaced / "bin" / "devteam"
        result = self._install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._devteam("store", "list", "--json").returncode, 0)

    def test_a_relative_bin_dir_still_gives_a_working_launcher(self):
        self.env.update(DEVTEAM_BIN_DIR="relative-bin")
        result = subprocess.run(
            ["bash", str(SCRIPT), "--from", str(REPO_ROOT)], cwd=str(self.tmp),
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.bin = self.tmp / "relative-bin" / "devteam"
        self.assertEqual(self._devteam("store", "list", "--json").returncode, 0)

    def test_the_newest_release_is_picked_by_version_and_bare_tags_are_ignored(self):
        # A fake curl: the releases listing, then a failed download that names the tag.
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        listing = (
            '[{"tag_name": "app-v9.0.0"}, {"tag_name": "v2.10.0"}, {"tag_name": "v2.9.0"},'
            ' {"tag_name": "v3.0.0", "draft": true}, {"tag_name": "v2.11.0", "prerelease": true}]'
        )
        curl = stubs / "curl"
        curl.write_text(
            '#!/bin/sh\ncase "$*" in *api.github.com*releases*) echo \'{}\' ;; *) echo "$*" >&2; exit 22 ;; esac\n'.format(listing)
        )
        curl.chmod(0o755)
        self.env["PATH"] = str(stubs) + os.pathsep + self.env["PATH"]
        result = subprocess.run(
            ["bash", str(SCRIPT)], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=60,
        )
        self.assertIn("Downloading v2.10.0", result.stdout)
        self.assertIn("archive/refs/tags/v2.10.0.tar.gz", result.stderr)
        self.assertNotEqual(result.returncode, 0)

    def test_a_second_run_succeeds_and_leaves_the_store_alone(self):
        self.assertEqual(self._install().returncode, 0)
        before = sorted(p.name for p in (self.tmp / "home").rglob("*"))
        again = self._install()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("already in the store", again.stdout)
        self.assertEqual(sorted(p.name for p in (self.tmp / "home").rglob("*")), before)

    def test_every_provider_has_a_bind_case(self):
        self.assertEqual(set(BIND_ARTIFACT), set(ALL_PROVIDERS))

    def test_the_installed_cli_binds_a_project_for_every_provider(self):
        self.assertEqual(self._install().returncode, 0)
        for provider in ALL_PROVIDERS:
            with self.subTest(provider=provider):
                project = self.tmp / "project-{}".format(provider)
                project.mkdir()
                subprocess.run(["git", "init", "-q", str(project)], check=True)
                bound = self._devteam("bind", str(project), "--provider", provider)
                self.assertEqual(bound.returncode, 0, bound.stderr)
                self.assertTrue((project / BIND_ARTIFACT[provider]).is_dir(), provider)

    def test_a_directory_that_is_not_a_tree_is_refused_before_anything_is_written(self):
        result = self._install(source=self.tmp)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a dev-team-agents tree", result.stderr)
        self.assertFalse(self.bin.exists())


if __name__ == "__main__":
    unittest.main()
