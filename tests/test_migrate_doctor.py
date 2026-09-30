"""v2 -> v3 migration, and the diagnostics that reconcile identity."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from devteam_support import StoreTestCase

from devteam import bind, doctor, migrate, project, registry, versions
from devteam.errors import ConflictError, UsageError


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

    def _install_sh_project(self, name="installed"):
        """A v2 install as `install.sh` left it: no bind ever ran, so no manifest.

        `_legacy_project` builds its tree with a vendored bind, whose manifest outlives
        the unbind — and a later bind prunes whatever that manifest names, removing the
        very tree a real v2 project keeps. Deleting it reproduces what users have.
        """
        root = self._legacy_project(name)
        bind.manifest_file(project.load(root)["project_id"]).unlink()
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
        # Two pointers, not one: layout 2 splits a project's own state into a
        # machine-local directory (`state-dir`) and a portable one (`memory-dir`),
        # and the bind this migration performs writes both (ADR-0013).
        self.assertEqual(
            sorted(p.name for p in (root / project.PROJECT_DIR).iterdir()),
            ["memory-dir", "plugins", "project.json", "resolved", "scripts", "state-dir", "templates", "user-data"],
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

    def test_plan_names_the_committed_v2_links_before_any_bind(self):
        # Before a bind there is no manifest; the plan reads the committed link
        # targets from git instead, so the untrack list is complete up front.
        root = self._install_sh_project()
        preview = migrate.plan(root)
        self.assertIn(".claude/agents/dev-team", preview["git_tracked_artifacts"])
        self.assertTrue(all(not p.startswith(".dev-team-agents/") for p in preview["git_tracked_artifacts"]))

    def test_apply_lists_the_bind_artifacts_git_still_tracks(self):
        root = self._legacy_project()
        result = migrate.apply(root)
        self.assertIn(".claude/agents/dev-team", result["git_tracked_artifacts"])


class BindOverV2Test(StoreTestCase):
    """A bind run straight over a v2 install — the path a user took before `bind` refused it.

    `bind` adopted the old relative links and left the vendored tree in git; `doctor`
    then reported `status: ok`, because its v2 check only ran without `project.json`.
    """

    def setUp(self):
        super().setUp()
        self.install_version("3.0.0", activate=True)

    _git_env = staticmethod(MigrationTest._git_env)
    _legacy_project = MigrationTest._legacy_project
    _install_sh_project = MigrationTest._install_sh_project

    def _bound_over_v2(self):
        """What a bind over v2 left before it was refused: real v2 trees plus a bind.

        Built by binding with the two runtime trees moved aside and putting them back
        afterwards — a bind today refuses to link over them, which is the point.
        """
        root = self._install_sh_project("bound-over-v2")
        install_dir = root / project.PROJECT_DIR
        parked = {}
        for name in bind.RUNTIME_TREES:
            if not (install_dir / name).exists():
                # A tree v2's installer never shipped (`plugins/`, ADR-0019).
                continue
            parked[name] = install_dir.parent / ("parked-" + name)
            (install_dir / name).rename(parked[name])
        bind.bind(root, provider_names=["claude"], mode="link")
        for name, path in parked.items():
            (install_dir / name).unlink()
            path.rename(install_dir / name)
        return root

    def test_the_bind_command_refuses_a_v2_install_and_points_at_migrate(self):
        root = self._install_sh_project()
        code, out, _ = self.run_cli("--json", "bind", str(root), "--provider", "claude", "--mode", "link")
        self.assertEqual(code, 4)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertIn("devteam migrate", payload["hint"])
        self.assertIsNone(project.load(root) and registry.get(project.load(root)["project_id"]))

    def test_the_bind_command_still_accepts_an_explicit_vendored_bind(self):
        root = self._install_sh_project()
        code, _, err = self.run_cli("bind", str(root), "--provider", "claude", "--mode", "vendored")
        self.assertEqual(code, 0, err)

    def test_sync_refuses_a_project_bound_over_v2_and_points_at_migrate(self):
        # The runtime links live where the v2 trees still are. Linking beside them is
        # impossible, and leaving them would run the hooks from the old v2 scripts —
        # so sync refuses with the one command that clears the way.
        root = self._bound_over_v2()
        project_id = project.load(root)["project_id"]
        with self.assertRaises(ConflictError) as caught:
            bind.sync_project(project_id)
        self.assertIn("devteam migrate", caught.exception.hint)
        # Nothing of the user's was touched.
        self.assertFalse((root / project.PROJECT_DIR / "scripts").is_symlink())

    def test_doctor_reports_the_leftover_tree_after_a_bind(self):
        root = self._bound_over_v2()
        report = doctor.run(project_root=root)
        leftover = [f for f in report["findings"] if f["category"] == "project" and f["level"] == "warn"]
        self.assertTrue(leftover, report["findings"])
        self.assertIn("devteam migrate", leftover[0]["hint"])

    def test_doctor_reports_tracked_artifacts_with_the_exact_untrack_command(self):
        root = self._bound_over_v2()
        report = doctor.run(project_root=root)
        tracked = [f for f in report["findings"] if f["category"] == "bind" and "tracked by git" in f["message"]]
        self.assertEqual(len(tracked), 1, report["findings"])
        self.assertIn("git rm -r --cached", tracked[0]["hint"])
        self.assertIn(".claude/agents/dev-team", tracked[0]["hint"])
        # The project's own settings file is merged into, not owned: never untracked.
        self.assertNotIn(".claude/settings.json", tracked[0]["hint"])

    def test_a_vendored_bind_is_neither_a_leftover_nor_a_tracking_problem(self):
        root = self.new_project("vendored-by-choice")
        bind.bind(root, provider_names=["claude"], mode="vendored")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        report = doctor.run(project_root=root)
        messages = [f["message"] for f in report["findings"] if f["level"] != "ok"]
        self.assertFalse(any("v2 vendored install" in m or "tracked by git" in m for m in messages), messages)

    def test_migrate_json_shapes_are_exact_for_plan_and_apply(self):
        # Pinned here until the app consumes `migrate` (roadmap phase 2); at that point
        # these two sets move into `test_json_contract.AppFacingKeySetContractTest`.
        root = self._install_sh_project()
        code, out, err = self.run_cli("--json", "migrate", str(root), "--provider", "claude")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            set(json.loads(out)) - {"ok"},
            {"path", "detected", "providers", "mode", "actions", "git_tracked",
             "git_tracked_artifacts", "preserved"},
        )
        code, out, err = self.run_cli("--json", "migrate", str(root), "--provider", "claude", "--apply")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            set(json.loads(out)) - {"ok"},
            {"path", "project_id", "version", "mode", "providers", "quarantined",
             "quarantine_dir", "git_tracked", "git_tracked_artifacts", "preserved", "unrecognised"},
        )

    def test_a_clean_link_bind_reports_no_tracked_artifacts(self):
        root = self.new_project("clean")
        bind.bind(root, provider_names=["claude"], mode="link")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, stdout=subprocess.DEVNULL)
        manifest = bind.read_manifest(project.load(root)["project_id"])
        self.assertEqual(bind.tracked_artifacts(root, manifest), [])


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

    def test_a_hostile_pin_in_the_registry_is_a_finding_not_an_abort(self):
        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        project_id = bind.bind(root, provider_names=["claude"])["project_id"]
        registry.set_pin(project_id, "../../elsewhere")
        report = doctor.run(project_root=root)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(f["category"] == "bind" for f in report["findings"]))

    def test_the_hook_finding_counts_every_registered_dispatcher(self):
        from devteam import hooks

        self.install_version("3.0.0", activate=True)
        root = self.new_project()
        bind.bind(root, provider_names=["claude"])
        report = doctor.run(project_root=root)
        message = [f["message"] for f in report["findings"] if f["category"] == "hooks"][0]
        self.assertTrue(message.startswith("{} dispatchers".format(len(hooks.EVENTS))), message)

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

    def _project_findings(self, root):
        report = doctor.run(project_root=root)
        return [f for f in report["findings"] if f["category"] == "project"]

    def test_an_unbound_v2_vendored_install_points_at_migrate(self):
        # No `devteam bind` was ever run here — just the vendored tree a v2
        # install leaves under `.dev-team-agents/`, same as `migrate.detect`
        # itself recognises. `devteam bind` cannot fold this in; only
        # `devteam migrate` knows to quarantine it instead of clobbering it.
        root = self.new_project("vendored")
        install_dir = root / project.PROJECT_DIR
        (install_dir / "agents").mkdir(parents=True)
        (install_dir / "agents" / "backend-developer.md").write_text(
            "# agent\n", encoding="utf-8"
        )
        findings = self._project_findings(root)
        self.assertTrue(findings)
        self.assertIn("devteam migrate", findings[0]["hint"])

    def test_a_pre_root_install_points_at_the_root_migration_script(self):
        # The shape `scripts/migrate-to-root.sh` targets: the framework still
        # sitting at `.claude/dev-team-agents/` instead of the project root.
        root = self.new_project("prerooted")
        (root / ".claude" / "dev-team-agents").mkdir(parents=True)
        findings = self._project_findings(root)
        self.assertTrue(findings)
        self.assertIn("migrate-to-root.sh", findings[0]["hint"])

    def test_a_directory_with_no_legacy_shape_still_gets_the_bind_hint(self):
        root = self.new_project("fresh")
        findings = self._project_findings(root)
        self.assertTrue(findings)
        self.assertIn("devteam bind", findings[0]["hint"])


if __name__ == "__main__":
    unittest.main()
