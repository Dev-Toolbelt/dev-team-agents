"""Coverage for the release renderers under `.github/scripts/release/`.

`render-winget-manifests.py` and `render-app-cask.py` turn the tracked scaffolds into the
manifests a release publishes. They run only inside the release workflow, so without these
tests the first execution would be a real tag. Like `test_release_bump.py` this module is
stdlib-only and drives the real scripts through ``subprocess`` against the real scaffolds,
asserting on the files written, not on stdout.

The four-edit consistency that `.github/scripts/ci/04-packaging.sh` enforces on the tracked
tree is checked here by running that same gate over the rendered output
(``WINGET_ROOT`` / ``PACKAGING_WINGET_ONLY``), when ``ruby`` and ``pyyaml`` are present.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".github" / "scripts" / "release"
WINGET = SCRIPTS / "render-winget-manifests.py"
CASK_RENDER = SCRIPTS / "render-app-cask.py"
GATE = REPO_ROOT / ".github" / "scripts" / "ci" / "04-packaging.sh"


def digest(name):
    return hashlib.sha256(name.encode()).hexdigest()


def run(script, *args, env=None):
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )


class RenderCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write_sums(self, names):
        path = self.tmp / "SHA256SUMS.txt"
        path.write_text("".join("{}  {}\n".format(digest(n), n) for n in names))
        return path


class WingetRenderTest(RenderCase):
    CLI = ["devteam-setup-1.2.3-x64.exe", "devteam-setup-1.2.3-arm64.exe"]
    APP = [
        "dev-team-agents-Setup-4.5.6-x64.exe",
        "dev-team-agents-Setup-4.5.6-arm64.exe",
    ]

    def render(self, package, tag, names):
        sums = self.write_sums(names)
        out = self.tmp / "out"
        result = run(WINGET, "--package", package, "--tag", tag,
                     "--sums", str(sums), "--out", str(out))
        return result, out

    def test_cli_manifests_land_in_the_versioned_directory_with_real_values(self):
        result, out = self.render("Devteam", "v1.2.3", self.CLI)
        self.assertEqual(result.returncode, 0, result.stderr)
        target = out / "d" / "DevToolbelt" / "Devteam" / "1.2.3"
        files = sorted(p.name for p in target.iterdir())
        self.assertEqual(len(files), 3, files)
        installer = (target / "DevToolbelt.Devteam.installer.yaml").read_text()
        self.assertIn("download/v1.2.3/devteam-setup-1.2.3-x64.exe", installer)
        self.assertIn('InstallerSha256: "%s"' % digest(self.CLI[0]), installer)
        self.assertIn('InstallerSha256: "%s"' % digest(self.CLI[1]), installer)
        for path in target.iterdir():
            text = path.read_text()
            self.assertIn("PackageVersion: 1.2.3", text)
            self.assertNotIn("0.0.0", text)
            self.assertNotIn("X.Y.Z", text)
            self.assertNotIn("0" * 64, text)

    def test_app_manifests_use_the_app_tag_and_asset_names(self):
        result, out = self.render("DevteamApp", "app-v4.5.6", self.APP)
        self.assertEqual(result.returncode, 0, result.stderr)
        installer = (out / "d/DevToolbelt/DevteamApp/4.5.6/DevToolbelt.DevteamApp.installer.yaml").read_text()
        self.assertIn("download/app-v4.5.6/dev-team-agents-Setup-4.5.6-arm64.exe", installer)

    def test_a_digest_missing_from_the_sums_file_is_refused(self):
        result, _ = self.render("Devteam", "v1.2.3", self.CLI[:1])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not listed", result.stderr)

    def test_a_tag_for_the_wrong_package_is_refused(self):
        result, _ = self.render("Devteam", "app-v1.2.3", self.CLI)
        self.assertNotEqual(result.returncode, 0)
        result, _ = self.render("DevteamApp", "v1.2.3", self.APP)
        self.assertNotEqual(result.returncode, 0)

    @unittest.skipUnless(shutil.which("ruby") and shutil.which("bash"), "gate needs ruby and bash")
    def test_the_repository_gate_accepts_the_rendered_tree(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("pyyaml is not installed")
        for package, tag, names in (("Devteam", "v1.2.3", self.CLI),
                                    ("DevteamApp", "app-v4.5.6", self.APP)):
            result, out = self.render(package, tag, names)
            self.assertEqual(result.returncode, 0, result.stderr)
        env = dict(os.environ, WINGET_ROOT=str(out), PACKAGING_WINGET_ONLY="1")
        gate = subprocess.run(["bash", str(GATE)], cwd=str(REPO_ROOT), env=env,
                              capture_output=True, text=True)
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        self.assertIn("all checks passed", gate.stdout)

    @unittest.skipUnless(shutil.which("ruby") and shutil.which("bash"), "gate needs ruby and bash")
    def test_the_gate_rejects_a_rendered_tree_whose_directory_was_not_renamed(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("pyyaml is not installed")
        result, out = self.render("Devteam", "v1.2.3", self.CLI)
        self.assertEqual(result.returncode, 0, result.stderr)
        base = out / "d" / "DevToolbelt" / "Devteam"
        (base / "1.2.3").rename(base / "0.0.0")
        env = dict(os.environ, WINGET_ROOT=str(out), PACKAGING_WINGET_ONLY="1")
        gate = subprocess.run(["bash", str(GATE)], cwd=str(REPO_ROOT), env=env,
                              capture_output=True, text=True)
        self.assertNotEqual(gate.returncode, 0)


class CaskRenderTest(RenderCase):
    def test_version_and_digest_are_rewritten_and_comments_dropped(self):
        dmg = "dev-team-agents-4.5.6.dmg"
        sums = self.write_sums([dmg])
        out = self.tmp / "devteam-app.rb"
        result = run(CASK_RENDER, "--tag", "app-v4.5.6", "--sums", str(sums), "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        text = out.read_text()
        self.assertRegex(text, r'(?m)^  version "4\.5\.6"$')
        self.assertIn('sha256 "%s"' % digest(dmg), text)
        self.assertNotIn("0.0.0-unreleased", text)
        self.assertNotIn("NO_RELEASE_SHA256", text)
        self.assertIn("app-v#{version}/dev-team-agents-#{version}.dmg", text)
        self.assertIsNone(re.search(r"(?m)^\s*#", text), "comments describe the scaffold and must go")
        self.assertIn('depends_on formula: "devteam"', text)

    @unittest.skipUnless(shutil.which("ruby"), "ruby not installed")
    def test_the_rendered_cask_parses(self):
        dmg = "dev-team-agents-4.5.6.dmg"
        sums = self.write_sums([dmg])
        out = self.tmp / "devteam-app.rb"
        run(CASK_RENDER, "--tag", "app-v4.5.6", "--sums", str(sums), "--out", str(out))
        check = subprocess.run(["ruby", "-c", str(out)], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_a_missing_dmg_digest_is_refused(self):
        sums = self.write_sums(["something-else.dmg"])
        result = run(CASK_RENDER, "--tag", "app-v4.5.6", "--sums", str(sums),
                     "--out", str(self.tmp / "x.rb"))
        self.assertNotEqual(result.returncode, 0)

    def test_a_framework_tag_is_refused(self):
        sums = self.write_sums(["dev-team-agents-4.5.6.dmg"])
        result = run(CASK_RENDER, "--tag", "v4.5.6", "--sums", str(sums),
                     "--out", str(self.tmp / "x.rb"))
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
