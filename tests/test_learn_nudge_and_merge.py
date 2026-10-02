"""The `/devteam:learn` nudge and `/devteam:merge` worktree finalization stay reachable.

The nudge has one canonical home, `commands/merge.md` § Step 4. It must fire when the marker's
recorded HEAD differs from the working branch tip — an "is not an ancestor" test never fires once
commits land. `/devteam:learn` must write the marker after its own auto-commit, with wall-clock time.
`/devteam:merge` must read the worktree session through the main checkout root, because the file is
untracked there and a linked worktree cannot see it by a relative path.
"""

import unittest

from devteam_support import REPO_ROOT

COMMANDS = REPO_ROOT / "commands"


def _read(name):
    return (COMMANDS / f"{name}.md").read_text(encoding="utf-8")


class LearnNudgeTests(unittest.TestCase):
    def test_no_command_uses_the_ancestor_condition(self):
        for name in ("merge", "pr", "refactor", "audit"):
            with self.subTest(command=name):
                self.assertNotIn("not an ancestor", _read(name))

    def test_merge_step_4_compares_marker_hash_to_branch_tip(self):
        body = _read("merge")
        step4 = body[body.index("## Step 4"):body.index("## Step 5")]
        self.assertIn(".learn-last-run", step4)
        self.assertIn("differs from the working branch tip", step4)

    def test_other_finalizers_delegate_to_merge_step_4(self):
        for name in ("pr", "refactor", "audit"):
            with self.subTest(command=name):
                self.assertIn("`commands/merge.md` § Step 4", _read(name))

    def test_learn_writes_marker_after_auto_commit_with_wall_clock(self):
        body = _read("learn")
        step5 = body.index("## Step 5")
        marker = body.index("> .dev-team-agents/.learn-last-run")
        self.assertGreater(marker, step5)
        self.assertNotIn("%ct", body)
        self.assertIn("$(date +%s) $(git rev-parse HEAD", body)


class MergeWorktreeTests(unittest.TestCase):
    def test_session_file_is_resolved_through_main_checkout_before_branches(self):
        body = _read("merge")
        common = body.index("git rev-parse --git-common-dir")
        session = body.index('"$ROOT/.dev-team-agents/.worktree-session"')
        branch = body.index("git branch --show-current")
        self.assertLess(common, session)
        self.assertLess(session, branch)

    def test_flags_are_stripped_from_the_target(self):
        self.assertIn("strip every `--flag` from `$ARGUMENTS`", _read("merge"))


if __name__ == "__main__":
    unittest.main()
