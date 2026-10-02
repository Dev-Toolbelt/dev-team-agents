"""The on-demand update check behind /devteam:update (v2 installs) and `update.sh --check`.

Both used to exec a PreToolUse hook that had been renamed away, so the check failed and
/devteam:update, reading "no output" as "up to date", reported an outdated project as
current. Each case runs a throwaway install tree with a fake `curl` first on PATH.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash

FAKE_CURL = """#!/usr/bin/env bash
# Answers like curl for uc_fetch_latest: -o <body> -w <status> <url>, or -fsSL <url>.
[ -n "${FAKE_TAG:-}" ] || exit 7
body='{"tag_name": "'"$FAKE_TAG"'"}'
out=""
while [ $# -gt 0 ]; do
    case "$1" in -o) out="$2"; shift ;; esac
    shift
done
if [ -n "$out" ]; then printf '%s' "$body" > "$out"; printf '200'; else printf '%s' "$body"; fi
"""


@requires_bash()
class CheckUpdatesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.install = self.tmp / ".dev-team-agents"
        for rel in ["scripts/check-updates.sh", "scripts/update.sh", "scripts/lib/state.sh",
                    "scripts/hooks/lib/update-check.sh"]:
            (self.install / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / rel, self.install / rel)
        (self.install / "user-data").mkdir()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(FAKE_CURL)
        curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
        self.env = dict(os.environ, PATH="{}:{}".format(bin_dir, os.environ["PATH"]))

    def installed(self, version):
        (self.install / "user-data" / "state.json").write_text(json.dumps({"installed_version": version}))

    def check(self, latest=None, *, via_update=False):
        env = dict(self.env)
        env.pop("FAKE_TAG", None)
        if latest is not None:
            env["FAKE_TAG"] = latest
        script = ["scripts/update.sh", "--check"] if via_update else ["scripts/check-updates.sh"]
        result = subprocess.run(["bash", str(self.install / script[0]), *script[1:]],
                                cwd=self.tmp, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_a_newer_release_is_reported_on_one_line(self):
        self.installed("2.48.0")
        self.assertEqual(self.check("v2.49.0"), "Update available: 2.48.0 → 2.49.0\n")

    def test_up_to_date_prints_nothing(self):
        self.installed("2.48.0")
        self.assertEqual(self.check("v2.48.0"), "")

    def test_an_install_ahead_of_the_release_prints_nothing(self):
        self.installed("2.49.0-dev.1")
        self.assertEqual(self.check("v2.48.0"), "")

    def test_no_answer_from_github_is_never_reported_as_up_to_date(self):
        self.installed("2.48.0")
        self.assertTrue(self.check(None).startswith("Could not check for updates:"))

    def test_an_unknown_installed_version_is_never_reported_as_up_to_date(self):
        self.assertTrue(self.check("v2.49.0").startswith("Could not check for updates:"))

    def test_update_sh_check_runs_the_same_check(self):
        self.installed("2.48.0")
        self.assertEqual(self.check("v2.49.0", via_update=True), "Update available: 2.48.0 → 2.49.0\n")


if __name__ == "__main__":
    unittest.main()
