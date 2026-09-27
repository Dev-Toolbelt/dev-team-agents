"""v2 -> v3 migration, and the diagnostics that reconcile identity."""

import shutil
import subprocess
import unittest
from pathlib import Path

from devteam_support import StoreTestCase

from devteam import bind, doctor, migrate, project, registry, versions
from devteam.errors import UsageError


class MigrationTest(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    def _legacy_project(self, name="legacy"):
        """A project that looks exactly like a v2 vendored install."""
        root = self.new_project(name)
        bind.bind(root, provider_names=["claude"], mode="vendored")
        memory = root / project.PROJECT_DIR / "user-data"
        memory.mkdir(parents=True, exist_ok=True)
        (memory / "session-summary.md").write_text("## old entry\n", encoding="utf-8")
        (root / "docs" / "note.md").write_text("project knowledge\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        subprocess.run(
            ["git", "commit", "-qm", "install"],
            cwd=str(root),
            check=True,
            stdout=subprocess.DEVNULL,
            env=self._git_env(),
        )
        bind.unbind(root, keep_artifacts=True)
        return root

    @staticmethod
    def _git_env():
        import os

        return dict(
            os.environ,
            GIT_AUTHOR_NAME="t",
            GIT_AUTHOR_EMAIL="t@e",
            GIT_COMMITTER_NAME="t",
            GIT_COMMITTER_EMAIL="t@e",
        )

    def test_detect_recognises_a_vendored_install(self):
        root = self._legacy_project()
        found = migrate.detect(root)
        self.assertTrue(found["is_v2"])
        self.assertIn("agents", found["vendored_trees"])
        self.assertTrue(found["has_user_data"])

    def test_plan_changes_nothing_on_disk(self):
        root = self._legacy_project()
        before = sorted(p.name for p in (root / project.PROJECT_DIR).iterdir())
        preview = migrate.plan(root)
        after = sorted(p.name for p in (root / project.PROJECT_DIR).iterdir())
        self.assertEqual(before, after)
        self.assertTrue(any("quarantine" in action for action in preview["actions"]))

    def test_plan_reports_git_tracked_paths(self):
        root = self._legacy_project()
        preview = migrate.plan(root)
        self.assertIn(".dev-team-agents/agents", preview["git_tracked"])

    def test_plan_refuses_a_project_that_was_never_installed(self):
        root = self.new_project("fresh")
        with self.assertRaises(UsageError):
            migrate.plan(root)

    def test_apply_preserves_memory_and_knowledge_and_quarantines_the_tree(self):
        root = self._legacy_project()
        result = migrate.apply(root)

        memory = root / project.PROJECT_DIR / "user-data" / "session-summary.md"
        self.assertEqual(memory.read_text(encoding="utf-8"), "## old entry\n")
        self.assertEqual(
            (root / "docs" / "note.md").read_text(encoding="utf-8"), "project knowledge\n"
        )
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["core", "project.json", "resolved", "state-dir", "user-data"],
        )
        moved = {item["from"] for item in result["quarantined"]}
        self.assertIn(".dev-team-agents/agents", moved)
        for item in result["quarantined"]:
            self.assertTrue(Path(item["to"]).exists(), item["to"])

    def test_apply_rebinds_against_the_store(self):
        root = self._legacy_project()
        result = migrate.apply(root)
        link = root / ".claude" / "agents" / "dev-team"
        self.assertTrue(link.exists())
        self.assertEqual(registry.get(result["project_id"])["path"], str(root.resolve()))
        self.assertEqual(result["version"], "3.0.0")

    def test_apply_reports_the_git_removal_instead_of_doing_it(self):
        root = self._legacy_project()
        result = migrate.apply(root)
        self.assertTrue(result["git_tracked"])
        still_tracked = subprocess.run(
            ["git", "ls-files", ".dev-team-agents/agents"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.decode()
        self.assertIn(".dev-team-agents/agents", still_tracked)


class DoctorTest(StoreTestCase):
    def test_reports_an_empty_store_as_a_failure(self):
        report = doctor.run(project_root=None)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(f["category"] == "store" for f in report["findings"]))

    def test_healthy_bind_reports_ok(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "ok")

    def test_missing_artifacts_are_a_warning_pointing_at_sync(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        shutil.rmtree(str(root / ".claude" / "agents" / "dev-team"), ignore_errors=True)
        (root / ".claude" / "agents" / "dev-team").unlink(missing_ok=True)
        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "warn")
        self.assertTrue(any("sync" in (f.get("hint") or "") for f in report["findings"]))

    def test_a_moved_project_is_reconciled_by_identity(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project("before-move")
        result = bind.bind(root, provider_names=["claude"])
        moved = self.tmp / "after-move"
        shutil.move(str(root), str(moved))

        report = doctor.run(project_root=moved)
        self.assertTrue(any(a["action"] == "relocated" for a in report["actions"]))
        self.assertEqual(registry.get(result["project_id"])["path"], str(moved.resolve()))
        self.assertEqual(len(registry.entries()), 1)

    def test_the_same_identity_at_two_live_paths_is_reported_not_merged(self):
        self.install_version("3.0.0", activate=True)
        original = self.new_project("origin")
        result = bind.bind(original, provider_names=["claude"])
        fork = self.tmp / "fork"
        shutil.copytree(str(original), str(fork), symlinks=True)

        report = doctor.run(project_root=fork)
        self.assertEqual(report["status"], "fail")
        collision = [f for f in report["findings"] if f["category"] == "identity"]
        self.assertTrue(collision)
        self.assertIn("two paths", collision[0]["message"])
        # Nothing was merged or re-pointed.
        self.assertEqual(registry.get(result["project_id"])["path"], str(original.resolve()))

    def test_reassign_identity_resolves_the_fork_case(self):
        self.install_version("3.0.0", activate=True)
        original = self.new_project("origin")
        bind.bind(original, provider_names=["claude"])
        fork = self.tmp / "fork"
        shutil.copytree(str(original), str(fork), symlinks=True)

        before = project.load(fork)["project_id"]
        doctor.run(project_root=fork, reassign_identity=True)
        after = project.load(fork)["project_id"]
        self.assertNotEqual(before, after)
        bind.bind(fork, provider_names=["claude"])
        self.assertEqual(len(registry.entries()), 2)

    def test_stale_pointer_to_an_uninstalled_version_is_a_failure(self):
        self.install_version("3.0.0", activate=True)
        shutil.rmtree(str(versions.version_dir("3.0.0")))
        report = doctor.run(project_root=None)
        self.assertEqual(report["status"], "fail")


if __name__ == "__main__":
    unittest.main()
