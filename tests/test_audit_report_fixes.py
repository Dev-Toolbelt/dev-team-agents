"""Regression coverage for audit-report findings: installer CWD sourcing,
new-adr.sh title escaping, and preferences mirror drift."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import requires_bash

ROOT = Path(__file__).resolve().parent.parent


class InstallPipedDoesNotSourceCwdTest(unittest.TestCase):
    def test_piped_install_ignores_cwd_lib_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "proj"
            (cwd / "lib").mkdir(parents=True)
            marker = cwd / "PWNED"
            (cwd / "lib" / "state.sh").write_text(f"touch '{marker}'\n")
            # A curl that always fails keeps the run offline; sourcing happens
            # before any network call, so the trap would already have fired.
            bindir = Path(tmp) / "bin"
            bindir.mkdir()
            fake = bindir / "curl"
            fake.write_text("#!/bin/sh\nexit 22\n")
            fake.chmod(0o755)
            env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
            with open(ROOT / "scripts" / "install.sh", "rb") as script:
                subprocess.run(
                    ["bash"], stdin=script, cwd=cwd, env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=60, check=False,
                )
            self.assertFalse(marker.exists(), "install.sh sourced ./lib/state.sh from the CWD")


@requires_bash()
class NewAdrTitleEscapingTest(unittest.TestCase):
    def test_special_characters_survive_substitution(self) -> None:
        title = "Auth & sessions | v2 \\ path"
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp)
            scripts = proj / "scripts"
            (proj / "templates").mkdir()
            scripts.mkdir()
            shutil.copy(ROOT / "scripts" / "new-adr.sh", scripts / "new-adr.sh")
            shutil.copy(ROOT / "templates" / "adr-template.md", proj / "templates")
            res = subprocess.run(
                ["bash", str(scripts / "new-adr.sh"), title], cwd=proj,
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            created = list(proj.rglob("0*-*.md"))
            self.assertEqual(len(created), 1, res.stdout)
            self.assertIn(title, created[0].read_text(encoding="utf-8"))


class PreferencesMirrorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = list(json.loads(
            (ROOT / "scripts/lib/preferences-defaults.json").read_text(encoding="utf-8")))

    def _assert_all(self, path: str, fmt: str, text: str | None = None) -> None:
        text = text if text is not None else (ROOT / path).read_text(encoding="utf-8")
        missing = [k for k in self.keys if fmt % k not in text]
        self.assertEqual(missing, [], f"{path} is missing keys")

    def test_documentation_mirrors(self) -> None:
        for path in ("CLAUDE-md/preferences.md", "skills/shared/user-preferences/SKILL.md",
                     "docs/user-preferences.md", "docs/user-preferences.pt-BR.md"):
            self._assert_all(path, '"%s"')
            self._assert_all(path, "`%s`")

    def test_install_sh_fallback_heredoc(self) -> None:
        text = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
        start = text.index("# Fallback: write a plain JSON file without python3.")
        self._assert_all("scripts/install.sh", '"%s":', text[start:])


if __name__ == "__main__":
    unittest.main()
