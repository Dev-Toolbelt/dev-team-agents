"""The session-start banner reports the account state and never gates (ADR-0029 SR-30).

A fail-closed hook locks a user out of their own editor on the first bug, so the hook only
informs: it reads the cache, never the network, and never exits non-zero because of the account.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth_support import AuthTestCase  # noqa: E402
from devteam_support import REPO_ROOT, requires_bash  # noqa: E402

SESSION_START = REPO_ROOT / "scripts" / "hooks" / "session-start.sh"


@requires_bash()
class AccountBannerTest(AuthTestCase):
    def hook(self, **env):
        root = self.new_project("banner")
        return subprocess.run(
            ["bash", str(SESSION_START)], cwd=str(root), capture_output=True, text=True,
            env=dict(os.environ, **env), timeout=120,
        )

    def account_line(self, result):
        lines = [line for line in result.stdout.splitlines() if line.startswith("Account: ")]
        self.assertEqual(len(lines), 1, result.stdout)
        return lines[0]

    def test_signed_out_is_reported_and_the_hook_still_succeeds(self):
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("signed out", self.account_line(result))

    def test_signed_in_is_reported_from_the_cache_without_touching_the_network(self):
        self.sign_in()
        before = len(self.idp.calls)
        self.idp.stop()
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(self.account_line(result), r"signed in|trial ends in")
        self.assertEqual(len(self.idp.calls), before)

    def test_a_signed_in_hook_makes_no_request_even_while_the_server_is_up(self):
        self.sign_in()
        before = len(self.idp.calls)
        self.hook()
        self.assertEqual(len(self.idp.calls), before)

    def test_a_broken_account_setup_never_fails_the_session(self):
        result = self.hook(DEVTEAM_AUTH_TEST_URL="https://example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_the_banner_still_prints_when_python_cannot_import_the_package(self):
        result = self.hook(PYTHONPATH="/nonexistent", DEVTEAM_PYTHON="/nonexistent/python")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[DEVTEAM:SESSION_BANNER]", result.stdout)


if __name__ == "__main__":
    unittest.main()
