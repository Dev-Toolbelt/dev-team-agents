"""The session-start update check's version comparison and message.

A plain string inequality used to decide there was an update: a local build ahead of
the release was offered a downgrade, and a project on the release was offered an
"update" to it, because the tag carries a "v" the stored version does not.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

LIB = REPO_ROOT / "scripts" / "hooks" / "lib" / "update-check.sh"

# macOS ships bash 3.2 as /bin/bash, and the hooks must run on it; test it too when present.
SHELLS = ["bash"] + (["/bin/bash"] if os.path.exists("/bin/bash") else [])


def bash(script, *args, shell="bash"):
    return subprocess.run(
        [shell, "-c", '. "$0"; ' + script, str(LIB), *args],
        capture_output=True, text=True, check=False,
    )


@requires_bash()
class IsNewerTest(unittest.TestCase):
    def is_newer(self, current, latest):
        answers = {bash('uc_is_newer "$1" "$2"', current, latest, shell=sh).returncode == 0 for sh in SHELLS}
        self.assertEqual(len(answers), 1, "shells disagree on {} vs {}".format(current, latest))
        return answers.pop()

    def test_a_newer_release_is_an_update(self):
        for current, latest in [
            ("2.48.0", "v2.49.0"),
            ("2.48.9", "v2.48.10"),
            ("2.9.0", "v2.10.0"),
            ("2.99.99", "v3.0.0"),
            ("2.48.0-rc1", "v2.48.1"),
            ("2.08.0", "v2.9.0"),
            ("2.48.0+build.7", "v2.48.1"),
        ]:
            with self.subTest(current=current, latest=latest):
                self.assertTrue(self.is_newer(current, latest))

    def test_the_same_version_is_not_an_update_with_or_without_the_v(self):
        for current, latest in [("2.48.0", "v2.48.0"), ("2.48.0", "2.48.0"), ("v2.48.0", "v2.48.0"), ("2.48.0", "v02.048.00")]:
            with self.subTest(current=current, latest=latest):
                self.assertFalse(self.is_newer(current, latest))

    def test_an_install_ahead_of_the_release_is_never_offered_a_downgrade(self):
        for current, latest in [("2.48.900", "v2.48.0"), ("3.0.0", "v2.99.99"), ("2.10.0", "v2.9.0")]:
            with self.subTest(current=current, latest=latest):
                self.assertFalse(self.is_newer(current, latest))

    def test_an_unparseable_version_raises_nothing(self):
        for current, latest in [
            ("unknown", "v2.48.0"),
            ("2.48.0", "garbage"),
            ("2.48", "v2.49.0"),
            ("", "v2.49.0"),
            ("2.48.0", "v2.49.0.1"),
            ("2.48.0", "v99999999999999999999.0.0"),
        ]:
            with self.subTest(current=current, latest=latest):
                self.assertFalse(self.is_newer(current, latest))

    def test_a_pre_release_suffix_is_ignored_like_versions_parse_semver(self):
        self.assertFalse(self.is_newer("2.48.0-rc1", "v2.48.0"))

    def test_a_hostile_version_never_reaches_arithmetic_evaluation(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        marker = tmp / "pwned"
        for hostile in ["a[$(touch {})]".format(marker), "1.2.3[$(touch {})]".format(marker), "1.2.$(touch {})".format(marker)]:
            with self.subTest(hostile=hostile):
                self.assertFalse(self.is_newer("2.48.0", hostile))
                self.assertFalse(self.is_newer(hostile, "v2.49.0"))
        self.assertFalse(marker.exists())

    def test_a_strict_mode_caller_is_not_aborted_and_nothing_leaks(self):
        for sh in SHELLS:
            with self.subTest(shell=sh):
                out = bash('set -euo pipefail; uc_is_newer 2.48.900 v2.48.0 || true; '
                           'uc_is_newer x y || true; echo "ok:${major-unset}:${c1-unset}"', shell=sh).stdout
                self.assertEqual(out.strip(), "ok:unset:unset")


@requires_bash()
class MessageTest(unittest.TestCase):
    def test_both_versions_are_shown_without_the_v(self):
        out = bash('uc_message available en "$1" "$2"', "2.48.0", "v2.49.0").stdout
        self.assertIn("2.48.0 → 2.49.0", out)


if __name__ == "__main__":
    unittest.main()
