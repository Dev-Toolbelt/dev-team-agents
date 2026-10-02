"""Shell portability regressions: stat/date helpers and the bash 3.2 gate."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

HELPER = REPO_ROOT / "scripts" / "hooks" / "lib" / "file-stat.sh"
GATE = REPO_ROOT / ".github" / "scripts" / "ci" / "06-bash32.sh"


def _sh(snippet: str, shell: str = "bash") -> str:
    return subprocess.run(
        [shell, "-c", f'. "{HELPER}"; {snippet}'],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


@requires_bash()
class FileStatHelpers(unittest.TestCase):
    def test_mtime_and_size_are_integers_on_host_stat(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b"12345")
            f.flush()
            mtime = _sh(f'dt_file_mtime "{f.name}"')
            size = _sh(f'dt_file_size "{f.name}"')
        self.assertTrue(mtime.isdigit(), mtime)
        self.assertGreater(int(mtime), 1_000_000_000)
        self.assertEqual(size, "5")

    def test_missing_file_is_zero(self):
        self.assertEqual(_sh('dt_file_mtime /nonexistent/x'), "0")

    def test_date_to_epoch(self):
        epoch = _sh('dt_date_to_epoch 2026-01-01')
        self.assertTrue(epoch.isdigit(), epoch)
        self.assertLess(abs(int(epoch) - 1767225600), 86400)
        self.assertEqual(_sh('dt_date_to_epoch garbage || echo none'), "none")

    @unittest.skipUnless(Path("/bin/bash").exists(), "no /bin/bash")
    def test_helpers_under_system_bash(self):
        self.assertTrue(_sh('dt_file_mtime /bin/bash', "/bin/bash").isdigit())


@requires_bash()
class Bash32Gate(unittest.TestCase):
    def _run(self, root: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(GATE), root], capture_output=True, text=True)

    def test_shipped_scripts_are_clean(self):
        r = self._run(str(REPO_ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_gate_catches_bash4_features(self):
        for line in ("declare -A m", "mapfile -t a < f", "x=${v,,}", "local -n r=x"):
            with self.subTest(line=line), tempfile.TemporaryDirectory() as d:
                (Path(d) / "scripts").mkdir()
                (Path(d) / "scripts" / "bad.sh").write_text(f"#!/bin/bash\nf() {{\n  {line}\n}}\n")
                self.assertEqual(self._run(d).returncode, 1)


if __name__ == "__main__":
    unittest.main()
