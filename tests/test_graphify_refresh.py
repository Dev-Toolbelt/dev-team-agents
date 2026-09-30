"""`scripts/graphify-refresh.sh` — when it rebuilds, and where it records the build.

The build marker lives in `graphify-out/.build-commit`, next to the graph it
describes, so every checkout — the main one and each linked worktree — has its own.
A marker shared through the main checkout's `state.json` let one worktree's build
stand in for another's, and the main checkout then skipped a rebuild it needed.

`graphify` itself is stubbed: it counts its runs and writes a minimal output tree,
which is all the script inspects.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devteam_support import REPO_ROOT, requires_bash, rmtree

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@e",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@e",
}

GRAPHIFY_STUB = """#!/bin/sh
echo run >> "$GRAPHIFY_RUNS"
mkdir -p "$2/graphify-out"
echo '{}' > "$2/graphify-out/graph.json"
"""


@requires_bash()
@unittest.skipUnless(shutil.which("jq") and shutil.which("rsync"), "graphify-refresh.sh needs jq and rsync")
class GraphifyRefreshTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="graphify-refresh-"))
        self.addCleanup(rmtree, self.tmp, True)
        self.runs = self.tmp / "runs"
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "graphify"
        stub.write_text(GRAPHIFY_STUB, encoding="utf-8")
        stub.chmod(0o755)
        self.env = dict(os.environ, **GIT_ENV)
        self.env["PATH"] = "{}{}{}".format(bin_dir, os.pathsep, self.env["PATH"])
        self.env["GRAPHIFY_RUNS"] = str(self.runs)
        for inherited in ("STATE_FILE", "USER_DATA_DIR"):
            self.env.pop(inherited, None)

        self.main = self.tmp / "main"
        (self.main / "src").mkdir(parents=True)
        (self.main / "src" / "a.txt").write_text("a\n", encoding="utf-8")
        user_data = self.main / ".dev-team-agents" / "user-data"
        user_data.mkdir(parents=True)
        # No manifestPaths: the empty array must not trip `set -u` on bash 3.2.
        (user_data / "graphify.json").write_text('{"targetPaths": ["src"]}\n', encoding="utf-8")
        (self.main / ".dev-team-agents" / "scripts").symlink_to(REPO_ROOT / "scripts")
        (self.main / ".gitignore").write_text(".dev-team-agents/scripts\n", encoding="utf-8")
        self.git(self.main, "init", "-q", ".")
        self.git(self.main, "add", "-A")
        self.git(self.main, "commit", "-qm", "init")

    def git(self, cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=str(cwd), env=self.env, check=True, capture_output=True, text=True
        ).stdout.strip()

    def refresh(self, cwd):
        script = Path(cwd) / ".dev-team-agents" / "scripts" / "graphify-refresh.sh"
        result = subprocess.run(
            ["bash", str(script)], cwd=str(cwd), env=self.env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def build_count(self):
        return len(self.runs.read_text().splitlines()) if self.runs.exists() else 0

    def marker(self, root):
        return (Path(root) / "graphify-out" / ".build-commit").read_text().strip()

    def commit_file(self, root, name):
        (Path(root) / "src" / name).write_text(name, encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "add " + name)

    def test_first_build_records_head_next_to_the_graph(self):
        self.refresh(self.main)

        self.assertEqual(self.build_count(), 1)
        self.assertEqual(self.marker(self.main), self.git(self.main, "rev-parse", "HEAD"))
        # Nothing is written to state.json any more.
        self.assertFalse((self.main / ".dev-team-agents" / "user-data" / "state.json").exists())

    def test_no_structural_change_skips_the_rebuild(self):
        self.refresh(self.main)
        (self.main / "src" / "a.txt").write_text("edited\n", encoding="utf-8")
        self.git(self.main, "commit", "-qam", "edit, not structural")

        self.refresh(self.main)

        self.assertEqual(self.build_count(), 1)

    def test_a_worktree_build_does_not_stand_in_for_the_main_checkout(self):
        self.refresh(self.main)
        worktree = self.tmp / "wt"
        self.git(self.main, "worktree", "add", "-q", str(worktree), "-b", "feature")
        (worktree / ".dev-team-agents" / "user-data").mkdir(parents=True, exist_ok=True)
        shutil.copy(
            self.main / ".dev-team-agents" / "user-data" / "graphify.json",
            worktree / ".dev-team-agents" / "user-data" / "graphify.json",
        )
        (worktree / ".dev-team-agents" / "scripts").symlink_to(REPO_ROOT / "scripts")
        self.commit_file(worktree, "new.txt")

        self.refresh(worktree)
        self.assertEqual(self.build_count(), 2)

        # The main checkout gets the same structural change in a commit of its own.
        self.commit_file(self.main, "new.txt")
        self.refresh(self.main)

        self.assertEqual(self.build_count(), 3, "the main checkout's graph never saw new.txt")
        self.assertEqual(self.marker(worktree), self.git(worktree, "rev-parse", "HEAD"))
        self.assertEqual(self.marker(self.main), self.git(self.main, "rev-parse", "HEAD"))

    def test_a_legacy_state_json_marker_is_honoured_in_the_main_checkout(self):
        self.refresh(self.main)
        head = self.git(self.main, "rev-parse", "HEAD")
        (self.main / "graphify-out" / ".build-commit").unlink()
        (self.main / ".dev-team-agents" / "user-data" / "state.json").write_text(
            '{{"graphify_last_run": "{}"}}\n'.format(head), encoding="utf-8"
        )

        self.refresh(self.main)

        self.assertEqual(self.build_count(), 1, "an up-to-date legacy marker must not force a rebuild")


if __name__ == "__main__":
    unittest.main()
