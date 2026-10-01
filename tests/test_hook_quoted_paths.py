"""Hooks hand file paths to inline python as argv, never as source text.

`open('$PREFS_FILE')` pasted a shell path into python source: a project under a
directory with a `'` in its name made the snippet a syntax error, so the hook silently
fell back to defaults (language `en`, no suppression, no auto-update) — and a crafted
path could run code. These tests put a quote in every path the hooks read.
"""

import json
import os
import subprocess
import unittest

from devteam_support import REPO_ROOT, StoreTestCase, requires_bash

SESSION_START = REPO_ROOT / "scripts" / "hooks" / "session-start.sh"
UPDATE_CHECK_LIB = REPO_ROOT / "scripts" / "hooks" / "lib" / "update-check.sh"
QUOTED = "it's-mine"


@requires_bash()
class QuotedPathTest(StoreTestCase):
    def test_session_start_reads_preferences_under_a_quoted_project_path(self):
        root = self.new_project(QUOTED)
        user_data = root / ".dev-team-agents" / "user-data"
        user_data.mkdir(parents=True, exist_ok=True)
        (user_data / "preferences.json").write_text(json.dumps({"language": "pt-BR"}), encoding="utf-8")
        result = subprocess.run(
            ["bash", str(SESSION_START)], cwd=str(root), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=dict(os.environ), check=True,
        )
        self.assertIn("Language: pt-BR", result.stdout.decode())

    def run_lib(self, call, *args):
        result = subprocess.run(
            ["bash", "-c", 'source "$1"; shift; ' + call, "_", str(UPDATE_CHECK_LIB), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ), check=False,
        )
        return result.returncode, result.stdout.decode().strip()

    def quoted_prefs(self, prefs):
        folder = self.tmp / QUOTED
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "preferences.json"
        path.write_text(json.dumps(prefs), encoding="utf-8")
        return path

    def test_uc_read_pref_reads_a_quoted_path_and_keeps_its_default(self):
        path = self.quoted_prefs({"update_check_interval_hours": 6})
        self.assertEqual(self.run_lib('uc_read_pref "$1" update_check_interval_hours 24', str(path)), (0, "6"))
        self.assertEqual(self.run_lib('uc_read_pref "$1" missing_key 24', str(path)), (0, "24"))

    def test_uc_auto_update_enabled_reads_a_quoted_path(self):
        path = self.quoted_prefs({"auto_update": True})
        code, _ = self.run_lib('uc_auto_update_enabled "$1" "$2"', str(path), str(self.tmp / "no-user-data"))
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
