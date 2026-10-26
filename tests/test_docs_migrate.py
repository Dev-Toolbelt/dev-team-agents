"""scripts/docs-migrate.py — the opt-in `development` → `gated` docs migration (ADR-0045)."""

import datetime
import json
import os
import subprocess
import sys
import unittest

from devteam_support import REPO_ROOT, StoreTestCase

SCRIPT = REPO_ROOT / "scripts" / "docs-migrate.py"
PROJECT_ID = "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10"
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@e")

DEV_FILES = {
    "docs/development/database.md": "# Database\n\nSee [architecture](architecture.md) and [ADR 1](adrs/0001-use-x.md).\n",
    "docs/development/architecture.md": "# Architecture\n\nSchema in [db](database.md).\n",
    "docs/development/adrs/0001-use-x.md": "# 1. Use X\n\nBack to [db](../database.md).\n",
    "docs/development/adrs/README.md": "# ADRs\n\n| ADR | Status |\n|---|---|\n| [0001](0001-use-x.md) | Accepted |\n",
    "docs/backlog/dod.md": "# Definition of Done\n\n## Code\n- [ ] Reviewed\n",
    "docs/backlog/sprints/sprints.md": "# Sprints\n\n| Scope | Sprint |\n|---|---|\n| a | [sprint-1](a-sprint-1.md) |\n",
    "docs/backlog/sprints/a-sprint-1.md": "# Sprint 1\n",
    "docs/backlog/README.md": "# Backlog\n\n## Tracker\nNone\n",
    "docs/project.md": "# Project\n\nData model: [db](development/database.md).\n",
    "CLAUDE.md": "# Rules\n\nRead docs/development/database.md and docs/development/adrs/ first.\n",
}


class DocsMigrateTest(StoreTestCase):
    def make_repo(self, files=None, layout=None, name="app"):
        root = self.tmp / name
        root.mkdir()
        data = {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"], "layout": 2}
        if layout:
            data["docs_layout"] = layout
        files = dict(DEV_FILES if files is None else files)
        files[".dev-team-agents/project.json"] = json.dumps(data, indent=2) + "\n"
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git(root, "init", "-q", ".")
        self.commit(root)
        return root

    def git(self, root, *args):
        return subprocess.run(["git", *args], cwd=str(root), env=GIT_ENV, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode()

    def commit(self, root):
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "c", "--allow-empty")

    def run_script(self, root, *args):
        done = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=str(root),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def snapshot(self, root):
        return self.git(root, "status", "--porcelain"), self.git(root, "rev-parse", "HEAD")

    def read(self, root, rel):
        return (root / rel).read_text(encoding="utf-8")

    def layout(self, root):
        return json.loads(self.read(root, ".dev-team-agents/project.json")).get("docs_layout")

    # -- plan -----------------------------------------------------------------

    def test_plan_prints_the_plan_and_changes_nothing(self):
        root = self.make_repo()
        before = self.snapshot(root)
        code, out, err = self.run_script(root)
        self.assertEqual(code, 0, out + err)
        self.assertIn("MOVE data-model docs/development/database.md -> docs/data-model.md", out)
        self.assertIn("MOVE adr docs/development/adrs/0001-use-x.md -> docs/adr/0001-use-x.md", out)
        self.assertIn("MERGE dod docs/backlog/dod.md -> docs/backlog.md", out)
        self.assertIn("LINKS CLAUDE.md", out)
        self.assertIn("SUMMARY", out)
        self.assertNotIn("APPLIED", out)
        self.assertEqual(self.snapshot(root), before)
        self.assertIsNone(self.layout(root))
        self.assertFalse((root / "docs/backlog.md").exists())

    # -- apply ----------------------------------------------------------------

    def test_apply_moves_merges_rewrites_and_records_the_layout(self):
        root = self.make_repo()
        code, out, err = self.run_script(root, "apply")
        self.assertEqual(code, 0, out + err)
        self.assertTrue(out.rstrip().endswith("APPLIED"), out)
        self.assertEqual(self.layout(root), "gated")
        project = json.loads(self.read(root, ".dev-team-agents/project.json"))
        self.assertEqual(project["project_id"], PROJECT_ID)
        self.assertEqual(project["layout"], 2)

        self.assertFalse((root / "docs/development/database.md").exists())
        self.assertIn("[ADR 1](adr/0001-use-x.md)", self.read(root, "docs/data-model.md"))
        self.assertIn("[architecture](architecture.md)", self.read(root, "docs/data-model.md"))
        self.assertIn("[db](data-model.md)", self.read(root, "docs/architecture.md"))
        self.assertIn("[db](../data-model.md)", self.read(root, "docs/adr/0001-use-x.md"))
        self.assertTrue((root / "docs/adr/README.md").exists())
        self.assertIn("[db](data-model.md)", self.read(root, "docs/project.md"))
        claude = self.read(root, "CLAUDE.md")
        self.assertIn("docs/data-model.md", claude)
        self.assertIn("docs/adr/", claude)
        self.assertNotIn("docs/development", claude)

        index = self.read(root, "docs/backlog.md")
        for heading in ("# Backlog", "## Definition of Done", "## Definition of Ready", "## Sprints",
                        "## Backlog Notes"):
            self.assertIn(heading, index)
        self.assertIn("### Code", index)
        self.assertIn("- [ ] Reviewed", index)
        self.assertIn("never copied here", index)
        self.assertIn("### Project additions", index)
        self.assertIn("[sprint-1](backlog/sprints/a-sprint-1.md)", index)
        self.assertIn("### Tracker", index)

        for original in ("docs/backlog/dod.md", "docs/backlog/sprints/sprints.md", "docs/backlog/README.md"):
            text = self.read(root, original)
            self.assertIn("Historical — superseded by [backlog.md]", text, original)
        self.assertIn("- [ ] Reviewed", self.read(root, "docs/backlog/dod.md"))
        self.assertIn("docs/development/database.md -> docs/data-model.md", self.git(root, "status", "--porcelain"))
        self.assertEqual(self.git(root, "rev-list", "--count", "HEAD").strip(), "1")

    def test_a_conflict_is_quarantined_and_the_target_untouched(self):
        files = dict(DEV_FILES, **{"docs/data-model.md": "# Existing model\n"})
        root = self.make_repo(files)
        code, out, err = self.run_script(root, "apply")
        self.assertEqual(code, 0, out + err)
        quarantine = "docs/legacy/migration-{}/development/database.md".format(datetime.date.today().isoformat())
        self.assertIn("CONFLICT data-model docs/development/database.md -> docs/data-model.md", out)
        self.assertEqual(self.read(root, "docs/data-model.md"), "# Existing model\n")
        self.assertIn("# Database", self.read(root, quarantine))
        self.assertIn("migration-", self.read(root, "docs/architecture.md"))

    # -- refusals -------------------------------------------------------------

    def assert_refused(self, root, *args, reason=""):
        before = self.snapshot(root)
        code, out, err = self.run_script(root, *(args or ("apply",)))
        self.assertEqual(code, 1, out + err)
        self.assertIn("REFUSE", out)
        self.assertIn(reason, out)
        self.assertEqual(self.snapshot(root), before)
        return out

    def test_a_dirty_tree_is_refused(self):
        root = self.make_repo()
        (root / "docs/project.md").write_text("# Edited\n", encoding="utf-8")
        self.assert_refused(root, reason="dirty")

    def test_an_already_gated_project_is_refused(self):
        root = self.make_repo(layout="gated")
        self.assert_refused(root, reason="already 'gated'")

    def test_an_unbound_project_is_refused(self):
        root = self.make_repo()
        self.git(root, "rm", "-q", ".dev-team-agents/project.json")
        self.commit(root)
        self.assert_refused(root, reason="not a bound project")

    def test_a_tracked_symlink_anywhere_in_scope_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "rc").write_text("secret\n", encoding="utf-8")
        cases = {
            "dangling docs/backlog.md": ("docs/backlog.md", str(outside / "profile")),
            "dod.md to a file outside": ("docs/backlog/dod.md", str(outside / "rc")),
            "CLAUDE.md": ("CLAUDE.md", str(outside / "rc")),
            "AGENTS.md": ("AGENTS.md", str(outside / "rc")),
        }
        for name, (rel, target) in cases.items():
            with self.subTest(name):
                files = {k: v for k, v in DEV_FILES.items() if k != rel}
                root = self.make_repo(files, name=name.replace(" ", "-").replace("/", "-"))
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(target, str(root / rel))
                self.commit(root)
                self.assert_refused(root, "plan", reason="symlink")
                self.assert_refused(root, "apply", reason="symlink")
                self.assertFalse((outside / "profile").exists())
                self.assertEqual((outside / "rc").read_text(encoding="utf-8"), "secret\n")
                self.assertIsNone(self.layout(root))

    def test_an_ignored_symlinked_docs_dir_is_refused(self):
        outside = self.tmp / "elsewhere"
        (outside / "development").mkdir(parents=True)
        files = {"CLAUDE.md": "# Rules\n", ".gitignore": "docs\n"}
        root = self.make_repo(files)
        os.symlink(str(outside), str(root / "docs"))
        self.assert_refused(root, "plan", reason="symlink")

    def test_an_untracked_claude_md_is_reported_not_rewritten(self):
        files = {k: v for k, v in DEV_FILES.items() if k != "CLAUDE.md"}
        files[".gitignore"] = "CLAUDE.md\n"
        root = self.make_repo(files)
        text = "See docs/development/database.md\n"
        (root / "CLAUDE.md").write_text(text, encoding="utf-8")
        code, out, err = self.run_script(root, "apply")
        self.assertEqual(code, 0, out + err)
        self.assertIn("UNTRACKED CLAUDE.md", out)
        self.assertEqual(self.read(root, "CLAUDE.md"), text)

    # -- set-layout -----------------------------------------------------------

    def test_set_layout_keeps_every_other_key(self):
        root = self.make_repo()
        code, out, err = self.run_script(root, "set-layout", "gated")
        self.assertEqual(code, 0, out + err)
        data = json.loads(self.read(root, ".dev-team-agents/project.json"))
        self.assertEqual(data, {"schema": 1, "project_id": PROJECT_ID, "context_paths": ["docs"],
                                "layout": 2, "docs_layout": "gated"})
        if os.name == "posix":  # Windows reports 0o666 for every writable file
            self.assertEqual(os.stat(str(root / ".dev-team-agents/project.json")).st_mode & 0o777, 0o644)
        self.assertEqual([p.name for p in (root / ".dev-team-agents").iterdir()], ["project.json"])

    def test_set_layout_rejects_an_unknown_value(self):
        root = self.make_repo()
        before = self.read(root, ".dev-team-agents/project.json")
        code, _, err = self.run_script(root, "set-layout", "flat")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)
        self.assertEqual(self.read(root, ".dev-team-agents/project.json"), before)

    def test_set_layout_refuses_an_unbound_project(self):
        (self.tmp / "bare").mkdir()
        code, out, _ = self.run_script(self.tmp / "bare", "set-layout", "gated")
        self.assertEqual(code, 1)
        self.assertIn("REFUSE", out)


if __name__ == "__main__":
    unittest.main()
