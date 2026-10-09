"""`/devteam:commit` runs `/devteam:learn` silently, before grouping, as part of the commit.

The learn pass must sit before Step 3 so the docs it writes are grouped and committed with the
work, must ask nothing (`--embedded`, never a plan approval), and the run marker must be written
only by the commit, after its commits — a pre-commit HEAD in the marker made a later commit skip
learn. Every learn.md step that prints, asks or writes the marker must name its `--embedded`
exception: an exception stated once in Step 1 loses to a later, more specific step. The guards
that replace the approval live in one place, `feature-learn` § Embedded Commit Capture.
"""

import unittest

from devteam_support import REPO_ROOT

COMMANDS = REPO_ROOT / "commands"
FEATURE_LEARN = REPO_ROOT / "skills" / "shared" / "feature-learn" / "SKILL.md"
SECTION = "§ Embedded Commit Capture"


def _read(name):
    return (COMMANDS / f"{name}.md").read_text(encoding="utf-8")


def _between(body, start, end):
    return body[body.index(start):body.index(end, body.index(start))]


def _line_with(body, needle):
    return next(line for line in body.splitlines() if needle in line)


class CommitEmbeddedLearnTests(unittest.TestCase):
    def setUp(self):
        self.commit = _read("commit")

    def test_learn_runs_embedded_before_grouping(self):
        step = _between(self.commit, "## Step 2.7", "## Step 3")
        self.assertIn("/devteam:learn --embedded", step)
        self.assertIn("Generating learn for this work before committing", step)
        self.assertIn(SECTION, step)
        self.assertNotIn("Awaiting your approval", step)

    def test_no_learn_pass_after_the_commits(self):
        self.assertNotIn("Auto knowledge capture", self.commit)

    def test_marker_is_settled_after_finalize_rebase_and_only_on_a_commit(self):
        step5 = _between(self.commit, "## Step 5", "## $ARGUMENTS")
        finalize = step5.index("worktree finalize action")
        settle = step5.index("If Step 2.7 ran")
        self.assertLess(finalize, settle)
        self.assertIn("when no commit was made", step5[settle:])
        self.assertIn("before a worktree teardown", step5[settle:])

    def test_commit_delegates_the_marker_format(self):
        self.assertNotIn("echo \"$(date +%s)", self.commit)

    def test_skip_learn_is_documented(self):
        self.assertIn("`--skip-learn`", _between(self.commit, "## $ARGUMENTS", "| `format"))
        self.assertIn("--skip-learn", self.commit.splitlines()[2])


class LearnEmbeddedExceptionTests(unittest.TestCase):
    def setUp(self):
        self.learn = _read("learn")

    def test_flag_delegates_to_the_canonical_section(self):
        self.assertIn("| `--embedded` |", self.learn)
        self.assertIn(SECTION, _between(self.learn, "## Step 1", "## Step 2"))

    def test_every_print_ask_or_marker_step_names_the_exception(self):
        for needle in (
            "**`--auto`**",
            "If **nothing to update** was determined",
            "### Spawn conditionally (only if reuse rule candidates",
            "set status to `Accepted`",
            "4. Record the run marker",
            "Then output a summary",
        ):
            with self.subTest(step=needle):
                self.assertIn("--embedded", _line_with(self.learn, needle))


class EmbeddedCaptureContractTests(unittest.TestCase):
    def setUp(self):
        skill = FEATURE_LEARN.read_text(encoding="utf-8")
        self.section = _between(skill, "## Embedded Commit Capture", "## Nothing to Promote")

    def test_learn_side_never_asks_and_never_writes_the_marker(self):
        self.assertIn("Never calls `AskUserQuestion`", self.section)
        self.assertIn("Never written by learn", self.section)
        self.assertIn("`Proposed`", self.section)

    def test_commit_side_guards_are_present(self):
        for guard in (
            "git write-tree",
            "git check-ignore -q",
            "docs/development/",
            "gitleaks protect --staged",
            "git restore --staged",
            "**Added by learn**",
            "git rev-parse --git-common-dir",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, self.section)


if __name__ == "__main__":
    unittest.main()
